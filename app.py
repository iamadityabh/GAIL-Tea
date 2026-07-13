import streamlit as st
from sqlalchemy import text
from config import get_db_engine
from query_single import handle_single_profile
from query_overall import handle_overall_query
from query_events import handle_event_query
from ingest import ingest_single_employee, delete_employee, ingest_single_event, delete_event
from update_agent import handle_conversational_update, refresh_departments_cache

st.set_page_config(page_title="GTI Enterprise HR", page_icon="🏢", layout="wide")
engine = get_db_engine()

# ==========================================
# Sidebar Navigation 
# ==========================================
st.sidebar.title("🏢 GTI HR Portal")
st.sidebar.markdown("---")
main_mode = st.sidebar.radio(
    "👉 Select Operation Mode:", 
    ["🔍 Ask a Query", "➕ Add Data", "✏️ Update Data"]
)
st.sidebar.markdown("---")

# ==========================================
# 1. ADD DATA SECTION
# ==========================================
if main_mode == "➕ Add Data":
    st.title("➕ Add or Delete Records")
    add_option = st.sidebar.selectbox("Select Category:", ["👤 Manage Employees", "🏢 Manage Departments", "📅 Manage Events"])
    
    # --- EMPLOYEES ---
    if add_option == "👤 Manage Employees":
        st.subheader("Add or Remove Employee Data")
        folder_name = st.text_input("Enter Employee Folder/ID (e.g., EMP-101):").strip()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Ingest Employee Data", use_container_width=True, type="primary") and folder_name:
                with st.spinner(f"Ingesting data for '{folder_name}'..."):
                    res = ingest_single_employee(folder_name)
                    st.success(res.get("message")) if res.get("status") == "success" else st.error(res.get("message"))
        with col2:
            if st.button("🗑️ Delete Employee", use_container_width=True) and folder_name:
                with st.spinner(f"Deleting records for '{folder_name}'..."):
                    res = delete_employee(folder_name)
                    st.success(res.get("message")) if res.get("status") == "success" else st.error(res.get("message"))

    # --- DEPARTMENTS (With Cache Sync) ---
    elif add_option == "🏢 Manage Departments":
        st.subheader("Add or Delete a Department")
        dept_id = st.text_input("Enter Department ID (e.g., D-01, HR-Tech):").strip()
        dept_name = st.text_input("Enter Department Name (Needed for Adding):").strip()
        head_name = st.text_input("Enter Department Head Name (e.g., Mr. Sharma):").strip()
        landline = st.text_input("Enter 3-4 Digit Landline Ext (e.g., 4012):").strip()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add Department", use_container_width=True, type="primary"):
                if dept_id and dept_name:
                    try:
                        with engine.connect() as conn:
                            conn.execute(
                                text("""
                                    INSERT INTO departments (department_id, department_name, head_name, landline_ext) 
                                    VALUES (:id, :name, :head, :landline)
                                """), 
                                {"id": dept_id, "name": dept_name, "head": head_name, "landline": landline}
                            )
                            conn.commit()
                        # 🔥 SYNC CACHE AFTER ADD
                        refresh_departments_cache(engine)
                        st.success(f"Department '{dept_name}' added and cache synced!")
                    except Exception as e:
                        st.error(f"Error adding department: {e}")
                else:
                    st.warning("Please provide at least Department ID and Name.")
                    
        with col2:
            if st.button("🗑️ Delete Department", use_container_width=True):
                if dept_id:
                    try:
                        with engine.connect() as conn:
                            conn.execute(text("DELETE FROM departments WHERE department_id = :id"), {"id": dept_id})
                            conn.commit()
                        # 🔥 SYNC CACHE AFTER DELETE
                        refresh_departments_cache(engine)
                        st.success(f"Department ID {dept_id} deleted and cache synced!")
                    except Exception as e:
                        st.error(f"Error deleting department: {e}")
                else:
                    st.warning("Please provide a Department ID to delete.")

    # --- EVENTS ---
    elif add_option == "📅 Manage Events":
        st.subheader("Add or Remove Event Data")
        st.info("Place your event PDFs and TXT files in the `events/<Event-ID>` folder before ingesting.")
        event_id = st.text_input("Enter Event Folder/ID (e.g., EVT-01):").strip()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Ingest Event Data", use_container_width=True, type="primary") and event_id:
                with st.spinner(f"Extracting and ingesting data for '{event_id}'..."):
                    res = ingest_single_event(event_id)
                    st.success(res.get("message")) if res.get("status") == "success" else st.error(res.get("message"))
        with col2:
            if st.button("🗑️ Delete Event", use_container_width=True) and event_id:
                with st.spinner(f"Deleting records for '{event_id}'..."):
                    res = delete_event(event_id)
                    st.success(res.get("message")) if res.get("status") == "success" else st.error(res.get("message"))


# ==========================================
# 2. UPDATE DATA SECTION (Agent Mode)
# ==========================================
elif main_mode == "✏️ Update Data":
    st.title("✏️ AI Update Agent")
    st.caption("Tell me what you want to modify in natural language. (e.g., 'Update Aditya's phone to 98765' or 'Change IT dept head to Ms. Aditi')")
    
    mem_key = "mem_update_agent"
    if mem_key not in st.session_state:
        st.session_state[mem_key] = [{"role": "assistant", "content": "Hello! I am your Database Agent. What would you like to update today?"}]
    
    for msg in st.session_state[mem_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("E.g., Update the IT dept head to Amit"):
        st.session_state[mem_key].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            handle_conversational_update(user_input, mem_key)


# ==========================================
# 3. ASK A QUERY SECTION
# ==========================================
elif main_mode == "🔍 Ask a Query":
    st.title("🤖 HR Assistant")
    query_option = st.sidebar.selectbox(
        "What type of query do you have?",
        ["👤 Single Employee Profile", "📊 Team & Company-wide (Overall)", "📅 Event Related Query"]
    )

    memory_keys = {
        "👤 Single Employee Profile": "mem_single_profile",
        "📊 Team & Company-wide (Overall)": "mem_overall",
        "📅 Event Related Query": "mem_events"
    }
    current_mem_key = memory_keys[query_option]
    
    if current_mem_key not in st.session_state:
        st.session_state[current_mem_key] = [{"role": "assistant", "content": f"Hello! I am ready to answer your **{query_option[2:]}** queries."}]
    
    for msg in st.session_state[current_mem_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_question := st.chat_input(f"Ask about {query_option[2:]}..."):
        st.session_state[current_mem_key].append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)
            
        with st.chat_message("assistant"):
            if query_option == "👤 Single Employee Profile":
                handle_single_profile(user_question, current_mem_key)
            elif query_option == "📊 Team & Company-wide (Overall)":
                handle_overall_query(user_question, current_mem_key)
            elif query_option == "📅 Event Related Query":
                handle_event_query(user_question, current_mem_key)