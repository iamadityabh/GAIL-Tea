import sys
from sqlalchemy import text
from config import get_db_engine
from query_single import handle_single_profile
from query_overall import handle_overall_query
from query_events import handle_event_query
from ingest import ingest_single_employee, delete_employee, ingest_single_event, delete_event
from update_agent import handle_conversational_update, refresh_departments_cache

engine = get_db_engine()

def main():
    # Replacing st.session_state with a standard dictionary for the lifespan of the app
    session_state = {
        "mem_update_agent": [{"role": "assistant", "content": "Hello! I am your Database Agent. What would you like to update today?"}],
        "mem_single_profile": [{"role": "assistant", "content": "Hello! I am ready to answer your Single Employee Profile queries."}],
        "mem_overall": [{"role": "assistant", "content": "Hello! I am ready to answer your Team & Company-wide queries."}],
        "mem_events": [{"role": "assistant", "content": "Hello! I am ready to answer your Event Related queries."}]
    }

    while True:
        print("\n" + "="*50)
        print("🏢 GTI Enterprise HR Portal (Terminal Edition)")
        print("="*50)
        print("1. ➕ Add Data")
        print("2. ✏️ Update Data (AI Agent)")
        print("3. 🔍 Ask a Query")
        print("4. ❌ Exit")
        
        main_mode = input("\n👉 Select Operation Mode (1-4): ").strip()

        # ==========================================
        # 1. ADD DATA SECTION
        # ==========================================
        if main_mode == "1":
            print("\n--- ➕ Add or Delete Records ---")
            print("1. 👤 Manage Employees")
            print("2. 🏢 Manage Departments")
            print("3. 📅 Manage Events")
            print("4. 🔙 Back to Main Menu")
            
            add_option = input("Select Category (1-4): ").strip()
            
            # --- EMPLOYEES ---
            if add_option == "1":
                folder_name = input("\nEnter Employee Folder/ID (e.g., EMP-101): ").strip()
                if not folder_name: continue
                
                action = input("Type '1' to Ingest or '2' to Delete: ").strip()
                if action == "1":
                    print(f"⏳ Ingesting data for '{folder_name}'...")
                    res = ingest_single_employee(folder_name)
                    print(f"✅ {res.get('message')}" if res.get("status") == "success" else f"❌ {res.get('message')}")
                elif action == "2":
                    print(f"⏳ Deleting records for '{folder_name}'...")
                    res = delete_employee(folder_name)
                    print(f"✅ {res.get('message')}" if res.get("status") == "success" else f"❌ {res.get('message')}")

            # --- DEPARTMENTS ---
            elif add_option == "2":
                dept_id = input("\nEnter Department ID (e.g., D-01, HR-Tech): ").strip()
                if not dept_id: continue
                
                action = input("Type '1' to Add/Update or '2' to Delete: ").strip()
                if action == "1":
                    dept_name = input("Enter Department Name: ").strip()
                    head_name = input("Enter Department Head Name: ").strip()
                    landline = input("Enter 3-4 Digit Landline Ext: ").strip()
                    
                    if dept_name:
                        try:
                            with engine.begin() as conn:  # 🔥 engine.begin() use kiya taaki auto-commit ho jaye
                                conn.execute(
                                    text("""
                                        INSERT INTO departments (department_id, department_name, head_name, landline_ext) 
                                        VALUES (:id, :name, :head, :landline)
                                    """), 
                                    {
                                        "id": dept_id, 
                                        "name": dept_name, 
                                        "head": head_name if head_name else "N/A",      # 🔥 FIX: Empty string check
                                        "landline": landline if landline else "N/A"     # 🔥 FIX: Empty string check
                                    }
                                )
                            refresh_departments_cache(engine)
                            print(f"✅ Department '{dept_name}' added and cache synced!")
                        except Exception as e:
                            print(f"❌ Error adding department: {e}")
                    else:
                        print("⚠️ Please provide a Department Name.")
                        
                elif action == "2":
                    try:
                        with engine.begin() as conn:
                            conn.execute(text("DELETE FROM departments WHERE department_id = :id"), {"id": dept_id})
                        refresh_departments_cache(engine)
                        print(f"✅ Department ID {dept_id} deleted and cache synced!")
                    except Exception as e:
                        print(f"❌ Error deleting department: {e}")

            # --- EVENTS ---
            elif add_option == "3":
                print("ℹ️ Note: Place your event PDFs and TXT files in the 'events/<Event-ID>' folder before ingesting.")
                event_id = input("\nEnter Event Folder/ID (e.g., EVT-01): ").strip()
                if not event_id: continue
                
                action = input("Type '1' to Ingest or '2' to Delete: ").strip()
                if action == "1":
                    print(f"⏳ Extracting and ingesting data for '{event_id}'...")
                    res = ingest_single_event(event_id)
                    print(f"✅ {res.get('message')}" if res.get("status") == "success" else f"❌ {res.get('message')}")
                elif action == "2":
                    print(f"⏳ Deleting records for '{event_id}'...")
                    res = delete_event(event_id)
                    print(f"✅ {res.get('message')}" if res.get("status") == "success" else f"❌ {res.get('message')}")

        # ==========================================
        # 2. UPDATE DATA SECTION (Agent Mode)
        # ==========================================
        elif main_mode == "2":
            print("\n--- ✏️ AI Update Agent ---")
            print("Tell me what you want to modify (Type 'exit' to return).")
            
            mem_key = "mem_update_agent"
            # Display chat history for this session
            for msg in session_state[mem_key]:
                print(f"[{msg['role'].capitalize()}]: {msg['content']}")
                
            while True:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ['exit', 'quit', 'back']: break
                if not user_input: continue
                
                session_state[mem_key].append({"role": "user", "content": user_input})
                print("[Assistant]: ", end="")
                # Pass session_state to maintain continuity
                handle_conversational_update(user_input, session_state=session_state, chat_memory_key=mem_key)

        # ==========================================
        # 3. ASK A QUERY SECTION
        # ==========================================
        elif main_mode == "3":
            print("\n--- 🤖 HR Assistant ---")
            print("1. 👤 Single Employee Profile")
            print("2. 📊 Team & Company-wide (Overall)")
            print("3. 📅 Event Related Query")
            print("4. 🔙 Back to Main Menu")
            
            q_choice = input("Select query type (1-4): ").strip()
            
            query_map = {
                "1": ("Single Employee Profile", "mem_single_profile", handle_single_profile),
                "2": ("Team & Company-wide", "mem_overall", handle_overall_query),
                "3": ("Event Related Query", "mem_events", handle_event_query)
            }
            
            if q_choice in query_map:
                name, mem_key, handler_func = query_map[q_choice]
                print(f"\n--- Chat: {name} (Type 'exit' to return) ---")
                
                for msg in session_state[mem_key]:
                    print(f"[{msg['role'].capitalize()}]: {msg['content']}")
                    
                while True:
                    user_question = input("\nYou: ").strip()
                    if user_question.lower() in ['exit', 'quit', 'back']: break
                    if not user_question: continue
                    
                    session_state[mem_key].append({"role": "user", "content": user_question})
                    print("[Assistant]: \n", end="")
                    
                    # Call the appropriate handler, passing the chat history list for the specific key
                    handler_func(user_question, session_state[mem_key])
            else:
                continue

        # ==========================================
        # 4. EXIT
        # ==========================================
        elif main_mode == "4":
            print("Exiting GTI Enterprise HR Portal. Goodbye! 👋")
            sys.exit(0)
            
        else:
            print("⚠️ Invalid choice. Please select 1, 2, 3, or 4.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting... 👋")
        sys.exit(0)