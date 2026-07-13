import json
from pathlib import Path
from langchain_core.prompts import PromptTemplate

# --- OCR & TABLES IMPORTS ---
import pdfplumber
import pytesseract
from pdf2image import convert_from_path

# --- IMPORT MODELS FROM CONFIG ---
# Yeh line aapki config.py se embedder, Groq LLM, aur db_engine ko load karegi
from config import get_embedder, get_llms, get_db_engine 

# ==========================================
# 1. LLM Prompts Setup
# ==========================================
info_prompt = PromptTemplate.from_template("""
You are a strict data extractor. Extract the details from the raw text below and return ONLY a JSON object.
Use EXACTLY these keys: "name" (string), "dept_id" (string), "phone_no" (string), "position" (string), "email" (string), "age" (integer). 
If a value is completely missing from the text, set it to null.

Raw Text:
{raw_text}
""")

metadata_prompt = PromptTemplate.from_template("""
You are an expert HR Data Extractor. 
Read the following unstructured text about an employee/trainee and extract the relevant details into a STRICT JSON format.

Use the following NESTED JSON structure exactly. If a piece of information is missing, set its value to "N/A" (or an empty array for lists).
CRITICAL: If you find any OTHER important information that does not fit into predefined keys, capture them inside the "custom_attributes" dictionary.

{{
  "personal_and_academic": {{
    "name": "string",
    "age": "string or integer",
    "id": "string",
    "roll_no": "string",
    "college_details": "string"
  }},
  "project": {{
    "project_name": "string",
    "description": "string",
    "tech_stack": ["list of strings"],
    "project_phases_names": ["list of strings"],
    "current_phase": "string",
    "timeline": "string",
    "pros_of_project": "string",
    "cons_of_project": "string"
  }},
  "mentorship": {{
    "mentor_name": "string",
    "mentor_position": "string"
  }},
  "skills_and_achievements": {{
    "skills": ["list of strings"],
    "certifications": ["list of strings"]
  }},
  "hr_observations": {{
    "performance_and_feedback": "string"
  }},
  "custom_attributes": {{
    "insert_logical_key_name_here": "value of the extracted information"
  }}
}}

Raw Text:
{raw_text}

RETURN ONLY VALID JSON. NO MARKDOWN. NO EXTRA TEXT.
""")

event_prompt = PromptTemplate.from_template("""
You are an expert Data Extractor. Read the following text combining multiple documents about a company event.
Extract the relevant details and format them into a strict JSON object. 

CRITICAL RULES:
1. ONLY return a valid JSON object.
2. Use EXACTLY these lowercase keys. If data is missing, set the value to null or "Not mentioned".
3. Key list: 
   - "event_name"
   - "event_start_date"
   - "event_end_date"
   - "event_status" (e.g., Scheduled, Unscheduled, Completed, Postponed)
   - "chief_guest"
   - "location"
   - "organiser"
   - "size" (number of attendees/scale)
   - "about_the_event" (A short 2-3 sentence summary)
   - "other_relevant_details" (Any other key highlight)

TEXT PROVIDED:
{raw_text}
""")

# ==========================================
# 2. Model Loader (UPGRADED FOR GROQ)
# ==========================================
def get_models():
    print("Loading Models from config.py... (Embedder & Groq API)")
    
    # config.py se embedder aur LLMs get karna
    embedder = get_embedder()
    extractor_llm, chat_llm = get_llms() 
    
    # Hum sirf extractor_llm (json_object format wala) use karenge ingestion ke liye
    info_chain = info_prompt | extractor_llm
    metadata_chain = metadata_prompt | extractor_llm
    event_chain = event_prompt | extractor_llm
    
    return embedder, info_chain, metadata_chain, event_chain

# ==========================================
# 3. Helper Functions (OCR & PDF)
# ==========================================
def extract_text_from_pdf(file_path):
    text = ""
    try:
        # Step 1: Try digital extraction with pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                
                tables = page.extract_tables()
                for table in tables:
                    text += "\n[TABLE START]\n"
                    for row in table:
                        clean_row = [str(cell).replace('\n', ' ') if cell else "" for cell in row]
                        text += " | ".join(clean_row) + "\n"
                    text += "[TABLE END]\n\n"

        # Step 2: OCR Fallback for Scanned Documents
        if len(text.strip()) < 10:
            print(f" ├── ⚠️ No digital text detected in {Path(file_path).name}. Running OCR...")
            images = convert_from_path(file_path)
            for img in images:
                ocr_text = pytesseract.image_to_string(img)
                text += ocr_text + "\n"

    except Exception as e:
        print(f"⚠️ Warning: Could not read {file_path}. Error: {e}")
        
    return text.strip()

