from fastapi import FastAPI, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import json
from datetime import datetime

app = FastAPI()

# ========== STORAGE ==========

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
# Local JSONL metadata store (one JSON record per line)
META_FILE = Path("metadata.jsonl")

# ========== HELPERS ==========

# Generate basic metadata tags from file name
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

# Read all metadata records from META_FILE
def load_all_records():
    records = []
    if META_FILE.exists():
        with open(META_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records

# Append one metadata record to META_FILE
def append_record(record: dict): 
    with open(META_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

# Rewrite META_FILE after deletions (MVP approach)
def rewrite_records(records: list[dict]):
    with open(META_FILE, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

# Generate a non-conflicting file path under UPLOAD_DIR
def unique_upload_path(original_name: str) -> Path:
    base = Path(original_name).stem
    suffix = Path(original_name).suffix  # includes dot, e.g. ".png"

    file_path = UPLOAD_DIR / original_name
    counter = 2
    while file_path.exists():
        file_path = UPLOAD_DIR / f"{base}__{counter}{suffix}"
        counter += 1
    return file_path


# ========== CORE ROUTES ==========

@app.get("/health")
def health():
    return {"status": "ok"}

# Upload file and generate metadata
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    original_name = file.filename

    # Prevent overwrite on duplicate uploads
    file_path = unique_upload_path(original_name)

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Generate tags
    tags = generate_tags(original_name)

    # Create metadata record
    record = {
        "id": f"{int(datetime.utcnow().timestamp())}_{original_name}",
        "filename": original_name,
        "saved_to": str(file_path),
        "tags": tags,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
    }

    # Append record to metadata file ("database")
    append_record(record)

    return record

# Search uploaded assets by keyword
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

# ========== ADMIN ROUTES ==========

# List all uploaded asset records (simple admin view)
@app.get("/assets")
def list_assets():
    records = load_all_records()
    return {"count": len(records), "results": records}

# Delete one asset record by id, and delete its saved file if it exists
@app.delete("/assets/{asset_id}")
def delete_asset(asset_id: str):
    records = load_all_records()

    target = None
    kept = []
    for r in records:
        if r.get("id") == asset_id and target is None:
            target = r
        else:
            kept.append(r)

    if target is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Delete the actual file
    file_path = Path(target["saved_to"])
    if file_path.exists():
        file_path.unlink()

    # Remove record from metadata store
    rewrite_records(kept)

    return {"deleted_id": asset_id, "remaining": len(kept)}
