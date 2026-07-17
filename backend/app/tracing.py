"""Observability: structured logging, request tracing, and metrics."""

import time
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from app.models import AgentTrace, AgentRole

# Structured logger
logger = logging.getLogger("research_assistant")
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | trace=%(trace_id)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class RequestTracer:
    """Traces a single research job across all agent invocations."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.trace_id = str(uuid.uuid4())[:8]
        self.traces: list[AgentTrace] = []
        self._extra = {"trace_id": self.trace_id}

    @contextmanager
    def trace_agent(self, agent: AgentRole, action: str, input_summary: str = ""):
        """Context manager that times an agent step and records a trace."""
        self.log(f"[{agent.value}] START: {action}")
        start = time.perf_counter()
        trace = AgentTrace(
            agent=agent,
            action=action,
            input_summary=input_summary,
            timestamp=datetime.utcnow(),
        )
        yield trace  # caller can set output_summary, token_usage, etc.
        elapsed_ms = (time.perf_counter() - start) * 1000
        trace.duration_ms = round(elapsed_ms, 2)
        self.traces.append(trace)
        self.log(
            f"[{agent.value}] DONE: {action} "
            f"({elapsed_ms:.0f}ms, tokens={trace.token_usage})"
        )

    def log(self, msg: str, level: int = logging.INFO):
        logger.log(level, f"[job={self.job_id}] {msg}", extra=self._extra)

    def log_error(self, msg: str):
        self.log(msg, level=logging.ERROR)

    def get_metrics(self) -> dict:
        """Aggregate metrics across all traces in this job."""
        total_ms = sum(t.duration_ms for t in self.traces)
        total_input = sum(t.token_usage.get("input", 0) for t in self.traces)
        total_output = sum(t.token_usage.get("output", 0) for t in self.traces)
        return {
            "total_duration_ms": round(total_ms, 2),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "agent_steps": len(self.traces),
        }