def parse_with_llm(raw_text, chain, name_label):
    if not raw_text.strip():
        return {}
    try:
        print(f"   -> Groq API is parsing {name_label}...")
        response = chain.invoke({"raw_text": raw_text})
        # Groq with JSON mode returns stringified JSON, just load it
        return json.loads(response.content)
    except Exception as e:
        print(f"⚠️ Groq API parsing failed for {name_label}: {e}")
        return {}

def extract_text_from_folder(folder_path: Path):
    combined_text = ""
    for file_path in folder_path.iterdir():
        if file_path.suffix == ".txt":
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    combined_text += f"\n--- {file_path.name} ---\n" + f.read()
            except Exception as e:
                print(f"⚠️ Warning: Could not read {file_path.name}. Error: {e}")
        elif file_path.suffix == ".pdf":
            combined_text += f"\n--- {file_path.name} ---\n" + extract_text_from_pdf(file_path)
    return combined_text

# ==========================================
# 4. CORE FUNCTIONS
# ==========================================

# ---------------- EMPLOYEES ----------------
def ingest_single_employee(folder_name: str) -> dict:
    folder_path = Path("data") / folder_name
    info_path = folder_path / "info.txt"
    metadata_path = folder_path / "metadata.txt"

    if not folder_path.exists() or not folder_path.is_dir():
        return {"status": "error", "message": f"Folder 'data/{folder_name}' does not exist."}
    if not info_path.exists():
        return {"status": "error", "message": f"info.txt is missing in folder '{folder_name}'."}

    conn = None
    cur = None
    
    try:
        engine = get_db_engine()
        conn = engine.raw_connection()
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM employees WHERE employee_id = %s;", (folder_name,))
        if cur.fetchone():
            return {"status": "error", "message": f"Employee ID '{folder_name}' already exists! Please use the 'Update Data' section to modify it."}

        print(f"\n📂 Processing Trainee Folder: {folder_name}")

        embedder, info_chain, metadata_chain, _ = get_models()

        with open(info_path, 'r', encoding='utf-8') as f:
            basic_data = parse_with_llm(f.read(), info_chain, "info.txt")
        emp_name = basic_data.get('name')

        if not emp_name or str(emp_name).strip().lower() in ["null", "none", "n/a", ""]:
            return {"status": "error", "message": f"Name is missing in info.txt for '{folder_name}'. Ingestion stopped."}

        cur.execute("""
            INSERT INTO employees (employee_id, employee_name, dept_id, age, phone_no, position) 
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (
            folder_name, 
            emp_name, 
            basic_data.get('dept_id'), 
            basic_data.get('age'), 
            basic_data.get('phone_no'), 
            basic_data.get('position', 'Trainee')
        ))
        print(f" ├── SQL: Inserted basic info for {emp_name} ({folder_name})")

        dynamic_data = {}
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                dynamic_data = parse_with_llm(f.read(), metadata_chain, "metadata.txt")
            
            cur.execute("""
                INSERT INTO employee_json (employee_id, metadata) 
                VALUES (%s, %s);
            """, (folder_name, json.dumps(dynamic_data)))
        else:
            print(" ├── ⚠️ metadata.txt not found. Setting dynamic metadata to empty.")

        unified_profile = {
            "employee_id": folder_name,
            "employee_name": emp_name,
            "age": basic_data.get('age'),
            "phone_no": basic_data.get('phone_no'),
            "position": basic_data.get('position', 'Trainee'),
            "dept_id": basic_data.get('dept_id'),
            "metadata": dynamic_data 
        }
        
        unified_string = json.dumps(unified_profile, indent=2)
        print(" ├── Creating UNIFIED Vector Embedding (SQL + JSON)...")
        unified_vector = embedder.encode(unified_string).tolist()
        
        cur.execute("""
            INSERT INTO metadata_vectors (employee_id, metadata_text, embedding) 
            VALUES (%s, %s, %s);
        """, (folder_name, unified_string, unified_vector))
        print(" ├── SQL: Unified Metadata and Vectors saved successfully!")

        pdf_files = list(folder_path.glob("*.pdf"))
        if not pdf_files:
            print(" ├── ⚠️ No PDF documents found.")
        
        for pdf_file in pdf_files:
            doc_type = pdf_file.stem 
            print(f" ├── Reading PDF: {pdf_file.name}...")
            doc_text = extract_text_from_pdf(pdf_file)
            
            if doc_text:
                vector_embedding = embedder.encode(doc_text).tolist()
                cur.execute("""
                    INSERT INTO employee_vectors (employee_id, document_type, chunk_text, embedding) 
                    VALUES (%s, %s, %s, %s);
                """, (folder_name, doc_type, doc_text, vector_embedding))
                print(f" │   └── PDF Vector Embedded and saved!")
            else:
                print(f" │   └── ⚠️ No text extracted.")

        conn.commit()
        success_msg = f"Successfully ingested all data for {emp_name} (ID: {folder_name})!"
        print(f"🚀 {success_msg}")
        return {"status": "success", "message": success_msg}

    except Exception as e:
        if conn: conn.rollback() 
        print(f"❌ Database/Processing Error: {e}")
        return {"status": "error", "message": str(e)}
    
    finally:
        if cur: cur.close()
        if conn: conn.close()

def delete_employee(folder_name: str) -> dict:
    conn = None
    cur = None
    try:
        engine = get_db_engine()
        conn = engine.raw_connection()
        cur = conn.cursor()

        cur.execute("SELECT employee_name FROM employees WHERE employee_id = %s;", (folder_name,))
        result = cur.fetchone()
        
        if not result:
            return {"status": "error", "message": f"Employee ID '{folder_name}' not found."}
        
        cur.execute("DELETE FROM employees WHERE employee_id = %s;", (folder_name,))
        conn.commit()
        return {"status": "success", "message": f"Successfully DELETED Employee ID: {folder_name}"}

    except Exception as e:
        if conn: conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ---------------- EVENTS ----------------
def ingest_single_event(event_id: str) -> dict:
    folder_path = Path("events") / event_id
    
    if not folder_path.exists() or not folder_path.is_dir():
        return {"status": "error", "message": f"Folder 'events/{event_id}' not found."}
        
    conn = None
    cur = None
    try:
        engine = get_db_engine()
        conn = engine.raw_connection()
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM company_events WHERE event_id = %s;", (event_id,))
        if cur.fetchone():
            return {"status": "error", "message": f"Event ID '{event_id}' already exists! Please use the 'Update Data' section to modify it."}

        raw_text = extract_text_from_folder(folder_path)
        if not raw_text.strip():
            return {"status": "error", "message": f"No readable text found in 'events/{event_id}'."}

        print(f"\n📅 Processing Event Folder: {event_id}")
        
        embedder, _, _, event_chain = get_models()

        event_json = parse_with_llm(raw_text, event_chain, f"Event Documents ({event_id})")
        event_name = event_json.get("event_name", f"Event {event_id}")

        json_string = json.dumps(event_json)
        print("   ├── Creating Vector Embedding for Event...")
        embedding_vector = embedder.encode(json_string).tolist()

        cur.execute("""
            INSERT INTO company_events (event_id, event_name, event_date, location, description, metadata, embedding) 
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            event_id, 
            event_name, 
            event_json.get("event_start_date", "Not specified"), 
            event_json.get("location", "Not specified"),
            event_json.get("about_the_event", "No description available"),
            json_string, 
            embedding_vector
        ))
        
        conn.commit()
        success_msg = f"Event '{event_name}' (ID: {event_id}) ingested successfully!"
        print(f"🚀 {success_msg}")
        return {"status": "success", "message": success_msg}
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Error ingesting event: {e}")
        return {"status": "error", "message": f"Ingestion failed: {str(e)}"}
    finally:
        if cur: cur.close()
        if conn: conn.close()
        
