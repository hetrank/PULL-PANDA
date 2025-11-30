"""
Test suite for LLM initialization.
Tests ChatGroq and parser configuration.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from langchain_core.output_parsers import StrOutputParser
import sys


class TestLLMInitialization:
    """Test suite for LLM and parser initialization."""

    @patch('config.GROQ_API_KEY', 'test_api_key')
    @patch('langchain_groq.ChatGroq')
    def test_llm_initialization_with_api_key(self, mock_chatgroq):
        """Test that LLM is initialized with correct API key."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
        
        mock_instance = Mock()
        mock_chatgroq.return_value = mock_instance
        
        import reviewer_refactored
        
        assert mock_chatgroq.called
        assert hasattr(reviewer_refactored, 'llm')

    @patch('config.GROQ_API_KEY', 'test_key')
    @patch('langchain_groq.ChatGroq')
    def test_llm_model_configuration(self, mock_chatgroq):
        """Test that correct model is specified."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_instance = Mock()
        mock_chatgroq.return_value = mock_instance
        
        import reviewer_refactored
        
        assert mock_chatgroq.called
        call_kwargs = mock_chatgroq.call_args[1]
        assert call_kwargs.get('model') == 'llama-3.3-70b-versatile'

    @patch('config.GROQ_API_KEY', 'test_key')
    @patch('langchain_groq.ChatGroq')
    def test_llm_temperature_configuration(self, mock_chatgroq):
        """Test that temperature is set correctly."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_instance = Mock()
        mock_chatgroq.return_value = mock_instance
        
        import reviewer_refactored
        
        assert mock_chatgroq.called
        call_kwargs = mock_chatgroq.call_args[1]
        assert call_kwargs.get('temperature') == 0.25

    @patch('config.GROQ_API_KEY', None)
    def test_llm_initialization_with_none_api_key(self):
        """Test behavior when API key is None."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
        
        with pytest.raises(ValueError, match="GROQ_API_KEY is missing or empty"):
            import reviewer_refactored

    @patch('config.GROQ_API_KEY', '')
    def test_llm_initialization_with_empty_api_key(self):
        """Test behavior when API key is empty string."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
        
        with pytest.raises(ValueError, match="GROQ_API_KEY is missing or empty"):
            import reviewer_refactored

    def test_parser_is_str_output_parser(self):
        """Test that parser is instance of StrOutputParser."""
        if 'reviewer_refactored' not in sys.modules:
            with patch('config.GROQ_API_KEY', 'test_key'):
                with patch('langchain_groq.ChatGroq'):
                    import reviewer_refactored
        else:
            import reviewer_refactored
        
        assert isinstance(reviewer_refactored.parser, StrOutputParser)

    def test_parser_returns_string(self):
        """Test that parser returns string output."""
        if 'reviewer_refactored' not in sys.modules:
            with patch('config.GROQ_API_KEY', 'test_key'):
                with patch('langchain_groq.ChatGroq'):
                    import reviewer_refactored
        else:
            import reviewer_refactored
        
        result = reviewer_refactored.parser.parse("test output")
        assert isinstance(result, str)

    @patch('config.GROQ_API_KEY', 'test_key')
    @patch('langchain_groq.ChatGroq')
    def test_llm_attributes_accessible(self, mock_chatgroq):
        """Test that LLM object has necessary attributes."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_instance = Mock()
        mock_instance.model = 'llama-3.3-70b-versatile'
        mock_instance.temperature = 0.25
        mock_chatgroq.return_value = mock_instance
        
        import reviewer_refactored
        
        assert hasattr(reviewer_refactored, 'llm')

    @patch('config.GROQ_API_KEY', 'test_key')
    @patch('langchain_groq.ChatGroq')
    def test_llm_can_be_invoked(self, mock_chatgroq):
        """Test that LLM object can be invoked."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_instance = Mock()
        mock_instance.invoke = Mock(return_value="response")
        mock_chatgroq.return_value = mock_instance
        
        import reviewer_refactored
        
        assert hasattr(reviewer_refactored.llm, 'invoke')
        assert callable(reviewer_refactored.llm.invoke)

    @patch('config.GROQ_API_KEY', 'test_key')
    @patch('langchain_groq.ChatGroq')
    def test_multiple_llm_initializations(self, mock_chatgroq):
        """Test behavior with multiple imports."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_instance = Mock()
        mock_chatgroq.return_value = mock_instance
        
        import reviewer_refactored
        first_call_count = mock_chatgroq.call_count
        
        del sys.modules['reviewer_refactored']
        import reviewer_refactored as reviewer_refactored2
        second_call_count = mock_chatgroq.call_count
        
        assert second_call_count > first_call_count

    def test_parser_parse_empty_string(self):
        """Test parser with empty string."""
        if 'reviewer_refactored' not in sys.modules:
            with patch('config.GROQ_API_KEY', 'test_key'):
                with patch('langchain_groq.ChatGroq'):
                    import reviewer_refactored
        else:
            import reviewer_refactored
        
        result = reviewer_refactored.parser.parse("")
        assert result == ""
        assert isinstance(result, str)

    def test_parser_parse_multiline_string(self):
        """Test parser with multiline string."""
        if 'reviewer_refactored' not in sys.modules:
            with patch('config.GROQ_API_KEY', 'test_key'):
                with patch('langchain_groq.ChatGroq'):
                    import reviewer_refactored
        else:
            import reviewer_refactored
        
        text = "Line 1\nLine 2\nLine 3"
        result = reviewer_refactored.parser.parse(text)
        assert result == text

    def test_parser_parse_unicode_string(self):
        """Test parser with unicode characters."""
        if 'reviewer_refactored' not in sys.modules:
            with patch('config.GROQ_API_KEY', 'test_key'):
                with patch('langchain_groq.ChatGroq'):
                    import reviewer_refactored
        else:
            import reviewer_refactored
        
        text = "Hello 世界 🌍"
        result = reviewer_refactored.parser.parse(text)
        assert result == text
        assert "世界" in result

    @patch('config.GROQ_API_KEY', 'sk-test-key-12345')
    @patch('langchain_groq.ChatGroq')
    def test_api_key_format(self, mock_chatgroq):
        """Test that API key is passed correctly."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_instance = Mock()
        mock_chatgroq.return_value = mock_instance
        
        import reviewer_refactored
        
        assert mock_chatgroq.called
        call_kwargs = mock_chatgroq.call_args[1]
        assert 'api_key' in call_kwargs
        assert call_kwargs['api_key'] == 'sk-test-key-12345'

    def test_exports_in_all(self):
        """Test that necessary items are exported in __all__."""
        if 'reviewer_refactored' not in sys.modules:
            with patch('config.GROQ_API_KEY', 'test_key'):
                with patch('langchain_groq.ChatGroq'):
                    import reviewer_refactored
        else:
            import reviewer_refactored
        
        assert 'llm' in reviewer_refactored.__all__
        assert 'parser' in reviewer_refactored.__all__
        assert 'fetch_pr_diff' in reviewer_refactored.__all__
        assert 'post_review_comment' in reviewer_refactored.__all__
        assert 'save_text_to_file' in reviewer_refactored.__all__

    @patch('config.GROQ_API_KEY', 'test_key')
    @patch('langchain_groq.ChatGroq')
    def test_llm_initialization_error_handling(self, mock_chatgroq):
        """Test handling of initialization errors."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_chatgroq.side_effect = ValueError("Failed to initialize ChatGroq")
        
        with pytest.raises(RuntimeError, match="Failed to initialize ChatGroq"):
            import reviewer_refactored

    @patch('config.GROQ_API_KEY', 'test_key')
    @patch('langchain_groq.ChatGroq')
    def test_llm_initialization_type_error(self, mock_chatgroq):
        """Test handling of TypeError during initialization."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_chatgroq.side_effect = TypeError("Invalid type for parameter")
        
        with pytest.raises(RuntimeError, match="Failed to initialize ChatGroq"):
            import reviewer_refactored

    @patch('config.GROQ_API_KEY', 'test_key')
    @patch('langchain_groq.ChatGroq')
    def test_llm_initialization_connection_error(self, mock_chatgroq):
        """Test handling of ConnectionError during initialization."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_chatgroq.side_effect = ConnectionError("Cannot connect to API")
        
        with pytest.raises(RuntimeError, match="Failed to initialize ChatGroq"):
            import reviewer_refactored

    @patch('config.GROQ_API_KEY', 'test_key')
    @patch('langchain_groq.ChatGroq')
    def test_llm_initialization_unexpected_error(self, mock_chatgroq):
        """Test handling of unexpected errors during initialization."""
        if 'reviewer_refactored' in sys.modules:
            del sys.modules['reviewer_refactored']
            
        mock_chatgroq.side_effect = RuntimeError("Unexpected runtime error")
        
        with pytest.raises(RuntimeError, match="Unexpected error initializing ChatGroq"):
            import reviewer_refactored