"""
Test suite for extract_pr_features method.
Tests feature extraction from PR diffs.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from iterative_prompt_selector import IterativePromptSelector


class TestExtractPRFeatures(unittest.TestCase):
    """Tests for extract_pr_features method"""

    def setUp(self):
        self.selector = IterativePromptSelector()

    def test_basic_size_features_empty_diff(self):
        """Test feature extraction with empty diff"""
        features = self.selector.extract_pr_features("")
        
        self.assertEqual(features['num_lines'], 1)  # Empty string has 1 line
        self.assertEqual(features['num_files'], 0)
        self.assertEqual(features['additions'], 0)
        self.assertEqual(features['deletions'], 0)
        self.assertEqual(features['net_changes'], 0)

    def test_basic_size_features_simple_diff(self):
        """Test feature extraction with simple diff"""
        diff = """diff --git a/file.py b/file.py
+added line
-removed line
+another addition"""
        
        features = self.selector.extract_pr_features(diff)
        
        self.assertEqual(features['num_files'], 1)
        self.assertEqual(features['additions'], 2)
        self.assertEqual(features['deletions'], 1)
        self.assertEqual(features['net_changes'], 1)

    def test_multiple_files(self):
        """Test detection of multiple files"""
        diff = """diff --git a/file1.py b/file1.py
+line1
diff --git a/file2.js b/file2.js
+line2
diff --git a/file3.java b/file3.java
+line3"""
        
        features = self.selector.extract_pr_features(diff)
        self.assertEqual(features['num_files'], 3)

    def test_code_complexity_features_comments(self):
        """Test detection of comments in various formats"""
        # Python comment
        diff_py = "# This is a comment\n+code"
        features = self.selector.extract_pr_features(diff_py)
        self.assertEqual(features['has_comments'], 1)
        
        # JavaScript single-line comment
        diff_js = "// This is a comment\n+code"
        features = self.selector.extract_pr_features(diff_js)
        self.assertEqual(features['has_comments'], 1)
        
        # Multi-line comment
        diff_multi = "/* This is\na multi-line\ncomment */\n+code"
        features = self.selector.extract_pr_features(diff_multi)
        self.assertEqual(features['has_comments'], 1)
        
        # No comments
        diff_no = "+code line\n+another line"
        features = self.selector.extract_pr_features(diff_no)
        self.assertEqual(features['has_comments'], 0)

    def test_code_complexity_features_functions(self):
        """Test detection of function definitions"""
        # Python function
        diff_py = "def my_function():\n    pass"
        features = self.selector.extract_pr_features(diff_py)
        self.assertEqual(features['has_functions'], 1)
        
        # JavaScript function
        diff_js = "function myFunc() { }"
        features = self.selector.extract_pr_features(diff_js)
        self.assertEqual(features['has_functions'], 1)
        
        # Go function
        diff_go = "func MyFunction() { }"
        features = self.selector.extract_pr_features(diff_go)
        self.assertEqual(features['has_functions'], 1)
        
        # No functions
        diff_no = "+variable = 5\n+another = 10"
        features = self.selector.extract_pr_features(diff_no)
        self.assertEqual(features['has_functions'], 0)

    def test_code_complexity_features_imports(self):
        """Test detection of import statements"""
        # Python import
        diff_py = "import numpy as np\nfrom sklearn import model"
        features = self.selector.extract_pr_features(diff_py)
        self.assertEqual(features['has_imports'], 1)
        
        # C include
        diff_c = "#include <stdio.h>"
        features = self.selector.extract_pr_features(diff_c)
        self.assertEqual(features['has_imports'], 1)
        
        # No imports
        diff_no = "+code line"
        features = self.selector.extract_pr_features(diff_no)
        self.assertEqual(features['has_imports'], 0)

    def test_content_type_features_test_files(self):
        """Test detection of test-related content"""
        test_keywords = ['test_file.py', 'spec.js', 'unittest.py', 'Test.java']
        
        for keyword in test_keywords:
            features = self.selector.extract_pr_features(keyword)
            self.assertEqual(features['has_test'], 1)
        
        features = self.selector.extract_pr_features("regular_file.py")
        self.assertEqual(features['has_test'], 0)

    def test_content_type_features_documentation(self):
        """Test detection of documentation"""
        doc_keywords = ['README.md', 'docs/', 'documentation.txt', '# comment']
        
        for keyword in doc_keywords:
            features = self.selector.extract_pr_features(keyword)
            self.assertEqual(features['has_docs'], 1)
        
        features = self.selector.extract_pr_features("code.py")
        self.assertEqual(features['has_docs'], 0)

    def test_content_type_features_config_files(self):
        """Test detection of configuration files"""
        config_files = ['config.json', 'settings.yml', 'app.yaml', 
                       'config.xml', 'app.conf']
        
        for config_file in config_files:
            features = self.selector.extract_pr_features(config_file)
            self.assertEqual(features['has_config'], 1)
        
        features = self.selector.extract_pr_features("code.py")
        self.assertEqual(features['has_config'], 0)

    def test_language_detection_python(self):
        """Test Python language detection"""
        features = self.selector.extract_pr_features("file.py")
        self.assertEqual(features['is_python'], 1)
        
        features = self.selector.extract_pr_features("file.PY")
        self.assertEqual(features['is_python'], 1)
        
        features = self.selector.extract_pr_features("file.js")
        self.assertEqual(features['is_python'], 0)

    def test_language_detection_javascript(self):
        """Test JavaScript/TypeScript language detection"""
        features = self.selector.extract_pr_features("file.js")
        self.assertEqual(features['is_js'], 1)
        
        features = self.selector.extract_pr_features("file.ts")
        self.assertEqual(features['is_js'], 1)
        
        features = self.selector.extract_pr_features("file.py")
        self.assertEqual(features['is_js'], 0)

    def test_language_detection_java(self):
        """Test Java language detection"""
        features = self.selector.extract_pr_features("file.java")
        self.assertEqual(features['is_java'], 1)
        
        features = self.selector.extract_pr_features("file.JAVA")
        self.assertEqual(features['is_java'], 1)
        
        features = self.selector.extract_pr_features("file.py")
        self.assertEqual(features['is_java'], 0)

    def test_complex_real_world_diff(self):
        """Test with a realistic complex diff"""
        diff = """diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,5 +1,8 @@
