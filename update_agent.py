import json
import streamlit as st
from sqlalchemy import text
from langchain_core.prompts import PromptTemplate
from config import get_llms, get_db_engine, get_embedder

engine = get_db_engine()
extractor_llm, _ = get_llms()
embedder = get_embedder()

# ==========================================
# 0. CACHE MANAGER (New!)
# ==========================================
def refresh_departments_cache(db_engine):
    """Fetches all departments and saves them as a single JSON block in cached_data table."""
    with db_engine.connect() as conn:
        rows = conn.execute(text("SELECT department_id, department_name, head_name, landline_ext FROM departments;")).fetchall()
        dept_list = [
            {
                "department_id": r[0], 
                "department_name": r[1],
                "head_name": r[2] if r[2] else "N/A",
                "landline_ext": r[3] if r[3] else "N/A"
            } 
            for r in rows
        ]
        conn.execute(
            text("UPDATE cached_data SET value = :val WHERE key = 'all_departments';"),
            {"val": json.dumps(dept_list)}
        )
        conn.commit()

# ==========================================
# 1. MCP PROMPTS
# ==========================================
update_extractor_prompt = PromptTemplate.from_template("""
You are an intelligent Database Update Router. 
Read the user's request and figure out what they want to update.

Return EXACTLY this JSON structure. 
{{
    "category": "employee" | "department" | "event" | "unknown",
    "target_name_or_id": "ONLY the name or ID of the entity (e.g., 'IT', 'Human Resources', 'Aditya'). DO NOT include the field name like 'head' or 'manager' here.",
    "changes_requested": {{
        "key_to_update": "new_value"
    }}
}}

EXAMPLES:
User: "Update IT department head to Amit"
JSON: {{"category": "department", "target_name_or_id": "IT", "changes_requested": {{"head_name": "Amit"}}}}

User: "Change human resources head to Mr. Ram Nath Kashyap"
JSON: {{"category": "department", "target_name_or_id": "human resources", "changes_requested": {{"head_name": "Mr. Ram Nath Kashyap"}}}}

User: "Aditya's phone number is 9876543210"
JSON: {{"category": "employee", "target_name_or_id": "Aditya", "changes_requested": {{"phone_no": "9876543210"}}}}

User Request: {user_input}
""")

confirmation_prompt = PromptTemplate.from_template("""
You are an HR Assistant. Compare the CURRENT DATA with the REQUESTED CHANGES.
Write a short, polite confirmation message for the user.
- If a value exists, say "Changing [Key] from [Old Value] to [New Value]".
- If it doesn't exist, say "Adding new detail [Key]: [New Value]".

CURRENT DATA (JSON): {current_data}
REQUESTED CHANGES: {changes}

Start directly with the list of changes. Keep it concise.
""")

json_patcher_prompt = PromptTemplate.from_template("""
You are a strict JSON patcher. 
Apply the requested changes to the existing JSON and return the ENTIRE updated JSON.
- If a key exists, update its value.
- If a key DOES NOT exist, intelligently add it to the most relevant section.
Maintain the exact nested structure. DO NOT remove existing data.

EXISTING JSON: {current_json}
REQUESTED CHANGES: {changes}

RETURN ONLY THE FULLY UPDATED JSON OBJECT. NO MARKDOWN.
""")

update_extractor_chain = update_extractor_prompt | extractor_llm
confirmation_chain = confirmation_prompt | extractor_llm
json_patcher_chain = json_patcher_prompt | extractor_llm

