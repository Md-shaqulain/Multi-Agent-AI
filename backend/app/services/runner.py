import asyncio, logging, os
from ..agents.graph import graph
from ..config import settings
from ..db import store
from .report import generate_files

log = logging.getLogger("runner")

STEPS = {"planner": "Planning research questions...", "researcher": "Searching the web...",
         "verifier": "Verifying facts...", "summarizer": "Summarizing...",
         "writer": "Writing report..."}

async def run_job(job_id: str, topic: str, depth: int):
    try:
        await store.update(job_id, status="running", progress="Starting...")
        report = None
        async for upd in graph.astream({"topic": topic, "depth": depth}, stream_mode="updates"):
            for node, out in upd.items():
                log.info(f"[{job_id}] finished node: {node}")
                await store.update(job_id, progress=STEPS.get(node, node) + " (done: " + node + ")")
                if node == "writer":
                    report = out["report"]
        await store.update(job_id, progress="Generating PDF & DOCX...")
        await asyncio.to_thread(generate_files, job_id, report, os.path.abspath(settings.OUTPUT_DIR))
        await store.update(job_id, status="completed", progress="Done", report=report)
    except Exception as e:
        log.exception(f"Job {job_id} failed")
        await store.update(job_id, status="failed", error=str(e), progress="Failed")
