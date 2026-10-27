import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPIC_NAMES = {"os": "Operating Systems", "dbms": "Databases", "ml": "Machine Learning"}


def load_monsters():
    return json.loads((ROOT / "data" / "monsters.json").read_text(encoding="utf-8"))


def load_lessons():
    lessons = []
    for topic in TOPIC_NAMES:
        for path in sorted((ROOT / "content" / topic).glob("*.json")):
            lesson = json.loads(path.read_text(encoding="utf-8"))
            lesson["topic"] = topic
            lessons.append(lesson)
    return lessons
