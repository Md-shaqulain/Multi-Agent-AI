from pydantic import BaseModel, Field
from typing import Optional, Any

class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200)
    depth: int = Field(4, ge=2, le=8, description="Number of research questions")

class JobCreated(BaseModel):
    job_id: str
    status: str

class JobOut(BaseModel):
    job_id: str
    topic: str
    status: str
    progress: str = ""
    error: Optional[str] = None
    report: Optional[dict[str, Any]] = None
