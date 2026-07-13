import json
import os
import psycopg2
from langchain_core.prompts import PromptTemplate
from config import get_llms, get_embedder

embedder = get_embedder()
_, chat_llm = get_llms()

overall_prompt = PromptTemplate.from_template("""
You are an HR Assistant answering team-wide or list queries.
Below is a JSON array containing data for multiple employees, and another JSON array for Company Departments.

CRITICAL RULES:
1. ANSWER DIRECTLY: ONLY answer what the user has explicitly asked. Do NOT dump extra employee details if the user hasn't asked for them, even if the data is present in the context.
2. THE ULTIMATE TRUTH FOR DEPARTMENTS: For any question about department names, department heads, or landlines, STRICTLY use the 'COMPANY DEPARTMENTS' JSON.
3. NO DATA MIXING: Never mix the skills, projects, or details of one employee with another.
4. FORMATTING: Be concise and professional. If listing multiple people, use bullet points.
5. If data is missing, say "I don't have that information."

User Question: {question}

--- COMPANY DEPARTMENTS (JSON) ---
{departments_json}

--- EMPLOYEES DATA (JSON ARRAY) ---
{sql_json_data}

Answer cleanly:
""")

overall_chain = overall_prompt | chat_llm

def handle_overall_query(user_question, current_mem_key=None):
    print("🛠️ Fetching Team & Department Data...")
    print("⚡ 1. Running Vector Search & Fetching Cached Departments...")
    try:
        conn = psycopg2.connect(dbname="GTI_2", user="postgres", password="root", host="localhost")
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
            LIMIT 10;
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
            LIMIT 10;
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