+import unittest
+from typing import List
+
 # Main application file
-def old_function():
-    pass
+def new_function(data: List[int]) -> int:
+    # Calculate sum
+    return sum(data)
 
diff --git a/tests/test_main.py b/tests/test_main.py
new file mode 100644
+import unittest
+from src.main import new_function
+
+class TestMain(unittest.TestCase):
+    def test_new_function(self):
+        self.assertEqual(new_function([1, 2, 3]), 6)
"""
        
        features = self.selector.extract_pr_features(diff)
        
        # Verify various features are detected
        self.assertEqual(features['num_files'], 2)
        self.assertGreater(features['additions'], 0)
        self.assertGreater(features['deletions'], 0)
        self.assertEqual(features['has_comments'], 1)
        self.assertEqual(features['has_functions'], 1)
        self.assertEqual(features['has_imports'], 1)
        self.assertEqual(features['has_test'], 1)
        self.assertEqual(features['is_python'], 1)

    def test_all_features_present(self):
        """Test that all expected features are present in output"""
        expected_features = [
            'num_lines', 'num_files', 'additions', 'deletions', 'net_changes',
            'has_comments', 'has_functions', 'has_imports', 'has_test',
            'has_docs', 'has_config', 'is_python', 'is_js', 'is_java'
        ]
        
        features = self.selector.extract_pr_features("test diff")
        
        for feature_name in expected_features:
            self.assertIn(feature_name, features)
