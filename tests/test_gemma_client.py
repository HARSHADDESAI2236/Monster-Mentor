import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from monster_mentor.gemma_client import GemmaClient, GemmaError, parse_json, validate_question
from monster_mentor.loader import load_lessons, load_monsters
from monster_mentor.quiz_engine import grade_quiz, shuffle_options

LESSON = load_lessons()[0]
GOOD_Q = {"q": "Q?", "options": ["a", "b", "c", "d"], "answer": 2, "why": "because"}


class ParsingTests(unittest.TestCase):
    def test_parse_fenced_json(self):
        self.assertEqual(parse_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_parse_json_with_chatter(self):
        self.assertEqual(parse_json('Sure! {"a": 1} hope that helps'), {"a": 1})

    def test_parse_garbage_raises(self):
        with self.assertRaises(GemmaError):
            parse_json("no json here")

    def test_validate_rejects_bad_answer_index(self):
        with self.assertRaises(GemmaError):
            validate_question({**GOOD_Q, "answer": 9})

    def test_validate_accepts_string_index(self):
        self.assertEqual(validate_question({**GOOD_Q, "answer": "1"})["answer"], 1)


class ClientTests(unittest.TestCase):
    def client(self):
        return GemmaClient(api_key="test-key")

    def test_status_requires_key(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertFalse(GemmaClient(api_key=None).status()[0])
        self.assertTrue(self.client().status()[0])

    def test_generate_quiz_filters_bad_questions(self):
        payload = json.dumps({"quiz": [GOOD_Q, {"q": "bad", "options": ["x"], "answer": 0}]})
        with mock.patch.object(GemmaClient, "_generate", return_value=payload):
            self.assertEqual(len(self.client().generate_quiz(LESSON, 2)), 1)

    def test_retries_then_succeeds(self):
        replies = ["oops", json.dumps({"quiz": [GOOD_Q]})]
        with mock.patch.object(GemmaClient, "_generate", side_effect=replies):
            self.assertEqual(len(self.client().generate_quiz(LESSON, 1)), 1)

    def test_generate_lesson_normalizes(self):
        lesson = {"title": "B+ Trees", "monster": "nobody", "analogy": "a", "concept": "c", "quiz": [GOOD_Q]}
        with mock.patch.object(GemmaClient, "_generate", return_value=json.dumps(lesson)):
            out = self.client().generate_lesson("B+ trees", "Databases", list(load_monsters()))
        self.assertEqual(out["id"], "b-trees")
        self.assertIn(out["monster"], load_monsters())

    def test_api_errors_become_friendly(self):
        with mock.patch.object(GemmaClient, "_generate", side_effect=RuntimeError("429 quota exceeded")):
            with self.assertRaises(GemmaError) as cm:
                self.client().chat([{"role": "user", "content": "hi"}])
        self.assertIn("Rate limit", str(cm.exception))

        with mock.patch.object(GemmaClient, "_generate", side_effect=RuntimeError("503 UNAVAILABLE: high demand")):
            with self.assertRaises(GemmaError) as cm:
                self.client().chat([{"role": "user", "content": "hi"}])
        self.assertIn("high demand", str(cm.exception))

    def test_stream_yields_chunks(self):
        with mock.patch.object(GemmaClient, "_stream", return_value=iter(["Hel", "lo"])):
            self.assertEqual("".join(self.client().stream_chat([{"role": "user", "content": "hi"}])), "Hello")


class EngineTests(unittest.TestCase):
    def test_grading_and_shuffle(self):
        self.assertEqual(grade_quiz([{"answer": 1}], [1])["score"], 1)
        s = shuffle_options(GOOD_Q)
        self.assertEqual(s["options"][s["answer"]], "c")

    def test_all_lessons_valid(self):
        monsters = load_monsters()
        for l in load_lessons():
            self.assertIn(l["monster"], monsters)


if __name__ == "__main__":
    unittest.main()
