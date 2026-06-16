"""Heuristic ATS-parsability / formatting score: quantified achievements, vague
bullets, deployment mentions, multi-column layout and embedded-photo detection."""
import re

_QUANT_PATTERN = re.compile(r"\d+(\.\d+)?\s*(%|percent|x|k|m|million|billion|users|ms|seconds|hours)?")
_DEPLOY_TERMS = ["deploy", "production", "shipped", "launched", "served", "scaled"]
_VAGUE_TERMS = ["responsible for", "worked on", "helped with", "involved in", "assisted"]


def _all_bullets(resume_sections: dict) -> list[str]:
    bullets = []
    for project in resume_sections.get("projects", []):
        bullets.extend(project.get("bullets", []))
    bullets.extend(resume_sections.get("experience", []))
    return [b for b in bullets if b and b.strip()]


def score_formatting(resume_text: str, resume_sections: dict) -> tuple[float, list[str]]:
    issues: list[str] = []
    bullets = _all_bullets(resume_sections)

    quantified = sum(1 for b in bullets if re.search(r"\d", b))
    quantification_ratio = quantified / len(bullets) if bullets else 0.0

    vague_count = sum(1 for b in bullets if any(term in b.lower() for term in _VAGUE_TERMS))
    deployment_mentions = sum(1 for b in bullets if any(term in b.lower() for term in _DEPLOY_TERMS))

    if quantification_ratio < 0.5:
        issues.append("Fewer than half of bullets include quantified results — add metrics.")
    if vague_count > 0:
        issues.append(f"{vague_count} bullet(s) use vague phrasing (e.g. 'responsible for').")
    if deployment_mentions == 0:
        issues.append("No mention of deployment or production usage detected.")

    if _looks_multi_column(resume_text):
        issues.append("Two-column layout detected — may break ATS text extraction.")

    score = 100.0
    score -= max(0, (0.5 - quantification_ratio)) * 100
    score -= min(vague_count, 5) * 6
    score -= 10 if deployment_mentions == 0 else 0
    score -= 10 if _looks_multi_column(resume_text) else 0
    score = round(max(0.0, min(100.0, score)), 1)

    return score, issues


def _looks_multi_column(resume_text: str) -> bool:
    """Heuristic: lines with large internal whitespace gaps suggest side-by-side columns."""
    suspicious_lines = sum(1 for line in resume_text.splitlines() if re.search(r"\S {6,}\S", line))
    return suspicious_lines > 5


def add_photo_issue(issues: list[str], has_photo: bool) -> list[str]:
    if has_photo:
        issues.append("Photo present — remove for ATS compatibility.")
    return issues
