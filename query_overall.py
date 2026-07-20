import json
import os
import psycopg2
from langchain_core.prompts import PromptTemplate
from config import get_llms, get_embedder

embedder = get_embedder()
_, chat_llm = get_llms()

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

overall_chain = overall_prompt | chat_llm

def handle_overall_query(user_question, current_mem_key=None):
    print("🛠️ Fetching Team & Department Data...")
    print("⚡ 1. Running Vector Search & Fetching Cached Departments...")
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        
        # 🔥 FETCH DIRECTLY FROM CACHE (Super Fast!)
        cur.execute("SELECT value FROM cached_data WHERE key = 'all_departments';")
        cached_row = cur.fetchone()
        departments_json = json.dumps(cached_row[0], indent=2) if cached_row else "[]"
        print("🏢 Departments Loaded from Cache")

        # --- Fetch Employees JSON using Vectors ---
        question_vector = embedder.encode(user_question).tolist()
        cur.execute("""
            SELECT employee_id, metadata_text 
            FROM metadata_vectors 
            ORDER BY embedding <=> %s::vector 
            LIMIT 150;
        """, (str(question_vector),))
        
        dynamic_results = cur.fetchall()
        overall_data_list = []
        
        if dynamic_results:
            print(f"🔍 Found {len(dynamic_results)} relevant employee records.")
            for r in dynamic_results:
                # r[1] holds the UNIFIED json string we created during ingestion
                try:
                    overall_data_list.append(json.loads(r[1]))
                except json.JSONDecodeError:
                    pass
                    
            sql_json_data = json.dumps(overall_data_list, indent=2)
            print("📄 Employee Data Passed to LLM")
        else:
            sql_json_data = "[]"
            error_reply = "I couldn't find any relevant employee data for that query."
            
    except Exception as e:
        print(f"⚠️ Database error: {str(e)}")
        error_reply = "An error occurred."
    finally:
        if 'cur' in locals() and cur: cur.close()
        if 'conn' in locals() and conn: conn.close()

    print("✅ Data Processed")

    if 'error_reply' in locals() and error_reply:
        return error_reply
    else:
        final_response = overall_chain.invoke({
            "question": user_question, 
            "departments_json": departments_json,
            "sql_json_data": sql_json_data
        })
        return final_response.content

def handle_overall_query_api(user_question: str) -> str:
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        
        # Fetch cached departments
        cur.execute("SELECT value FROM cached_data WHERE key = 'all_departments';")
        cached_row = cur.fetchone()
        departments_json = json.dumps(cached_row[0], indent=2) if cached_row else "[]"

        # Fetch employee vectors
        question_vector = embedder.encode(user_question).tolist()
        cur.execute("""
            SELECT employee_id, metadata_text 
            FROM metadata_vectors 
            ORDER BY embedding <=> %s::vector 
            LIMIT 150;
        """, (str(question_vector),))
        
        dynamic_results = cur.fetchall()
        overall_data_list = []
        
        if dynamic_results:
            for r in dynamic_results:
                try:
                    overall_data_list.append(json.loads(r[1]))
                except json.JSONDecodeError:
                    pass
            sql_json_data = json.dumps(overall_data_list, indent=2)
        else:
            return "I couldn't find any relevant employee data for that query."
            
    except Exception as e:
        return f"Database error: {str(e)}"
    finally:
        if 'cur' in locals() and cur: cur.close()
        if 'conn' in locals() and conn: conn.close()

    # Invoke LLM without Streamlit streaming
    final_response = overall_chain.invoke({
        "question": user_question, 
        "departments_json": departments_json,
        "sql_json_data": sql_json_data
    })
    return final_response.content