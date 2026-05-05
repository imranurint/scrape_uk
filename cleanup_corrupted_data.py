#!/usr/bin/env python3
"""
Cleanup script to remove corrupted data for university ID 8b4176aa14c94c558192a7396e3ab900
"""

import asyncio
import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal
from models.db import Course, CourseDetail, University


async def cleanup_corrupted_data():
    """Remove corrupted data for specific university ID"""
    university_id = uuid.UUID("8b4176aa14c94c558192a7396e3ab900")
    
    async with AsyncSessionLocal() as session:
        try:
            # First, get university info to confirm
            university_result = await session.execute(
                select(University).where(University.id == university_id)
            )
            university = university_result.scalar_one_or_none()
            
            if university:
                print(f"Found university: {university.name}")
                print(f"University ID: {university_id}")
                
                # Delete course details first (due to foreign key constraint)
                course_details_delete = delete(CourseDetail).where(
                    CourseDetail.course_id.in_(
                        select(Course.id).where(Course.university_id == university_id)
                    )
                )
                result_details = await session.execute(course_details_delete)
                print(f"Deleted {result_details.rowcount} course detail records")
                
                # Then delete courses
                courses_delete = delete(Course).where(Course.university_id == university_id)
                result_courses = await session.execute(courses_delete)
                print(f"Deleted {result_courses.rowcount} course records")
                
                # Finally delete university
                university_delete = delete(University).where(University.id == university_id)
                result_university = await session.execute(university_delete)
                print(f"Deleted {result_university.rowcount} university record")
                
                await session.commit()
                print("✅ Cleanup completed successfully!")
                
            else:
                print(f"❌ University with ID {university_id} not found")
                
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(cleanup_corrupted_data())
