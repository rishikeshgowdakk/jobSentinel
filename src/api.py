import os
import asyncio
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.core.db import db
from src.core.config import config
from src.core.logger import logger
from src.main import run_scanner

app = FastAPI(title="JobSentinel API")

class Preferences(BaseModel):
    keywords: str
    locations: str
    job_type: str = "All"
    experience_level: str = "All"

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
    # Start the scanner in the background
    asyncio.create_task(run_scanner())

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
        # Validate extension
        if not file.filename.lower().endswith('.pdf'):
            return {"status": "error", "message": "Only PDF files are supported"}

        content = await file.read()
        if not content:
            return {"status": "error", "message": "Empty file uploaded"}
        
        # Save temp PDF
        temp_pdf = "temp_resume.pdf"
        try:
            with open(temp_pdf, "wb") as f:
                f.write(content)
        except Exception as write_err:
            logger.error(f"Failed to write temp PDF: {write_err}")
            return {"status": "error", "message": f"Server File Error: {str(write_err)}"}
            
        # Extract text using PyMuPDF
        try:
            doc = fitz.open(temp_pdf)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            if not text.strip():
                os.remove(temp_pdf)
                return {"status": "error", "message": "Could not extract any text from this PDF. Is it a scanned image?"}
                
        except Exception as fitz_err:
            logger.error(f"PyMuPDF failed to parse PDF: {fitz_err}")
            if os.path.exists(temp_pdf): os.remove(temp_pdf)
            return {"status": "error", "message": f"PDF Parse Error: {str(fitz_err)}"}

        os.remove(temp_pdf)
        
        # Save as master_resume.md
        try:
            with open(config.MASTER_RESUME_PATH, "w") as f:
                f.write(text)
        except Exception as md_err:
            logger.error(f"Failed to save master_resume.md: {md_err}")
            return {"status": "error", "message": f"Storage Error: {str(md_err)}"}
            
        logger.info(f"Updated master resume from {file.filename}")
        return {"status": "success", "message": "Resume updated and parsed successfully"}
    except Exception as e:
        logger.error(f"Unexpected error in upload_resume: {e}")
        return {"status": "error", "message": f"Unexpected System Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
