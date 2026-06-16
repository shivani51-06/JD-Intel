# JD Intel - AI-Powered Resume Scorer

JD Intel scores your resume against a job description using real interview data scraped from LeetCode, Reddit, and Glassdoor - not just keyword matching.

**Live Demo**: [jd-intel.vercel.app](https://jd-intel.vercel.app)

---

## What it does

1. **Upload your resume** (PDF, DOCX, or paste text) and paste a job description
2. A multi-agent pipeline runs in real time:
   - Parses the JD to extract required skills, experience level, and role type
   - Scrapes interview experiences for that company + role from Reddit and LeetCode
   - Aggregates signals: most-asked topics, interview format, difficulty trends
3. **Results page** shows:
   - Composite score (0-100) with breakdown by category
   - Skill gap table - matched, partial, and missing skills
   - Interview blindspots - topics that appear in real interviews but not your resume
   - Bullet rewrite suggestions - specific resume lines rewritten to better match the JD
   - Parsability issues - formatting problems that hurt ATS systems

---

## Tech Stack

**Backend**
- FastAPI + LangGraph (multi-agent pipeline)
- sentence-transformers (`all-mpnet-base-v2`) for semantic skill matching
- BERTopic + spaCy for topic modeling and NER
- ChromaDB for caching scraped interview signals
- Playwright + PRAW for web scraping
- Anthropic Claude API for JD parsing, resume segmentation, and bullet rewrites (with heuristic fallbacks)

**Frontend**
- Next.js 14 (App Router) + TypeScript + Tailwind CSS
- Recharts for radar and bar charts
- Server-Sent Events (SSE) for real-time pipeline progress

**Deployment**
- Frontend: Vercel
- Backend: Hugging Face Spaces (Docker)

---

## Running locally

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python -m playwright install chromium
cp .env.example .env         # fill in your API keys
uvicorn main:app --port 8000
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE=http://localhost:8000
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Environment Variables

**Backend** (`.env`):
| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (optional — falls back to heuristics) |
| `REDDIT_CLIENT_ID` | Reddit app client ID (optional) |
| `REDDIT_CLIENT_SECRET` | Reddit app secret (optional) |
| `FRONTEND_URL` | Comma-separated allowed CORS origins |

**Frontend** (`.env.local`):
| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_BASE` | Backend URL |
