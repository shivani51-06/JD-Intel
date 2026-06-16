"""Pydantic schemas for JD Intel API requests/responses."""
from typing import Optional, Literal
from pydantic import BaseModel


class RequiredSkill(BaseModel):
    skill: str
    weight: float
    context: str


class JDParsed(BaseModel):
    required_skills: list[RequiredSkill] = []
    nice_to_have: list[RequiredSkill] = []
    seniority: str = "unknown"
    role_type: str = "unknown"
    implicit_expectations: list[str] = []


class InterviewFormat(BaseModel):
    rounds: Optional[int] = None
    oa_mentioned: bool = False
    take_home: bool = False


class InterviewSignals(BaseModel):
    top_topics: list[str] = []
    skill_frequencies: dict[str, float] = {}
    interview_format: InterviewFormat = InterviewFormat()
    recency: str = ""
    sources: dict[str, int] = {}


class ProjectSection(BaseModel):
    name: str
    description: str = ""
    tech_stack: list[str] = []
    bullets: list[str] = []


class ResumeSections(BaseModel):
    summary: str = ""
    education: list[str] = []
    experience: list[str] = []
    projects: list[ProjectSection] = []
    skills: list[str] = []
    certifications: list[str] = []


class SkillMatch(BaseModel):
    skill: str
    status: Literal["matched", "partial", "missing"]
    similarity: float


class BulletSuggestion(BaseModel):
    original: str
    issue: str
    rewrites: list[str]


class AnalysisReport(BaseModel):
    composite_score: float
    jd_match_score: float
    interview_coverage_score: float
    formatting_score: float
    section_scores: dict[str, float]
    missing_skills: list[str]
    skill_matches: list[SkillMatch] = []
    interview_blindspots: list[str]
    top_interview_topics: list[str]
    bullet_suggestions: list[BulletSuggestion]
    parsability_issues: list[str]
    warnings: list[str] = []


class RewriteRequest(BaseModel):
    bullet: str
    jd_skills: list[str]
    interview_topics: list[str]
    company: str


class RewriteResponse(BaseModel):
    rewrites: list[str]


class JobStatus(BaseModel):
    job_id: str
    stage: str
    progress: float
    detail: str = ""
