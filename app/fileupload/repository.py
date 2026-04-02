import os
import base64
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from .models import FileUpload

BASE_URL = os.getenv("BASE_URL", "")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

def _to_dict(r: FileUpload) -> dict:
    return {
        "fileUploadId": r.fileUploadId,
        "fileName": r.fileName,
        "filePath": r.filePath,
        "fileType": r.fileType,
        "fileUrl": f"{BASE_URL}{r.filePath}" if r.filePath else None,
        "createdDate": r.createdDate,
    }

def get_all(db: Session, filters, order_ascending, order_property, page_index, page_size):
    query = db.query(FileUpload).filter(FileUpload.deletedInd == False)
    if filters:
        for f in filters:
            col = getattr(FileUpload, f.get("property", ""), None)
            if col is not None: query = query.filter(col == f.get("value"))
    if order_property:
        col = getattr(FileUpload, order_property, None)
        if col: query = query.order_by(asc(col) if order_ascending is not False else desc(col))
    total = query.count()
    if page_index and page_size: query = query.offset((page_index - 1) * page_size).limit(page_size)
    return {"count": total, "list": [_to_dict(r) for r in query.all()], "parameters": None}

def create(db: Session, data) -> int:
    file_path = data.filePath
    # If base64 file data is provided, save to disk
    if data.fileData and data.fileName:
        try:
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            file_bytes = base64.b64decode(data.fileData)
            safe_name = os.path.basename(data.fileName)
            disk_path = os.path.join(UPLOAD_DIR, safe_name)
            with open(disk_path, "wb") as f:
                f.write(file_bytes)
            file_path = f"{UPLOAD_DIR}/{safe_name}"
        except Exception as e:
            print(f"[FileUpload] Failed to save file: {e}")
    entity = FileUpload(
        fileName=data.fileName, filePath=file_path,
        fileType=data.fileType, createdDate=datetime.now(timezone.utc), deletedInd=False
    )
    db.add(entity); db.commit(); db.refresh(entity)
    return entity.fileUploadId