# ==========================================
# 2. STATE MACHINE (Conversational Flow)
# ==========================================
def handle_conversational_update(user_input, chat_memory_key):
    state_key = "update_stage"
    context_key = "update_context" 
    
    if state_key not in st.session_state:
        st.session_state[state_key] = "INIT"
        st.session_state[context_key] = {}

    stage = st.session_state[state_key]
    conn = engine.connect()

    try:
        # STAGE 0/1: INIT -> Extraction & Target Search
        if stage == "INIT":
            st.write("🧠 *Analyzing update request...*")
            response = update_extractor_chain.invoke({"user_input": user_input})
            extracted_data = json.loads(response.content)
            
            category = extracted_data.get("category", "unknown").lower()
            target = extracted_data.get("target_name_or_id")
            changes = extracted_data.get("changes_requested", {})
            
            if category == "unknown" or not target or not changes:
                reply = "I couldn't clearly understand. Could you specify the entity (employee/event/dept) and what needs changing?"
                st.session_state[chat_memory_key].append({"role": "assistant", "content": reply})
                st.markdown(reply)
                return

            st.session_state[context_key] = extracted_data
            current_full_data = {}
            
            # Employee Search
            if category == "employee":
                result = conn.execute(
                    text("""
                        SELECT e.employee_id, e.employee_name, e.age, e.phone_no, e.position, e.dept_id, j.metadata 
                        FROM employees e 
                        LEFT JOIN employee_json j ON e.employee_id = j.employee_id
                        WHERE e.employee_name ILIKE :name OR e.employee_id = :name
                    """), {"name": f"%{target}%"}
                ).fetchall()
                if len(result) == 1:
                    emp = result[0]
                    current_full_data = {
                        "employee_id": emp[0], "employee_name": emp[1], "age": emp[2],
                        "phone_no": emp[3], "position": emp[4], "dept_id": emp[5],
                        "metadata": emp[6] if emp[6] else {}
                    }
                    st.session_state[context_key]['db_id'] = emp[0]
                    st.session_state[context_key]['db_name'] = emp[1]
                    st.session_state[context_key]['current_data'] = current_full_data
                else:
                    reply = f"Couldn't exactly match an employee for '{target}'."

            # Event Search
            elif category == "event":
                result = conn.execute(
                    text("SELECT event_id, event_name, event_date, metadata FROM company_events WHERE event_name ILIKE :name OR event_id = :name"),
                    {"name": f"%{target}%"}
                ).fetchall()
                if len(result) == 1:
                    evt = result[0]
                    current_full_data = {
                        "event_id": evt[0], "event_name": evt[1], "event_date": str(evt[2]),
                        "metadata": evt[3] if evt[3] else {}
                    }
                    st.session_state[context_key]['db_id'] = evt[0]
                    st.session_state[context_key]['db_name'] = evt[1]
                    st.session_state[context_key]['current_data'] = current_full_data
                else:
                    reply = f"Could not precisely find the event '{target}'."

            # Department Search
            elif category == "department":
                result = conn.execute(
                    text("SELECT department_id, department_name, head_name, landline_ext FROM departments WHERE department_name ILIKE :name OR department_id = :name"),
                    {"name": f"%{target}%"}
                ).fetchall()
                if len(result) == 1:
                    dep = result[0]
                    current_full_data = {
                        "department_id": dep[0], "department_name": dep[1], 
                        "head_name": dep[2], "landline_ext": dep[3]
                    }
                    st.session_state[context_key]['db_id'] = dep[0]
                    st.session_state[context_key]['db_name'] = dep[1]
                    st.session_state[context_key]['current_data'] = current_full_data
                else:
                    reply = f"Could not precisely find the department '{target}'."

            # Generate Confirmation Message
            if 'db_id' in st.session_state[context_key]:
                st.write("🔍 *Verifying existing data...*")
                conf_response = confirmation_chain.invoke({
                    "current_data": json.dumps(current_full_data),
                    "changes": json.dumps(changes)
                })
                reply = f"🔍 Found **{st.session_state[context_key]['db_name']}**.\n\n" + conf_response.content + "\n\n**Shall I go ahead and apply these changes? (Confirm / Cancel)**"
                st.session_state[state_key] = "CONFIRM_CHANGES"

            st.session_state[chat_memory_key].append({"role": "assistant", "content": reply})
            st.markdown(reply)

        # STAGE 2: EXECUTE CHANGES
        elif stage == "CONFIRM_CHANGES":
            if user_input.strip().lower() in ['confirm', 'yes', 'y', 'do it']:
                ctx = st.session_state[context_key]
                category = ctx['category']
                db_id = ctx['db_id']
                changes = ctx['changes_requested']
                current_data = ctx['current_data']
                
                st.write("⚙️ *Executing database updates...*")
                
                if category == "employee":
                    static_keys = ['age', 'phone_no', 'position', 'dept_id', 'employee_name']
                    static_updates = {k: v for k, v in changes.items() if k in static_keys}
                    dynamic_updates = {k: v for k, v in changes.items() if k not in static_keys}
                    
                    if static_updates:
                        set_clause = ", ".join([f"{k} = :{k}" for k in static_updates.keys()])
                        static_updates['id'] = db_id
                        conn.execute(text(f"UPDATE employees SET {set_clause} WHERE employee_id = :id"), static_updates)
                        for k, v in static_updates.items():
                            if k != 'id': current_data[k] = v

                    if dynamic_updates:
                        patch_res = json_patcher_chain.invoke({"current_json": json.dumps(current_data.get("metadata", {})), "changes": json.dumps(dynamic_updates)})
                        try:
                            current_data["metadata"] = json.loads(patch_res.content)
                        except:
                            pass
                        conn.execute(text("UPDATE employee_json SET metadata = :meta WHERE employee_id = :id"), {"meta": json.dumps(current_data["metadata"]), "id": db_id})

                    # UNIFIED VECTOR UPDATE
                    unified_json_str = json.dumps(current_data)
                    new_vector = embedder.encode(unified_json_str).tolist()
                    conn.execute(text("UPDATE metadata_vectors SET metadata_text = :txt, embedding = :emb WHERE employee_id = :id"), {"txt": unified_json_str, "emb": str(new_vector), "id": db_id})

                elif category == "event":
                    # 🔥 Yahan location aur description add kar diye hain
                    static_keys = ['event_name', 'event_date', 'location', 'description']
                    
                    static_updates = {k: v for k, v in changes.items() if k in static_keys}
                    dynamic_updates = {k: v for k, v in changes.items() if k not in static_keys}
                    
                    if static_updates:
                        set_clause = ", ".join([f"{k} = :{k}" for k in static_updates.keys()])
                        static_updates['id'] = db_id
                        conn.execute(text(f"UPDATE company_events SET {set_clause} WHERE event_id = :id"), static_updates)
                        for k, v in static_updates.items():
                            if k != 'id': current_data[k] = v

                    if dynamic_updates:
                        patch_res = json_patcher_chain.invoke({"current_json": json.dumps(current_data.get("metadata", {})), "changes": json.dumps(dynamic_updates)})
                        try:
                            current_data["metadata"] = json.loads(patch_res.content)
                        except:
                            pass
                        
                    # UNIFIED VECTOR UPDATE FOR EVENT
                    unified_json_str = json.dumps(current_data)
                    new_vector = embedder.encode(unified_json_str).tolist()
                    
                    conn.execute(text("UPDATE company_events SET metadata = :meta, embedding = :emb WHERE event_id = :id"), 
                                 {"meta": json.dumps(current_data["metadata"]), "emb": str(new_vector), "id": db_id})
                    
                elif category == "department":
                    allowed_keys = ['department_name', 'head_name', 'landline_ext']
                    valid_updates = {k: v for k, v in changes.items() if k in allowed_keys}
                    if valid_updates:
                        set_clause = ", ".join([f"{k} = :{k}" for k in valid_updates.keys()])
                        valid_updates['id'] = db_id
                        conn.execute(text(f"UPDATE departments SET {set_clause} WHERE department_id = :id"), valid_updates)
                        # 🔥 SYNC CACHE AFTER DEPT UPDATE
                        conn.commit()
                        refresh_departments_cache(engine)
                        st.write("├── ✅ Department updated and Cache Synchronized.")

                conn.commit()
                reply = f"✅ Update applied successfully to **{ctx['db_name']}**! All systems synchronized."
                
                st.session_state[state_key] = "INIT"
                st.session_state[context_key] = {}
                st.session_state[chat_memory_key].append({"role": "assistant", "content": reply})
                st.markdown(reply)
                
            else:
                st.session_state[state_key] = "INIT"
                reply = "Update cancelled safely. No changes were made."
                st.session_state[chat_memory_key].append({"role": "assistant", "content": reply})
                st.markdown(reply)

    except Exception as e:
        conn.rollback()
        st.error(f"Execution Error: {e}")
        st.session_state[state_key] = "INIT" 
    finally:
        conn.close()

