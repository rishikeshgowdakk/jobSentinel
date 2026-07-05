import os
import asyncio
import json
import math
import re
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect, Request, Form
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

class PasteResume(BaseModel):
    text: str
    utr: str = ""

# Helper to calculate cosine similarity for local backfill evaluations
def calculate_cosine_similarity(v1, v2):
    if not v1 or not v2:
        return 0.0
    dot_product = sum(x*y for x, y in zip(v1, v2))
    magnitude1 = math.sqrt(sum(x*x for x in v1))
    magnitude2 = math.sqrt(sum(x*x for x in v2))
    if not magnitude1 or not magnitude2:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

# Extract user_id from custom header X-User-ID or fallback
def get_user_id(request: Request) -> str:
    user_id = request.headers.get("x-user-id")
    if not user_id or user_id == "null" or user_id == "undefined":
        return "default_user"
    return user_id

# Connection Manager for WebSockets to support user-specific channels
class ConnectionManager:
    def __init__(self):
        self.connections: List[tuple] = [] # list of (WebSocket, user_id)

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.connections.append((websocket, user_id))

    def disconnect(self, websocket: WebSocket):
        self.connections = [c for c in self.connections if c[0] != websocket]

    async def send_to_user(self, user_id: str, message: dict):
        for ws, uid in self.connections:
            if uid == user_id:
                try:
                    await ws.send_json(message)
                except Exception:
                    continue

    async def broadcast(self, message: dict):
        for ws, uid in self.connections:
            try:
                await ws.send_json(message)
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

# Background task to evaluate existing database jobs against a newly uploaded resume
async def evaluate_existing_jobs(user_id: str):
    try:
        logger.info(f"Backfill: Evaluating existing jobs for newly uploaded profile of user {user_id}...")
        profile = db.get_profile(user_id)
        if not profile:
            logger.warning(f"Backfill: No profile found for user {user_id}")
            return
            
        cur = db.conn.cursor()
        cur.execute("SELECT job_id, title, description, embedding FROM processed_jobs")
        rows = cur.fetchall()
        cur.close()
        
        if not rows:
            logger.info("Backfill: No global crawled jobs found in database to evaluate.")
            return

        analyzer = GeminiAnalyzer()
        prefs = db.get_user_preferences(user_id)
        
        logger.info(f"Backfill: Matching {len(rows)} existing jobs against new resume profile for {user_id}...")
        
        for row in rows:
            job_id, title, description, embedding_str = row
            job_embedding = json.loads(embedding_str) if embedding_str else []
            
            match_analysis = analyzer.analyze_job_semantic(
                profile=profile,
                job_title=title,
                job_description=description,
                target_seniority=prefs.get("experience_level", "All"),
                target_job_type=prefs.get("job_type", "All")
            )
            
            vector_sim = calculate_cosine_similarity(job_embedding, profile.get('embedding', []))
            semantic_score = match_analysis.get('matchScore', 60)
            combined_score = int(0.25 * (vector_sim * 100) + 0.75 * semantic_score)
            combined_score = min(max(combined_score, 0), 100)
            
            match_analysis['matchScore'] = combined_score
            match_analysis['job_id'] = job_id
            
            db.save_match(user_id, match_analysis)
            
        logger.info(f"Backfill: Evaluation complete for user {user_id}. {len(rows)} jobs processed.")
    except Exception as e:
        logger.error(f"Backfill matching failed for user {user_id}: {e}")

@app.on_event("startup")
async def startup_event():
    # Start the scanner with targeted user notifications/broadcast callback
    asyncio.create_task(run_scanner(broadcast_callback=manager.send_to_user))
    # Start the log broadcaster
    asyncio.create_task(log_broadcaster())

@app.websocket("/api/ws/stream")
async def websocket_endpoint(websocket: WebSocket, user_id: str = "default_user"):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep WebSocket connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/jobs")
async def get_jobs(request: Request):
    user_id = get_user_id(request)
    return db.get_recent_jobs(user_id=user_id)

@app.post("/api/jobs/{job_id}/status")
async def update_job_status(job_id: str, update: JobStatusUpdate, request: Request):
    user_id = get_user_id(request)
    db.set_job_status(user_id, job_id, update.status)
    return {"status": "success", "message": f"Job status updated to {update.status}"}

@app.get("/api/profile")
async def get_profile(request: Request):
    user_id = get_user_id(request)
    profile = db.get_profile(user_id)
    if profile:
        return profile["structured_data"]
    return None

@app.get("/api/preferences")
async def get_preferences(request: Request):
    user_id = get_user_id(request)
    return {
        "keywords": db.get_setting(user_id, "keywords", config.JOB_KEYWORDS),
        "locations": db.get_setting(user_id, "locations", config.JOB_LOCATIONS),
        "job_type": db.get_setting(user_id, "job_type", "All"),
        "experience_level": db.get_setting(user_id, "experience_level", "All")
    }

@app.post("/api/preferences")
async def update_preferences(prefs: Preferences, request: Request):
    user_id = get_user_id(request)
    db.set_setting(user_id, "keywords", prefs.keywords)
    db.set_setting(user_id, "locations", prefs.locations)
    db.set_setting(user_id, "job_type", prefs.job_type)
    db.set_setting(user_id, "experience_level", prefs.experience_level)
    return {"status": "success", "message": "Preferences updated"}

