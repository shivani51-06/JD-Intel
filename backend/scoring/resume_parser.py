"""Resume text extraction (PDF/DOCX) and Claude-driven section segmentation."""
import io
import json
import os
import re

import anthropic
import pdfplumber
from docx import Document

CLAUDE_MODEL = "claude-sonnet-4-20250514"

_SEGMENTATION_PROMPT = """Segment the following resume text into structured JSON sections. \
Return ONLY valid JSON matching this schema, no prose:

{{
  "summary": "...",
  "education": ["..."],
  "experience": ["..."],
  "projects": [{{"name": "...", "description": "...", "tech_stack": ["..."], "bullets": ["..."]}}],
  "skills": ["..."],
  "certifications": ["..."]
}}

Resume text:
---
{resume_text}
---
"""


def extract_resume_text(raw_bytes: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf_text(raw_bytes)
    if lower.endswith(".docx"):
        return _extract_docx_text(raw_bytes)
    return raw_bytes.decode("utf-8", errors="ignore")


def _extract_pdf_text(raw_bytes: bytes) -> str:
    text_chunks = []
    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
        for page in pdf.pages:
            text_chunks.append(page.extract_text() or "")
    return "\n".join(text_chunks)


def detect_resume_photo(raw_bytes: bytes, filename: str) -> bool:
    """Use pdfplumber's image extraction to flag an embedded photo (ATS red flag)."""
    if not filename.lower().endswith(".pdf"):
        return False
    try:
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                if page.images:
                    return True
    except Exception:
        return False
    return False


def _extract_docx_text(raw_bytes: bytes) -> str:
    document = Document(io.BytesIO(raw_bytes))
    return "\n".join(p.text for p in document.paragraphs)


def _client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


async def parse_resume_sections(resume_text: str) -> dict:
    try:
        return _segment_with_claude(resume_text)
    except Exception:
        return _segment_with_heuristics(resume_text)


def _segment_with_claude(resume_text: str) -> dict:
    message = _client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": _SEGMENTATION_PROMPT.format(resume_text=resume_text[:15000])}],
    )
    raw = message.content[0].text
    json_str = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_str:
        raise ValueError("Claude did not return JSON")
    return json.loads(json_str.group(0))


_SECTION_HEADERS = {
    "summary": ["summary", "objective", "about"],
    "education": ["education"],
    "experience": ["experience", "work history", "employment"],
    "projects": ["projects"],
    "skills": ["skills", "technical skills"],
    "certifications": ["certifications", "certificates"],
}


def _segment_with_heuristics(resume_text: str) -> dict:
    """Naive header-based segmentation fallback when the Claude call fails."""
    lines = [line.strip() for line in resume_text.splitlines()]
    sections: dict[str, list[str]] = {key: [] for key in _SECTION_HEADERS}
    current = None

    for line in lines:
        lowered = line.lower().strip(":#- ")
        matched_section = None
        for section, headers in _SECTION_HEADERS.items():
            if lowered in headers:
                matched_section = section
                break
        if matched_section:
            current = matched_section
            continue
        if current and line:
            sections[current].append(line)

    projects = [
        {"name": f"Project {i + 1}", "description": text, "tech_stack": [], "bullets": [text]}
        for i, text in enumerate(sections["projects"])
    ]

    return {
        "summary": " ".join(sections["summary"]),
        "education": sections["education"],
        "experience": sections["experience"],
        "projects": projects,
        "skills": sections["skills"],
        "certifications": sections["certifications"],
    }
