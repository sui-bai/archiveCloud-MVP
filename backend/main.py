from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import shutil

app = FastAPI()

def generate_tags(filename: str):
    name = filename.lower()
    tags = []

    # Time
    if any(k in name for k in ["revolution", "independence", "1776", "washington"]):
        tags.append("american_revolution")

    # Location
    if any(k in name for k in ["nashville", "tennessee", "tn"]):
        tags.append("nashville")

    # File Type
    ext = name.split(".")[-1]
    tags.append(ext)

    return tags


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    tags = generate_tags(file.filename)

    return {
        "filename": file.filename,
        "tags": tags,
        "saved_to": str(file_path)
    }