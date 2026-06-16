"""Embeds JD skills and resume sections with sentence-transformers and computes
weighted-cosine JD match scores plus per-skill match status and section-level scores."""
from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-mpnet-base-v2"
_MATCH_THRESHOLD = 0.6
_PARTIAL_THRESHOLD = 0.4

_model: SentenceTransformer | None = None

# Per-process embedding cache, keyed by text, to avoid re-embedding the same
# resume/JD content across multiple scoring calls within a session.
_embedding_cache: dict[str, np.ndarray] = {}


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _embed(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 768))
    uncached = [t for t in texts if t not in _embedding_cache]
    if uncached:
        vectors = _get_model().encode(uncached, normalize_embeddings=True)
        for text, vector in zip(uncached, vectors):
            _embedding_cache[text] = vector
    return np.array([_embedding_cache[t] for t in texts])


def _resume_section_texts(resume_sections: dict) -> list[str]:
    texts = []
    if resume_sections.get("summary"):
        texts.append(resume_sections["summary"])
    texts.extend(resume_sections.get("experience", []))
    for project in resume_sections.get("projects", []):
        texts.append(" ".join([
            project.get("description", ""),
            " ".join(project.get("tech_stack", [])),
            " ".join(project.get("bullets", [])),
        ]))
    texts.extend(resume_sections.get("skills", []))
    return [t for t in texts if t and t.strip()]


def _max_similarity(skill_vector: np.ndarray, section_vectors: np.ndarray) -> float:
    if section_vectors.shape[0] == 0:
        return 0.0
    sims = section_vectors @ skill_vector
    return float(np.max(sims))


def score_jd_match(jd_parsed: dict, resume_sections: dict) -> tuple[float, list[dict], list[str]]:
    required_skills = jd_parsed.get("required_skills", [])
    if not required_skills:
        return 0.0, [], []

    section_texts = _resume_section_texts(resume_sections)
    section_vectors = _embed(section_texts)

    skill_names = [s["skill"] for s in required_skills]
    skill_vectors = _embed(skill_names)

    weighted_sum = 0.0
    weight_total = 0.0
    matches: list[dict] = []
    missing: list[str] = []

    for skill_entry, skill_vector in zip(required_skills, skill_vectors):
        weight = float(skill_entry.get("weight", 1.0))
        similarity = _max_similarity(skill_vector, section_vectors)
        weighted_sum += weight * similarity
        weight_total += weight

        if similarity >= _MATCH_THRESHOLD:
            status = "matched"
        elif similarity >= _PARTIAL_THRESHOLD:
            status = "partial"
        else:
            status = "missing"
            missing.append(skill_entry["skill"])

        matches.append({"skill": skill_entry["skill"], "status": status, "similarity": round(similarity, 3)})

    score = round(100 * weighted_sum / weight_total, 1) if weight_total else 0.0
    return score, matches, missing


def score_sections(jd_parsed: dict, resume_sections: dict) -> dict[str, float]:
    required_skills = jd_parsed.get("required_skills", []) + jd_parsed.get("nice_to_have", [])
    if not required_skills:
        return {}

    skill_names = [s["skill"] for s in required_skills]
    skill_weights = np.array([float(s.get("weight", 1.0)) for s in required_skills])
    skill_vectors = _embed(skill_names)

    section_definitions = {
        "summary": [resume_sections.get("summary", "")],
        "experience": resume_sections.get("experience", []),
        "projects": [
            " ".join([p.get("description", ""), " ".join(p.get("tech_stack", [])), " ".join(p.get("bullets", []))])
            for p in resume_sections.get("projects", [])
        ],
        "skills": resume_sections.get("skills", []),
    }

    scores = {}
    for section_name, texts in section_definitions.items():
        texts = [t for t in texts if t and t.strip()]
        if not texts:
            scores[section_name] = 0.0
            continue
        section_vectors = _embed(texts)
        sims = np.array([_max_similarity(vec, section_vectors) for vec in skill_vectors])
        weighted = float(np.sum(sims * skill_weights) / np.sum(skill_weights))
        scores[section_name] = round(100 * weighted, 1)

    return scores
