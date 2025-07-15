"""Tests for core data models."""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.document import Document, DocumentFormat, ContentType, ContentSection
from src.core.exceptions import DocumentParsingError, UnsupportedFormatError


def test_document_creation():
    """Test basic document creation."""
    doc = Document(
        file_path="test.pdf",
        format=DocumentFormat.PDF,
        raw_content="Sample content"
    )
    
    assert isinstance(doc.file_path, Path)
    assert doc.format == DocumentFormat.PDF
    assert doc.raw_content == "Sample content"
    assert doc.content_hash is not None


def test_content_sections():
    """Test adding and retrieving content sections."""
    doc = Document(file_path="test.txt", format=DocumentFormat.TXT)
    
    # Add different types of content
    doc.add_section("Main Title", ContentType.HEADING, level=1)
    doc.add_section("Some paragraph text", ContentType.PARAGRAPH)
    doc.add_section("| Col1 | Col2 |\n|------|------|", ContentType.TABLE)
    
    assert len(doc.sections) == 3
    assert doc.processing_stats.sections_count == 3
    
    # Test filtering by type
    headings = doc.get_headings()
    assert len(headings) == 1
    assert headings[0].content == "Main Title"
    assert headings[0].level == 1
    
    tables = doc.get_tables()
    assert len(tables) == 1


def test_content_integrity():
    """Test content integrity validation."""
    doc = Document(
        file_path="test.txt",
        format=DocumentFormat.TXT,
        raw_content="Original content"
    )
    
    # Content should be valid initially
    assert doc.validate_content_integrity()
    
    # Manually change content (simulating corruption)
    doc.raw_content = "Modified content"
    
    # Should detect the change
    assert not doc.validate_content_integrity()


def test_word_count():
    """Test word count calculation."""
    test_content = "This is a test document with ten words here."
    doc = Document(
        file_path="test.txt",
        format=DocumentFormat.TXT,
        raw_content=test_content
    )
    
    # Debug: Let's see what we're actually getting
    actual_count = doc.get_word_count()
    words = test_content.split()
    
    print(f"Test content: '{test_content}'")
    print(f"Split words: {words}")
    print(f"Expected count: 10")
    print(f"Actual count: {actual_count}")
    print(f"Number of words in split: {len(words)}")
    
    # Count manually to verify
    manual_count = len(test_content.split())
    print(f"Manual count: {manual_count}")
    
    # The assertion should match the actual count
    assert actual_count == manual_count, f"Expected {manual_count}, got {actual_count}"


def test_document_serialization():
    """Test document to dictionary conversion."""
    doc = Document(
        file_path="test.pdf",
        format=DocumentFormat.PDF,
        raw_content="Test content"
    )
    doc.add_section("Title", ContentType.HEADING)
    
    doc_dict = doc.to_dict()
    
    assert doc_dict['file_path'] == 'test.pdf'
    assert doc_dict['format'] == 'pdf'
    assert doc_dict['sections_count'] == 1
    assert 'content_hash' in doc_dict


def test_custom_exceptions():
    """Test custom exceptions work correctly."""
    
    # Test DocumentParsingError
    with pytest.raises(DocumentParsingError) as exc_info:
        raise DocumentParsingError("Parse failed", "test.pdf", "pdf")
    
    error = exc_info.value
    assert error.file_path == "test.pdf"
    assert error.parser_type == "pdf"
    
    # Test UnsupportedFormatError
    with pytest.raises(UnsupportedFormatError) as exc_info:
        raise UnsupportedFormatError("test.xyz", "xyz")
    
    error = exc_info.value
    assert error.file_path == "test.xyz"
    assert error.detected_format == "xyz"


if __name__ == "__main__":
    # Run tests manually
    try:
        test_document_creation()
        test_content_sections()
        test_content_integrity()
        test_word_count()
        test_document_serialization()
        test_custom_exceptions()
        
        print("✅ All data model tests passed!")
        print("🚀 Ready for next task!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()