#!/usr/bin/env python3
"""
Script to query SQLite database and export to JSON files
Creates a data folder with university-named files
"""

import asyncio
import json
import os
import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal
from models.db import Course, University


def sanitize_filename(name):
    """Sanitize university name for filename"""
    # Replace invalid characters with underscore
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    return sanitized


async def export_to_json():
    """Export database to JSON files"""
    async with AsyncSessionLocal() as session:
        try:
            # Create data folder
            data_folder = 'data'
            if not os.path.exists(data_folder):
                os.makedirs(data_folder)
            
            # Get all universities with their courses
            query = (
                select(University)
                .outerjoin(Course, University.id == Course.university_id)
            )
            
            result = await session.execute(query)
            universities = result.scalars().unique().all()
            
            # Export each university to its own file
            for uni in universities:
                # Load courses for this university
                await session.refresh(uni, attribute_names=['courses'])
                
                # Convert courses to dict with raw_json
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
                        "raw_json": course.raw_json,  # Include raw_json field
                    }
                    courses.append(course_dict)
                
                # Create filename from university name
                filename = sanitize_filename(uni.name) + '.json'
                filepath = os.path.join(data_folder, filename)
                
                # Save to file
                with open(filepath, 'w') as f:
                    json.dump(courses, f, indent=2)
                
                print(f"✅ {uni.name}: {len(courses)} courses -> {filename}")
            
            print(f"\n✅ All data exported to '{data_folder}' folder")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(export_to_json())