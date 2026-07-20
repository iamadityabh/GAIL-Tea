import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

# Import your existing business logic files
from config import get_db_engine
from query_single import handle_single_profile_api
from query_overall import handle_overall_query_api
from query_events import handle_event_query_api
from ingest import ingest_single_employee, delete_employee, ingest_single_event, delete_event
from update_agent import handle_conversational_update_api, refresh_departments_cache
from sqlalchemy import text

app = FastAPI(title="GAIL HR Chatbot Backend API")

# Allow your Lovable frontend to talk to this Python server securely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Real deployment mein front-end ka exact local URL daal dena
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = get_db_engine()

# ==========================================
# 0. PYDANTIC DATA VALIDATION SCHEMAS
# ==========================================
class QueryRequest(BaseModel):
    question: str

class UpdateRequest(BaseModel):
    user_input: str
    update_stage: str = "INIT"
    update_context: Dict[str, Any] = {}

class IngestRequest(BaseModel):
    folder_id: str

class DeptRequest(BaseModel):
    dept_id: str
    dept_name: Optional[str] = None
    head_name: Optional[str] = None
    landline_ext: Optional[str] = None

# ==========================================
# 1. SEARCH ENDPOINTS (Ask a Query)
# ==========================================
@app.post("/api/query/single")
async def query_single(req: QueryRequest):
    try:
        # Puraani system user chat parameters memory key par depend karti thi,
        # API framework mein hum seedhe clean response text process karke bhejenge
        response_text = handle_single_profile_api(req.question)
        return {"status": "success", "reply": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query/overall")
async def query_overall(req: QueryRequest):
    try:
        response_text = handle_overall_query_api(req.question)
        return {"status": "success", "reply": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query/events")
async def query_events(req: QueryRequest):
    try:
        response_text = handle_event_query_api(req.question)
        return {"status": "success", "reply": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 2. UPDATE DATA ENDPOINT (AI Update Agent State-Machine)
# ==========================================
@app.post("/api/update/conversational")
async def update_conversational(req: UpdateRequest):
    try:
        # Frontend state variables handle karke har response ke saath raw updates bhejega
        response_data = handle_conversational_update_api(
            req.user_input, req.update_stage, req.update_context
        )
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 3. ADMINISTRATIVE DATA INGESTION (Add Data)
# ==========================================
@app.post("/api/manage/employee/ingest")
async def api_ingest_employee(req: IngestRequest):
    res = ingest_single_employee(req.folder_id)
    return res

@app.post("/api/manage/employee/delete")
async def api_delete_employee(req: IngestRequest):
    res = delete_employee(req.folder_id)
    return res

@app.post("/api/manage/event/ingest")
async def api_ingest_event(req: IngestRequest):
    res = ingest_single_event(req.folder_id)
    return res

@app.post("/api/manage/event/delete")
async def api_delete_event(req: IngestRequest):
    res = delete_event(req.folder_id)
    return res

@app.post("/api/manage/department/add")
async def api_add_department(req: DeptRequest):
    if not req.dept_id or not req.dept_name:
        raise HTTPException(status_code=400, detail="Missing Department ID or Name")
    try:
        # 🔥 'begin()' use karo taaki manual commit na karna pade aur transaction safe rahe
        with engine.begin() as conn: 
            conn.execute(
                text("""
                    INSERT INTO departments (department_id, department_name, head_name, landline_ext) 
                    VALUES (:id, :name, :head, :landline)
                """), 
                {
                    "id": req.dept_id, 
                    "name": req.dept_name, 
                    # 🔥 THE FIX: Agar empty string aayi, toh automatically "N/A" save kar do
                    "head": req.head_name if req.head_name else "N/A", 
                    "landline": req.landline_ext if req.landline_ext else "N/A"
                }
            )
        # Cache refresh function ko transaction ke bahar run karna better hai
        refresh_departments_cache(engine)
        return {"status": "success", "message": f"Department '{req.dept_name}' added and cache synced!"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/manage/department/delete")
async def api_delete_department(req: DeptRequest):
    try:
        with engine.connect() as conn:
            conn.execute(text("DELETE FROM departments WHERE department_id = :id"), {"id": req.dept_id})
            conn.commit()
        refresh_departments_cache(engine)
        return {"status": "success", "message": f"Department ID {req.dept_id} deleted and cache synced!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)