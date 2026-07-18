"""Researcher agent: executes search queries and compiles source findings."""

import asyncio
from google.genai import types
from app.agents.gemini import client
from app.models import GraphState, SourceResult, AgentRole
from app.config import get_settings
from app.tracing import RequestTracer
from app.agents.tools import web_search


async def run_researcher(state: GraphState, tracer: RequestTracer) -> GraphState:
    """Execute search queries from the plan and compile findings."""
    settings = get_settings()

    all_sources: list[SourceResult] = []

    with tracer.trace_agent(
        AgentRole.RESEARCHER,
        "search_and_gather",
        input_summary=f"{len(state.plan.search_queries)} queries",
    ) as trace:
        # Run all search queries concurrently
        per_query = max(1, state.max_sources // len(state.plan.search_queries))
        search_tasks = [
            web_search(q, max_results=per_query)
            for q in state.plan.search_queries
        ]
        results_batches = await asyncio.gather(*search_tasks, return_exceptions=True)

        for i, batch in enumerate(results_batches):
            if isinstance(batch, Exception):
                tracer.log_error(f"Search failed for query {i}: {batch}")
                continue
            for r in batch:
                all_sources.append(
                    SourceResult(
                        query=state.plan.search_queries[i],
                        title=r.get("title", ""),
                        snippet=r.get("snippet", ""),
                        url=r.get("url", ""),
                        relevance_score=float(r.get("relevance_score", 0.5)),
                    )
                )

        # Deduplicate by title
        seen_titles = set()
        unique_sources = []
        for s in all_sources:
            if s.title not in seen_titles:
                seen_titles.add(s.title)
                unique_sources.append(s)
        all_sources = unique_sources

        # Sort by relevance and cap at max_sources
        all_sources.sort(key=lambda s: s.relevance_score, reverse=True)
        state.sources = all_sources[: state.max_sources]

        trace.output_summary = f"{len(state.sources)} sources gathered"

    # Synthesize raw findings from sources
    with tracer.trace_agent(
        AgentRole.RESEARCHER,
        "synthesize_findings",
        input_summary=f"{len(state.sources)} sources",
    ) as trace:
        source_text = "\n\n".join(
            f"[Source {i+1}] {s.title}\n{s.snippet}"
            for i, s in enumerate(state.sources)
        )

        prompt = f"""You are a research analyst. Given the following sources about "{state.query}",
synthesize the key findings into a structured analysis. Include specific data points,
identify consensus and disagreements between sources, and note any gaps.

Sources:
{source_text}

Sub-questions to address:
{chr(10).join(f'- {q}' for q in state.plan.sub_questions)}

Write a thorough analysis (500-1500 words depending on depth: {state.depth})."""

        response = await client.aio.models.generate_content(
            model=settings.llm_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=settings.llm_max_tokens,
            ),
        )

        state.raw_findings = response.text
        trace.output_summary = f"{len(response.text)} chars of findings"
        trace.token_usage = {
            "input": response.usage_metadata.prompt_token_count,
            "output": response.usage_metadata.candidates_token_count,
        }

    return state
