"""Core document data model."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
import hashlib


class DocumentFormat(Enum):
    """Supported document formats."""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    TXT = "txt"
    UNKNOWN = "unknown"


class ContentType(Enum):
    """Types of content sections."""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    CODE_BLOCK = "code_block"
    LIST = "list"
    IMAGE = "image"
    LINK = "link"
    REFERENCE = "reference"


@dataclass
class ContentSection:
    """Represents a section of content within a document."""
    content: str
    content_type: ContentType
    level: int = 0  # For headings: 1=h1, 2=h2, etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_position: Optional[int] = None
    end_position: Optional[int] = None


@dataclass
class DocumentMetadata:
    """Metadata about the document."""
    title: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    custom_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingStats:
    """Statistics about the processing operation."""
    parsing_time: float = 0.0
    processing_time: float = 0.0
    conversion_time: float = 0.0
    total_time: float = 0.0
    sections_count: int = 0
    tables_count: int = 0
    images_count: int = 0
    errors_count: int = 0
    warnings_count: List[str] = field(default_factory=list)


@dataclass
class Document:
    """Main document model that holds all document data."""
    
    # Basic properties
    file_path: Path
    format: DocumentFormat
    raw_content: str = ""
    
    # Processed content
    sections: List[ContentSection] = field(default_factory=list)
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    
    # Processing information
    processing_stats: ProcessingStats = field(default_factory=ProcessingStats)
    content_hash: Optional[str] = None
    ai_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize computed properties after object creation."""
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)
        
        # Generate content hash if we have content
        if self.raw_content:
            self.content_hash = self._generate_content_hash()
    
    def _generate_content_hash(self) -> str:
        """Generate MD5 hash of content for integrity checking."""
        return hashlib.md5(self.raw_content.encode('utf-8')).hexdigest()
    
    def add_section(self, content: str, content_type: ContentType, 
                   level: int = 0, metadata: Dict[str, Any] = None) -> None:
        """Add a content section to the document."""
        section = ContentSection(
            content=content,
            content_type=content_type,
            level=level,
            metadata=metadata or {}
        )
        self.sections.append(section)
        self.processing_stats.sections_count = len(self.sections)
    
    def get_sections_by_type(self, content_type: ContentType) -> List[ContentSection]:
        """Get all sections of a specific type."""
        return [section for section in self.sections if section.content_type == content_type]
    
    def get_headings(self) -> List[ContentSection]:
        """Get all heading sections."""
        return self.get_sections_by_type(ContentType.HEADING)
    
    def get_tables(self) -> List[ContentSection]:
        """Get all table sections."""
        return self.get_sections_by_type(ContentType.TABLE)
    
    def validate_content_integrity(self) -> bool:
        """Validate that content hasn't been corrupted."""
        if not self.raw_content or not self.content_hash:
            return False
        
        current_hash = self._generate_content_hash()
        return current_hash == self.content_hash
    
    def get_word_count(self) -> int:
        """Calculate total word count."""
        if not self.raw_content:
            return 0
        return len(self.raw_content.split())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary for serialization."""
        return {
            'file_path': str(self.file_path),
            'format': self.format.value,
            'content_hash': self.content_hash,
            'sections_count': len(self.sections),
            'metadata': {
                'title': self.metadata.title,
                'word_count': self.get_word_count(),
                'page_count': self.metadata.page_count
            },
            'processing_stats': {
                'total_time': self.processing_stats.total_time,
                'sections_count': self.processing_stats.sections_count,
                'errors_count': self.processing_stats.errors_count
            }
        }