def delete_event(event_id: str) -> dict:
    conn = None
    cur = None
    try:
        engine = get_db_engine()
        conn = engine.raw_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT event_name FROM company_events WHERE event_id = %s;", (event_id,))
        if not cur.fetchone():
            return {"status": "error", "message": f"Event ID '{event_id}' not found."}

        cur.execute("DELETE FROM company_events WHERE event_id = %s;", (event_id,))
        conn.commit()
        return {"status": "success", "message": f"Event ID {event_id} deleted successfully!"}
    except Exception as e:
        if conn: conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ==========================================
# 5. Testing Block (Terminal Run)
# ==========================================
if __name__ == "__main__":
    print("\n🛠️ Database Manager (Using Groq API)")
    print("1. Ingest (Add) New Employee")
    print("2. Delete Existing Employee")
    print("3. Ingest (Add) New Event")
    print("4. Delete Existing Event")
    
    choice = input("\n👉 Enter your choice (1, 2, 3, or 4): ").strip()
    
    if choice == "1":
        test_folder = input("👉 Enter Employee folder name (e.g., EMP101): ").strip()
        if test_folder:
            print(ingest_single_employee(test_folder))
    elif choice == "2":
        del_folder = input("👉 Enter Employee ID to delete (e.g., EMP101): ").strip()
        if del_folder:
            print(delete_employee(del_folder))
    elif choice == "3":
        test_event = input("👉 Enter Event folder name (e.g., EVT-01): ").strip()
        if test_event:
            print(ingest_single_event(test_event))
    elif choice == "4":
        del_event = input("👉 Enter Event ID to delete (e.g., EVT-01): ").strip()
        if del_event:
            print(delete_event(del_event))
    else:
        print("❌ Invalid choice.")