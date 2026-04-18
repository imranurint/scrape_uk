# models/__init__.py
from models.db import Base, Course, CourseDetail, University

__all__ = ["Base", "University", "Course", "CourseDetail"]
