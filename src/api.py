import os
import asyncio
import fitz  # PyMuPDF
import json
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from src.core.db import db
from src.core.config import config
from src.core.logger import logger, log_queue
from src.main import run_scanner

app = FastAPI(title="JobSentinel API")

class Preferences(BaseModel):
    keywords: str
    locations: str
    job_type: str = "All"
    experience_level: str = "All"

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                continue

manager = ConnectionManager()

# Background task to stream log_queue to WebSockets
async def log_broadcaster():
    while True:
        log_entry = await log_queue.get()
        await manager.broadcast(log_entry)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Start the scanner
    asyncio.create_task(run_scanner(broadcast_callback=manager.broadcast))
    # Start the log broadcaster
    asyncio.create_task(log_broadcaster())

@app.websocket("/api/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Wait for any messages from client (not strictly needed but keeps connection alive)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/jobs")
async def get_jobs():
    return db.get_recent_jobs()

@app.get("/api/preferences")
async def get_preferences():
    return {
        "keywords": db.get_setting("keywords", config.JOB_KEYWORDS),
        "locations": db.get_setting("locations", config.JOB_LOCATIONS),
        "job_type": db.get_setting("job_type", "All"),
        "experience_level": db.get_setting("experience_level", "All")
    }

@app.post("/api/preferences")
async def update_preferences(prefs: Preferences):
    db.set_setting("keywords", prefs.keywords)
    db.set_setting("locations", prefs.locations)
    db.set_setting("job_type", prefs.job_type)
    db.set_setting("experience_level", prefs.experience_level)
    return {"status": "success", "message": "Preferences updated"}

@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith('.pdf'):
            return {"status": "error", "message": "Only PDF files are supported"}

        content = await file.read()
        if not content:
            return {"status": "error", "message": "Empty file uploaded"}
        
        temp_pdf = "temp_resume.pdf"
        with open(temp_pdf, "wb") as f:
            f.write(content)
            
        doc = fitz.open(temp_pdf)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        os.remove(temp_pdf)

        if not text.strip():
            return {"status": "error", "message": "Could not extract text from PDF"}

        with open(config.MASTER_RESUME_PATH, "w") as f:
            f.write(text)
            
        logger.info(f"Updated master resume from {file.filename}")
        return {"status": "success", "message": "Resume updated successfully"}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
