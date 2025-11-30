"""
Corrected generate_review test suite.
Fixes the '__or__' AttributeError by mocking llm and parser properly.
"""

import unittest
from unittest.mock import patch, Mock
from online_estimator_version import IterativePromptSelector


class TestGenerateReview(unittest.TestCase):

    def setUp(self):
        with patch("online_estimator_version.get_prompts"):
            self.selector = IterativePromptSelector()

        # Create mock prompts (their __or__ will be set in test methods)
        self.selector.prompts = {
            "detailed": Mock(),
            "concise": Mock(),
            "security": Mock(),
        }

    # ------------------------------------------------------------------
    def _build_pipe_chain(self, final_return):
        """
        Helper: Build a complete mock pipeline:
        prompt | llm | parser
        """

        mock_prompt = Mock()
        mock_llm = Mock()
        mock_parser = Mock()

        # Set OR chaining
        mock_prompt.__or__.return_value = mock_llm
        mock_llm.__or__.return_value = mock_parser

        # Final output
        mock_parser.invoke.return_value = final_return

        return mock_prompt, mock_llm, mock_parser

    # ==================================================================
    def test_successful_review_generation(self):
        diff = "def foo(): pass"

        mock_prompt, mock_llm, mock_parser = self._build_pipe_chain(
            "Great code review!"
        )
        self.selector.prompts["detailed"] = mock_prompt

        # Mock truncate + static analysis
        with patch("online_estimator_version.safe_truncate", side_effect=lambda t, m: t[:m]), \
             patch("online_estimator_version.run_static_analysis", side_effect=lambda *a, **k: "No issues"):

            review, elapsed = self.selector.generate_review(diff, "detailed")

        self.assertEqual(review, "Great code review!")
        self.assertIsInstance(elapsed, float)

    # ==================================================================
    def test_llm_invocation_failure_handling(self):
        diff = "def foo(): pass"

        mock_prompt, mock_llm, mock_parser = self._build_pipe_chain(None)
        mock_parser.invoke.side_effect = RuntimeError("LLM error")

        self.selector.prompts["security"] = mock_prompt

        with patch("online_estimator_version.safe_truncate", side_effect=lambda t, m: t[:m]), \
             patch("online_estimator_version.run_static_analysis", side_effect=lambda *a: "OK"):

            review, elapsed = self.selector.generate_review(diff, "security")

        self.assertIn("LLM invocation failed", review)

    # ==================================================================
    def test_rag_retrieval_failure_handling(self):
        diff = "def foo(): pass"

        mock_prompt, mock_llm, mock_parser = self._build_pipe_chain("Review text")
        self.selector.prompts["concise"] = mock_prompt

        # Patch retriever failure
        with patch("online_estimator_version.safe_truncate", side_effect=lambda t, m: t[:m]), \
             patch("online_estimator_version.run_static_analysis", side_effect=lambda *a: "OK"), \
             patch("online_estimator_version.llm", mock_llm), \
             patch("online_estimator_version.parser", mock_parser):

            # Force RAG failure
            self.selector.retriever.invoke.side_effect = RuntimeError("RAG error")

            review, elapsed = self.selector.generate_review(diff, "concise")

        self.assertIn("RAG retrieval failed", review)

    # ==================================================================
    def test_static_analysis_failure_handling(self):
        diff = "def foo(): pass"

        mock_prompt, mock_llm, mock_parser = self._build_pipe_chain("Review text")
        self.selector.prompts["detailed"] = mock_prompt

        with patch("online_estimator_version.safe_truncate", side_effect=lambda t, m: t[:m]), \
             patch("online_estimator_version.run_static_analysis", side_effect=ValueError("Static error")):

            review, elapsed = self.selector.generate_review(diff, "detailed")

        self.assertIn("Static analysis failed", review)

    # ==================================================================
    def test_truncation_applied(self):
        diff = "x" * 10000

        mock_prompt, mock_llm, mock_parser = self._build_pipe_chain("Review")
        self.selector.prompts["detailed"] = mock_prompt

        fake_truncate = Mock(side_effect=lambda t, m: t[:m])

        with patch("online_estimator_version.safe_truncate", fake_truncate), \
             patch("online_estimator_version.run_static_analysis", return_value="OK"):

            self.selector.generate_review(diff, "detailed")

        self.assertGreaterEqual(fake_truncate.call_count, 1)
