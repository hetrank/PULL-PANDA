"""
Updated test suite for extract_pr_features method.

Matches the structure of TestProcessPR:
- unittest.TestCase
- setUp() with patched get_prompts
- self.selector used everywhere
"""

import unittest
from unittest.mock import patch
from online_estimator_version import IterativePromptSelector


class TestExtractPRFeatures(unittest.TestCase):
    """Tests for extract_pr_features method."""

    def setUp(self):
        # Match EXACT structure used across all test files
        with patch("online_estimator_version.get_prompts"):
            self.selector = IterativePromptSelector()

    # ============================================================
    # BASIC DIFF FEATURES
    # ============================================================
    def test_basic_diff_features(self):
        diff = "diff --git a/file.py b/file.py\n+added line\n-removed line"
        features = self.selector.extract_pr_features(diff)

        self.assertIn("num_lines", features)
        self.assertIn("num_files", features)
        self.assertIn("additions", features)
        self.assertIn("deletions", features)
        self.assertEqual(features["num_files"], 1)

    # ============================================================
    # EMPTY DIFF
    # ============================================================
    def test_empty_diff(self):
        features = self.selector.extract_pr_features("")

        self.assertEqual(features["num_lines"], 1)  # empty string has 1 line
        self.assertEqual(features["num_files"], 0)
        self.assertEqual(features["additions"], 0)
        self.assertEqual(features["deletions"], 0)

    # ============================================================
    # MULTIPLE FILES
    # ============================================================
    def test_multiple_files_detection(self):
        diff = (
            "diff --git a/file1.py b/file1.py\n+code\n"
            "diff --git a/file2.js b/file2.js\n+more code"
        )
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["num_files"], 2)

    # ============================================================
    # LANGUAGE DETECTION
    # ============================================================
    def test_python_file_detection(self):
        diff = "diff --git a/script.py b/script.py"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["is_python"], 1)
        self.assertEqual(features["is_js"], 0)
        self.assertEqual(features["is_java"], 0)

    def test_javascript_file_detection(self):
        diff = "diff --git a/app.js b/app.js"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["is_js"], 1)
        self.assertEqual(features["is_python"], 0)

    def test_typescript_file_detection(self):
        diff = "diff --git a/component.ts b/component.ts"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["is_js"], 1)

    def test_java_file_detection(self):
        diff = "diff --git a/Main.java b/Main.java"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["is_java"], 1)

    # ============================================================
    # CODE STRUCTURE FEATURES
    # ============================================================
    def test_function_detection(self):
        diff = "def my_function():\n    pass"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["has_functions"], 1)

    def test_import_detection(self):
        diff = "import os\nfrom datetime import datetime"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["has_imports"], 1)

    def test_comment_detection(self):
        diff = "# comment\n// another\n/* block */"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["has_comments"], 1)

    # ============================================================
    # SPECIAL FILE TYPES
    # ============================================================
    def test_test_file_detection(self):
        diff = "diff --git a/test_module.py b/test_module.py"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["has_test"], 1)

    def test_documentation_detection(self):
        diff = "README.md updated with new docs"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["has_docs"], 1)

    def test_config_file_detection(self):
        diff = "diff --git a/config.json b/config.json"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["has_config"], 1)

    # ============================================================
    # NET CHANGE CALCULATION
    # ============================================================
    def test_net_changes_calculation(self):
        diff = "+l1\n+l2\n+l3\n-l4"
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["additions"], 3)
        self.assertEqual(features["deletions"], 1)
        self.assertEqual(features["net_changes"], 2)

    # ============================================================
    # LARGE DIFF HANDLING
    # ============================================================
    def test_large_diff_handling(self):
        diff = "\n".join([f"+line{i}" for i in range(1000)])
        features = self.selector.extract_pr_features(diff)

        self.assertEqual(features["num_lines"], 1000)
        self.assertEqual(features["additions"], 1000)
