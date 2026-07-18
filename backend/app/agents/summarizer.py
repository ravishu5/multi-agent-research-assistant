"""Summarizer agent: produces final summary, key points, and confidence score."""

import json
from google.genai import types
from app.agents.gemini import client
from app.models import GraphState, AgentRole
from app.config import get_settings
from app.tracing import RequestTracer


SUMMARIZER_PROMPT = """You are a research summarizer. Given the raw findings below, 
produce a final research report.

Original question: {query}
Research approach: {approach}

Raw findings:
{findings}

Return ONLY valid JSON (no markdown fences) with this structure:
{{
    "summary": "A comprehensive, well-structured summary (use markdown formatting). 
                Include relevant data points and cite source numbers like [Source 1].",
    "key_points": ["Key finding 1", "Key finding 2", ...],
    "confidence_score": <float 0-1 based on source quality and coverage>
}}

Guidelines for confidence_score:
- 0.9+: Multiple high-quality sources agree, strong data
- 0.7-0.9: Good coverage with minor gaps
- 0.5-0.7: Limited sources or some contradictions
- <0.5: Sparse or unreliable sources"""


async def run_summarizer(state: GraphState, tracer: RequestTracer) -> GraphState:
    """Generate the final summary from raw findings."""
    settings = get_settings()

    with tracer.trace_agent(
        AgentRole.SUMMARIZER,
        "generate_summary",
        input_summary=f"{len(state.raw_findings)} chars of findings",
    ) as trace:
        prompt = SUMMARIZER_PROMPT.format(
            query=state.query,
            approach=state.plan.approach,
            findings=state.raw_findings[:8000],  # cap context
        )

        response = await client.aio.models.generate_content(
            model=settings.llm_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=settings.llm_max_tokens,
            ),
        )

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]

        try:
            result = json.loads(text)
            state.summary = result.get("summary", "")
            state.key_points = result.get("key_points", [])
            state.confidence_score = float(result.get("confidence_score", 0.5))
        except (json.JSONDecodeError, Exception) as e:
            tracer.log_error(f"Summarizer JSON parse failed: {e}")
            # Fallback: use raw text as summary
            state.summary = response.text
            state.key_points = []
            state.confidence_score = 0.4

        trace.output_summary = (
            f"Summary: {len(state.summary)} chars, "
            f"{len(state.key_points)} key points, "
            f"confidence: {state.confidence_score:.0%}"
        )
        trace.token_usage = {
            "input": response.usage_metadata.prompt_token_count,
            "output": response.usage_metadata.candidates_token_count,
        }

    return state
