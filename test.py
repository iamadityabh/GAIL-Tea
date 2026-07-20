"""
test.py — GARIS Model Evaluation Harness
==========================================
Standalone evaluator for the LLM-driven components of GARIS
(extraction, single-profile synthesis, overall/department synthesis,
event synthesis). Uses ONE real employee, ALL departments, and ONE
event as fixed "golden" context, so no live DB connection is needed.

Usage
-----
    # Test whichever backend config.py currently points to (Groq by default)
    python test.py

    # Force-test a specific backend, bypassing config.py
    python test.py --backend groq
    python test.py --backend ollama --ollama-model qwen2.5:7b-instruct

    # Compare both back to back in one run
    python test.py --backend both --ollama-model qwen2.5:7b-instruct

Add / edit TEST CASES in the "TEST CASES" section below to expand coverage.
"""

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from langchain_core.prompts import PromptTemplate

# ==========================================================================
# 0. GOLDEN DATA  (from your real employees / departments / company_events)
# ==========================================================================

EMPLOYEE_SQL_JSON = {
    "employee_id": "101",
    "employee_name": "Aditya Bhardwaj",
    "age": 20,
    "phone_no": "8130543451",
    "position": "Intern",
    "department": "Human Resources",
    "project": {
        "project_name": "AI-powered chatbot system",
        "description": "Automate routine departmental tasks and improve information accessibility for employees",
        "tech_stack": ["AI", "NLP", "Backend services", "Frontend development", "Database connectivity"],
        "project_phases_names": [
            "Requirement Analysis", "System Design", "Development and Integration",
            "Testing and Bug Resolution", "Deployment with Performance Monitoring",
        ],
        "current_phase": "Development and Integration",
        "pros_of_project": "Reducing time spent handling repetitive queries, improving information accessibility",
        "cons_of_project": "N/A",
    },
    "mentorship": {"mentor_name": "Ms. Neha Sharma", "mentor_position": "Assistant Manager (IT)"},
    "hr_observations": {
        "performance_and_feedback": "Gaining valuable hands-on experience in AI applications, NLP, "
                                     "software development practices, system integration, and project management"
    },
    "custom_attributes": {
        "project_team_size": "5",
        "deployment_environment": "Internal network",
        "integration_with_existing_systems": "Yes",
    },
    "skills_and_achievements": {
        "skills": ["AI", "NLP", "Software development practices", "System integration", "Project management"],
        "certifications": ["N/A"],
    },
}

# Real unstructured PDF/resume chunk — deliberately kept verbatim, this is what
# ingest.py would have stored as an employee_vectors chunk_text. Note it says
# "Software Intern" while the structured record above says "Intern" — a real
# conflict already present in your data, used to test rule #5 (conflicting info).
EMPLOYEE_RAG_CHUNK = """
GAIL(India)Limited
SoftwareIntern May2026–Present
- DevelopingaGenAIchatbotleveragingRAGandLLMagentsfordynamicdataretrieval.
- ImplementAgenticAIworkflowstoautomatereal-timedatabaseupdatesandeliminatedatastaleness.
Skills: Python,C,C++,SQL,MySQL,PL/SQL,Flask,TensorFlow,Scikit-Learn,OpenCV,NumPy,Pandas
"""

DEPARTMENTS_JSON = [
    {"department_id": "1", "department_name": "Human Resources", "head_name": "Mr. Ram Nath Kashyap", "landline_ext": "4001"},
    {"department_id": "2", "department_name": "Engineering", "head_name": "Mr. Rajeev Kumar", "landline_ext": "4002"},
    {"department_id": "3", "department_name": "Sales & Marketing", "head_name": "Mr. Amit Singh", "landline_ext": "4003"},
    {"department_id": "4", "department_name": "IT Support", "head_name": "Ms. Priya Desai", "landline_ext": "4004"},
    {"department_id": "5", "department_name": "Finance", "head_name": "Mr. Vikram Malhotra", "landline_ext": "4005"},
]

EVENT_JSON = [{
    "event_id": "EV1",
    "event_name": "Summer Internship Orientation 2026",
    "event_date": "2026-06-10",
    "location": "GAIL Training Institute Auditorium",
    "description": "Welcome newly joined interns and familiarize them with the institute's policies, code of "
                    "conduct, training schedule, project allocation process, attendance rules, and safety guidelines.",
}]

