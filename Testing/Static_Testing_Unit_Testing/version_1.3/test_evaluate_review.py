"""
Updated Test suite for evaluate_review with module-level patching
(because heuristic_metrics and meta_evaluate are imported at module level)
"""

import unittest
from unittest.mock import patch
from online_estimator_version import IterativePromptSelector


class TestEvaluateReview(unittest.TestCase):

    def setUp(self):
        with patch("online_estimator_version.get_prompts"):
            self.selector = IterativePromptSelector()

    # --------------------------------------------------------------
    def test_successful_evaluation(self):

        diff = "def foo(): pass"
        review = "Good code structure."
        static = "No issues"
        context = "Best practices"

        heur_mock = lambda *a, **k: {
            "sections_presence": {"summary": True},
            "bullet_points": 3,
            "length_words": 50,
            "mentions_bug": False,
            "mentions_suggest": True,
        }

        meta_mock = lambda *a, **k: (
            {"clarity": 7, "usefulness": 8, "depth": 6, "actionability": 7, "positivity": 5},
            "ignored",
        )

        with patch("online_estimator_version.heuristic_metrics", side_effect=heur_mock), \
             patch("online_estimator_version.meta_evaluate", side_effect=meta_mock):

            score, heur_out, meta_out = self.selector.evaluate_review(
                diff, review
            )

            self.assertIsInstance(score, float)
            self.assertIsInstance(heur_out, dict)
            self.assertIsInstance(meta_out, dict)

    # --------------------------------------------------------------
    def test_evaluation_with_meta_error(self):

        heur_mock = lambda *a, **k: {"dummy": True}
        meta_mock = lambda *a, **k: ({"error": "Failed"}, "")

        with patch("online_estimator_version.heuristic_metrics", side_effect=heur_mock), \
             patch("online_estimator_version.meta_evaluate", side_effect=meta_mock):

            score, heur_out, meta_out = self.selector.evaluate_review(
                "diff", "review"
            )

            self.assertEqual(score, 5.0)

    # --------------------------------------------------------------
    def test_evaluation_score_calculation(self):

        heur_data = {
            "sections_presence": {"summary": True, "issues": True, "suggestions": True},
            "bullet_points": 8,
            "length_words": 150,
            "mentions_bug": True,
            "mentions_suggest": True,
        }

        meta_data = {
            "clarity": 9,
            "usefulness": 8,
            "depth": 7,
            "actionability": 8,
            "positivity": 6,
        }

        with patch("online_estimator_version.heuristic_metrics", return_value=heur_data), \
             patch("online_estimator_version.meta_evaluate", return_value=(meta_data, "text")):

            score, _, _ = self.selector.evaluate_review(
                "diff", "review"
            )

            self.assertGreater(score, 0)

    # --------------------------------------------------------------
    def test_evaluation_with_short_review(self):

        heur_data = {
            "sections_presence": {},
            "bullet_points": 0,
            "length_words": 20,
            "mentions_bug": False,
            "mentions_suggest": False,
        }

        with patch("online_estimator_version.heuristic_metrics", return_value=heur_data), \
             patch("online_estimator_version.meta_evaluate", return_value=({"clarity": 5}, "")):

            score, _, _ = self.selector.evaluate_review(
                "diff", "short review"
            )

            self.assertIsInstance(score, float)

    # --------------------------------------------------------------
    def test_evaluation_with_long_review(self):

        heur_data = {
            "sections_presence": {"summary": True, "issues": True},
            "bullet_points": 15,
            "length_words": 1500,
            "mentions_bug": True,
            "mentions_suggest": True,
        }

        with patch("online_estimator_version.heuristic_metrics", return_value=heur_data), \
             patch("online_estimator_version.meta_evaluate", return_value=({"clarity": 6}, "")):

            score, _, _ = self.selector.evaluate_review(
                "diff", "X" * 10000
            )

            self.assertIsInstance(score, float)
