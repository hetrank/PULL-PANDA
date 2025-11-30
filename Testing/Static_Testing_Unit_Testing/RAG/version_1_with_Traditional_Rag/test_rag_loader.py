"""
Test suite for rag_loader.py module.

Tests cover:
- Repository file downloading with various scenarios
- FAISS index building and loading
- Context assembly with character limits
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from rag_loader import (
    download_repo_files,
    build_index_for_repo,
    assemble_context
)


class TestDownloadRepoFiles:
    """Test suite for download_repo_files function."""
    
    @patch('rag_loader.requests.get')
    def test_download_single_python_file(self, mock_get):
        """Test downloading a single Python file from repository."""
        # Mock the API responses
        mock_contents = Mock()
        mock_contents.status_code = 200
        mock_contents.json.return_value = [
            {
                "type": "file",
                "name": "test.py",
                "download_url": "https://raw.githubusercontent.com/test/test.py",
                "path": "test.py"
            }
        ]
        
        mock_file = Mock()
        mock_file.status_code = 200
        mock_file.text = "def hello():\n    print('Hello')"
        
        mock_get.side_effect = [mock_contents, mock_file]
        
        result = download_repo_files("owner", "repo", "token123")
        
        assert len(result) == 1
        assert "def hello()" in result[0]
        assert mock_get.call_count == 2
    
    @patch('rag_loader.requests.get')
    def test_download_multiple_file_types(self, mock_get):
        """Test downloading Python, text, and markdown files."""
        mock_contents = Mock()
        mock_contents.status_code = 200
        mock_contents.json.return_value = [
            {
                "type": "file",
                "name": "code.py",
                "download_url": "https://raw.githubusercontent.com/test/code.py",
                "path": "code.py"
            },
            {
                "type": "file",
                "name": "readme.md",
                "download_url": "https://raw.githubusercontent.com/test/readme.md",
                "path": "readme.md"
            },
            {
                "type": "file",
                "name": "notes.txt",
                "download_url": "https://raw.githubusercontent.com/test/notes.txt",
                "path": "notes.txt"
            }
        ]
        
        mock_file1 = Mock()
        mock_file1.status_code = 200
        mock_file1.text = "python code"
        
        mock_file2 = Mock()
        mock_file2.status_code = 200
        mock_file2.text = "# README"
        
        mock_file3 = Mock()
        mock_file3.status_code = 200
        mock_file3.text = "notes content"
        
        mock_get.side_effect = [mock_contents, mock_file1, mock_file2, mock_file3]
        
        result = download_repo_files("owner", "repo", "token123")
        
        assert len(result) == 3
        assert "python code" in result
        assert "# README" in result
        assert "notes content" in result
    
    @patch('rag_loader.requests.get')
    def test_download_ignores_non_target_files(self, mock_get):
        """Test that non-.py, .txt, .md files are ignored."""
        mock_contents = Mock()
        mock_contents.status_code = 200
        mock_contents.json.return_value = [
            {
                "type": "file",
                "name": "image.png",
                "download_url": "https://raw.githubusercontent.com/test/image.png",
                "path": "image.png"
            },
            {
                "type": "file",
                "name": "data.json",
                "download_url": "https://raw.githubusercontent.com/test/data.json",
                "path": "data.json"
            },
            {
                "type": "file",
                "name": "test.py",
                "download_url": "https://raw.githubusercontent.com/test/test.py",
                "path": "test.py"
            }
        ]
        
        mock_file = Mock()
        mock_file.status_code = 200
        mock_file.text = "python content"
        
        mock_get.side_effect = [mock_contents, mock_file]
        
        result = download_repo_files("owner", "repo", "token123")
        
        assert len(result) == 1
        assert "python content" in result[0]
    
    @patch('rag_loader.requests.get')
    def test_download_handles_nested_directories(self, mock_get):
        """Test traversing nested directory structure."""
        # First call - root directory with subdirectory
        mock_root = Mock()
        mock_root.status_code = 200
        mock_root.json.return_value = [
            {
                "type": "dir",
                "name": "src",
                "path": "src"
            },
            {
                "type": "file",
                "name": "root.py",
                "download_url": "https://raw.githubusercontent.com/test/root.py",
                "path": "root.py"
            }
        ]
        
        # Second call - subdirectory contents
        mock_subdir = Mock()
        mock_subdir.status_code = 200
        mock_subdir.json.return_value = [
            {
                "type": "file",
                "name": "module.py",
                "download_url": "https://raw.githubusercontent.com/test/src/module.py",
                "path": "src/module.py"
            }
        ]
        
        mock_file1 = Mock()
        mock_file1.status_code = 200
        mock_file1.text = "root file"
        
        mock_file2 = Mock()
        mock_file2.status_code = 200
        mock_file2.text = "module file"
        
        #mock_get.side_effect = [mock_root, mock_file1, mock_subdir, mock_file2]
        mock_get.side_effect = [mock_root, mock_subdir, mock_file1, mock_file2]

        result = download_repo_files("owner", "repo", "token123")
        
        assert len(result) == 2
        assert "root file" in result
        assert "module file" in result
    
    @patch('rag_loader.requests.get')
    def test_download_handles_api_error(self, mock_get, capsys):
        """Test handling of GitHub API errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = download_repo_files("owner", "repo", "token123")
        
        assert result == []
        captured = capsys.readouterr()
        assert "❌ Error fetching" in captured.out
    
    @patch('rag_loader.requests.get')
    def test_download_handles_file_download_error(self, mock_get):
        """Test handling of file download errors."""
        mock_contents = Mock()
        mock_contents.status_code = 200
        mock_contents.json.return_value = [
            {
                "type": "file",
                "name": "test.py",
                "download_url": "https://raw.githubusercontent.com/test/test.py",
                "path": "test.py"
            }
        ]
        
        mock_file = Mock()
        mock_file.status_code = 404
        
        mock_get.side_effect = [mock_contents, mock_file]
        
        result = download_repo_files("owner", "repo", "token123")
        
        assert len(result) == 0
    
    @patch('rag_loader.requests.get')
    def test_download_empty_repository(self, mock_get):
        """Test downloading from an empty repository."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        mock_get.return_value = mock_response
        
        result = download_repo_files("owner", "repo", "token123")
        
        assert result == []


class TestBuildIndexForRepo:
    """Test suite for build_index_for_repo function."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.index_path = Path(self.test_dir) / "rag_indexes" / "owner_repo"
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('rag_loader.FAISS')
    @patch('rag_loader.download_repo_files')
    @patch('rag_loader.HuggingFaceEmbeddings')
    def test_build_new_index(self, mock_embeddings, mock_download, mock_faiss):
        """Test building a new FAISS index when none exists."""
        mock_download.return_value = ["file content 1", "file content 2"]
        mock_vectorstore = MagicMock()
        mock_faiss.from_texts.return_value = mock_vectorstore
        
        with patch('rag_loader.Path') as mock_path:
            mock_index_path = MagicMock()
            mock_index_file = MagicMock()
            mock_index_file.exists.return_value = False
            mock_index_path.__truediv__.return_value = mock_index_file
            mock_path.return_value = mock_index_path
            
            result = build_index_for_repo("owner", "repo", "token123", force_rebuild=False)
            
            assert result == mock_vectorstore
            mock_faiss.from_texts.assert_called_once()
            mock_vectorstore.save_local.assert_called_once()
    
    @patch('rag_loader.FAISS')
    @patch('rag_loader.download_repo_files')
    @patch('rag_loader.HuggingFaceEmbeddings')
    def test_build_index_with_empty_repo(self, mock_embeddings, mock_download, mock_faiss):
        """Test building index when repository has no files."""
        mock_download.return_value = []
        mock_vectorstore = MagicMock()
        mock_faiss.from_texts.return_value = mock_vectorstore
        
        with patch('rag_loader.Path') as mock_path:
            mock_index_path = MagicMock()
            mock_index_file = MagicMock()
            mock_index_file.exists.return_value = False
            mock_index_path.__truediv__.return_value = mock_index_file
            mock_path.return_value = mock_index_path
            
            result = build_index_for_repo("owner", "repo", "token123")
            
            # Should use fallback dummy text
            call_args = mock_faiss.from_texts.call_args
            assert "Initial dummy text" in call_args[0][0]
    
    @patch('rag_loader.FAISS')
    @patch('rag_loader.HuggingFaceEmbeddings')
    def test_load_existing_index(self, mock_embeddings, mock_faiss):
        """Test loading an existing FAISS index."""
        mock_vectorstore = MagicMock()
        mock_faiss.load_local.return_value = mock_vectorstore
        
        with patch('rag_loader.Path') as mock_path:
            mock_index_path = MagicMock()
            mock_index_file = MagicMock()
            mock_index_file.exists.return_value = True
            mock_index_path.__truediv__.return_value = mock_index_file
            mock_path.return_value = mock_index_path
            
            result = build_index_for_repo("owner", "repo", "token123", force_rebuild=False)
            
            assert result == mock_vectorstore
            mock_faiss.load_local.assert_called_once()
            mock_faiss.from_texts.assert_not_called()
    
    @patch('rag_loader.FAISS')
    @patch('rag_loader.download_repo_files')
    @patch('rag_loader.HuggingFaceEmbeddings')
    def test_force_rebuild_existing_index(self, mock_embeddings, mock_download, mock_faiss):
        """Test force rebuilding an existing index."""
        mock_download.return_value = ["new content"]
        mock_vectorstore = MagicMock()
        mock_faiss.from_texts.return_value = mock_vectorstore
        
        with patch('rag_loader.Path') as mock_path:
            mock_index_path = MagicMock()
            mock_index_file = MagicMock()
            mock_index_file.exists.return_value = True
            mock_index_path.__truediv__.return_value = mock_index_file
            mock_path.return_value = mock_index_path
            
            result = build_index_for_repo("owner", "repo", "token123", force_rebuild=True)
            
            assert result == mock_vectorstore
            mock_faiss.from_texts.assert_called_once()
            mock_faiss.load_local.assert_not_called()


