"""Check the links in a week file: alive, and readable without a subscription?

Fetches each link logged-out (no cookies), like an incognito window, and reports
one verdict per link:

  OK         reachable and no sign of a paywall or login wall
  PAYWALLED  the site says subscribers only (Substack audience, or publisher
             metadata isAccessibleForFree=false)
  LOGIN      domain needs an account to view (X, LinkedIn, Facebook, ...)
  DEAD       4xx/5xx or could not connect
  UNSURE     reachable, but heuristics smell a paywall -- check in incognito

Only reports; never edits the week file.

Run from the repo folder:
  python check_links.py                 this week's file
  python check_links.py 2026-09-25      a specific week
  python check_links.py --all           every file in weeks/
"""

import re
import sys
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).parent
WEEKS = ROOT / "weeks"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}
TIMEOUT = 15

LOGIN_DOMAINS = {"x.com", "twitter.com", "linkedin.com", "facebook.com",
                 "instagram.com", "threads.net"}

PAYWALL_PHRASES = [
    "subscribe to continue", "subscribe to read", "subscribe to keep reading",
    "already a subscriber", "this post is for paid subscribers",
    "this post is for paying subscribers", "sign in to continue reading",
    "create a free account to continue", "upgrade to paid",
    "you've reached your limit", "you have reached your limit",
    "to continue reading", "members only", "member-only story",
]
SHORT_BODY_WORDS = 250

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def upcoming_friday(today: date) -> date:
    return today + timedelta(days=(4 - today.weekday()) % 7)


def week_files(argv: list[str]) -> list[Path]:
    if "--all" in argv:
        return sorted(WEEKS.glob("*.md"))
    target = date.fromisoformat(argv[1]) if len(argv) > 1 else upcoming_friday(date.today())
    return [WEEKS / f"{target.isoformat()}.md"]


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def strip_html(html: str) -> str:
    html = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text)


def substack_audience(url: str, html: str, session: requests.Session):
    """Return Substack's audience value for a post, or None if not a Substack post."""
    if "substackcdn.com" not in html and "substack.com" not in html:
        return None
    parsed = urlparse(url)
    m = re.match(r"^/p/([^/?#]+)", parsed.path)
    if m:
        api = f"{parsed.scheme}://{parsed.netloc}/api/v1/posts/{m.group(1)}"
        try:
            r = session.get(api, headers=HEADERS, timeout=TIMEOUT)
            if r.ok:
                audience = r.json().get("audience")
                if audience:
                    return audience
        except (requests.RequestException, ValueError):
            pass
    m = re.search(r'"audience"\s*:\s*"(\w+)"', html)
    return m.group(1) if m else None


def accessible_for_free(html: str):
    """True/False from publisher JSON-LD metadata, or None if absent."""
    m = re.search(r'"isAccessibleForFree"\s*:\s*"?(true|false)"?', html, flags=re.I)
    return None if not m else m.group(1).lower() == "true"


def check(url: str, session: requests.Session) -> tuple[str, str]:
    """Return (verdict, reason)."""
    dom = domain_of(url)
    if dom in LOGIN_DOMAINS or dom.endswith(tuple("." + d for d in LOGIN_DOMAINS)):
        return "LOGIN", f"{dom} requires an account"

    try:
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as e:
        return "DEAD", type(e).__name__

    if r.status_code >= 400:
        return "DEAD", f"HTTP {r.status_code}"

    ctype = r.headers.get("Content-Type", "")
    if "html" not in ctype:
        return "OK", f"HTTP {r.status_code}, {ctype.split(';')[0] or 'non-HTML'}"

    html = r.text

    audience = substack_audience(url, html, session)
    if audience is not None:
        if audience == "everyone":
            return "OK", "Substack: audience=everyone"
        return "PAYWALLED", f"Substack: audience={audience}"

    free = accessible_for_free(html)
    if free is False:
        return "PAYWALLED", "isAccessibleForFree=false"
    if free is True:
        return "OK", "isAccessibleForFree=true"

    if dom.endswith("medium.com") and re.search(r'"isLocked"\s*:\s*true', html):
        return "PAYWALLED", "Medium member-only"

    text = strip_html(html).lower()
    hits = [p for p in PAYWALL_PHRASES if p in text]
    words = len(text.split())
    if hits and words < SHORT_BODY_WORDS:
        return "UNSURE", f"short page ({words} words) + '{hits[0]}'"
    if hits:
        return "UNSURE", f"phrase '{hits[0]}' present ({words} words)"
    if words < SHORT_BODY_WORDS:
        return "UNSURE", f"very little text ({words} words) -- may be JS-rendered"
    return "OK", f"HTTP {r.status_code}, {words} words"


def main() -> None:
    files = week_files(sys.argv)
    session = requests.Session()
    problems = 0

    for path in files:
        if not path.exists():
            print(f"{path.name}: not found")
            continue
        links = LINK_RE.findall(path.read_text(encoding="utf-8"))
        print(f"\n{path.name}: {len(links)} link(s)")
        for title, url in links:
            verdict, reason = check(url, session)
            if verdict != "OK":
                problems += 1
            print(f"  {verdict:<9} {title[:55]:<55}  {reason}")
            if verdict != "OK":
                print(f"            {url}")

    print(f"\n{problems} link(s) need a look." if problems else "\nAll links look fine.")


if __name__ == "__main__":
    main()
