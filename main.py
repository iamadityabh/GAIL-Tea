import json
import os
import streamlit as st
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from sqlalchemy import create_engine, text
from langchain_groq import ChatGroq

# Ingest module functions
from ingest import ingest_single_employee, delete_employee 

# ==========================================
# 0. UI Configuration & Env
# ==========================================
st.set_page_config(page_title="GTI Enterprise HR", page_icon="🏢", layout="wide")
load_dotenv()

if not os.getenv("GROQ_API_KEY"):
    st.error("❌ ERROR: GROQ_API_KEY is missing! Please check your .env file.")
    st.stop()

# ==========================================
# 1. Setup & DB Connection
# ==========================================
@st.cache_resource
def get_db_engine():
    DB_URL = "postgresql+psycopg2://postgres:root@localhost:5432/GTI_2"
    return create_engine(DB_URL)

engine = get_db_engine()

# LLMs
extractor_llm = ChatGroq(
    model="llama-3.1-8b-instant", 
    temperature=0, 
    model_kwargs={"response_format": {"type": "json_object"}} 
)
chat_llm = ChatGroq(
    model="llama-3.1-8b-instant", 
    temperature=0.3
)

# ==========================================
# 2. Prompts Setup
# ==========================================
extractor_prompt = PromptTemplate.from_template("""
You are a highly logical HR Entity Extractor. Extract specific entities mentioned in the user's query about an employee.

CRITICAL RULES FOR VALUES:
1. "name": Extract ONLY a specific person's name. NEVER extract generic words like "employees", "people", "who", "all", or "staff". If no specific name is given, set to null.
2. "department", "position": Extract ONLY actual organizational roles or departments.
3. "project_phase": Extract ONLY if the user mentions an actual lifecycle state.
4. "tech_stack": Extract ONLY actual software/technology names (e.g., "Python", "React", "SQL").
5. If the user is ASKING to see a detail in the output, DO NOT put it as a filter value.

Return ONLY a valid JSON object with EXACTLY these lowercase keys:
{{"name": null, "department": null, "position": null, "project_phase": null, "tech_stack": null}}

User Question: {question}
""")

synthesizer_prompt = PromptTemplate.from_template("""
You are a highly efficient, professional, and precise HR Assistant. 

CRITICAL RULES:
1. DIRECT ANSWERS: If the user asks a specific question (e.g., "Which college?", "What is his phone number?"), answer ONLY that specific question cleanly and directly. DO NOT output the entire profile.
2. FULL PROFILE: ONLY IF the user asks for a general overview (e.g., "Tell me about him", "Give me his profile"), provide a well-structured summary using clean headings (e.g., **Personal Info**, **Education**, etc.) and bullet points.
3. FORMATTING: Never use a robotic Q&A format like "What is his college? Answer: XYZ". State it naturally.
4. ACCURACY: Answer ONLY based on the provided JSON and PDF data. If missing, say "I do not have that information."

User Question: {question}

--- STRUCTURED DATABASE RECORD (JSON) ---
{sql_json_data}

--- UNSTRUCTURED PDF DATA ---
{rag_data}

Response:
""")

extractor_chain = extractor_prompt | extractor_llm
synthesizer_chain = synthesizer_prompt | chat_llm

# ==========================================
# 3. Sidebar Navigation 
# ==========================================
st.sidebar.title("🏢 GTI HR Portal")
st.sidebar.markdown("---")

main_mode = st.sidebar.radio("👉 Select Operation Mode:", ["🔍 Ask a Query", "⚙️ Make Changes"])
st.sidebar.markdown("---")

# ==========================================
# 4. Main Logic Routing
# ==========================================

if main_mode == "⚙️ Make Changes":
    st.title("⚙️ Database Management")
    st.caption("Add, update, or remove records from the company database.")
    
    change_option = st.sidebar.selectbox(
        "Select Category:",
        ["👤 Add/Update Employee Details", "🏢 Add/Update Department Details", "📅 Add/Update Events"]
    )
    
    if change_option == "👤 Add/Update Employee Details":
        st.subheader("Manage Employee Data")
        folder_name = st.text_input("Enter Employee Folder/ID (e.g., 101):").strip()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Ingest Data", use_container_width=True, type="primary"):
                if not folder_name:
                    st.warning("⚠️ Please enter an Employee Folder/ID first.")
                else:
                    with st.spinner(f"Ingesting data for '{folder_name}'..."):
                        result = ingest_single_employee(folder_name)
                        st.success(result.get("message")) if result.get("status") == "success" else st.error(result.get("message"))
                            
        with col2:
            if st.button("🗑️ Delete Employee", use_container_width=True):
                if not folder_name:
                    st.warning("⚠️ Please enter an Employee Folder/ID first.")
                else:
                    with st.spinner(f"Deleting records for '{folder_name}'..."):
                        result = delete_employee(folder_name)
                        st.success(result.get("message")) if result.get("status") == "success" else st.error(result.get("message"))

    elif change_option == "🏢 Add/Update Department Details":
        st.info("Department CRUD operations will go here.")
    elif change_option == "📅 Add/Update Events":
        st.info("Event CRUD operations will go here.")


