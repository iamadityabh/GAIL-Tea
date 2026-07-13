const BASE_URL = "https://gail-tea.onrender.com";

// ==========================================
// 1. QUERY HANDLERS (Returning { markdown: "..." } format)
// ==========================================
export async function querySingleEmployee(question: string) {
  try {
    const response = await fetch(`${BASE_URL}/api/query/single`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    
    const data = await response.json();
    return { markdown: data.reply || "⚠️ Error: Backend returned an empty response." };
  } catch (error: any) {
    return { markdown: `🔌 Connection Failed: Is your backend running? Error: ${error.message}` };
  }
}

export async function queryOverall(question: string) {
  try {
    const response = await fetch(`${BASE_URL}/api/query/overall`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    
    const data = await response.json();
    return { markdown: data.reply || "⚠️ Error: Backend returned an empty response." };
  } catch (error: any) {
    return { markdown: `🔌 Connection Failed: Is your backend running? Error: ${error.message}` };
  }
}

export async function queryEvents(question: string) {
  try {
    const response = await fetch(`${BASE_URL}/api/query/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    
    const data = await response.json();
    return { markdown: data.reply || "⚠️ Error: Backend returned an empty response." };
  } catch (error: any) {
    return { markdown: `🔌 Connection Failed: Is your backend running? Error: ${error.message}` };
  }
}

// ==========================================
// 2. UPDATE AGENT HANDLER
// (Handles the state logic locally since ChatSurface doesn't support it)
// ==========================================
let globalUpdateStage = "INIT";
let globalUpdateContext = {};

export async function updateAgent(userInput: string) {
  try {
    const response = await fetch(`${BASE_URL}/api/update/conversational`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        user_input: userInput, 
        update_stage: globalUpdateStage, 
        update_context: globalUpdateContext 
      }),
    });
    
    const data = await response.json();
    
    // Update local state variables for the next turn
    globalUpdateStage = data.update_stage;
    globalUpdateContext = data.update_context;
    
    return { markdown: data.reply || "⚠️ Update Agent returned an empty response." };
  } catch (error: any) {
    return { markdown: `🔌 Connection Failed: Is your backend running? Error: ${error.message}` };
  }
}

// ==========================================
// 3. INGESTION & DATA MANAGEMENT HANDLERS
// ==========================================
export async function ingestEmployee(folderId: string) {
  try {
    const response = await fetch(`${BASE_URL}/api/manage/employee/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_id: folderId }),
    });
    return await response.json();
  } catch (error: any) {
    return { status: "error", message: `Connection Failed: ${error.message}` };
  }
}

export async function deleteEmployee(folderId: string) {
  try {
    const response = await fetch(`${BASE_URL}/api/manage/employee/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_id: folderId }),
    });
    return await response.json();
  } catch (error: any) {
    return { status: "error", message: `Connection Failed: ${error.message}` };
  }
}

export async function ingestEvent(eventId: string) {
  try {
    const response = await fetch(`${BASE_URL}/api/manage/event/ingest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_id: eventId }),
    });
    return await response.json();
  } catch (error: any) {
    return { status: "error", message: `Connection Failed: ${error.message}` };
  }
}

export async function deleteEvent(eventId: string) {
  try {
    const response = await fetch(`${BASE_URL}/api/manage/event/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ folder_id: eventId }),
    });
    return await response.json();
  } catch (error: any) {
    return { status: "error", message: `Connection Failed: ${error.message}` };
  }
}

export async function addDepartment(deptId: string, deptName: string, headName: string = "", landlineExt: string = "") {
  try {
    const response = await fetch(`${BASE_URL}/api/manage/department/add`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        dept_id: deptId, 
        dept_name: deptName, 
        head_name: headName, 
        landline_ext: landlineExt 
      }),
    });
    return await response.json();
  } catch (error: any) {
    return { status: "error", message: `Connection Failed: ${error.message}` };
  }
}

export async function deleteDepartment(deptId: string) {
  try {
    const response = await fetch(`${BASE_URL}/api/manage/department/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dept_id: deptId }),
    });
    return await response.json();
  } catch (error: any) {
    return { status: "error", message: `Connection Failed: ${error.message}` };
  }
}