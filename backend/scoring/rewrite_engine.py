"""Generates Claude-powered bullet rewrite suggestions for low-similarity bullets."""
import os
import re

import anthropic
import numpy as np

from .skill_ranker import _embed, _max_similarity

CLAUDE_MODEL = "claude-sonnet-4-20250514"
_REWRITE_THRESHOLD = 0.6

_REWRITE_PROMPT = """Given this resume bullet: "{bullet}"
The JD requires: {jd_skills}
Real interviewers at {company} ask about: {topics}

Rewrite this bullet to address these gaps while keeping it truthful (do not invent \
metrics or experience the candidate didn't describe). Return exactly 3 variants, \
one per line, each prefixed with "- ".
"""


def _client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


async def generate_rewrites(bullet: str, jd_skills: list[str], interview_topics: list[str], company: str) -> list[str]:
    try:
        return _rewrite_with_claude(bullet, jd_skills, interview_topics, company)
    except Exception:
        return _rewrite_with_template(bullet, jd_skills, interview_topics)


def _rewrite_with_claude(bullet: str, jd_skills: list[str], topics: list[str], company: str) -> list[str]:
    prompt = _REWRITE_PROMPT.format(
        bullet=bullet,
        jd_skills=", ".join(jd_skills[:8]) or "general technical skills",
        topics=", ".join(topics[:5]) or "core technical fundamentals",
        company=company or "this company",
    )
    message = _client().messages.create(
        model=CLAUDE_MODEL, max_tokens=600, messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text
    variants = [line.strip("- ").strip() for line in raw.splitlines() if line.strip().startswith("-")]
    if not variants:
        raise ValueError("Claude returned no rewrite variants")
    return variants[:3]


def _rewrite_with_template(bullet: str, jd_skills: list[str], topics: list[str]) -> list[str]:
    """Deterministic fallback used when the Claude call fails — appends gap-closing
    context rather than fabricating new claims."""
    top_skill = jd_skills[0] if jd_skills else "the role's core stack"
    top_topic = topics[0] if topics else "system design fundamentals"
    return [
        f"{bullet} — emphasize the {top_skill} components involved and the measurable outcome.",
        f"{bullet}; consider noting how this work relates to {top_topic}, a frequent interview focus.",
        f"{bullet} (add scale/impact metrics, e.g. users served, latency, or accuracy improvement).",
    ]


async def build_bullet_suggestions(resume_sections: dict, jd_parsed: dict, interview_signals: dict, company: str) -> list[dict]:
    jd_skills = [s["skill"] for s in jd_parsed.get("required_skills", [])]
    topics = interview_signals.get("top_topics", [])
    if not jd_skills:
        return []

    skill_vectors = _embed(jd_skills)

    bullets: list[tuple[str, str]] = []
    for project in resume_sections.get("projects", []):
        for bullet in project.get("bullets", []):
            bullets.append((bullet, project.get("name", "")))
    for bullet in resume_sections.get("experience", []):
        bullets.append((bullet, ""))

    bullets = [b for b in bullets if b[0] and b[0].strip()]
    if not bullets:
        return []

    bullet_texts = [b[0] for b in bullets]
    bullet_vectors = _embed(bullet_texts)

    suggestions = []
    for (bullet_text, _), bullet_vector in zip(bullets, bullet_vectors):
        sims = bullet_vector @ skill_vectors.T if skill_vectors.shape[0] else np.array([0.0])
        max_sim = float(np.max(sims)) if sims.size else 0.0
        if max_sim < _REWRITE_THRESHOLD:
            issue = _diagnose_issue(bullet_text)
            rewrites = await generate_rewrites(bullet_text, jd_skills, topics, company)
            suggestions.append({"original": bullet_text, "issue": issue, "rewrites": rewrites})

    return suggestions


def _diagnose_issue(bullet: str) -> str:
    issues = []
    if not re.search(r"\d", bullet):
        issues.append("no quantified impact")
    if any(term in bullet.lower() for term in ["responsible for", "worked on", "helped"]):
        issues.append("vague action verbs")
    if not any(term in bullet.lower() for term in ["deploy", "production", "launched", "served"]):
        issues.append("no deployment/production context")
    return "Bullet lacks: " + ", ".join(issues) if issues else "Low semantic overlap with JD's required skills"
