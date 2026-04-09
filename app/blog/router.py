import os
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from . import repository, schemas
# from app.auth.dependencies import get_current_user, require_roles, Roles, CurrentUser


router = APIRouter(
  
    prefix="/api/Blog",
    tags=["Blog"]
)
UPLOAD_DIR = "uploads"

# Ensure folder exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------- GET /api/Blog ----------------
@router.get("", response_model=schemas.BlogListResponse)
def get_all_blogs(db: Session = Depends(get_db)):

    blogs = repository.get_all_blogs(db)

    return {
        "count": len(blogs),
        "list": blogs,
        "parameters": {
            "filters": [],
            "order": None,
            "page": None
        }
    }


# ---------------- POST /api/Blog ----------------
@router.post("", response_model=schemas.BlogWrappedResponse)
def create_blog(
    blogTitle: str = Form(...),
    blogContent: str = Form(...),
    description: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # Save file locally
    file_path = os.path.join(UPLOAD_DIR, image.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(image.file.read())

    blog_data = schemas.BlogCreate(
        blogTitle=blogTitle,
        blogContent=blogContent,
        description=description,
        imageUrl=file_path
    )

    created_blog = repository.create_blog(db, blog_data)

    return {
        "success": True,
        "message": "Blog created successfully",
        "data": created_blog
    }

# ---------------- GET /api/Blog/{id} ----------------
@router.get("/{id}", response_model=schemas.BlogResponse)
def get_blog_by_id(id: int, db: Session = Depends(get_db)):

    blog = repository.get_blog_by_id(db, id)

    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    return blog

# ---------------- PUT /api/Blog/{id} ----------------
@router.put("/{id}", response_model=schemas.BlogWrappedResponse)
def update_blog(
    id: int,
    blogTitle: str | None = Form(None),
    blogContent: str | None = Form(None),
    description: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):

    blog = repository.get_blog_by_id(db, id)
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    update_data = {}

    if blogTitle is not None:
        update_data["blogTitle"] = blogTitle

    if blogContent is not None:
        update_data["blogContent"] = blogContent

    if description is not None:
        update_data["description"] = description

    if image is not None:
        file_path = os.path.join("uploads", image.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(image.file.read())
        update_data["imageUrl"] = file_path

    updated_blog = repository.update_blog(db, id, update_data)

    return {
        "success": True,
        "message": "Blog updated successfully",
        "data": updated_blog
    }
# ---------------- DELETE /api/Blog/{id} ----------------
@router.delete("/{id}", response_model=schemas.BlogWrappedResponse)
def delete_blog(id: int, db: Session = Depends(get_db)):

    deleted_blog = repository.delete_blog(db, id)

    if not deleted_blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    return {
        "success": True,
        "message": "Blog deleted permanently",
        "data": deleted_blog
    }