"""JD Intel FastAPI app: routes for resume analysis, status polling, signal lookup, and rewrites."""
import asyncio
import json
import uuid
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import os

from cache import SignalCache
from models import RewriteRequest, RewriteResponse, JobStatus
from pipeline import build_pipeline, PipelineState
from scoring.resume_parser import extract_resume_text
from scoring.rewrite_engine import generate_rewrites

load_dotenv()

app = FastAPI(title="JD Intel API")

_allowed_origins = [o.strip() for o in os.environ.get("FRONTEND_URL", "http://localhost:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = SignalCache()
pipeline = build_pipeline(cache)

# In-memory job progress store: job_id -> JobStatus dict
_jobs: dict[str, dict] = {}


def _set_status(job_id: str, stage: str, progress: float, detail: str = "") -> None:
    _jobs[job_id] = {"job_id": job_id, "stage": stage, "progress": progress, "detail": detail}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str) -> JobStatus:
    status = _jobs.get(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    return JobStatus(**status)


@app.get("/api/signals/{company}/{role}")
async def get_signals(company: str, role: str):
    signals = cache.get(company, role)
    if signals is None:
        raise HTTPException(status_code=404, detail="No cached signals for this company/role")
    return signals


@app.post("/api/rewrite", response_model=RewriteResponse)
async def rewrite_bullet(req: RewriteRequest):
    rewrites = await generate_rewrites(req.bullet, req.jd_skills, req.interview_topics, req.company)
    return RewriteResponse(rewrites=rewrites)


@app.post("/api/analyze")
async def analyze(
    resume: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
    jd: str = Form(...),
    company: str = Form(...),
    role: str = Form(...),
):
    job_id = str(uuid.uuid4())

    if resume is not None:
        raw_bytes = await resume.read()
        text = extract_resume_text(raw_bytes, resume.filename or "")
    elif resume_text:
        text = resume_text
    else:
        raise HTTPException(status_code=400, detail="Provide either `resume` file or `resume_text`")

    initial_state: PipelineState = {
        "resume_text": text,
        "jd_text": jd,
        "company": company,
        "role": role,
        "jd_parsed": {},
        "interview_posts": [],
        "interview_signals": {},
        "resume_sections": {},
        "scores": {},
        "suggestions": [],
    }

    async def event_stream():
        _set_status(job_id, "starting", 0.0)
        yield _sse_event("status", {"job_id": job_id, "stage": "starting", "progress": 0.0})
        accumulated: dict = dict(initial_state)
        try:
            async for update in pipeline.astream(initial_state, stream_mode="updates"):
                node_name = next(iter(update.keys()))
                node_output = update[node_name]
                accumulated.update(node_output)
                progress = _PROGRESS_BY_NODE.get(node_name, 0.5)
                _set_status(job_id, node_name, progress)
                yield _sse_event("agent_complete", {"agent": node_name, "progress": progress})
                await asyncio.sleep(0)
        except Exception as exc:  # noqa: BLE001 - surface pipeline errors to the client
            _set_status(job_id, "error", 1.0, str(exc))
            yield _sse_event("error", {"detail": str(exc)})
            return

        report = accumulated.get("scores", {})
        _set_status(job_id, "done", 1.0)
        yield _sse_event("done", {"job_id": job_id, "report": report})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


_PROGRESS_BY_NODE = {
    "jd_parser": 0.2,
    "interview_scraper": 0.45,
    "signal_aggregator": 0.65,
    "scorer": 0.9,
}


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