elif main_mode == "🔍 Ask a Query":
    st.title("🤖 HR Assistant")
    st.caption("Ask questions about employees, teams, or company events.")
    
    query_option = st.sidebar.selectbox(
        "What type of query do you have?",
        ["👤 Single Employee Profile", "📊 Team & Company-wide (Overall)", "📅 Event Related Query"]
    )

    # ---------------------------------------------------------
    # 🔥 INDEPENDENT UI MEMORY (Keeps chat history on screen)
    # ---------------------------------------------------------
    memory_keys = {
        "👤 Single Employee Profile": "mem_single_profile",
        "📊 Team & Company-wide (Overall)": "mem_overall",
        "📅 Event Related Query": "mem_events"
    }
    
    current_mem_key = memory_keys[query_option]
    
    # Initialize UI memory
    if current_mem_key not in st.session_state:
        st.session_state[current_mem_key] = [
            {"role": "assistant", "content": f"Hello! I am ready to answer your **{query_option[2:]}** queries."}
        ]
    
    # Display the chat history ON SCREEN
    for msg in st.session_state[current_mem_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input 
    if user_question := st.chat_input(f"Ask about {query_option[2:]}..."):
        
        # Save user message to UI memory
        st.session_state[current_mem_key].append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)
            
        with st.chat_message("assistant"):
            if query_option == "👤 Single Employee Profile":
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

                    check_values = {k: v for k, v in clues.items()}
                    if not any(check_values.values()):
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
                            SELECT e.employee_id, e.employee_name, e.age, e.phone_no, e.position, 
                                   d.department_name, j.metadata 
                            FROM employees e 
                            LEFT JOIN departments d ON e.dept_id = d.department_id
                            LEFT JOIN employee_json j ON e.employee_id = j.employee_id
                            WHERE 1=1
                        """
                        
                        conditions = []
                        params = {}
                        
                        if clues.get('name'): conditions.append("e.employee_name ILIKE :name"); params['name'] = f"%{clues['name']}%"
                        if clues.get('department'): conditions.append("d.department_name ILIKE :dept"); params['dept'] = f"%{clues['department']}%"
                        if clues.get('position'): conditions.append("e.position ILIKE :pos"); params['pos'] = f"%{clues['position']}%"
                        if clues.get('project_phase'): conditions.append("j.metadata->'project'->>'phase' ILIKE :phase"); params['phase'] = f"%{clues['project_phase']}%"
                        if clues.get('tech_stack'): conditions.append("j.metadata->'project'->>'tech_stack' ILIKE :tech"); params['tech'] = f"%{clues['tech_stack']}%"

                        if conditions: base_query += " AND " + " AND ".join(conditions)

                        try:
                            results = conn.execute(text(base_query), params).fetchall()
                            
                            if len(results) == 0:
                                error_reply = "I couldn't find any employees matching those criteria."
                            elif len(results) > 1:
                                names = [f"{r._mapping['employee_name']} ({r._mapping.get('department_name', 'N/A')})" for r in results]
                                error_reply = f"I found multiple matching employees: **{', '.join(names)}**. Please ask again with a specific department or role."
                            else:
                                record = dict(results[0]._mapping)
                                final_emp_id = record.pop('employee_id')
                                sql_json_data = json.dumps(record, indent=2)
                                st.write(f"├── ✅ Fetching RAG data for {record['employee_name']}...")
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

                # 👉 FINAL ANSWER STREAMING
                if error_reply:
                    st.markdown(error_reply)
                    st.session_state[current_mem_key].append({"role": "assistant", "content": error_reply})
                else:
                    stream = synthesizer_chain.stream({
                        "question": user_question,
                        "sql_json_data": sql_json_data,
                        "rag_data": rag_data
                    })
                    full_response = st.write_stream((chunk.content for chunk in stream))
                    
                    # Save assistant message to UI memory
                    st.session_state[current_mem_key].append({"role": "assistant", "content": full_response})
            
            elif query_option == "📊 Team & Company-wide (Overall)":
                st.markdown("*(Overall team logic goes here...)*")
            elif query_option == "📅 Event Related Query":
                st.markdown("*(Event querying logic goes here...)*")