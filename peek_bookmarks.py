import json, os
from pathlib import Path

BOOKMARKS = Path(os.environ["LOCALAPPDATA"]) / "Google/Chrome/User Data/Default/Bookmarks"
data = json.loads(BOOKMARKS.read_text(encoding="utf-8"))

def walk(node, depth=0):
    if node.get("type") == "folder":
        print("  " * depth + f"[{node['name']}]")
        for child in node.get("children", []):
            walk(child, depth + 1)
    else:
        print("  " * depth + f"- {node['name']}")

for root in data["roots"].values():
    walk(root)