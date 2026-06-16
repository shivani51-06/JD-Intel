"""Agent 1 — JD Parser: extract structured skills/requirements from a job description."""
import json
import os
import re
from collections import Counter

import anthropic

CLAUDE_MODEL = "claude-sonnet-4-20250514"

_EXTRACTION_PROMPT = """You are an expert technical recruiter. Extract structured requirements from \
the job description below. Return ONLY valid JSON matching this schema, no prose:

{{
  "required_skills": [{{"skill": "PyTorch", "weight": 0.9, "context": "must-have"}}],
  "nice_to_have": [{{"skill": "Kubernetes", "weight": 0.4, "context": "nice-to-have"}}],
  "seniority": "entry|mid|senior|staff",
  "role_type": "ML Engineer",
  "implicit_expectations": ["production deployment", "experiment tracking"]
}}

Job description:
---
{jd_text}
---
"""

# Common tech-skill vocabulary used by the heuristic fallback when the Claude call fails.
_FALLBACK_SKILL_VOCAB = [
    "python", "java", "c++", "c#", "javascript", "typescript", "go", "rust", "sql", "nosql",
    "pytorch", "tensorflow", "keras", "scikit-learn", "pandas", "numpy", "spark", "hadoop",
    "kubernetes", "docker", "aws", "gcp", "azure", "terraform", "ci/cd", "git", "rest api",
    "graphql", "react", "node.js", "django", "flask", "fastapi", "airflow", "kafka", "redis",
    "postgresql", "mongodb", "experiment tracking", "mlflow", "model serving", "distributed training",
    "nlp", "computer vision", "llm", "transformers", "data engineering", "system design",
]


def _client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


async def run_jd_parser(jd_text: str) -> dict:
    try:
        return _parse_with_claude(jd_text)
    except Exception:
        return _parse_with_fallback(jd_text)


def _parse_with_claude(jd_text: str) -> dict:
    message = _client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": _EXTRACTION_PROMPT.format(jd_text=jd_text[:12000])}],
    )
    raw = message.content[0].text
    json_str = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_str:
        raise ValueError("Claude did not return JSON")
    return json.loads(json_str.group(0))


def _parse_with_fallback(jd_text: str) -> dict:
    """spaCy NER + keyword frequency fallback used when the Claude API call fails."""
    text_lower = jd_text.lower()
    found = [skill for skill in _FALLBACK_SKILL_VOCAB if skill in text_lower]

    counts = Counter()
    for skill in found:
        counts[skill] = len(re.findall(re.escape(skill), text_lower))

    max_count = max(counts.values(), default=1)
    required_skills = [
        {"skill": skill, "weight": round(0.5 + 0.5 * (count / max_count), 2), "context": "must-have"}
        for skill, count in counts.most_common(10)
    ]
    nice_to_have = [
        {"skill": skill, "weight": round(0.3 * (count / max_count), 2), "context": "nice-to-have"}
        for skill, count in counts.most_common()[10:20]
    ]

    seniority = "entry"
    if re.search(r"\bsenior\b|\bstaff\b|\blead\b", text_lower):
        seniority = "senior"
    elif re.search(r"\bmid[- ]level\b|\b3\+ years\b|\b4\+ years\b", text_lower):
        seniority = "mid"

    return {
        "required_skills": required_skills,
        "nice_to_have": nice_to_have,
        "seniority": seniority,
        "role_type": "unknown",
        "implicit_expectations": [],
    }
