"""Cross-checks scraped interview topics against resume content; flags blindspots —
topics that show up repeatedly in real interviews but are absent from both the JD and resume."""
from .skill_ranker import _embed, _max_similarity, _resume_section_texts

_TOPIC_MATCH_THRESHOLD = 0.5
_BLINDSPOT_TOP_N = 5


def score_interview_coverage(interview_signals: dict, resume_sections: dict) -> tuple[float, list[str]]:
    top_topics = interview_signals.get("top_topics", [])
    if not top_topics:
        return 0.0, []

    section_texts = _resume_section_texts(resume_sections)
    section_vectors = _embed(section_texts)
    topic_vectors = _embed(top_topics)

    matched = []
    for topic, topic_vector in zip(top_topics, topic_vectors):
        if _max_similarity(topic_vector, section_vectors) >= _TOPIC_MATCH_THRESHOLD:
            matched.append(topic)

    coverage = round(100 * len(matched) / len(top_topics), 1)
    return coverage, matched


def detect_blindspots(interview_signals: dict, jd_parsed: dict, resume_sections: dict) -> list[str]:
    top_topics = interview_signals.get("top_topics", [])[:_BLINDSPOT_TOP_N]
    if not top_topics:
        return []

    jd_terms = " ".join(
        [s["skill"] for s in jd_parsed.get("required_skills", []) + jd_parsed.get("nice_to_have", [])]
        + jd_parsed.get("implicit_expectations", [])
    )
    section_texts = _resume_section_texts(resume_sections) + ([jd_terms] if jd_terms.strip() else [])
    if not section_texts:
        return list(top_topics)

    section_vectors = _embed(section_texts)
    topic_vectors = _embed(top_topics)

    blindspots = []
    for topic, topic_vector in zip(top_topics, topic_vectors):
        if _max_similarity(topic_vector, section_vectors) < _TOPIC_MATCH_THRESHOLD:
            blindspots.append(topic)

    return blindspots
