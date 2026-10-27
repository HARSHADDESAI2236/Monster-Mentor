import unittest
from pathlib import Path
import json

from monster_mentor.loader import load_lessons, load_monsters, TOPIC_NAMES
from monster_mentor.quiz_engine import grade_quiz, shuffle_options
from monster_mentor.progress import record, load
from monster_mentor.prompts import monster_system, quiz_prompt, explain_mistakes_prompt, lesson_prompt
from monster_mentor.gemma_client import validate_question


class TestMonsterMentorPS19(unittest.TestCase):
    """
    Test suite verifying PS 1.9 specifications:
    - Tough concepts explained (OS, DBMS, ML)
    - Friendly monsters as analogies
    - Quick quiz after each concept
    - Quiz engine, grading, and prompt generation
    """

    @classmethod
    def setUpClass(cls):
        cls.lessons = load_lessons()
        cls.monsters = load_monsters()

    def test_ps19_topics_coverage(self):
        """Check OS, DBMS, ML are all supported and have lessons."""
        expected_topics = {"os", "dbms", "ml"}
        self.assertTrue(expected_topics.issubset(set(TOPIC_NAMES.keys())))
        
        topics_with_lessons = {lesson["topic"] for lesson in self.lessons}
        self.assertEqual(expected_topics, topics_with_lessons, 
                         f"Expected lessons for {expected_topics}, but found {topics_with_lessons}")

    def test_os_concepts_and_analogies(self):
        """Validate OS lessons have friendly monster analogies and technical concepts."""
        os_lessons = [l for l in self.lessons if l["topic"] == "os"]
        self.assertGreaterEqual(len(os_lessons), 3)
        
        os_titles = {l["id"] for l in os_lessons}
        self.assertIn("deadlocks", os_titles)
        self.assertIn("memory", os_titles)
        self.assertIn("processes", os_titles)

        for lesson in os_lessons:
            self.assertTrue(len(lesson["analogy"].strip()) > 20, f"OS Analogy too short for {lesson['id']}")
            self.assertTrue(len(lesson["concept"].strip()) > 30, f"OS Concept too short for {lesson['id']}")
            self.assertIn(lesson["monster"], self.monsters)

    def test_dbms_concepts_and_analogies(self):
        """Validate DBMS lessons have friendly monster analogies and technical concepts."""
        dbms_lessons = [l for l in self.lessons if l["topic"] == "dbms"]
        self.assertGreaterEqual(len(dbms_lessons), 3)

        dbms_titles = {l["id"] for l in dbms_lessons}
        self.assertIn("indexing", dbms_titles)
        self.assertIn("normalization", dbms_titles)
        self.assertIn("transactions", dbms_titles)

        for lesson in dbms_lessons:
            self.assertTrue(len(lesson["analogy"].strip()) > 20, f"DBMS Analogy too short for {lesson['id']}")
            self.assertTrue(len(lesson["concept"].strip()) > 30, f"DBMS Concept too short for {lesson['id']}")
            self.assertIn(lesson["monster"], self.monsters)

    def test_ml_concepts_and_analogies(self):
        """Validate ML lessons have friendly monster analogies and technical concepts."""
        ml_lessons = [l for l in self.lessons if l["topic"] == "ml"]
        self.assertGreaterEqual(len(ml_lessons), 3)

        ml_titles = {l["id"] for l in ml_lessons}
        self.assertIn("bias-variance", ml_titles)
        self.assertIn("gradient-descent", ml_titles)
        self.assertIn("overfitting", ml_titles)

        for lesson in ml_lessons:
            self.assertTrue(len(lesson["analogy"].strip()) > 20, f"ML Analogy too short for {lesson['id']}")
            self.assertTrue(len(lesson["concept"].strip()) > 30, f"ML Concept too short for {lesson['id']}")
            self.assertIn(lesson["monster"], self.monsters)

    def test_monster_profiles(self):
        """Verify each monster has friendly attributes (name, color, shape, trait)."""
        for m_id, monster in self.monsters.items():
            self.assertIn("name", monster)
            self.assertIn("color", monster)
            self.assertIn("shape", monster)
            self.assertIn("trait", monster)
            self.assertTrue(monster["color"].startswith("#"))
            self.assertIn(monster["shape"], ["round", "tall"])
            self.assertTrue(len(monster["trait"]) > 5)

    def test_quick_quiz_after_each_lesson(self):
        """Verify every single lesson has a quick quiz with valid questions and explanations."""
        for lesson in self.lessons:
            quiz = lesson.get("quiz")
            self.assertIsInstance(quiz, list, f"Quiz missing in {lesson['id']}")
            self.assertGreaterEqual(len(quiz), 2, f"Expected at least 2 questions in {lesson['id']}")
            
            for q in quiz:
                validated = validate_question(q)
                self.assertIn("why", validated)
                self.assertTrue(len(validated["why"].strip()) > 5, 
                                f"Explanation 'why' missing or empty in {lesson['id']}: {q['q']}")
                self.assertGreaterEqual(len(validated["options"]), 2)
                self.assertGreaterEqual(validated["answer"], 0)
                self.assertLess(validated["answer"], len(validated["options"]))

    def test_quiz_grading_scenarios(self):
        """Test quiz engine evaluation, pass criteria, and accuracy."""
        quiz_sample = [
            {"q": "Q1", "options": ["A", "B", "C", "D"], "answer": 1, "why": "B is right"},
            {"q": "Q2", "options": ["A", "B", "C", "D"], "answer": 3, "why": "D is right"},
            {"q": "Q3", "options": ["A", "B"], "answer": 0, "why": "A is right"}
        ]
        
        # Perfect score
        res_full = grade_quiz(quiz_sample, [1, 3, 0])
        self.assertEqual(res_full["score"], 3)
        self.assertEqual(res_full["total"], 3)
        self.assertTrue(res_full["passed"])
        self.assertEqual(res_full["results"], [True, True, True])

        # Passing score (2/3 = 66.7% >= 60%)
        res_pass = grade_quiz(quiz_sample, [1, 3, 1])
        self.assertEqual(res_pass["score"], 2)
        self.assertTrue(res_pass["passed"])
        self.assertEqual(res_pass["results"], [True, True, False])

        # Failing score (1/3 = 33.3% < 60%)
        res_fail = grade_quiz(quiz_sample, [1, 0, 1])
        self.assertEqual(res_fail["score"], 1)
        self.assertFalse(res_fail["passed"])
        self.assertEqual(res_fail["results"], [True, False, False])

        # Zero score
        res_zero = grade_quiz(quiz_sample, [0, 0, 1])
        self.assertEqual(res_zero["score"], 0)
        self.assertFalse(res_zero["passed"])

    def test_quiz_shuffle_integrity(self):
        """Verify shuffle maintains correct answer semantics."""
        original = {
            "q": "What is thrashing?",
            "options": ["Fast page lookups", "Constant swapping", "Memory encryption", "Deadlock"],
            "answer": 1,
            "why": "Constant swapping"
        }
        correct_text = original["options"][original["answer"]]

        for _ in range(10):
            shuffled = shuffle_options(original)
            # Make sure all options are preserved
            self.assertEqual(sorted(shuffled["options"]), sorted(original["options"]))
            # Make sure updated answer index points to the exact same correct text
            self.assertEqual(shuffled["options"][shuffled["answer"]], correct_text)

    def test_progress_persistence(self):
        """Verify recording and score tracking behavior."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tf:
            temp_path = Path(tf.name)
        
        try:
            p = {}
            # Record first score
            record(p, "deadlocks", 1, 2, path=temp_path)
            self.assertEqual(p["deadlocks"]["score"], 1)
            
            # Record improved score
            record(p, "deadlocks", 2, 2, path=temp_path)
            self.assertEqual(p["deadlocks"]["score"], 2)
            
            # Lower score should not overwrite best score
            record(p, "deadlocks", 0, 2, path=temp_path)
            self.assertEqual(p["deadlocks"]["score"], 2)
            
            # Reload from disk
            loaded = load(path=temp_path)
            self.assertEqual(loaded["deadlocks"]["score"], 2)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_prompts_conform_to_monster_pedagogy(self):
        """Verify prompt templates inject monster analogies, personalities, and proper formatting."""
        lesson = self.lessons[0]
        monster = self.monsters[lesson["monster"]]

        # Monster system prompt
        sys_prompt = monster_system(monster, lesson)
        self.assertIn(monster["name"], sys_prompt)
        self.assertIn(monster["trait"], sys_prompt)
        self.assertIn(lesson["analogy"], sys_prompt)
        self.assertIn("explain using your monster analogy first", sys_prompt)

        # Quiz prompt
        q_prompt = quiz_prompt(lesson, 3)
        self.assertIn(lesson["title"], q_prompt)
        self.assertIn("Return ONLY JSON", q_prompt)

        # Explain mistakes prompt
        wrong_examples = [{"q": "Test Q", "picked": "Choice A", "correct": "Choice B"}]
        mistakes_prompt = explain_mistakes_prompt(lesson, wrong_examples)
        self.assertIn("Test Q", mistakes_prompt)
        self.assertIn("using the monster analogy", mistakes_prompt)

    def test_ui_visual_components_and_cheer(self):
        """Verify UI SVG components render properly formatted and cheer evaluates scores."""
        import sys
        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from app import realistic_pumpkin_svg, cute_3d_ghost_svg, haunted_landscape_svg, cheer

        pumpkin = realistic_pumpkin_svg(300)
        self.assertTrue(pumpkin.strip().startswith("<svg"))
        self.assertTrue(pumpkin.strip().endswith("</svg>"))
        self.assertIn("flameGlow", pumpkin)
        self.assertIn("pSkin", pumpkin)

        ghost = cute_3d_ghost_svg()
        self.assertTrue(ghost.strip().startswith("<svg"))
        self.assertTrue(ghost.strip().endswith("</svg>"))
        self.assertIn("ghostShade", ghost)

        landscape = haunted_landscape_svg()
        self.assertTrue(landscape.strip().startswith("<svg"))
        self.assertTrue(landscape.strip().endswith("</svg>"))
        self.assertIn("skyGrad", landscape)

        # Cheer evaluation
        self.assertIn("Spooktacular", cheer(3, 3))
        self.assertIn("Passed", cheer(2, 3))
        self.assertIn("Tough", cheer(0, 3))
        self.assertIn("Ready", cheer(0, 0))


if __name__ == "__main__":
    unittest.main()
