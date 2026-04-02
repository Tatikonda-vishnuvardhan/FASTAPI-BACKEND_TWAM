from sqlalchemy.orm import Session
from . import models


# -------- GET ALL --------
def get_all_blogs(db: Session):
    return db.query(models.Blog)\
        .filter(models.Blog.deletedInd == False)\
        .filter(models.Blog.isActive == True)\
        .all()


# -------- CREATE --------
def create_blog(db: Session, blog_data):
    db_blog = models.Blog(**blog_data.dict())
    db.add(db_blog)
    db.commit()
    db.refresh(db_blog)
    return db_blog

# -------- GET BY ID --------
def get_blog_by_id(db: Session, blog_id: int):
    return db.query(models.Blog)\
        .filter(models.Blog.blogId == blog_id)\
        .filter(models.Blog.deletedInd == False)\
        .first()
# -------- UPDATE --------
def update_blog(db: Session, blog_id: int, blog_data: dict):
    blog = db.query(models.Blog).filter(models.Blog.blogId == blog_id).first()

    if not blog:
        return None

    for key, value in blog_data.items():
        setattr(blog, key, value)

    db.commit()
    db.refresh(blog)
    return blog

# -------- DELETE (SOFT DELETE) --------
def delete_blog(db: Session, blog_id: int):
    blog = db.query(models.Blog).filter(models.Blog.blogId == blog_id).first()

    if not blog:
        return None

    db.delete(blog)
    db.commit()

    return blog