# ==========================================================================
# 1. REAL PROMPTS  (copied verbatim from query_single.py / query_overall.py / query_events.py)
# ==========================================================================

extractor_prompt = PromptTemplate.from_template("""
You are a highly logical HR Entity Extractor. Extract specific entities mentioned in the user's query about an employee.
CRITICAL RULES FOR VALUES:
1. "name": Extract ONLY a specific person's name. NEVER extract generic words.
2. "department", "position": Extract ONLY actual organizational roles or departments.
3. "project_phase": Extract ONLY if the user mentions an actual lifecycle state.
4. "tech_stack": Extract ONLY actual software/technology names.
Return ONLY a valid JSON object with EXACTLY these lowercase keys:
{{"name": null, "department": null, "position": null, "project_phase": null, "tech_stack": null}}

User Question: {question}
""")

synthesizer_prompt = PromptTemplate.from_template("""
You are a highly efficient, professional, and precise HR Assistant.

CRITICAL RULES:

1. DIRECT ANSWERS:
If the user asks a specific question, answer ONLY that specific question directly and naturally.
Prefer a simple conversational sentence or short paragraph.
Do NOT unnecessarily use headings, bullet points, numbered lists, or question-answer format.

2. FULL PROFILE:
ONLY IF the user asks for a general overview, profile, summary, or complete details, provide a clean and well-structured summary. Use formatting only when it genuinely improves readability.

3. STRUCTURED DATABASE DATA:
The STRUCTURED DATABASE RECORD (JSON) contains the latest structured database information for basic fields such as phone number, age, position, department, etc.

4. NO AUTOCORRECT:
Even if a value in the JSON looks fake, incomplete, unusual, or like a typo (for example, '100' as a phone number), use the value EXACTLY as provided. Never correct or modify stored values.

5. CONFLICTING INFORMATION:
Compare the STRUCTURED DATABASE RECORD with the UNSTRUCTURED PDF DATA.
If the same information is present in both sources but the values conflict, clearly mention BOTH values and their respective sources in a natural sentence.

Example:
The structured database lists Aditya's position as **Engineer**, while the PDF records mention his position as **Senior Engineer**.

Do not use a separate conflict section or bullet list unless there are multiple conflicting fields.

6. PRESENTATION:
Write responses naturally, like a professional HR assistant communicating with a user.
For simple questions, use one or two concise sentences.
Use Markdown bold only for important values when useful.
Use headings and bullet points only for detailed profiles, summaries, or responses containing multiple distinct pieces of information.
Never display raw JSON, embeddings, vector data, internal database fields, or technical metadata.

7. DATA GROUNDING:
Use ONLY information available in the STRUCTURED DATABASE RECORD and UNSTRUCTURED PDF DATA.
Do not invent or assume missing information.
If the requested information is unavailable in both sources, simply state that it is not available.

User Question: {question}

--- STRUCTURED DATABASE RECORD (JSON) ---
{sql_json_data}

--- UNSTRUCTURED PDF DATA ---
{rag_data}

Response:
""")

overall_prompt = PromptTemplate.from_template("""
You are a highly efficient, professional, and precise HR Assistant answering team-wide, department-wide, or list-based queries.

CRITICAL RULES:

1. DIRECT ANSWERS:
Answer ONLY what the user has explicitly asked.
Do NOT provide extra employee or department details unless they are directly relevant to the question.

2. DEPARTMENT DATA:
For questions about department names, department heads, or landline numbers, use the COMPANY DEPARTMENTS JSON as the primary structured source.

3. CONFLICTING INFORMATION:
If the same information appears with different values in COMPANY DEPARTMENTS and EMPLOYEES DATA, do NOT silently choose one or hide the conflict.
Clearly mention BOTH values and identify their respective sources in a natural sentence.

Example:
The Company Departments record lists the department head as **Amit Sharma**, while the employee data mentions **Rahul Verma**.

Do not mention conflicts when the information is not actually contradictory.

4. NO DATA MIXING:
Never mix or combine the skills, projects, roles, personal details, or other information of one employee with another.
Always ensure that information belongs to the correct employee.

5. PRESENTATION:
Respond naturally, like a professional HR assistant.
For simple questions, use a concise sentence or short paragraph.
If the user asks for multiple employees, departments, projects, or other list-based information, use bullet points only when it improves readability.
Do NOT unnecessarily use headings, numbered sections, bullet points, or question-answer format.
For detailed summaries or large results, organize the information clearly and professionally.
Use Markdown bold sparingly for important names or values when useful.

6. DATA ACCURACY:
Use values exactly as they appear in the provided data.
Do not autocorrect, modify, assume, or fabricate information, even if a value appears unusual or incorrect.

7. MISSING DATA:
If the requested information is unavailable in the provided data, simply say:
"I don't have that information."

8. DATA GROUNDING:
Base your answer ONLY on the provided COMPANY DEPARTMENTS and EMPLOYEES DATA.
Do not use external knowledge or make assumptions.

User Question: {question}

--- COMPANY DEPARTMENTS (JSON) ---
{departments_json}

--- EMPLOYEES DATA (JSON ARRAY) ---
{sql_json_data}

Response:
""")

