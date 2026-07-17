"""API routes for research job management."""

import json
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
import redis.asyncio as aioredis

from app.config import get_settings, Settings
from app.models import (
    ResearchRequest,
    ApprovalRequest,
    JobSubmitResponse,
    JobStatusResponse,
    JobResultResponse,
    JobStatus,
    GraphState,
    AgentTrace,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def get_redis(settings: Settings = Depends(get_settings)) -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


@router.post("/submit", response_model=JobSubmitResponse)
async def submit_job(req: ResearchRequest, settings: Settings = Depends(get_settings)):
    """Submit a new research job to the async task queue."""
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Store initial job metadata in Redis
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    await r.hset(f"job:{job_id}", mapping={
        "status": JobStatus.PENDING.value,
        "query": req.query,
        "depth": req.depth,
        "max_sources": str(req.max_sources),
        "created_at": now,
        "updated_at": now,
    })
    await r.close()

    # Dispatch to Celery
    from app.worker import run_research_pipeline
    run_research_pipeline.delay({
        "job_id": job_id,
        "query": req.query,
        "depth": req.depth,
        "max_sources": req.max_sources,
    })

    return JobSubmitResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Research job submitted. Poll /jobs/{job_id}/status for updates.",
    )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str, settings: Settings = Depends(get_settings)):
    """Poll the current status of a research job."""
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    job_meta = await r.hgetall(f"job:{job_id}")

    if not job_meta:
        await r.close()
        raise HTTPException(status_code=404, detail="Job not found")

    # Try to get traces from full state
    traces = []
    state_json = await r.get(f"job:{job_id}:state")
    if state_json:
        state_data = json.loads(state_json)
        traces = [AgentTrace(**t) for t in state_data.get("traces", [])]

    await r.close()

    status = job_meta.get("status", "pending")
    progress_map = {
        "pending": "Job queued, waiting to start...",
        "planning": "Planner agent is decomposing your query...",
        "researching": "Researcher agent is gathering sources...",
        "awaiting_approval": "Research complete. Awaiting your approval to summarize.",
        "summarizing": "Summarizer agent is writing the report...",
        "completed": "Research complete!",
        "failed": "Job failed. Check errors.",
    }

    return JobStatusResponse(
        job_id=job_id,
        status=JobStatus(status),
        progress=progress_map.get(status, "Processing..."),
        created_at=datetime.fromisoformat(job_meta.get("created_at", datetime.utcnow().isoformat())),
        updated_at=datetime.fromisoformat(job_meta.get("updated_at", datetime.utcnow().isoformat())),
        traces=traces,
        errors=[],
    )


@router.get("/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: str, settings: Settings = Depends(get_settings)):
    """Get the full result of a completed research job."""
    r = aioredis.from_url(settings.redis_url, decode_responses=True)

    state_json = await r.get(f"job:{job_id}:state")
    job_meta = await r.hgetall(f"job:{job_id}")
    await r.close()

    if not state_json:
        raise HTTPException(status_code=404, detail="Job not found or still in progress")

    state = GraphState(**json.loads(state_json))

    if state.status not in (JobStatus.COMPLETED, JobStatus.AWAITING_APPROVAL):
        raise HTTPException(
            status_code=400,
            detail=f"Job is not complete yet. Current status: {state.status}",
        )

    return JobResultResponse(
        job_id=job_id,
        status=state.status,
        query=state.query,
        plan=state.plan,
        sources=state.sources,
        summary=state.summary,
        key_points=state.key_points,
        confidence_score=state.confidence_score,
        traces=state.traces,
        guardrail_results=state.guardrail_results,
        created_at=datetime.fromisoformat(job_meta.get("created_at", datetime.utcnow().isoformat())),
        completed_at=datetime.fromisoformat(job_meta.get("updated_at", datetime.utcnow().isoformat())),
    )


@router.post("/{job_id}/approve")
async def approve_job(job_id: str, req: ApprovalRequest, settings: Settings = Depends(get_settings)):
    """Approve or reject research findings (human-in-the-loop checkpoint)."""
    r = aioredis.from_url(settings.redis_url, decode_responses=True)

    job_meta = await r.hgetall(f"job:{job_id}")
    if not job_meta:
        await r.close()
        raise HTTPException(status_code=404, detail="Job not found")

    if job_meta.get("status") != JobStatus.AWAITING_APPROVAL.value:
        await r.close()
        raise HTTPException(status_code=400, detail="Job is not awaiting approval")

    await r.close()

    # Dispatch resume task to Celery
    from app.worker import resume_after_approval
    resume_after_approval.delay(job_id, req.approved, req.feedback or "")

    action = "approved" if req.approved else "rejected"
    return {"message": f"Research findings {action}. Resuming pipeline...", "job_id": job_id}


@router.get("/", response_model=list[dict])
async def list_jobs(settings: Settings = Depends(get_settings)):
    """List all research jobs."""
    r = aioredis.from_url(settings.redis_url, decode_responses=True)

    jobs = []
    async for key in r.scan_iter("job:*"):
        if ":state" in key:
            continue
        job_id = key.split(":")[1]
        meta = await r.hgetall(key)
        if meta:
            jobs.append({
                "job_id": job_id,
                "query": meta.get("query", ""),
                "status": meta.get("status", "unknown"),
                "depth": meta.get("depth", "standard"),
                "created_at": meta.get("created_at", ""),
                "updated_at": meta.get("updated_at", ""),
            })

    await r.close()
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return jobs
