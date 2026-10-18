import logging
from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

log = logging.getLogger("db")

class Store:
    """MongoDB store; falls back to in-memory dict if Mongo is unavailable."""
    def __init__(self):
        self.mem, self.coll = {}, None

    async def connect(self):
        try:
            c = AsyncIOMotorClient(settings.MONGO_URI, serverSelectionTimeoutMS=3000)
            await c.admin.command("ping")
            self.coll = c[settings.MONGO_DB]["jobs"]
            log.info("Connected to MongoDB")
        except Exception as e:
            log.warning(f"MongoDB unavailable ({e}); using in-memory store")

    async def save(self, job: dict):
        if self.coll is not None:
            await self.coll.replace_one({"_id": job["_id"]}, job, upsert=True)
        else:
            self.mem[job["_id"]] = job

    async def get(self, job_id: str):
        if self.coll is not None:
            return await self.coll.find_one({"_id": job_id})
        return self.mem.get(job_id)

    async def update(self, job_id: str, **fields):
        if self.coll is not None:
            await self.coll.update_one({"_id": job_id}, {"$set": fields})
        elif job_id in self.mem:
            self.mem[job_id].update(fields)

    async def list(self, limit=20):
        if self.coll is not None:
            return await self.coll.find({}, {"report": 0}).sort("created", -1).to_list(limit)
        return sorted(self.mem.values(), key=lambda j: j["created"], reverse=True)[:limit]

store = Store()
