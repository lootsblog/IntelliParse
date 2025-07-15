"""Content validation utilities."""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..core.document import Document, ContentSection, ContentType
from ..core.exceptions import ContentValidationError
from ..utils.logger import get_logger


class ContentValidator:
    """Validates document content and conversion quality."""
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.logger = get_logger("ContentValidator")
        self.validation_results = {
            'errors': [],
            'warnings': [],
            'info': []
        }
    
    def validate_document(self, document: Document) -> Dict[str, Any]:
        """Comprehensive document validation."""
        self.validation_results = {'errors': [], 'warnings': [], 'info': []}
        
        # Basic document validation
        self._validate_basic_properties(document)
        self._validate_content_integrity(document)
        self._validate_sections(document)
        self._validate_metadata(document)
        
        # Report results
        total_issues = len(self.validation_results['errors']) + len(self.validation_results['warnings'])
        self.logger.info(f"Validation complete: {total_issues} issues found")
        
        return self.validation_results
    
    def _validate_basic_properties(self, document: Document):
        """Validate basic document properties."""
        if not document.file_path:
            self._add_error("Document missing file_path")
        
        if not document.raw_content:
            self._add_error("Document has no content")
        
        if not document.format:
            self._add_error("Document format not specified")
    
    def _validate_content_integrity(self, document: Document):
        """Validate content integrity using hash."""
        if document.content_hash:
            if not document.validate_content_integrity():
                self._add_error("Content integrity check failed - content may be corrupted")
        else:
            self._add_warning("No content hash available for integrity check")
    
    def _validate_sections(self, document: Document):
        """Validate document sections."""
        if not document.sections:
            self._add_warning("Document has no processed sections")
            return
        
        # Check for empty sections
        empty_sections = [i for i, section in enumerate(document.sections) if not section.content.strip()]
        if empty_sections:
            self._add_warning(f"Found {len(empty_sections)} empty sections")
        
        # Check for very short sections
        short_sections = [
            i for i, section in enumerate(document.sections) 
            if len(section.content.strip()) < 10 and section.content_type == ContentType.PARAGRAPH
        ]
        if short_sections:
            self._add_info(f"Found {len(short_sections)} very short sections")
        
        # Validate section hierarchy
        self._validate_heading_hierarchy(document)
    
    def _validate_heading_hierarchy(self, document: Document):
        """Validate heading level hierarchy."""
        headings = document.get_headings()
        if not headings:
            return
        
        prev_level = 0
        for i, heading in enumerate(headings):
            if heading.level > prev_level + 1:
                self._add_warning(f"Heading level jump at section {i}: {prev_level} to {heading.level}")
            prev_level = heading.level
    
    def _validate_metadata(self, document: Document):
        """Validate document metadata."""
        if not document.metadata.title:
            self._add_info("Document has no title")
        
        if document.metadata.page_count and document.metadata.page_count <= 0:
            self._add_error("Invalid page count")
        
        if document.metadata.word_count and document.metadata.word_count <= 0:
            self._add_error("Invalid word count")
    
    def _add_error(self, message: str):
        """Add validation error."""
        self.validation_results['errors'].append(message)
        self.logger.error(f"Validation error: {message}")
        
        if self.strict_mode:
            raise ContentValidationError(message, "strict_validation")
    
    def _add_warning(self, message: str):
        """Add validation warning."""
        self.validation_results['warnings'].append(message)
        self.logger.warning(f"Validation warning: {message}")
    
    def _add_info(self, message: str):
        """Add validation info."""
        self.validation_results['info'].append(message)
        self.logger.info(f"Validation info: {message}")
    
    def validate_markdown(self, markdown_content: str) -> bool:
        """Validate generated markdown syntax."""
        try:
            # Basic markdown validation
            lines = markdown_content.split('\n')
            
            # Check for malformed headers
            for i, line in enumerate(lines):
                if line.startswith('#'):
                    if not re.match(r'^#{1,6}\s+.+', line):
                        self._add_warning(f"Malformed header at line {i+1}: {line[:50]}")
            
            # Check for unmatched code blocks
            code_block_count = markdown_content.count('```')
            if code_block_count % 2 != 0:
                self._add_error("Unmatched code blocks in markdown")
            
            return len(self.validation_results['errors']) == 0
            
        except Exception as e:
            self._add_error(f"Markdown validation failed: {e}")
            return False
    
    def check_content_preservation(self, original: str, converted: str) -> float:
        """Check how well content was preserved during conversion."""
        if not original or not converted:
            return 0.0
        
        # Simple word-based preservation check
        original_words = set(original.lower().split())
        converted_words = set(converted.lower().split())
        
        if not original_words:
            return 1.0 if not converted_words else 0.0
        
        preserved_words = original_words.intersection(converted_words)
        preservation_ratio = len(preserved_words) / len(original_words)
        
        if preservation_ratio < 0.9:
            self._add_warning(f"Content preservation ratio: {preservation_ratio:.2f}")
        
        return preservation_ratio
    
    def get_validation_summary(self) -> str:
        """Get human-readable validation summary."""
        errors = len(self.validation_results['errors'])
        warnings = len(self.validation_results['warnings'])
        info = len(self.validation_results['info'])
        
        summary = f"Validation Summary: {errors} errors, {warnings} warnings, {info} info messages"
        
        if errors > 0:
            summary += "\nErrors:\n" + "\n".join(f"  - {error}" for error in self.validation_results['errors'])
        
        if warnings > 0:
            summary += "\nWarnings:\n" + "\n".join(f"  - {warning}" for warning in self.validation_results['warnings'])
        
        return summary