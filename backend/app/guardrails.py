"""Guardrails: output validation, hallucination detection, content safety."""

import re
from app.models import GraphState, SourceResult
from app.config import get_settings


def run_all_guardrails(state: GraphState) -> dict[str, dict]:
    """Run all guardrail checks and return results."""
    results = {
        "output_length": check_output_length(state.summary),
        "hallucination": check_hallucination(state.summary, state.sources),
        "source_coverage": check_source_coverage(state.sources, state.plan.sub_questions),
        "confidence": check_confidence_score(state.confidence_score),
        "content_safety": check_content_safety(state.summary),
    }
    return results


def check_output_length(summary: str) -> dict:
    """Validate summary isn't empty or excessively long."""
    settings = get_settings()
    length = len(summary)
    passed = 50 < length < settings.max_output_length
    return {
        "passed": passed,
        "detail": f"Length {length} chars"
        + ("" if passed else f" (limit: 50-{settings.max_output_length})"),
    }


def check_hallucination(summary: str, sources: list[SourceResult]) -> dict:
    """
    Basic hallucination check: verify claims in summary can be grounded
    in source snippets. Uses keyword overlap as a lightweight proxy.
    """
    if not sources or not summary:
        return {"passed": False, "detail": "No sources or summary to check", "score": 0.0}

    # Build a set of significant keywords from sources
    source_text = " ".join(s.snippet.lower() for s in sources)
    source_words = set(re.findall(r"\b[a-z]{4,}\b", source_text))

    # Extract significant words from summary
    summary_words = set(re.findall(r"\b[a-z]{4,}\b", summary.lower()))

    if not summary_words:
        return {"passed": False, "detail": "Summary has no checkable words", "score": 0.0}

    # Overlap ratio as grounding score
    overlap = summary_words & source_words
    score = len(overlap) / len(summary_words) if summary_words else 0.0

    settings = get_settings()
    passed = score >= settings.hallucination_threshold

    return {
        "passed": passed,
        "score": round(score, 3),
        "detail": f"Grounding score {score:.1%} "
        + ("(OK)" if passed else f"(below {settings.hallucination_threshold:.0%} threshold)"),
    }


def check_source_coverage(sources: list[SourceResult], sub_questions: list[str]) -> dict:
    """Check that sources cover the planned sub-questions."""
    if not sub_questions:
        return {"passed": True, "detail": "No sub-questions to check", "coverage": 1.0}

    covered = 0
    for q in sub_questions:
        q_words = set(re.findall(r"\b[a-z]{4,}\b", q.lower()))
        for s in sources:
            s_words = set(re.findall(r"\b[a-z]{4,}\b", s.snippet.lower()))
            if len(q_words & s_words) >= 2:
                covered += 1
                break

    coverage = covered / len(sub_questions)
    return {
        "passed": coverage >= 0.5,
        "coverage": round(coverage, 2),
        "detail": f"{covered}/{len(sub_questions)} sub-questions covered",
    }


def check_confidence_score(score: float) -> dict:
    """Flag low-confidence results."""
    passed = score >= 0.5
    return {
        "passed": passed,
        "score": score,
        "detail": f"Confidence {score:.0%}" + ("" if passed else " (low confidence, review recommended)"),
    }


def check_content_safety(text: str) -> dict:
    """Basic content safety check for harmful patterns."""
    # Lightweight keyword check — in production, use a classifier
    unsafe_patterns = [
        r"\b(how to (hack|exploit|attack))\b",
        r"\b(build (a |)(bomb|weapon))\b",
    ]
    for pattern in unsafe_patterns:
        if re.search(pattern, text.lower()):
            return {"passed": False, "detail": "Content safety flag triggered"}
    return {"passed": True, "detail": "OK"}
