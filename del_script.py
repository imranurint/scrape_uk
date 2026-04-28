import asyncio
import uuid
from sqlalchemy import delete
from config.database import AsyncSessionLocal
from models.db import University

UNIVERSITY_IDS = [
    "b03fe930df8d470e8afbe21ad82bbe06",
    "2649d88636b5467384f92bed4c444500",
    "32029d34683047ea95ef42d73fb1431b",
    "bba3a204ff4b4a7cb8ddaed47ca6e6d8",
    "ef7619bd6a7445ccb97f0d940a8bf4fc",
    "e2e1f5775efd40a0af77c8665b307087",
    "161546a2a95e4fdeb3ba50d57f8312b9",
    "a5948d97a1d24c60b75fc28ad98e7403",
    "a04e155ab28b4671a9ab917d0969dae6"
]

async def delete_universities():
    async with AsyncSessionLocal() as session:
        target_ids = [uuid.UUID(uid) for uid in UNIVERSITY_IDS]
        
        # This will cascade delete courses and course_details
        stmt = delete(University).where(University.id.in_(target_ids))
        
        result = await session.execute(stmt)
        await session.commit()
        print(f"Deleted {result.rowcount} universities and all their associated data.")

if __name__ == "__main__":
    asyncio.run(delete_universities())