event_prompt = PromptTemplate.from_template("""
You are an expert HR Assistant answering queries about company events.
Below is a JSON array containing data for one or more relevant company events.

CRITICAL RULES:
1. STRICT PRECISION (CRUCIAL): Provide ONLY the information explicitly requested by the user. 
   - If the user asks for just a list (e.g., "list all events", "names of events"), ONLY provide the names. DO NOT dump dates, locations, or descriptions.
   - If the user asks for details (e.g., "tell me about event X", "details of upcoming events"), THEN provide full detailed profiles.
2. NO HALLUCINATION: Answer ONLY based on the provided event data. 
3. MISSING DATA: If the data does not contain the answer, strictly say "I don't have that information about the event."
4. EMPTY CATEGORIES: Do not list empty statuses or categories unless specifically asked.

Presentation Rules:
- Present information in clean Markdown.
- Use bullet points for lists.
- Never dump raw database fields (e.g., use "Start Date" instead of "event_start_date").
- ONLY IF providing detailed profiles for multiple events, create a separate subsection for each event.
- Keep responses concise, professional, and easy to read.

User Question: {question}

--- RELEVANT EVENT DATA (JSON) ---
{event_data}

Answer cleanly:
""")

# ==========================================================================
# 2. BACKEND SELECTION
# ==========================================================================

def build_llms(backend: str, ollama_model: str):
    """Returns (extractor_llm, chat_llm) for the requested backend."""
    if backend == "groq":
        from langchain_groq import ChatGroq
        extractor_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0,
                                  model_kwargs={"response_format": {"type": "json_object"}})
        chat_llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3)
        return extractor_llm, chat_llm

    if backend == "ollama":
        from langchain_ollama import ChatOllama
        extractor_llm = ChatOllama(model=ollama_model, temperature=0, format="json")
        chat_llm = ChatOllama(model=ollama_model, temperature=0.3)
        return extractor_llm, chat_llm

    if backend == "config":
        from config import get_llms
        return get_llms()

    raise ValueError(f"Unknown backend: {backend}")


# ==========================================================================
# 3. SCORING HELPERS
# ==========================================================================

def contains_all(text: str, keywords) -> bool:
    t = text.lower()
    return all(k.lower() in t for k in keywords)

def contains_any(text: str, keywords) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in keywords)

def not_contains(text: str, keywords) -> bool:
    t = text.lower()
    return all(k.lower() not in t for k in keywords)

def word_count_under(text: str, limit: int) -> bool:
    return len(text.split()) <= limit


# ==========================================================================
# 4. TEST CASES
# ==========================================================================

@dataclass
class ExtractionCase:
    name: str
    question: str
    expected: dict  # only keys that matter are checked

@dataclass
class SynthCase:
    name: str
    kind: str  # "single" | "overall" | "event"
    question: str
    check: Callable[[str], bool]
    check_desc: str

EXTRACTION_CASES = [
    ExtractionCase("name_only", "What is Aditya Bhardwaj's phone number?",
                    {"name": "Aditya Bhardwaj"}),
    ExtractionCase("department_only", "List all employees in the Human Resources department.",
                    {"name": None, "department": "Human Resources"}),
    ExtractionCase("project_phase", "Who is currently in the Testing and Bug Resolution phase?",
                    {"project_phase": "Testing and Bug Resolution"}),
    ExtractionCase("tech_stack", "Which employees are working with NLP?",
                    {"tech_stack": "NLP"}),
    ExtractionCase("no_entities", "How many employees do we have in total?",
                    {"name": None, "department": None, "position": None,
                     "project_phase": None, "tech_stack": None}),
]

