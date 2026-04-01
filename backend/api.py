from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import shutil
import os
import uuid
import logging
from utils.parser import extract_text_from_pdf
from utils.cleaner import clean_text
from utils.scorer import compute_scores, generate_feedback
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "temp")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

skills_path = os.path.join(BASE_DIR, "skills.txt")
with open(skills_path) as f:
    skills_list = set(
    line.strip().lower()
    for line in f
    if line.strip()
)
def generate_top_improvements(explanations):
    items = []

    for skill, data in explanations.items():
        if data["status"] in ["missing", "weak"]:
            score = 0
            if data["importance"] == "high":
                score += 2
            if data["status"] == "missing":
                score += 2
            items.append((score, skill))

    items.sort(key=lambda x: (x[0], x[1]), reverse=True)

    return [s.replace("_", " ").title() for _, s in items[:3]]


@app.post("/analyze/")
async def analyze_resume(
    file: UploadFile = File(...),
    job_desc: str = Form(...)
):
    file_path = None

    try:
        if not file.filename.endswith(".pdf"):
            return JSONResponse(status_code=400, content={"error": "Only PDF files are allowed"})

        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        resume_text = extract_text_from_pdf(file_path)

        if not resume_text or not resume_text.strip():
            return JSONResponse(status_code=400, content={"error": "Could not read resume data"})

        job_clean = clean_text(job_desc)

        if not job_clean.strip():
            return JSONResponse(status_code=400, content={"error": "Empty job description"})

        job_skills = set()
        for skill in skills_list:
            if skill in job_clean:
                job_skills.add(skill)

        result = compute_scores(
            job_clean,
            resume_text,
            job_skills,
            skills_list
        )

        feedback = generate_feedback(
            result["explanations"],
            result["skill_evidence"],
            job_skills
        )

        top_improvements = generate_top_improvements(result["explanations"])

        return {
            "score": round(result["final_score"] * 100, 2),
            "matched_skills": [s.replace("_", " ").title() for s in result["matched"]],
            "missing_skills": [s.replace("_", " ").title() for s in result["missing"]],
            "feedback": feedback,
            "top_improvements": top_improvements
        }

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal Server Error during processing"})

    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logging.warning(f"Failed to delete temp file {file_path}: {e}")