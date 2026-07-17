"""Planner agent: decomposes a research query into sub-questions and search queries."""

import json
import asyncio
import google.generativeai as genai
from app.models import GraphState, ResearchPlan, AgentRole
from app.config import get_settings
from app.tracing import RequestTracer


PLANNER_PROMPT = """You are a research planning agent. Given a user's research question, 
decompose it into a structured research plan.

Research question: {query}
Depth: {depth}

Based on the depth:
- "quick": 2-3 sub-questions, 2-3 search queries
- "standard": 3-5 sub-questions, 4-6 search queries  
- "deep": 5-8 sub-questions, 6-10 search queries

Return ONLY valid JSON (no markdown fences) with this structure:
{{
    "sub_questions": ["question1", "question2", ...],
    "search_queries": ["query1", "query2", ...],
    "approach": "Brief 1-2 sentence description of the research approach"
}}"""


async def run_planner(state: GraphState, tracer: RequestTracer) -> GraphState:
    """Generate a research plan from the user's query."""
    settings = get_settings()
    genai.configure(api_key=settings.google_api_key)
    model = genai.GenerativeModel(settings.llm_model)

    with tracer.trace_agent(
        AgentRole.PLANNER, "generate_plan", input_summary=state.query[:100]
    ) as trace:
        prompt = PLANNER_PROMPT.format(query=state.query, depth=state.depth)

        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=settings.llm_temperature,
                max_output_tokens=1500,
            ),
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]

        try:
            plan_data = json.loads(text)
            state.plan = ResearchPlan(**plan_data)
        except (json.JSONDecodeError, Exception) as e:
            tracer.log_error(f"Planner JSON parse failed: {e}")
            state.plan = ResearchPlan(
                sub_questions=[state.query],
                search_queries=[state.query],
                approach="Direct search due to plan generation failure.",
            )

        trace.output_summary = f"{len(state.plan.sub_questions)} sub-questions, {len(state.plan.search_queries)} queries"
        trace.token_usage = {
            "input": response.usage_metadata.prompt_token_count,
            "output": response.usage_metadata.candidates_token_count,
        }

    state.status = state.status  # keep current
    return state