SYNTH_CASES = [
    SynthCase("phone_number_exact", "single", "What is Aditya Bhardwaj's phone number?",
              lambda a: contains_all(a, ["8130543451"]),
              "answer contains the exact phone number from structured data"),

    SynthCase("position_conflict", "single", "What is Aditya Bhardwaj's position at GAIL?",
              lambda a: contains_any(a, ["Intern"]) and contains_any(a, ["Software Intern", "SoftwareIntern"]),
              "answer surfaces BOTH conflicting position values (Intern vs Software Intern)"),

    SynthCase("mentor_lookup", "single", "Who is Aditya's mentor?",
              lambda a: contains_all(a, ["Neha Sharma"]),
              "answer contains mentor name from structured data"),

    SynthCase("no_hallucination", "single", "What is Aditya's blood group?",
              lambda a: contains_any(a, ["not available", "don't have", "do not have", "no information", "unavailable"]),
              "answer honestly states the info is unavailable, does not invent a blood group"),

    SynthCase("dept_head_lookup", "overall", "Who is the head of the IT Support department?",
              lambda a: contains_all(a, ["Priya Desai"]),
              "answer contains correct department head from departments JSON"),

    SynthCase("dept_landline", "overall", "What is the landline extension for the Finance department?",
              lambda a: contains_all(a, ["4005"]),
              "answer contains correct landline extension"),

    SynthCase("dept_list_names_only", "overall", "List all department names.",
              lambda a: contains_all(a, ["Human Resources", "Engineering", "Sales", "IT Support", "Finance"])
                        and not_contains(a, ["4001", "4002", "4003", "4004", "4005"]),
              "answer lists all 5 department names WITHOUT dumping landline extensions (precision rule)"),

    SynthCase("event_datetime_location", "event", "When and where is the summer internship orientation?",
              lambda a: contains_any(a, ["June 10", "10 June", "2026-06-10", "10th June"])
                        and contains_any(a, ["Auditorium"]),
              "answer contains correct event date AND location"),

    SynthCase("event_list_names_only", "event", "List all events.",
              lambda a: contains_all(a, ["Summer Internship Orientation"])
                        and not_contains(a, ["2026-06-10", "June 10", "Auditorium"]),
              "answer lists ONLY event name, not date/location (strict precision rule)"),

    SynthCase("event_missing_info", "event", "How many people registered for the orientation?",
              lambda a: contains_any(a, ["don't have that information", "do not have that information"]),
              "answer uses the exact required fallback phrase for missing event info"),
]


# ==========================================================================
# 5. RUNNER
# ==========================================================================

@dataclass
class Result:
    category: str
    name: str
    passed: bool
    latency: float
    detail: str = ""

def run_extraction_tests(extractor_llm, results: list):
    chain = extractor_prompt | extractor_llm
    for case in EXTRACTION_CASES:
        t0 = time.time()
        try:
            resp = chain.invoke({"question": case.question})
            latency = time.time() - t0
            raw = resp.content.strip()
            # strip accidental markdown fences
            raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
            parsed = json.loads(raw)
            ok = True
            mismatches = []
            for k, expected_v in case.expected.items():
                got_v = parsed.get(k, "<missing>")
                if expected_v is None:
                    match = got_v in (None, "null", "")
                else:
                    match = isinstance(got_v, str) and expected_v.lower() in got_v.lower()
                if not match:
                    ok = False
                    mismatches.append(f"{k}: expected~{expected_v!r} got={got_v!r}")
            detail = "OK" if ok else "; ".join(mismatches)
            results.append(Result("extraction", case.name, ok, latency, detail))
        except json.JSONDecodeError as e:
            results.append(Result("extraction", case.name, False, time.time() - t0, f"INVALID JSON: {e}"))
        except Exception as e:
            results.append(Result("extraction", case.name, False, time.time() - t0, f"ERROR: {e}"))

