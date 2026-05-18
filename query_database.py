#!/usr/bin/env python3
"""
Script to query SQLite database and show university and course counts
"""

import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal
from models.db import Course, University


async def query_database():
    """Query database for university and course counts"""
    async with AsyncSessionLocal() as session:
        try:
            # Count total universities
            uni_count_result = await session.execute(
                select(func.count()).select_from(University)
            )
            total_universities = uni_count_result.scalar()
            print(f"🎓 Total Universities: {total_universities}")
            print()

            # Count total courses
            course_count_result = await session.execute(
                select(func.count()).select_from(Course)
            )
            total_courses = course_count_result.scalar()
            print(f"📚 Total Courses: {total_courses}")
            print()

            # Get all universities with their course counts
            query = (
                select(
                    University.id,
                    University.name,
                    University.location,
                    func.count(Course.id).label('course_count')
                )
                .outerjoin(Course, University.id == Course.university_id)
                .group_by(University.id, University.name, University.location)
                .order_by(func.count(Course.id).desc())
            )
            
            result = await session.execute(query)
            universities = result.all()
            
            print("📊 University Course Counts:")
            print("-" * 80)
            print(f"{'University Name':<40} {'Location':<20} {'Courses':>10}")
            print("-" * 80)
            
            for uni_id, name, location, course_count in universities:
                location_str = location or "N/A"
                print(f"{name:<40} {location_str:<20} {course_count:>10}")
            
            print("-" * 80)
            print(f"{'TOTAL':<40} {'':<20} {total_courses:>10}")
            print()
            
            # Show universities with no courses
            no_courses = [u for u in universities if u[3] == 0]
            if no_courses:
                print(f"⚠️  Universities with no courses: {len(no_courses)}")
                for uni_id, name, location, course_count in no_courses:
                    print(f"   - {name}")
            
        except Exception as e:
            print(f"❌ Error querying database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(query_database())
