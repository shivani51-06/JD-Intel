"""Agent 3 — Signal Aggregator: turn raw scraped posts into topic + skill signals.

Runs BERTopic over the post corpus (falling back to TF-IDF frequency ranking when
the corpus is too small for BERTopic to be meaningful, i.e. < 10 documents), and
spaCy NER to count skill mentions weighted by frequency x recency x source credibility.
"""
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

import spacy
from sklearn.feature_extraction.text import TfidfVectorizer

_BERTOPIC_MIN_DOCS = 10

_TECH_SKILL_PATTERNS = [
    "python", "java", "c++", "sql", "pytorch", "tensorflow", "system design",
    "probability", "statistics", "machine learning", "data structures", "algorithms",
    "distributed systems", "kubernetes", "docker", "aws", "leadership principles",
    "behavioral", "object oriented design", "sql window functions", "a/b testing",
    "deep learning", "nlp", "computer vision", "recommendation systems",
]

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            _nlp = spacy.blank("en")
        if "entity_ruler" not in _nlp.pipe_names:
            ruler = _nlp.add_pipe("entity_ruler")
            patterns = [{"label": "TECH_SKILL", "pattern": skill} for skill in _TECH_SKILL_PATTERNS]
            ruler.add_patterns(patterns)
    return _nlp


def _round_robin_format_signals(posts: list[dict]) -> dict:
    rounds_mentions = []
    oa_mentioned = False
    take_home = False
    for post in posts:
        text = f"{post.get('title', '')} {post.get('body', '')}".lower()
        match = re.search(r"(\d+)\s*rounds?", text)
        if match:
            rounds_mentions.append(int(match.group(1)))
        if "online assessment" in text or re.search(r"\boa\b", text):
            oa_mentioned = True
        if "take home" in text or "take-home" in text:
            take_home = True
    rounds = round(sum(rounds_mentions) / len(rounds_mentions)) if rounds_mentions else None
    return {"rounds": rounds, "oa_mentioned": oa_mentioned, "take_home": take_home}


def _extract_topics(corpus: list[str]) -> list[str]:
    if len(corpus) >= _BERTOPIC_MIN_DOCS:
        try:
            from bertopic import BERTopic

            model = BERTopic(verbose=False, calculate_probabilities=False)
            model.fit_transform(corpus)
            topic_info = model.get_topic_info()
            topics = []
            for _, row in topic_info.iterrows():
                if row["Topic"] == -1:
                    continue
                words = [w for w, _ in model.get_topic(row["Topic"])[:3]]
                if words:
                    topics.append(" ".join(words))
                if len(topics) >= 10:
                    break
            if topics:
                return topics
        except Exception:
            pass

    # TF-IDF fallback for small corpora or BERTopic failure
    if not corpus:
        return []
    vectorizer = TfidfVectorizer(stop_words="english", max_features=200, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform(corpus)
    scores = matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(zip(terms, scores), key=lambda kv: kv[1], reverse=True)
    return [term for term, _ in ranked[:10]]


def _score_skills(posts: list[dict]) -> dict[str, float]:
    nlp = _get_nlp()
    weighted_counts: defaultdict[str, float] = defaultdict(float)

    for post in posts:
        text = f"{post.get('title', '')} {post.get('body', '')}"
        doc = nlp(text)
        mentioned = Counter()
        for ent in doc.ents:
            if ent.label_ == "TECH_SKILL":
                mentioned[ent.text.lower()] += 1
        # also catch raw vocabulary matches if entity ruler isn't populated
        text_lower = text.lower()
        for skill in _TECH_SKILL_PATTERNS:
            if skill in text_lower and skill not in mentioned:
                mentioned[skill] += text_lower.count(skill)

        recency_weight = post.get("recency_weight", 1.0)
        credibility = post.get("credibility", 0.8)
        for skill, freq in mentioned.items():
            weighted_counts[skill] += freq * recency_weight * credibility

    return dict(sorted(weighted_counts.items(), key=lambda kv: kv[1], reverse=True))


async def run_signal_aggregator(posts: list[dict], company: str, role: str, cache) -> dict:
    cached = cache.get(company, role)
    if cached is not None:
        return cached

    warnings = []
    if not posts:
        warnings.append(
            f"No interview posts found for {company} / {role}; signals are based on an empty corpus."
        )

    corpus = [f"{p.get('title', '')} {p.get('body', '')}".strip() for p in posts if p.get("body") or p.get("title")]
    top_topics = _extract_topics(corpus)
    skill_frequencies = _score_skills(posts)
    interview_format = _round_robin_format_signals(posts)

    sources = Counter(p.get("source", "unknown") for p in posts)

    signals = {
        "top_topics": top_topics,
        "skill_frequencies": skill_frequencies,
        "interview_format": interview_format,
        "recency": f"last_scraped: {datetime.now(timezone.utc).date().isoformat()}",
        "sources": dict(sources),
        "raw_posts": posts,
        "warnings": warnings,
    }

    cache.set(company, role, signals)
    return signals
