import asyncio
import json
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from config.database import AsyncSessionLocal
from models.db import University, Course, CourseDetail

# Helper to handle UUID and Datetime serialization in JSON
class DBEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def export_all_universities_json():
    async with AsyncSessionLocal() as session:
        # Query ALL universities with courses and details eagerly loaded
        stmt = (
            select(University)
            .options(
                selectinload(University.courses).selectinload(Course.details)
            )
        )
        
        result = await session.execute(stmt)
        universities = result.scalars().all()

        output_data = []

        for uni in universities:
            uni_dict = {
                "university_id": uni.id,
                "university_name": uni.name,
                "location": uni.location,
                "website": uni.website,
                "courses": []
            }

            for course in uni.courses:
                course_data = {
                    "course_id": course.id,
                    "name": course.name,
                    "degree": course.degree,
                    "level": course.level,
                    "department": course.department,
                    "study_mode": course.study_mode,
                    "duration_years": float(course.duration_years) if course.duration_years else None,
                    "fees": {
                        "uk": course.fee_uk_yearly,
                        "international": course.fee_intl_yearly
                    },
                    "url": course.source_url,
                    # Merge deep details into the course object
                    "details": {
                        "description": course.details.description if course.details else None,
                        "entry_requirements": course.details.entry_requirements if course.details else None,
                        "modules": course.details.modules if course.details else None,
                        "career_prospects": course.details.career_prospects if course.details else None,
                    }
                }
                uni_dict["courses"].append(course_data)
            
            output_data.append(uni_dict)

        # Write to JSON file
        with open("all_universities_data.json", "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, cls=DBEncoder)
        
    print(f"Successfully exported {len(output_data)} universities to all_universities_data.json")

if __name__ == "__main__":
    asyncio.run(export_all_universities_json())