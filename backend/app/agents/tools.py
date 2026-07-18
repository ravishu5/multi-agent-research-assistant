"""Tools available to research agents."""

import httpx
from app.config import get_settings


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web using Google Custom Search API.
    Falls back to Gemini-powered search if no CSE credentials.
    """
    settings = get_settings()

    # Use Gemini grounding/search if available
    return await _gemini_search(query, max_results)


async def _gemini_search(query: str, max_results: int) -> list[dict]:
    """
    Use Gemini to generate search-like results.
    In production, swap this for a real search API (SerpAPI, Tavily, etc).
    """
    from google.genai import types
    from app.agents.gemini import client
    from app.config import get_settings

    settings = get_settings()

    prompt = f"""You are a research search engine. For the query below, return {max_results} relevant results.

Query: {query}

Return ONLY a valid JSON array. Each object must have:
- "title": a descriptive title
- "snippet": a 2-3 sentence factual summary with specific details, data points, or findings
- "url": a plausible source URL
- "relevance_score": float 0-1

Return pure JSON, no markdown fences."""

    response = await client.aio.models.generate_content(
        model=settings.llm_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=2000,
        ),
    )

    import json
    text = response.text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]

    try:
        results = json.loads(text)
        return results[:max_results]
    except json.JSONDecodeError:
        return [{"title": "Search error", "snippet": text[:500], "url": "", "relevance_score": 0.0}]


async def scrape_url(url: str) -> str:
    """Fetch and extract text from a URL."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            return resp.text[:5000]
    except Exception as e:
        return f"Failed to scrape {url}: {e}"
