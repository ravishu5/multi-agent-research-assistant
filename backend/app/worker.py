"""Celery worker for offloading long-running agent tasks."""

import asyncio
import json
from datetime import datetime
from celery import Celery
from app.config import get_settings
from app.models import GraphState, JobStatus
from app.agents.graph import research_graph

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


def _run_async(coro):
    """Run an async function in the Celery sync worker."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="research.run_pipeline")
def run_research_pipeline(self, job_data: dict) -> dict:
    """
    Execute the full research pipeline as a Celery task.
    Updates Redis with intermediate state for status polling.
    """
    import redis

    r = redis.Redis.from_url(settings.redis_url)
    job_id = job_data["job_id"]

    def update_status(status: str, extra: dict | None = None):
        state_update = {"status": status, "updated_at": datetime.utcnow().isoformat()}
        if extra:
            state_update.update(extra)
        r.hset(f"job:{job_id}", mapping={k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) for k, v in state_update.items()})

    try:
        # Initialize state
        state = GraphState(
            job_id=job_id,
            query=job_data["query"],
            depth=job_data.get("depth", "standard"),
            max_sources=job_data.get("max_sources", 5),
            status=JobStatus.PENDING,
        )

        update_status("planning")

        # Run the graph up to the approval gate (or completion for "quick")
        result = _run_async(research_graph.ainvoke(state.model_dump()))

        # Convert result back to GraphState for serialization
        final_state = GraphState(**result)

        # Store full state in Redis
        state_dict = final_state.model_dump(mode="json")
        r.set(f"job:{job_id}:state", json.dumps(state_dict))
        update_status(final_state.status.value)

        return state_dict

    except Exception as e:
        update_status("failed", {"error": str(e)})
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
        return state_data

    # Resume from approval gate → summarize
    state = GraphState(**state_data)

    result = _run_async(research_graph.ainvoke(state.model_dump()))
    final_state = GraphState(**result)

    state_dict = final_state.model_dump(mode="json")
    r.set(f"job:{job_id}:state", json.dumps(state_dict))
    r.hset(f"job:{job_id}", "status", final_state.status.value)
    r.hset(f"job:{job_id}", "updated_at", datetime.utcnow().isoformat())

    return state_dict
