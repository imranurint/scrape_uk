#!/usr/bin/env python3
"""
Script to query SQLite database and show university and course counts
"""

import asyncio
import os
import sys

# Add project root to sys.path to allow running from within db_script/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal
from models.db import Course, University


async def query_database():
    """Query database for university and course counts and save to data/summary.txt"""
    async with AsyncSessionLocal() as session:
        try:
            # Count total universities
            uni_count_result = await session.execute(
                select(func.count()).select_from(University)
            )
            total_universities = uni_count_result.scalar()
            
            # Count total courses
            course_count_result = await session.execute(
                select(func.count()).select_from(Course)
            )
            total_courses = course_count_result.scalar()

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

            # Ensure data directory exists
            os.makedirs("data", exist_ok=True)
            
            summary_path = os.path.join("data", "summary.txt")
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(f"🎓 Total Universities: {total_universities}\n\n")
                f.write(f"📚 Total Courses: {total_courses}\n\n")
                f.write("📊 University Course Counts:\n")
                f.write("-" * 80 + "\n")
                f.write(f"{'University Name':<40} {'Location':<20} {'Courses':>10}\n")
                f.write("-" * 80 + "\n")
                
                for uni_id, name, location, course_count in universities:
                    location_str = location or "N/A"
                    f.write(f"{name:<40} {location_str:<20} {course_count:>10}\n")
                
                f.write("-" * 80 + "\n")
                f.write(f"{'TOTAL':<40} {'':<20} {total_courses:>10}\n\n")
                
                # Show universities with no courses
                no_courses = [u for u in universities if u[3] == 0]
                if no_courses:
                    f.write(f"⚠️  Universities with no courses: {len(no_courses)}\n")
                    for uni_id, name, location, course_count in no_courses:
                        f.write(f"   - {name}\n")
            
            print(f"✅ Summary written to {summary_path}")
            
        except Exception as e:
            print(f"❌ Error querying database: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(query_database())
