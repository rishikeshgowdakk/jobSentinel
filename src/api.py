import os
import asyncio
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from src.core.db import db
from src.core.config import config
from src.core.logger import logger
from src.main import run_scanner

app = FastAPI(title="JobSentinel API")

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

@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    try:
        content = await file.read()
        
        # Save temp PDF
        temp_pdf = "temp_resume.pdf"
        with open(temp_pdf, "wb") as f:
            f.write(content)
            
        # Extract text using PyMuPDF
        doc = fitz.open(temp_pdf)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        os.remove(temp_pdf)
        
        # Save as master_resume.md
        with open(config.MASTER_RESUME_PATH, "w") as f:
            f.write(text)
            
        logger.info(f"Updated master resume from {file.filename}")
        return {"status": "success", "message": "Resume updated and parsed successfully"}
    except Exception as e:
        logger.error(f"Failed to upload resume: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
