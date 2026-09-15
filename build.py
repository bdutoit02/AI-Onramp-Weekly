"""Build the AI Onramp Weekly site.

Reads every Markdown file in weeks/, newest first, and writes a single
docs/index.html. Copies static/style.css alongside it.

Run from the repo folder:  python build.py
"""

import shutil
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
WEEKS = ROOT / "weeks"
STATIC = ROOT / "static"
DOCS = ROOT / "docs"

SITE_TITLE = "AI Onramp Weekly"
TAGLINE = "Curated reading for people keeping up with AI without living on it."
REPO_URL = "https://github.com/bdutoit02/AI-Onramp-Weekly"

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
  <h1>{title}</h1>
  <p class="tagline">{tagline}</p>
</header>
<main>
{body}
</main>
<footer>
  <p>Last built {built}. <a href="{repo}">Source on GitHub</a>.</p>
</footer>
</body>
</html>
"""


def week_to_html(path: Path) -> str:
    """Convert one weekly Markdown file into an <article> block."""
    text = path.read_text(encoding="utf-8")
    body = markdown.markdown(text)
    return f'<article class="week" id="{path.stem}">\n{body}\n</article>'


def main() -> None:
    DOCS.mkdir(exist_ok=True)

    week_files = sorted(WEEKS.glob("*.md"), reverse=True)  # newest first
    articles = "\n\n".join(week_to_html(f) for f in week_files)

    page = PAGE.format(
        title=SITE_TITLE,
        tagline=TAGLINE,
        body=articles,
        built=date.today().isoformat(),
        repo=REPO_URL,
    )
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    shutil.copy(STATIC / "style.css", DOCS / "style.css")

    print(f"Wrote docs/index.html from {len(week_files)} week file(s).")


if __name__ == "__main__":
    main()
