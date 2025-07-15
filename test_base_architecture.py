"""Tests for base architecture components."""

import pytest
from pathlib import Path
import tempfile
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.parsers.base import BaseParser, ParserFactory
from src.utils.validators import ContentValidator
from src.core.exceptions import ContentValidationError
from src.core.document import Document, DocumentFormat, ContentType
from src.utils.config import ConverterConfig
from src.core.exceptions import DocumentParsingError, UnsupportedFormatError


class MockParser(BaseParser):
    """Mock parser for testing."""
    
    def get_supported_formats(self):
        return [DocumentFormat.TXT]
    
    def can_parse(self, file_path):
        return file_path.suffix.lower() == '.txt'
    
    def _extract_content(self, file_path):
        return f"Mock content from {file_path.name}"
    
    def _extract_metadata(self, file_path):
        return {'title': f"Mock Title for {file_path.name}"}


def test_base_parser_interface():
    """Test base parser abstract interface."""
    config = ConverterConfig()
    
    # Cannot instantiate abstract class
    with pytest.raises(TypeError):
        BaseParser(config)
    
    # Can instantiate concrete implementation
    parser = MockParser(config)
    assert parser.config == config
    assert parser.logger is not None
    assert hasattr(parser, 'parsing_stats')


def test_mock_parser_functionality():
    """Test mock parser functionality."""
    config = ConverterConfig()
    parser = MockParser(config)
    
    # Test format detection
    formats = parser.get_supported_formats()
    assert DocumentFormat.TXT in formats
    
    # Test can_parse
    assert parser.can_parse(Path("test.txt"))
    assert not parser.can_parse(Path("test.pdf"))


def test_parser_with_real_file():
    """Test parser with actual file."""
    config = ConverterConfig()
    parser = MockParser(config)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content for parsing")
        temp_path = Path(f.name)
    
    try:
        # Parse the file
        document = parser.parse(temp_path)
        
        assert isinstance(document, Document)
        assert document.file_path == temp_path
        assert document.format == DocumentFormat.TXT
        assert "Mock content" in document.raw_content
        assert document.metadata.title == f"Mock Title for {temp_path.name}"
        assert document.processing_stats.parsing_time > 0
        
    finally:
        temp_path.unlink()


def test_parser_error_handling():
    """Test parser error handling."""
    config = ConverterConfig()
    parser = MockParser(config)
    
    # Test with non-existent file
    with pytest.raises(DocumentParsingError):
        parser.parse(Path("nonexistent.txt"))
    
    # Test with unsupported format
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        with pytest.raises(UnsupportedFormatError):
            parser.parse(temp_path)
    finally:
        temp_path.unlink()


def test_parser_factory():
    """Test parser factory functionality."""
    config = ConverterConfig()
    factory = ParserFactory(config)
    
    # Register mock parser
    factory.register_parser("mock", MockParser)
    
    # Test parser info
    parser_info = factory.list_parsers()
    assert "mock" in parser_info
    assert "txt" in parser_info["mock"]
    
    # Test getting parser
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        parser = factory.get_parser(temp_path)
        assert isinstance(parser, MockParser)
    finally:
        temp_path.unlink()


def test_content_validator():
    """Test content validation functionality."""
    validator = ContentValidator()
    
    # Create test document
    doc = Document(
        file_path="test.txt",
        format=DocumentFormat.TXT,
        raw_content="Test content for validation"
    )
    doc.add_section("Test Heading", ContentType.HEADING, level=1)
    doc.add_section("Test paragraph content", ContentType.PARAGRAPH)
    
    # Validate document
    results = validator.validate_document(doc)
    
    assert 'errors' in results
    assert 'warnings' in results
    assert 'info' in results
    
    # Should have minimal issues for well-formed document
    assert len(results['errors']) == 0


def test_content_validator_strict_mode():
    """Test content validator in strict mode."""
    validator = ContentValidator(strict_mode=True)
    
    # Create document with issues
    doc = Document(file_path="", format=None, raw_content="")
    
    # Should raise exception in strict mode
    with pytest.raises(ContentValidationError):
        validator.validate_document(doc)


def test_markdown_validation():
    """Test markdown content validation."""
    validator = ContentValidator()
    
    # Valid markdown
    valid_md = """# Heading 1
        This is a paragraph.
        Heading 2
        Another paragraph."""
    assert validator.validate_markdown(valid_md)

    # Invalid markdown (unmatched code block)
    invalid_md = """# Heading
    pythoncode block without closing
    More content."""
    
    assert not validator.validate_markdown(invalid_md)


def test_content_preservation_check():
    """Test content preservation checking."""
    validator = ContentValidator()
    
    original = "This is the original content with specific words"
    converted = "This is the converted content with specific words"
    
    preservation_ratio = validator.check_content_preservation(original, converted)
    assert preservation_ratio > 0.8  # Should be high similarity


if __name__ == "__main__":
    # Run tests manually
    try:
        test_base_parser_interface()
        test_mock_parser_functionality()
        test_parser_with_real_file()
        test_parser_error_handling()
        test_parser_factory()
        test_content_validator()
        test_content_validator_strict_mode()
        
        test_content_preservation_check()
        
        print("✅ All base architecture tests passed!")
        print("🚀 MILESTONE 1 COMPLETE - Foundation & Core Architecture!")
        print("📋 Ready for MILESTONE 2 - Document Parsing Engine!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()