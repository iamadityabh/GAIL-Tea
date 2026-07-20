import json
import sys
from sqlalchemy import text
from langchain_core.prompts import PromptTemplate
from config import get_db_engine, get_llms

engine = get_db_engine()
extractor_llm, chat_llm = get_llms()

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

extractor_chain = extractor_prompt | extractor_llm
synthesizer_chain = synthesizer_prompt | chat_llm


def handle_single_profile(user_question, chat_history=None):
    """
    Replaced 'current_mem_key' with a 'chat_history' list parameter to replace st.session_state.
    Pass a list here if you want to maintain conversation history.
    """
    if chat_history is None:
        chat_history = []

    print("\n🛠️ Backend Terminal Logs:")
    print("⚡ 1. Extracting Clues...")
    
    try:
        clues_response = extractor_chain.invoke({"question": user_question})
        raw_clues = json.loads(clues_response.content)
        clues = {"name": None, "department": None, "position": None, "project_phase": None, "tech_stack": None}
        
        for k, v in raw_clues.items():
            if str(k).lower() in clues: 
                clues[str(k).lower()] = v
                
        bad_words = ["employees", "employee", "people", "staff", "all", "list", "everyone", "who", "what"]
        if clues['name'] and clues['name'].lower() in bad_words: 
            clues['name'] = None
            
        print("🔍 Clues found (JSON):")
        print(json.dumps(clues, indent=2))
        
    except Exception as e:
        print(f"❌ Error extracting clues: {e}")
        return

    if not any(clues.values()):
        error_msg = "Please provide an employee name, department, or position to search."
        print(f"⚠️ Warning: {error_msg}")
        chat_history.append({"role": "assistant", "content": error_msg})
        return error_msg
        
    sql_json_data = ""
    rag_data = "No document info required for this query."
    final_emp_id = None
    error_reply = None

    with engine.connect() as conn:
        print("🗄️ 2. Searching Database...")
        base_query = """
            SELECT e.employee_id, e.employee_name, e.age, e.phone_no, e.position, d.department_name, j.metadata 
            FROM employees e 
            LEFT JOIN departments d ON e.dept_id = d.department_id
            LEFT JOIN employee_json j ON e.employee_id = j.employee_id
            WHERE 1=1
        """
        conditions, params = [], {}
        if clues.get('name'): 
            conditions.append("e.employee_name ILIKE :name")
            params['name'] = f"%{clues['name']}%"
        if clues.get('department'): 
            conditions.append("d.department_name ILIKE :dept")
            params['dept'] = f"%{clues['department']}%"
        if clues.get('position'): 
            conditions.append("e.position ILIKE :pos")
            params['pos'] = f"%{clues['position']}%"
        
        if conditions: 
            base_query += " AND " + " AND ".join(conditions)

        try:
            results = conn.execute(text(base_query), params).fetchall()
            
            if len(results) == 0:
                error_reply = "I couldn't find any employees matching those criteria."
            elif len(results) > 1:
                names = [f"{r._mapping['employee_name']}" for r in results]
                error_reply = f"I found multiple matching employees: **{', '.join(names)}**. Please be more specific."
            else:
                record = dict(results[0]._mapping)
                final_emp_id = record.pop('employee_id')
                sql_json_data = json.dumps(record, indent=2)
                
                print("📄 Raw SQL JSON passed to LLM:")
                print(sql_json_data)
                
                if final_emp_id:
                    rag_query = text("SELECT document_type, chunk_text FROM employee_vectors WHERE employee_id = :emp_id")
                    rag_result = conn.execute(rag_query, {"emp_id": final_emp_id}).fetchall()
                    if rag_result:
                        rag_data = "\n".join([f"[{row[0]}] {row[1]}" for row in rag_result])
                        print(f"├── ✅ Found PDF/RAG Data ({len(rag_result)} chunks).")

        except Exception as e:
            print(f"├── ⚠️ SQL Error: {e}")
            return

    print("✅ Backend Processing Complete\n")

    if error_reply:
        print(error_reply)
        chat_history.append({"role": "assistant", "content": error_reply})
        return error_reply
    else:
        stream = synthesizer_chain.stream({"question": user_question, "sql_json_data": sql_json_data, "rag_data": rag_data})
        
        # Simulating st.write_stream to standard output
        full_response = ""
        for chunk in stream:
            sys.stdout.write(chunk.content)
            sys.stdout.flush()
            full_response += chunk.content
            
        print() # Add a final newline after the stream ends
        chat_history.append({"role": "assistant", "content": full_response})
        return full_response


def handle_single_profile_api(user_question: str) -> str:
    # 1. Exact purani logic se raw variables parse karo
    clues_response = extractor_chain.invoke({"question": user_question})
    raw_clues = json.loads(clues_response.content)
    
    clues = {"name": None, "department": None, "position": None, "project_phase": None, "tech_stack": None}
    for k, v in raw_clues.items():
        if str(k).lower() in clues: 
            clues[str(k).lower()] = v
        
    if not any(clues.values()):
        return "Please provide an employee name, department, or position to search."

    # 2. Database check
    with engine.connect() as conn:
        base_query = """
            SELECT e.employee_id, e.employee_name, e.age, e.phone_no, e.position, d.department_name, j.metadata 
            FROM employees e 
            LEFT JOIN departments d ON e.dept_id = d.department_id
            LEFT JOIN employee_json j ON e.employee_id = j.employee_id
            WHERE 1=1
        """
        conditions, params = [], {}
        if clues.get('name'): 
            conditions.append("e.employee_name ILIKE :name")
            params['name'] = f"%{clues['name']}%"
        if clues.get('department'): 
            conditions.append("d.department_name ILIKE :dept")
            params['dept'] = f"%{clues['department']}%"
        if clues.get('position'): 
            conditions.append("e.position ILIKE :pos")
            params['pos'] = f"%{clues['position']}%"
        
        if conditions: 
            base_query += " AND " + " AND ".join(conditions)
            
        results = conn.execute(text(base_query), params).fetchall()
        
        if len(results) == 0:
            return "I couldn't find any employees matching those criteria."
        elif len(results) > 1:
            names = [f"{r._mapping['employee_name']}" for r in results]
            return f"I found multiple matching employees: {', '.join(names)}. Please be more specific."
        
        record = dict(results[0]._mapping)
        final_emp_id = record.pop('employee_id')
        sql_json_data = json.dumps(record, indent=2)
        
        rag_data = "No document info required for this query."
        if final_emp_id:
            rag_query = text("SELECT document_type, chunk_text FROM employee_vectors WHERE employee_id = :emp_id")
            rag_result = conn.execute(rag_query, {"emp_id": final_emp_id}).fetchall()
            if rag_result:
                rag_data = "\n".join([f"[{row[0]}] {row[1]}" for row in rag_result])

    # 3. End mein stream karne ke bajay directly invoke karke pure text block return karo
    final_response = synthesizer_chain.invoke({
        "question": user_question, 
        "sql_json_data": sql_json_data, 
        "rag_data": rag_data
    })
    
    return final_response.content