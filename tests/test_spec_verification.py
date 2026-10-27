import unittest
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from monster_mentor.loader import load_lessons, load_monsters, TOPIC_NAMES
from monster_mentor.quiz_engine import grade_quiz, shuffle_options
from monster_mentor.prompts import monster_system, quiz_prompt, explain_mistakes_prompt, lesson_prompt
from monster_mentor.gemma_client import GemmaClient, DEFAULT_MODEL, MODELS


class TestMonsterMentorFullSpec(unittest.TestCase):
    """
    Test suite verifying the user's core specification:
    1. Explains hard computer science topics (Operating Systems, Databases, Machine Learning)
    2. Uses friendly monsters
    3. Each lesson has:
       - A monster story
       - The real explanation
       - A short quiz
    4. Built with Python and Streamlit
    5. Gemma 4 powers:
       - Chat ('Ask the monster')
       - Fresh quizzes ('Fresh quiz')
       - New lesson creation ('New lesson')
       - Mistake explanations
    """

    @classmethod
    def setUpClass(cls):
        cls.lessons = load_lessons()
        cls.monsters = load_monsters()

    def test_topics_coverage(self):
        """1. Verify OS, DBMS, ML are all covered with rich lessons."""
        expected_topics = {"os": "Operating Systems", "dbms": "Database Systems", "ml": "Machine Learning"}
        for topic_key, topic_label in expected_topics.items():
            self.assertIn(topic_key, TOPIC_NAMES)
            topic_lessons = [l for l in self.lessons if l["topic"] == topic_key]
            self.assertGreaterEqual(len(topic_lessons), 3, f"Topic '{topic_label}' has fewer than 3 lessons.")

    def test_friendly_monsters(self):
        """2. Verify friendly monsters exist with unique traits, names, and Halloween attributes."""
        self.assertGreaterEqual(len(self.monsters), 7)
        for m_id, monster in self.monsters.items():
            self.assertIn("name", monster)
            self.assertIn("trait", monster)
            self.assertIn("color", monster)
            self.assertTrue(len(monster["name"].strip()) > 0)
            self.assertTrue(len(monster["trait"].strip()) > 10)

    def test_lesson_three_part_structure(self):
        """3. Verify each lesson has (a) monster story, (b) real explanation, (c) short quiz."""
        for lesson in self.lessons:
            # (a) Monster story
            self.assertIn("analogy", lesson, f"Missing monster story in {lesson['id']}")
            self.assertGreater(len(lesson["analogy"].strip()), 30)

            # (b) Real explanation
            self.assertIn("concept", lesson, f"Missing real explanation in {lesson['id']}")
            self.assertGreater(len(lesson["concept"].strip()), 40)

            # (c) Short quiz
            self.assertIn("quiz", lesson, f"Missing quiz in {lesson['id']}")
            quiz = lesson["quiz"]
            self.assertGreaterEqual(len(quiz), 2, f"Quiz should have at least 2 questions in {lesson['id']}")
            for q in quiz:
                self.assertIn("q", q)
                self.assertIn("options", q)
                self.assertIn("answer", q)
                self.assertIn("why", q)
                self.assertGreaterEqual(len(q["options"]), 2)
                self.assertGreaterEqual(q["answer"], 0)
                self.assertLess(q["answer"], len(q["options"]))
                self.assertGreater(len(q["why"].strip()), 5)

            # Associated monster must be valid
            self.assertIn(lesson["monster"], self.monsters)

    def test_gemma_4_capabilities(self):
        """4. Verify Gemma 4 powers chat, fresh quizzes, new lessons, and mistake explanations."""
        # Models supported
        self.assertIn("gemma-4-26b-a4b-it", MODELS)
        self.assertIn("gemma-4-31b-it", MODELS)
        self.assertEqual(DEFAULT_MODEL, "gemma-4-26b-a4b-it")

        sample_lesson = self.lessons[0]
        sample_monster = self.monsters[sample_lesson["monster"]]

        # a) Chat prompt ('Ask the monster')
        chat_prompt = monster_system(sample_monster, sample_lesson)
        self.assertIn(sample_monster["name"], chat_prompt)
        self.assertIn(sample_monster["trait"], chat_prompt)
        self.assertIn("explain using your monster analogy first", chat_prompt)

        # b) Fresh quiz prompt ('Fresh quiz')
        f_prompt = quiz_prompt(sample_lesson, 3)
        self.assertIn(sample_lesson["title"], f_prompt)
        self.assertIn("Return ONLY JSON", f_prompt)

        # c) New lesson creation prompt ('New lesson')
        l_prompt = lesson_prompt("Distributed Locks", "Operating Systems", list(self.monsters.keys()))
        self.assertIn("Distributed Locks", l_prompt)
        self.assertIn("Operating Systems", l_prompt)

        # d) Mistake explanations
        mistakes = [{"q": "Question 1", "picked": "Choice A", "correct": "Choice B"}]
        m_prompt = explain_mistakes_prompt(sample_lesson, mistakes)
        self.assertIn("Choice A", m_prompt)
        self.assertIn("Choice B", m_prompt)

    def test_offline_mode_graceful_fallback(self):
        """5. Verify the app operates gracefully offline without an API key."""
        client_offline = GemmaClient(api_key=None)
        status_ok, msg = client_offline.status()
        self.assertFalse(status_ok)
        self.assertIn("API key", msg)


if __name__ == "__main__":
    unittest.main()
