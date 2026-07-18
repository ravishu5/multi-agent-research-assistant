"""Celery worker for offloading long-running agent tasks."""

import asyncio
import json
from datetime import datetime
from celery import Celery
from app.config import get_settings
from app.models import GraphState, JobStatus
from app.agents.graph import research_graph
from app.agents.summarizer import run_summarizer
from app.guardrails import run_all_guardrails
from app.tracing import RequestTracer

settings = get_settings()

celery_app = Celery(
    "research_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=300,  # 5 min hard limit
    task_soft_time_limit=240,  # 4 min soft limit
)

_loop: asyncio.AbstractEventLoop | None = None


def _run_async(coro):
    """Run a coroutine on a persistent per-process event loop.

    The Gemini client (app.agents.gemini.client) is a module-level singleton
    reused across tasks in this worker process; its async httpx connections
    bind to whichever loop is running when they're first used. Opening and
    closing a fresh loop per task (the previous approach) invalidates those
    connections after the first task, causing every subsequent task to fail
    with "RuntimeError: Event loop is closed". Reusing one loop for the
    lifetime of the process avoids that.
    """
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)


def _update_job_status(r, job_id: str, status: str, extra: dict | None = None):
    state_update = {"status": status, "updated_at": datetime.utcnow().isoformat()}
    if extra:
        state_update.update(extra)
    r.hset(
        f"job:{job_id}",
        mapping={
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            for k, v in state_update.items()
        },
    )


@celery_app.task(bind=True, name="research.run_pipeline")
def run_research_pipeline(self, job_data: dict) -> dict:
    """
    Execute the full research pipeline as a Celery task.
    Updates Redis with intermediate state for status polling.
    """
    import redis

    r = redis.Redis.from_url(settings.redis_url)
    job_id = job_data["job_id"]

    try:
        # Initialize state
        state = GraphState(
            job_id=job_id,
            query=job_data["query"],
            depth=job_data.get("depth", "standard"),
            max_sources=job_data.get("max_sources", 5),
            status=JobStatus.PENDING,
        )

        _update_job_status(r, job_id, "planning")

        # Run the graph up to the approval gate (or completion for "quick")
        result = _run_async(research_graph.ainvoke(state.model_dump()))

        # Convert result back to GraphState for serialization
        final_state = GraphState(**result)

        # Store full state in Redis
        state_dict = final_state.model_dump(mode="json")
        r.set(f"job:{job_id}:state", json.dumps(state_dict))
        _update_job_status(r, job_id, final_state.status.value)

        return state_dict

    except Exception as e:
        _update_job_status(r, job_id, "failed", {"error": str(e)})
        raise


@celery_app.task(bind=True, name="research.resume_after_approval")
def resume_after_approval(self, job_id: str, approved: bool, feedback: str = "") -> dict:
    """Resume the pipeline after human approval."""
    import redis

    r = redis.Redis.from_url(settings.redis_url)

    # Load saved state
    state_json = r.get(f"job:{job_id}:state")
    if not state_json:
        raise ValueError(f"No state found for job {job_id}")

    state_data = json.loads(state_json)
    state_data["approved"] = approved
    state_data["approval_feedback"] = feedback
    state_data["needs_approval"] = False

    if not approved:
        state_data["status"] = JobStatus.FAILED.value
        r.set(f"job:{job_id}:state", json.dumps(state_data))
        _update_job_status(r, job_id, JobStatus.FAILED.value)
        return state_data

    try:
        # Go straight to summarization rather than re-invoking the graph
        # from its entry point: the graph has no checkpointer, so an
        # ainvoke() here would restart at "planner" and redo planning and
        # research from scratch, ignoring the sources the user just
        # reviewed and approved.
        state = GraphState(**state_data)
        tracer = RequestTracer(job_id=job_id)
        tracer.traces = list(state.traces)
        state.status = JobStatus.SUMMARIZING
        _update_job_status(r, job_id, JobStatus.SUMMARIZING.value)

        updated = _run_async(run_summarizer(state, tracer))
        updated.status = JobStatus.COMPLETED
        updated.traces = tracer.traces
        updated.guardrail_results = run_all_guardrails(updated)

        state_dict = updated.model_dump(mode="json")
        r.set(f"job:{job_id}:state", json.dumps(state_dict))
        _update_job_status(r, job_id, JobStatus.COMPLETED.value)

        return state_dict

    except Exception as e:
        _update_job_status(r, job_id, "failed", {"error": str(e)})
        raise
