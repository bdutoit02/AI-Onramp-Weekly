"""Import Chrome bookmarks from the "Onramp Inbox" folder into this week's file.

Reads Chrome's bookmark file (read-only), finds the inbox folder, and adds
one bullet per bookmark to weeks/<friday>.md under "## Readings".
Creates the week file if it doesn't exist; skips URLs already in it.

Run from the repo folder:  python import_bookmarks.py
Optional: python import_bookmarks.py 2026-09-25   (target a specific week)
"""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
WEEKS = ROOT / "weeks"
BOOKMARKS = Path(os.environ["LOCALAPPDATA"]) / "Google/Chrome/User Data/Default/Bookmarks"
INBOX_FOLDER = "Onramp Inbox"

WEEK_TEMPLATE = """# Week ending {title_date}

TODO: one or two sentences on what mattered this week.

## Readings
"""


def upcoming_friday(today: date) -> date:
    """The Friday this week (or today, if today is a Friday)."""
    return today + timedelta(days=(4 - today.weekday()) % 7)


def chrome_time(value: str) -> date:
    """Chrome stores times as microseconds since 1 Jan 1601."""
    epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
    return (epoch + timedelta(microseconds=int(value))).date()


def find_folder(node: dict, name: str):
    """Depth-first search of the bookmark tree for a folder by name."""
    if node.get("type") == "folder":
        if node["name"].lower() == name.lower():
            return node
        for child in node.get("children", []):
            found = find_folder(child, name)
            if found:
                return found
    return None


def clean_title(title: str) -> str:
    title = re.sub(r"^\(\d+\)\s*", "", title)          # "(3) " unread counts
    title = re.sub(r"\s*[-|\\]\s*YouTube$", "", title)  # " - YouTube"
    return title.strip()


def bullet(item: dict) -> str:
    title = clean_title(item["name"])
    url = item["url"]
    domain = urlparse(url).netloc.removeprefix("www.")
    added = chrome_time(item["date_added"])
    nice_date = f"{added.day} {added:%b %Y}"
    return f"- [{title}]({url}) — *{domain}, {nice_date}.* TODO note."


def main() -> None:
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else upcoming_friday(date.today())
    week_file = WEEKS / f"{target.isoformat()}.md"

    data = json.loads(BOOKMARKS.read_text(encoding="utf-8"))
    folder = None
    for root in data["roots"].values():
        folder = find_folder(root, INBOX_FOLDER)
        if folder:
            break
    if not folder:
        sys.exit(f"No bookmark folder called '{INBOX_FOLDER}' found.")

    links = [c for c in folder.get("children", []) if c.get("type") == "url"]
    if not links:
        sys.exit(f"'{INBOX_FOLDER}' is empty; nothing to import.")

    if week_file.exists():
        text = week_file.read_text(encoding="utf-8")
    else:
        text = WEEK_TEMPLATE.format(title_date=f"{target.day} {target:%B %Y}")

    new_lines = [bullet(item) for item in links if item["url"] not in text]
    if not new_lines:
        print(f"All {len(links)} inbox link(s) already in {week_file.name}; nothing added.")
        return

    text = text.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n"
    WEEKS.mkdir(exist_ok=True)
    week_file.write_text(text, encoding="utf-8")

    print(f"Added {len(new_lines)} link(s) to {week_file.name}:")
    for line in new_lines:
        print("  " + line[:90] + ("..." if len(line) > 90 else ""))
    print("Now fill in the TODOs, then run build.py.")


if __name__ == "__main__":
    main()
