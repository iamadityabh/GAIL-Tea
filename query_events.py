import json
import os
import psycopg2
from langchain_core.prompts import PromptTemplate
from config import get_llms, get_embedder

embedder = get_embedder()
_, chat_llm = get_llms()

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

event_chain = event_prompt | chat_llm

def handle_event_query(user_question, current_mem_key=None):
    print("🛠️ Searching Event Records...")
    print("⚡ 1. Running Vector Search on Events...")
    try:
        # Connect directly for pgvector
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        # Encode the user's question
        question_vector = embedder.encode(user_question).tolist()
        
        # Fetch top 3 matching events based on semantic similarity
        cur.execute("""
            SELECT event_id, event_name, metadata 
            FROM company_events 
            ORDER BY embedding <=> %s::vector 
            LIMIT 150;
        """, (str(question_vector),))
        
        results = cur.fetchall()
        event_data_list = []
        
        if results:
            print(f"🔍 Found {len(results)} relevant events.")
            for r in results:
                # r[2] contains the JSONB metadata
                event_data_list.append(r[2])
                
            event_json_data = json.dumps(event_data_list, indent=2)
            print("📄 Event Data Passed to LLM.")
        else:
            event_json_data = "[]"
            error_reply = "I couldn't find any relevant events matching your query."
            
    except Exception as e:
        print(f"⚠️ Database error: {str(e)}")
        error_reply = "An error occurred while searching for events."
    finally:
        if 'cur' in locals() and cur: cur.close()
        if 'conn' in locals() and conn: conn.close()

    print("✅ Event Search Complete")

    # FINAL ANSWER
    if 'error_reply' in locals() and error_reply:
        return error_reply
    else:
        final_response = event_chain.invoke({
            "question": user_question,
            "event_data": event_json_data
        })
        return final_response.content

def handle_event_query_api(user_question: str) -> str:
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()

        question_vector = embedder.encode(user_question).tolist()
        
        cur.execute("""
            SELECT event_id, event_name, metadata 
            FROM company_events 
            ORDER BY embedding <=> %s::vector 
            LIMIT 150;
        """, (str(question_vector),))
        
        results = cur.fetchall()
        event_data_list = []
        
        if results:
            for r in results:
                event_data_list.append(r[2])
            event_json_data = json.dumps(event_data_list, indent=2)
        else:
            return "I couldn't find any relevant events matching your query."
            
    except Exception as e:
        return f"Database error: {str(e)}"
    finally:
        if 'cur' in locals() and cur: cur.close()
        if 'conn' in locals() and conn: conn.close()

    final_response = event_chain.invoke({
        "question": user_question,
        "event_data": event_json_data
    })
    return final_response.content