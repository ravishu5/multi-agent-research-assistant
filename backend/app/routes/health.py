"""Health check endpoint."""

from fastapi import APIRouter
import redis

from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Check API and dependency health."""
    settings = get_settings()
    checks = {"api": "ok", "redis": "unknown", "celery": "unknown"}

    # Check Redis
    try:
        r = redis.Redis.from_url(settings.redis_url)
        r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    # Check Celery (via Redis broker)
    try:
        r = redis.Redis.from_url(settings.celery_broker_url)
        r.ping()
        checks["celery"] = "ok"
    except Exception:
        checks["celery"] = "error"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