class TestAssembleContext:
    """Test suite for assemble_context function."""
    
    def test_assemble_single_document(self):
        """Test assembling context from a single document."""
        mock_doc = Mock()
        mock_doc.page_content = "This is test content"
        
        result = assemble_context([mock_doc], char_limit=1000)
        
        assert "This is test content" in result
    
    def test_assemble_multiple_documents(self):
        """Test assembling context from multiple documents."""
        mock_doc1 = Mock()
        mock_doc1.page_content = "First document"
        
        mock_doc2 = Mock()
        mock_doc2.page_content = "Second document"
        
        mock_doc3 = Mock()
        mock_doc3.page_content = "Third document"
        
        result = assemble_context([mock_doc1, mock_doc2, mock_doc3], char_limit=5000)
        
        assert "First document" in result
        assert "Second document" in result
        assert "Third document" in result
    
    def test_assemble_respects_char_limit(self):
        """Test that context assembly respects character limit."""
        mock_doc1 = Mock()
        mock_doc1.page_content = "A" * 100
        
        mock_doc2 = Mock()
        mock_doc2.page_content = "B" * 100
        
        mock_doc3 = Mock()
        mock_doc3.page_content = "C" * 100
        
        result = assemble_context([mock_doc1, mock_doc2, mock_doc3], char_limit=150)
        
        assert len(result) <= 150
        assert "A" * 100 in result
        assert "C" * 100 not in result
    
    def test_assemble_with_string_documents(self):
        """Test assembling context when documents don't have page_content attribute."""
        docs = ["Document one", "Document two"]
        
        result = assemble_context(docs, char_limit=1000)
        
        assert "Document one" in result
        assert "Document two" in result
    
    def test_assemble_empty_list(self):
        """Test assembling context from empty document list."""
        result = assemble_context([], char_limit=1000)
        
        assert result == ""
    
    def test_assemble_exact_limit(self):
        """Test behavior when content exactly matches limit."""
        mock_doc = Mock()
        mock_doc.page_content = "X" * 50
        
        result = assemble_context([mock_doc], char_limit=50)
        
        assert "X" * 50 in result
    
    def test_assemble_adds_newlines(self):
        """Test that documents are separated by double newlines."""
        mock_doc1 = Mock()
        mock_doc1.page_content = "First"
        
        mock_doc2 = Mock()
        mock_doc2.page_content = "Second"
        
        result = assemble_context([mock_doc1, mock_doc2], char_limit=1000)
        
        assert "First\n\nSecond" in result