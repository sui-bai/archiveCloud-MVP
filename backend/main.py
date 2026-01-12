from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import shutil
import json
from datetime import datetime

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
META_FILE = Path("metadata.jsonl")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    tags = generate_tags(file.filename)

    record = {
    "id": f"{int(datetime.utcnow().timestamp())}_{file.filename}",
    "filename": file.filename,
    "saved_to": str(file_path),
    "tags": tags,
    "uploaded_at": datetime.utcnow().isoformat() + "Z",
    }

    with open(META_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record

@app.get("/search")
def search(q: str):
    q_lower = q.lower()
    results = []

    if META_FILE.exists():
        with open(META_FILE, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                hay = " ".join([item["filename"]] + item.get("tags", [])).lower()
                if q_lower in hay:
                    results.append(item)

    return {"query": q, "count": len(results), "results": results}