@app.post("/api/resume/upload")
async def upload_resume(background_tasks: BackgroundTasks, request: Request, file: UploadFile = File(...), utr: str = Form("")):
    try:
        user_id = get_user_id(request)
        
        # Clean and validate UPI transaction UTR format
        utr_clean = utr.strip()
        if utr_clean:
            if not re.match(r'^\d{12}$', utr_clean):
                return {"status": "error", "message": "Invalid UTR format. UTR must be a 12-digit number."}
                
            if db.is_utr_used(utr_clean):
                return {"status": "error", "message": "This transaction reference (UTR) has already been used."}
        filename = file.filename.lower()
        if not filename.endswith(('.pdf', '.txt', '.md')):
            return {"status": "error", "message": "Only PDF, TXT, and MD files are supported"}

        content = await file.read()
        if not content:
            return {"status": "error", "message": "Empty file uploaded"}
        
        if filename.endswith(('.txt', '.md')):
            text = content.decode('utf-8', errors='ignore')
        else:
            try:
                doc = fitz.open(stream=content, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
            except Exception as pdf_e:
                logger.error(f"PyMuPDF stream error: {pdf_e}")
                return {"status": "error", "message": "Failed to parse PDF file"}

        if not text.strip():
            return {"status": "error", "message": "Could not extract text from file"}

        # Run parsing & embeddings
        analyzer = GeminiAnalyzer()
        logger.info(f"Extracting structured details from uploaded resume for user {user_id}...")
        structured_data = analyzer.extract_resume_parameters(text)
        
        logger.info(f"Generating semantic embeddings for resume of user {user_id}...")
        embedding = analyzer.get_embedding(text)
        
        # Save payment transaction to prevent double spending
        if utr_clean:
            db.save_payment(utr_clean, user_id, 1.0)
        
        # Save to database
        db.save_profile(user_id, text, structured_data, embedding)
        
        # Schedule backfill evaluation for existing database jobs
        background_tasks.add_task(evaluate_existing_jobs, user_id)
        
        return {"status": "success", "message": "Resume uploaded successfully. Instant match evaluation started in background!"}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/resume/paste")
async def paste_resume(req: PasteResume, background_tasks: BackgroundTasks, request: Request):
    try:
        user_id = get_user_id(request)
        
        # Clean and validate UPI transaction UTR format
        utr_clean = req.utr.strip()
        if utr_clean:
            if not re.match(r'^\d{12}$', utr_clean):
                return {"status": "error", "message": "Invalid UTR format. UTR must be a 12-digit number."}
                
            if db.is_utr_used(utr_clean):
                return {"status": "error", "message": "This transaction reference (UTR) has already been used."}
        text = req.text
        if not text or not text.strip():
            return {"status": "error", "message": "Empty resume text provided"}
            
        # Run parsing & embeddings
        analyzer = GeminiAnalyzer()
        logger.info(f"Extracting structured details from pasted resume for user {user_id}...")
        structured_data = analyzer.extract_resume_parameters(text)
        
        logger.info(f"Generating semantic embeddings for pasted resume of user {user_id}...")
        embedding = analyzer.get_embedding(text)
        
        # Save payment transaction to prevent double spending
        if utr_clean:
            db.save_payment(utr_clean, user_id, 1.0)
        
        # Save to database
        db.save_profile(user_id, text, structured_data, embedding)
        
        # Schedule backfill evaluation for existing database jobs
        background_tasks.add_task(evaluate_existing_jobs, user_id)
        
        return {"status": "success", "message": "Resume text processed successfully. Instant match evaluation started in background!"}
    except Exception as e:
        logger.error(f"Paste error: {e}")
        return {"status": "error", "message": str(e)}



@app.delete("/api/resume")
async def delete_resume(request: Request):
    try:
        user_id = get_user_id(request)
        db.delete_profile(user_id)
        return {"status": "success", "message": "Resume profile removed successfully"}
    except Exception as e:
        logger.error(f"Delete profile error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/market-insights")
async def get_market_insights(request: Request):
    user_id = get_user_id(request)
    jobs = db.get_recent_jobs(user_id=user_id, limit=200) # Fetch up to 200 jobs for robust statistical insights
    analyzer = GeminiAnalyzer()
    return analyzer.generate_market_insights(jobs)

@app.get("/api/up-skill")
async def get_upskill_recommendations(request: Request):
    user_id = get_user_id(request)
    profile = db.get_profile(user_id)
    if not profile:
        return []
    
    # Gather distinct missing skills from match logs
    jobs = db.get_recent_jobs(user_id=user_id, limit=50)
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
async def get_resume_suggestions(request: Request):
    user_id = get_user_id(request)
    profile = db.get_profile(user_id)
    if not profile:
        return None
    jobs = db.get_recent_jobs(user_id=user_id, limit=15)
    analyzer = GeminiAnalyzer()
    return analyzer.generate_resume_suggestions(profile, jobs)

@app.get("/api/analytics")
async def get_analytics(request: Request):
    user_id = get_user_id(request)
    jobs = db.get_recent_jobs(user_id=user_id, limit=100)
    profile = db.get_profile(user_id)
    
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
        "marketDemandScore": min(100, 60 + total_jobs) if total_jobs > 0 else 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
