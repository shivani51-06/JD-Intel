"""LangGraph StateGraph wiring the JD Intel multi-agent pipeline."""
from typing import TypedDict

from langgraph.graph import StateGraph, END

from agents.jd_parser import run_jd_parser
from agents.interview_scraper import run_interview_scraper
from agents.signal_aggregator import run_signal_aggregator
from scoring.resume_parser import parse_resume_sections
from scoring.skill_ranker import score_jd_match, score_sections
from scoring.interview_scorer import score_interview_coverage, detect_blindspots
from scoring.rewrite_engine import build_bullet_suggestions
from scoring.formatting import score_formatting


class PipelineState(TypedDict):
    resume_text: str
    jd_text: str
    company: str
    role: str
    jd_parsed: dict
    interview_posts: list
    interview_signals: dict
    resume_sections: dict
    scores: dict
    suggestions: list


async def _jd_parser_node(state: PipelineState) -> dict:
    jd_parsed = await run_jd_parser(state["jd_text"])
    return {"jd_parsed": jd_parsed}


async def _interview_scraper_node(state: PipelineState, cache) -> dict:
    posts = await run_interview_scraper(state["company"], state["role"], cache)
    return {"interview_posts": posts}


async def _signal_aggregator_node(state: PipelineState, cache) -> dict:
    signals = await run_signal_aggregator(state["interview_posts"], state["company"], state["role"], cache)
    return {"interview_signals": signals}


async def _scorer_node(state: PipelineState) -> dict:
    resume_sections = await parse_resume_sections(state["resume_text"])

    jd_match_score, skill_matches, missing_skills = score_jd_match(state["jd_parsed"], resume_sections)
    section_scores = score_sections(state["jd_parsed"], resume_sections)
    interview_coverage_score, matched_topics = score_interview_coverage(
        state["interview_signals"], resume_sections
    )
    blindspots = detect_blindspots(state["interview_signals"], state["jd_parsed"], resume_sections)
    formatting_score, parsability_issues = score_formatting(state["resume_text"], resume_sections)

    composite = round(
        0.4 * jd_match_score + 0.4 * interview_coverage_score + 0.2 * formatting_score, 1
    )

    suggestions = await build_bullet_suggestions(
        resume_sections, state["jd_parsed"], state["interview_signals"], state["company"]
    )

    report = {
        "composite_score": composite,
        "jd_match_score": jd_match_score,
        "interview_coverage_score": interview_coverage_score,
        "formatting_score": formatting_score,
        "section_scores": section_scores,
        "missing_skills": missing_skills,
        "skill_matches": [m.__dict__ if hasattr(m, "__dict__") else m for m in skill_matches],
        "interview_blindspots": blindspots,
        "top_interview_topics": state["interview_signals"].get("top_topics", []),
        "bullet_suggestions": suggestions,
        "parsability_issues": parsability_issues,
        "warnings": state["interview_signals"].get("warnings", []),
    }

    return {"resume_sections": resume_sections, "scores": report, "suggestions": suggestions}


def build_pipeline(cache):
    graph = StateGraph(PipelineState)

    async def _interview_scraper_with_cache(state: PipelineState) -> dict:
        return await _interview_scraper_node(state, cache)

    async def _signal_aggregator_with_cache(state: PipelineState) -> dict:
        return await _signal_aggregator_node(state, cache)

    graph.add_node("jd_parser", _jd_parser_node)
    graph.add_node("interview_scraper", _interview_scraper_with_cache)
    graph.add_node("signal_aggregator", _signal_aggregator_with_cache)
    graph.add_node("scorer", _scorer_node)

    graph.set_entry_point("jd_parser")
    graph.add_edge("jd_parser", "interview_scraper")
    graph.add_edge("interview_scraper", "signal_aggregator")
    graph.add_edge("signal_aggregator", "scorer")
    graph.add_edge("scorer", END)

    return graph.compile()