def run_synth_tests(chat_llm, results: list):
    single_chain = synthesizer_prompt | chat_llm
    overall_chain = overall_prompt | chat_llm
    event_chain = event_prompt | chat_llm

    for case in SYNTH_CASES:
        t0 = time.time()
        try:
            if case.kind == "single":
                resp = single_chain.invoke({
                    "question": case.question,
                    "sql_json_data": json.dumps(EMPLOYEE_SQL_JSON, indent=2),
                    "rag_data": EMPLOYEE_RAG_CHUNK,
                })
            elif case.kind == "overall":
                resp = overall_chain.invoke({
                    "question": case.question,
                    "departments_json": json.dumps(DEPARTMENTS_JSON, indent=2),
                    "sql_json_data": json.dumps([EMPLOYEE_SQL_JSON], indent=2),
                })
            elif case.kind == "event":
                resp = event_chain.invoke({
                    "question": case.question,
                    "event_data": json.dumps(EVENT_JSON, indent=2),
                })
            else:
                raise ValueError(case.kind)

            latency = time.time() - t0
            answer = resp.content
            ok = case.check(answer)
            detail = case.check_desc if ok else f"FAILED check: {case.check_desc} | answer='{answer[:200]}...'"
            results.append(Result(f"synthesis:{case.kind}", case.name, ok, latency, detail))
        except Exception as e:
            results.append(Result(f"synthesis:{case.kind}", case.name, False, time.time() - t0, f"ERROR: {e}"))


# ==========================================================================
# 6. REPORTING
# ==========================================================================

def print_report(backend_label: str, results: list):
    print("\n" + "=" * 78)
    print(f" RESULTS — backend: {backend_label}")
    print("=" * 78)

    by_cat = {}
    for r in results:
        by_cat.setdefault(r.category, []).append(r)

    total_pass, total = 0, 0
    for cat, rs in by_cat.items():
        passed = sum(1 for r in rs if r.passed)
        total_pass += passed
        total += len(rs)
        avg_lat = sum(r.latency for r in rs) / len(rs)
        print(f"\n[{cat}]  {passed}/{len(rs)} passed   avg latency {avg_lat:.2f}s")
        for r in rs:
            status = "PASS" if r.passed else "FAIL"
            print(f"  [{status}] {r.name}  ({r.latency:.2f}s)")
            if not r.passed:
                print(f"           -> {r.detail}")

    print("\n" + "-" * 78)
    pct = (total_pass / total * 100) if total else 0
    print(f" TOTAL: {total_pass}/{total} passed ({pct:.1f}%)")
    print("-" * 78)
    return total_pass, total


def save_json_report(backend_label: str, results: list, path: str):
    payload = {
        "backend": backend_label,
        "results": [r.__dict__ for r in results],
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
        },
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"\nSaved detailed JSON report -> {path}")


# ==========================================================================
# 7. MAIN
# ==========================================================================

def run_for_backend(backend: str, ollama_model: str):
    print(f"\nBuilding models for backend='{backend}'"
          + (f" (ollama model={ollama_model})" if backend == "ollama" else "") + " ...")
    extractor_llm, chat_llm = build_llms(backend, ollama_model)

    results = []
    run_extraction_tests(extractor_llm, results)
    run_synth_tests(chat_llm, results)

    label = ollama_model if backend == "ollama" else backend
    passed, total = print_report(label, results)
    save_json_report(label, results, f"eval_report_{label.replace(':', '_')}.json")
    return label, passed, total


def main():
    parser = argparse.ArgumentParser(description="Evaluate GARIS LLM components against golden test data.")
    parser.add_argument("--backend", choices=["config", "groq", "ollama", "both"], default="config",
                         help="Which backend to test. 'config' uses whatever config.py currently returns. "
                              "'both' runs groq AND ollama back to back for comparison.")
    parser.add_argument("--ollama-model", default="qwen2.5:7b-instruct",
                         help="Ollama model tag to use when --backend=ollama or both.")
    args = parser.parse_args()

    summary = []
    if args.backend == "both":
        summary.append(run_for_backend("groq", args.ollama_model))
        summary.append(run_for_backend("ollama", args.ollama_model))
    else:
        summary.append(run_for_backend(args.backend, args.ollama_model))

    if len(summary) > 1:
        print("\n" + "=" * 78)
        print(" COMPARISON")
        print("=" * 78)
        for label, passed, total in summary:
            pct = (passed / total * 100) if total else 0
            print(f"  {label:30s}  {passed}/{total} passed ({pct:.1f}%)")


if __name__ == "__main__":
    sys.exit(main())
