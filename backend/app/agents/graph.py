"""LangGraph workflow: planner -> researcher -> [human approval] -> summarizer."""

from langgraph.graph import StateGraph, END
from app.models import GraphState, JobStatus
from app.agents.planner import run_planner
from app.agents.researcher import run_researcher
from app.agents.summarizer import run_summarizer
from app.guardrails import run_all_guardrails
from app.tracing import RequestTracer


def build_research_graph():
    """Build the LangGraph state machine for research workflow."""

    graph = StateGraph(GraphState)

    # --- Node functions (wrappers that create tracer from state) ---

    async def plan_node(state: GraphState) -> dict:
        tracer = _get_tracer(state)
        state.status = JobStatus.PLANNING
        updated = await run_planner(state, tracer)
        return {
            "plan": updated.plan,
            "status": JobStatus.PLANNING,
            "traces": tracer.traces,
        }

    async def research_node(state: GraphState) -> dict:
        tracer = _get_tracer(state)
        # Carry over existing traces
        tracer.traces = list(state.traces)
        state.status = JobStatus.RESEARCHING
        updated = await run_researcher(state, tracer)
        return {
            "sources": updated.sources,
            "raw_findings": updated.raw_findings,
            "status": JobStatus.RESEARCHING,
            "needs_approval": True,
            "traces": tracer.traces,
        }

    async def approval_gate(state: GraphState) -> dict:
        """Mark job as awaiting human approval."""
        return {
            "status": JobStatus.AWAITING_APPROVAL,
            "needs_approval": True,
        }

    async def summarize_node(state: GraphState) -> dict:
        tracer = _get_tracer(state)
        tracer.traces = list(state.traces)
        state.status = JobStatus.SUMMARIZING
        updated = await run_summarizer(state, tracer)

        # Run guardrails on final output
        guardrail_results = run_all_guardrails(updated)

        return {
            "summary": updated.summary,
            "key_points": updated.key_points,
            "confidence_score": updated.confidence_score,
            "status": JobStatus.COMPLETED,
            "guardrail_results": guardrail_results,
            "traces": tracer.traces,
        }

    # --- Conditional edge ---

    def should_wait_for_approval(state: GraphState) -> str:
        """Route to approval gate or straight to summarizer based on depth."""
        if state.depth == "quick":
            return "summarize"
        return "approval_gate"

    def check_approval(state: GraphState) -> str:
        """After approval gate, check if approved."""
        if state.approved:
            return "summarize"
        # Stay at approval gate (will be resumed externally)
        return END

    # --- Build graph ---

    graph.add_node("plan", plan_node)
    graph.add_node("research", research_node)
    graph.add_node("approval_gate", approval_gate)
    graph.add_node("summarize", summarize_node)

    graph.set_entry_point("plan")
    graph.add_edge("plan", "research")
    graph.add_conditional_edges("research", should_wait_for_approval, {
        "summarize": "summarize",
        "approval_gate": "approval_gate",
    })
    graph.add_conditional_edges("approval_gate", check_approval, {
        "summarize": "summarize",
        END: END,
    })
    graph.add_edge("summarize", END)

    return graph.compile()


def _get_tracer(state: GraphState) -> RequestTracer:
    """Create a tracer for the current job."""
    return RequestTracer(job_id=state.job_id)


# Pre-compiled graph
research_graph = build_research_graph()
