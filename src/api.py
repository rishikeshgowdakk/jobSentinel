import os
import asyncio
import json
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from src.core.db import db
from src.core.config import config
from src.core.logger import logger, log_queue
from src.main import run_scanner
from src.intelligence.gemini import GeminiAnalyzer

app = FastAPI(title="JobSentinel API")

class Preferences(BaseModel):
    keywords: str
    locations: str
    job_type: str = "All"
    experience_level: str = "All"

class JobStatusUpdate(BaseModel):
    status: str

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
            # Wait for any messages from client to keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/jobs")
async def get_jobs():
    return db.get_recent_jobs()

@app.post("/api/jobs/{job_id}/status")
async def update_job_status(job_id: str, update: JobStatusUpdate):
    db.set_job_status(job_id, update.status)
    return {"status": "success", "message": f"Job status updated to {update.status}"}

@app.get("/api/profile")
async def get_profile():
    profile = db.get_profile()
    if profile:
        return profile["structured_data"]
    return None

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
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)

        if not text.strip():
            return {"status": "error", "message": "Could not extract text from PDF"}

        # Run parsing & embeddings
        analyzer = GeminiAnalyzer()
        logger.info("Extracting structured details from uploaded resume...")
        structured_data = analyzer.extract_resume_parameters(text)
        
        logger.info("Generating semantic embeddings for the resume...")
        embedding = analyzer.get_embedding(text)
        
        # Save to database
        db.save_profile(text, structured_data, embedding)
        
        return {"status": "success", "message": "Resume uploaded and analyzed successfully"}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/market-insights")
async def get_market_insights():
    jobs = db.get_recent_jobs(limit=30)
    analyzer = GeminiAnalyzer()
    return analyzer.generate_market_insights(jobs)

@app.get("/api/up-skill")
async def get_upskill_recommendations():
    profile = db.get_profile()
    if not profile:
        return []
    
    # Gather distinct missing skills from match logs
    jobs = db.get_recent_jobs(limit=30)
    missing_set = set()
    for j in jobs:
        for s in j.get("missingSkills", []):
            if s:
                missing_set.add(s)
                
    missing_list = list(missing_set)[:5] # Suggest for top 5 missing skills
    if not missing_list:
        missing_list = ["Docker", "Kubernetes", "Kafka"]
        
    analyzer = GeminiAnalyzer()
    return analyzer.generate_learning_recommendations(missing_list)

@app.get("/api/resume-suggestions")
async def get_resume_suggestions():
    profile = db.get_profile()
    if not profile:
        return None
    jobs = db.get_recent_jobs(limit=15)
    analyzer = GeminiAnalyzer()
    return analyzer.generate_resume_suggestions(profile, jobs)

@app.get("/api/analytics")
async def get_analytics():
    jobs = db.get_recent_jobs(limit=100)
    profile = db.get_profile()
    
    total_jobs = len(jobs)
    matched_jobs = len([j for j in jobs if j.get("matchScore", 0) >= 80])
    saved_jobs = len([j for j in jobs if j.get("status") == "saved"])
    applied_jobs = len([j for j in jobs if j.get("status") == "applied"])
    interviewing_jobs = len([j for j in jobs if j.get("status") == "interviewing"])
    rejected_jobs = len([j for j in jobs if j.get("status") == "rejected"])
    
    success_rate = int((interviewing_jobs / max(applied_jobs, 1)) * 100)
    success_rate = min(100, success_rate)
    
    resume_score = 0
    profile_strength = 0
    if profile:
        sd = profile.get("structured_data", {})
        # Simple heuristics for profile strength and resume score
        yoe = sd.get("yoe", 0)
        skills = len(sd.get("skills", []))
        projects = len(sd.get("projects", []))
        
        resume_score = 50 + min(yoe * 5, 20) + min(skills * 2, 20) + min(projects * 5, 10)
        resume_score = min(100, resume_score)
        
        profile_strength = 40 + min(skills * 5, 30) + min(projects * 10, 30)
        profile_strength = min(100, profile_strength)
    
    return {
        "totalJobs": total_jobs,
        "matchedCount": matched_jobs,
        "savedCount": saved_jobs,
        "appliedCount": applied_jobs,
        "interviewCount": interviewing_jobs,
        "rejectedCount": rejected_jobs,
        "successRate": success_rate,
        "resumeScore": resume_score,
        "profileStrength": profile_strength,
        "marketDemandScore": 82 if total_jobs > 0 else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
