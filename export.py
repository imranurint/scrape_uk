#!/usr/bin/env python3
"""
Script to query SQLite database and export to JSON
Format: { "University Name": [courses...] }
"""

import asyncio
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal
from models.db import Course, University


async def export_to_json():
    """Export database to JSON format"""
    async with AsyncSessionLocal() as session:
        try:
            # Get all universities with their courses
            query = (
                select(University)
                .outerjoin(Course, University.id == Course.university_id)
            )
            
            result = await session.execute(query)
            universities = result.scalars().unique().all()
            
            # Build JSON structure
            data = {}
            for uni in universities:
                # Load courses for this university
                await session.refresh(uni, attribute_names=['courses'])
                
                # Convert courses to dict
                courses = []
                for course in uni.courses:
                    course_dict = {
                        "name": course.name,
                        "degree": course.degree,
                        "level": course.level,
                        "department": course.department,
                        "ucas_code": course.ucas_code,
                        "study_mode": course.study_mode,
                        "duration_years": str(course.duration_years) if course.duration_years else None,
                        "start_month": course.start_month,
                        "fee_uk_yearly": course.fee_uk_yearly,
                        "fee_intl_yearly": course.fee_intl_yearly,
                        "source_url": course.source_url,
                    }
                    courses.append(course_dict)
                
                data[uni.name] = courses
            
            # Save to file
            with open('universities_data.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ Data saved to universities_data.json")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(export_to_json())