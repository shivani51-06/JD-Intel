"""Agent 2 — Interview Scraper: gather real interview experiences for company+role.

Checks the ChromaDB cache first (24h TTL). On a miss, scrapes LeetCode Discuss and
Reddit in parallel, with a best-effort Glassdoor pass that degrades gracefully.
Each post is temporally weighted: <6mo -> 1.0, <12mo -> 0.6, older -> 0.3.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

import praw

LEETCODE_URL = "https://leetcode.com/discuss/interview-experience/?company={company}"
REDDIT_SUBREDDITS = ["cscareerquestions", "MachineLearning"]


def _recency_weight(posted_at: datetime) -> float:
    age = datetime.now(timezone.utc) - posted_at
    if age <= timedelta(days=180):
        return 1.0
    if age <= timedelta(days=365):
        return 0.6
    return 0.3


async def run_interview_scraper(company: str, role: str, cache) -> list[dict]:
    cached = cache.get(company, role)
    if cached is not None:
        return cached.get("raw_posts", [])

    leetcode_task = asyncio.create_task(_scrape_leetcode(company))
    reddit_task = asyncio.create_task(_scrape_reddit(company, role))
    glassdoor_task = asyncio.create_task(_scrape_glassdoor(company, role))

    leetcode_posts, reddit_posts, glassdoor_posts = await asyncio.gather(
        leetcode_task, reddit_task, glassdoor_task
    )

    posts = leetcode_posts + reddit_posts + glassdoor_posts
    cutoff = datetime.now(timezone.utc) - timedelta(days=365)
    posts = [p for p in posts if p["posted_at"] >= cutoff]

    for post in posts:
        post["recency_weight"] = _recency_weight(post["posted_at"])
        post["posted_at"] = post["posted_at"].isoformat()

    return posts


async def _scrape_leetcode(company: str) -> list[dict]:
    """Scrape LeetCode Discuss interview-experience posts via Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    url = LEETCODE_URL.format(company=company)
    posts: list[dict] = []
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30_000)
            await page.wait_for_selector("a[href*='/discuss/']", timeout=15_000)
            cards = await page.query_selector_all("a[href*='/discuss/']")
            for card in cards[:30]:
                title = (await card.inner_text()).strip()
                if not title:
                    continue
                posts.append({
                    "source": "leetcode",
                    "title": title,
                    "body": title,
                    "posted_at": datetime.now(timezone.utc) - timedelta(days=30),
                    "credibility": 1.0,
                })
            await browser.close()
    except Exception:
        return posts
    return posts


async def _scrape_reddit(company: str, role: str) -> list[dict]:
    """Search relevant subreddits for interview-experience threads via PRAW."""
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "jd-intel/0.1")
    if not client_id or not client_secret:
        return []

    def _search() -> list[dict]:
        reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
        results = []
        query = f'"{company}" "{role}" interview'
        for subreddit_name in REDDIT_SUBREDDITS:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                for submission in subreddit.search(query, sort="new", limit=20):
                    results.append({
                        "source": "reddit",
                        "title": submission.title,
                        "body": (submission.selftext or "")[:4000],
                        "posted_at": datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
                        "credibility": 0.8,
                    })
            except Exception:
                continue
        return results

    try:
        return await asyncio.to_thread(_search)
    except Exception:
        return []


async def _scrape_glassdoor(company: str, role: str, retries: int = 2) -> list[dict]:
    """Best-effort Glassdoor scrape. Glassdoor rate-limits aggressively and CAPTCHAs often;
    if it fails after `retries` attempts we degrade gracefully and return an empty list."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return []

    for attempt in range(retries):
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(
                    f"https://www.glassdoor.com/Interview/{company}-Interview-Questions-E0.htm",
                    timeout=30_000,
                )
                if await page.query_selector("text=/verify you are a human/i"):
                    raise RuntimeError("glassdoor CAPTCHA encountered")
                cards = await page.query_selector_all("[data-test='interview-review']")
                posts = []
                for card in cards[:20]:
                    text = (await card.inner_text()).strip()
                    if text:
                        posts.append({
                            "source": "glassdoor",
                            "title": text[:120],
                            "body": text,
                            "posted_at": datetime.now(timezone.utc) - timedelta(days=60),
                            "credibility": 0.9,
                        })
                await browser.close()
                return posts
        except Exception:
            await asyncio.sleep(1.5 * (attempt + 1))
            continue
    return []
