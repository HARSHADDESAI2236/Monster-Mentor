import json
from pathlib import Path

PATH = Path.home() / ".monster_mentor_progress.json"


def load(path=PATH):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def record(progress, lesson_id, score, total, path=PATH):
    best = progress.get(lesson_id, {}).get("score", -1)
    if score > best:
        progress[lesson_id] = {"score": score, "total": total}
    try:
        path.write_text(json.dumps(progress), encoding="utf-8")
    except OSError:
        pass  # progress just won't persist
    return progress