def handle_conversational_update_api(user_input: str, stage: str, context: dict) -> dict:
    conn = engine.connect()
    try:
        if stage == "INIT":
            response = update_extractor_chain.invoke({"user_input": user_input})
            extracted_data = json.loads(response.content)
            
            category = extracted_data.get("category", "unknown").lower()
            target = extracted_data.get("target_name_or_id")
            changes = extracted_data.get("changes_requested", {})
            
            if category == "unknown" or not target or not changes:
                return {"reply": "I couldn't clearly understand. Could you specify the entity (employee/event/dept) and what needs changing?", "update_stage": "INIT", "update_context": {}}

            context = extracted_data
            current_full_data = {}
            reply = ""
            
            if category == "employee":
                result = conn.execute(
                    text("""
                        SELECT e.employee_id, e.employee_name, e.age, e.phone_no, e.position, e.dept_id, j.metadata 
                        FROM employees e 
                        LEFT JOIN employee_json j ON e.employee_id = j.employee_id
                        WHERE e.employee_name ILIKE :name OR e.employee_id = :name
                    """), {"name": f"%{target}%"}
                ).fetchall()
                if len(result) == 1:
                    emp = result[0]
                    current_full_data = {
                        "employee_id": emp[0], "employee_name": emp[1], "age": emp[2],
                        "phone_no": emp[3], "position": emp[4], "dept_id": emp[5],
                        "metadata": emp[6] if emp[6] else {}
                    }
                    context['db_id'] = emp[0]
                    context['db_name'] = emp[1]
                    context['current_data'] = current_full_data
                else:
                    reply = f"Couldn't exactly match an employee for '{target}'."

            elif category == "event":
                result = conn.execute(
                    text("SELECT event_id, event_name, event_date, metadata FROM company_events WHERE event_name ILIKE :name OR event_id = :name"),
                    {"name": f"%{target}%"}
                ).fetchall()
                if len(result) == 1:
                    evt = result[0]
                    current_full_data = {
                        "event_id": evt[0], "event_name": evt[1], "event_date": str(evt[2]),
                        "metadata": evt[3] if evt[3] else {}
                    }
                    context['db_id'] = evt[0]
                    context['db_name'] = evt[1]
                    context['current_data'] = current_full_data
                else:
                    reply = f"Could not precisely find the event '{target}'."

            elif category == "department":
                result = conn.execute(
                    text("SELECT department_id, department_name, head_name, landline_ext FROM departments WHERE department_name ILIKE :name OR department_id = :name"),
                    {"name": f"%{target}%"}
                ).fetchall()
                if len(result) == 1:
                    dep = result[0]
                    current_full_data = {
                        "department_id": dep[0], "department_name": dep[1], 
                        "head_name": dep[2], "landline_ext": dep[3]
                    }
                    context['db_id'] = dep[0]
                    context['db_name'] = dep[1]
                    context['current_data'] = current_full_data
                else:
                    reply = f"Could not precisely find the department '{target}'."

            if 'db_id' in context:
                conf_response = confirmation_chain.invoke({
                    "current_data": json.dumps(current_full_data),
                    "changes": json.dumps(changes)
                })
                reply = f"Found **{context['db_name']}**.\n\n" + conf_response.content + "\n\n**Shall I go ahead and apply these changes? (Confirm / Cancel)**"
                return {"reply": reply, "update_stage": "CONFIRM_CHANGES", "update_context": context}
            
            return {"reply": reply, "update_stage": "INIT", "update_context": {}}

        elif stage == "CONFIRM_CHANGES":
            if user_input.strip().lower() in ['confirm', 'yes', 'y', 'do it']:
                category = context['category']
                db_id = context['db_id']
                changes = context['changes_requested']
                current_data = context['current_data']
                
                if category == "employee":
                    static_keys = ['age', 'phone_no', 'position', 'dept_id', 'employee_name']
                    static_updates = {k: v for k, v in changes.items() if k in static_keys}
                    dynamic_updates = {k: v for k, v in changes.items() if k not in static_keys}
                    
                    if static_updates:
                        set_clause = ", ".join([f"{k} = :{k}" for k in static_updates.keys()])
                        static_updates['id'] = db_id
                        conn.execute(text(f"UPDATE employees SET {set_clause} WHERE employee_id = :id"), static_updates)
                        for k, v in static_updates.items():
                            if k != 'id': current_data[k] = v

                    if dynamic_updates:
                        patch_res = json_patcher_chain.invoke({"current_json": json.dumps(current_data.get("metadata", {})), "changes": json.dumps(dynamic_updates)})
                        try:
                            current_data["metadata"] = json.loads(patch_res.content)
                        except:
                            pass
                        conn.execute(text("UPDATE employee_json SET metadata = :meta WHERE employee_id = :id"), {"meta": json.dumps(current_data["metadata"]), "id": db_id})

                    unified_json_str = json.dumps(current_data)
                    new_vector = embedder.encode(unified_json_str).tolist()
                    conn.execute(text("UPDATE metadata_vectors SET metadata_text = :txt, embedding = :emb WHERE employee_id = :id"), {"txt": unified_json_str, "emb": str(new_vector), "id": db_id})

                elif category == "event":
                    static_keys = ['event_name', 'event_date', 'location', 'description']
                    static_updates = {k: v for k, v in changes.items() if k in static_keys}
                    dynamic_updates = {k: v for k, v in changes.items() if k not in static_keys}
                    
                    if static_updates:
                        set_clause = ", ".join([f"{k} = :{k}" for k in static_updates.keys()])
                        static_updates['id'] = db_id
                        conn.execute(text(f"UPDATE company_events SET {set_clause} WHERE event_id = :id"), static_updates)
                        for k, v in static_updates.items():
                            if k != 'id': current_data[k] = v

                    if dynamic_updates:
                        patch_res = json_patcher_chain.invoke({"current_json": json.dumps(current_data.get("metadata", {})), "changes": json.dumps(dynamic_updates)})
                        try:
                            current_data["metadata"] = json.loads(patch_res.content)
                        except:
                            pass
                        
                    unified_json_str = json.dumps(current_data)
                    new_vector = embedder.encode(unified_json_str).tolist()
                    conn.execute(text("UPDATE company_events SET metadata = :meta, embedding = :emb WHERE event_id = :id"), 
                                 {"meta": json.dumps(current_data["metadata"]), "emb": str(new_vector), "id": db_id})
                    
                elif category == "department":
                    allowed_keys = ['department_name', 'head_name', 'landline_ext']
                    valid_updates = {k: v for k, v in changes.items() if k in allowed_keys}
                    if valid_updates:
                        set_clause = ", ".join([f"{k} = :{k}" for k in valid_updates.keys()])
                        valid_updates['id'] = db_id
                        conn.execute(text(f"UPDATE departments SET {set_clause} WHERE department_id = :id"), valid_updates)
                        conn.commit()
                        refresh_departments_cache(engine)

                conn.commit()
                reply = f"Update applied successfully to **{context['db_name']}**! All systems synchronized."
                return {"reply": reply, "update_stage": "INIT", "update_context": {}}
                
            else:
                reply = "Update cancelled safely. No changes were made."
                return {"reply": reply, "update_stage": "INIT", "update_context": {}}

    except Exception as e:
        conn.rollback()
        return {"reply": f"Execution Error: {str(e)}", "update_stage": "INIT", "update_context": {}}
    finally:
        conn.close()