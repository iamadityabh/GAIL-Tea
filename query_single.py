import json
import streamlit as st
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
1. DIRECT ANSWERS: If the user asks a specific question, answer ONLY that specific question cleanly and directly.
2. FULL PROFILE: ONLY IF the user asks for a general overview, provide a well-structured summary.
3. ABSOLUTE TRUTH: The STRUCTURED DATABASE RECORD (JSON) is the latest data for basic info (phone_no, age, position, etc.). 
4. NO AUTOCORRECT: Even if a value in the JSON looks fake, incomplete, or like a typo (e.g., '100' for a phone number), YOU MUST USE THE JSON VALUE EXACTLY. 

User Question: {question}
--- STRUCTURED DATABASE RECORD (JSON) ---
{sql_json_data}
--- UNSTRUCTURED PDF DATA ---
{rag_data}
Response:
""")

extractor_chain = extractor_prompt | extractor_llm
synthesizer_chain = synthesizer_prompt | chat_llm

def handle_single_profile(user_question, current_mem_key):
    status_box = st.status("🛠️ Backend Terminal Logs (Click to expand)", expanded=True)
    
    with status_box:
        st.write("⚡ **1. Extracting Clues...**")
        try:
            clues_response = extractor_chain.invoke({"question": user_question})
            raw_clues = json.loads(clues_response.content)
            clues = {"name": None, "department": None, "position": None, "project_phase": None, "tech_stack": None}
            for k, v in raw_clues.items():
                if str(k).lower() in clues: clues[str(k).lower()] = v
            bad_words = ["employees", "employee", "people", "staff", "all", "list", "everyone", "who", "what"]
            if clues['name'] and clues['name'].lower() in bad_words: clues['name'] = None
            st.write("🔍 **Clues found (JSON):**")
            st.json(clues) 
        except Exception as e:
            st.error(f"❌ Error extracting clues: {e}")
            st.stop()

        if not any(clues.values()):
            error_msg = "Please provide an employee name, department, or position to search."
            st.warning(error_msg)
            st.session_state[current_mem_key].append({"role": "assistant", "content": error_msg})
            st.stop()
            
        sql_json_data = ""
        rag_data = "No document info required for this query."
        final_emp_id = None
        error_reply = None

        with engine.connect() as conn:
            st.write("🗄️ **2. Searching Database...**")
            base_query = """
                SELECT e.employee_id, e.employee_name, e.age, e.phone_no, e.position, d.department_name, j.metadata 
                FROM employees e 
                LEFT JOIN departments d ON e.dept_id = d.department_id
                LEFT JOIN employee_json j ON e.employee_id = j.employee_id
                WHERE 1=1
            """
            conditions, params = [], {}
            if clues.get('name'): conditions.append("e.employee_name ILIKE :name"); params['name'] = f"%{clues['name']}%"
            if clues.get('department'): conditions.append("d.department_name ILIKE :dept"); params['dept'] = f"%{clues['department']}%"
            if clues.get('position'): conditions.append("e.position ILIKE :pos"); params['pos'] = f"%{clues['position']}%"
            
            if conditions: base_query += " AND " + " AND ".join(conditions)

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
                    st.write("📄 **Raw SQL JSON passed to LLM:**")
                    st.json(record)
                    
                    if final_emp_id:
                        rag_query = text("SELECT document_type, chunk_text FROM employee_vectors WHERE employee_id = :emp_id")
                        rag_result = conn.execute(rag_query, {"emp_id": final_emp_id}).fetchall()
                        if rag_result:
                            rag_data = "\n".join([f"[{row[0]}] {row[1]}" for row in rag_result])
                            st.write(f"├── ✅ Found PDF/RAG Data ({len(rag_result)} chunks).")

            except Exception as e:
                st.error(f"├── ⚠️ SQL Error: {e}")
                st.stop()

    status_box.update(label="✅ Backend Processing Complete", state="complete", expanded=False)

    if error_reply:
        st.markdown(error_reply)
        st.session_state[current_mem_key].append({"role": "assistant", "content": error_reply})
    else:
        stream = synthesizer_chain.stream({"question": user_question, "sql_json_data": sql_json_data, "rag_data": rag_data})
        full_response = st.write_stream((chunk.content for chunk in stream))
        st.session_state[current_mem_key].append({"role": "assistant", "content": full_response})

# query_single.py ke end mein ye function append kar dena:
def handle_single_profile_api(user_question: str) -> str:
    # 1. Exact purani logic se raw variables parse karo
    clues_response = extractor_chain.invoke({"question": user_question})
    raw_clues = json.loads(clues_response.content)
    
    clues = {"name": None, "department": None, "position": None, "project_phase": None, "tech_stack": None}
    for k, v in raw_clues.items():
        if str(k).lower() in clues: clues[str(k).lower()] = v
        
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
        if clues.get('name'): conditions.append("e.employee_name ILIKE :name"); params['name'] = f"%{clues['name']}%"
        if clues.get('department'): conditions.append("d.department_name ILIKE :dept"); params['dept'] = f"%{clues['department']}%"
        if clues.get('position'): conditions.append("e.position ILIKE :pos"); params['pos'] = f"%{clues['position']}%"
        
        if conditions: base_query += " AND " + " AND ".join(conditions)
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
    final_response = synthesizer_chain.invoke({"question": user_question, "sql_json_data": sql_json_data, "rag_data": rag_data})
    return final_response.content