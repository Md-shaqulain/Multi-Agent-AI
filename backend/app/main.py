import os, time, logging
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from .config import settings, setup_logging
from .db import store
from .models import ResearchRequest, JobCreated, JobOut
from .services.runner import run_job

setup_logging()
log = logging.getLogger("api")

@asynccontextmanager
async def lifespan(app):
    await store.connect()
    yield

app = FastAPI(title="Multi-Agent Research Platform", version="1.0.0", lifespan=lifespan)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    t = time.time()
    resp = await call_next(request)
    log.info(f"{request.method} {request.url.path} -> {resp.status_code} ({time.time()-t:.2f}s)")
    return resp

@app.exception_handler(Exception)
async def global_error(request: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {exc}"})

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/research", response_model=JobCreated, status_code=202)
async def create_research(req: ResearchRequest, bg: BackgroundTasks):
    job_id = uuid4().hex
    await store.save({"_id": job_id, "topic": req.topic, "status": "queued",
                      "progress": "Queued", "error": None, "report": None, "created": time.time()})
    bg.add_task(run_job, job_id, req.topic, req.depth)
    return JobCreated(job_id=job_id, status="queued")

@app.get("/research/{job_id}", response_model=JobOut)
async def get_research(job_id: str):
    j = await store.get(job_id)
    if not j:
        raise HTTPException(404, "Job not found")
    return JobOut(job_id=j["_id"], topic=j["topic"], status=j["status"],
                  progress=j.get("progress", ""), error=j.get("error"), report=j.get("report"))

@app.get("/research/{job_id}/download/{fmt}")
async def download(job_id: str, fmt: str):
    if fmt not in ("pdf", "docx"):
        raise HTTPException(400, "fmt must be pdf or docx")
    path = os.path.abspath(os.path.join(settings.OUTPUT_DIR, f"{job_id}.{fmt}"))
    if not os.path.exists(path):
        raise HTTPException(404, "File not ready")
    return FileResponse(path, filename=f"research_report.{fmt}")

@app.get("/jobs")
async def jobs():
    return [{"job_id": j["_id"], "topic": j["topic"], "status": j["status"]}
            for j in await store.list()]
