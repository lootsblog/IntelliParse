"""Text file parser for plain text documents."""

import chardet
import re
from pathlib import Path
from typing import Dict, Any, List

from .base import BaseParser
from ..core.document import DocumentFormat, ContentType
from ..core.exceptions import DocumentParsingError


class TxtParser(BaseParser):
    """Parser for plain text files (.txt)."""
    
    def __init__(self, config):
        super().__init__(config)
        self.supported_formats = [DocumentFormat.TXT]
    
    def get_supported_formats(self) -> List[DocumentFormat]:
        """Return supported document formats."""
        return self.supported_formats
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() == '.txt'
    
    def _extract_content(self, file_path: Path) -> str:
        """Extract raw text content from text file."""
        try:
            # Detect encoding
            encoding = self._detect_encoding(file_path)
            self.logger.debug(f"Detected encoding: {encoding} for {file_path}")
            
            # Read file with detected encoding
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            
            # Preprocess content
            content = self.preprocess_content(content)
            
            # Validate content
            if not self.validate_content(content):
                raise DocumentParsingError(f"Invalid or empty content in {file_path}")
            
            return content
            
        except UnicodeDecodeError as e:
            raise DocumentParsingError(f"Encoding error reading {file_path}: {e}")
        except IOError as e:
            raise DocumentParsingError(f"IO error reading {file_path}: {e}")
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from text file."""
        try:
            # Get file stats
            stat = file_path.stat()
            
            # Read content for analysis
            content = self._extract_content(file_path)
            
            # Extract basic metadata
            metadata = {
                'title': self._extract_title(content, file_path),
                'created_date': None,  # Not available for txt files
                'modified_date': stat.st_mtime,
                'page_count': self._estimate_page_count(content),
                'word_count': len(content.split()) if content else 0,
                'language': self._detect_language(content),
                'encoding': self._detect_encoding(file_path)
            }
            
            return metadata
            
        except Exception as e:
            self.logger.warning(f"Error extracting metadata from {file_path}: {e}")
            return {
                'title': file_path.stem,
                'word_count': 0
            }
    
    def _detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding."""
        try:
            # Read a sample of the file for encoding detection
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10KB
            
            if not raw_data:
                return 'utf-8'
            
            # Detect encoding
            detection = chardet.detect(raw_data)
            encoding = detection.get('encoding', 'utf-8')
            confidence = detection.get('confidence', 0.0)
            
            self.logger.debug(f"Encoding detection: {encoding} (confidence: {confidence:.2f})")
            
            # Handle common cases
            if encoding:
                encoding = encoding.lower()
                
                # ASCII is essentially UTF-8 for our purposes
                if encoding == 'ascii':
                    encoding = 'utf-8'
                
                # Handle Windows encoding variations
                elif encoding in ['windows-1252', 'cp1252']:
                    encoding = 'utf-8'  # Use UTF-8 as fallback
                
                # Ensure we return a valid Python encoding name
                elif encoding not in ['utf-8', 'utf-16', 'latin1', 'cp1252']:
                    encoding = 'utf-8'  # Safe fallback
            
            # Fallback to UTF-8 if detection is not confident enough
            if not encoding or confidence < 0.7:
                encoding = 'utf-8'
                self.logger.debug(f"Low confidence or invalid encoding, using fallback: utf-8")
            
            return encoding
            
        except Exception as e:
            self.logger.warning(f"Encoding detection failed: {e}, using UTF-8")
            return 'utf-8'
        
    def _extract_title(self, content: str, file_path: Path) -> str:
        """Extract document title from content or filename."""
        if not content:
            return file_path.stem
        
        lines = content.strip().split('\n')
        
        # Try to find title in first few lines
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) > 5:
                # Check if it looks like a title (not too long, no special chars)
                if len(line) < 100 and not re.search(r'[.]{2,}|[:\-]{2,}', line):
                    return line
        
        # Fallback to filename
        return file_path.stem
    
    def _estimate_page_count(self, content: str) -> int:
        """Estimate page count based on content length."""
        if not content:
            return 0
        
        # Rough estimation: 250 words per page
        word_count = len(content.split())
        return max(1, word_count // 250)
    
    def _detect_language(self, content: str) -> str:
        """Basic language detection."""
        if not content:
            return 'unknown'
        
        # Very basic language detection based on common words
        # This is a simplified version - in production you might use langdetect
        
        english_indicators = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with']
        spanish_indicators = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no']
        french_indicators = ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir']
        
        content_lower = content.lower()
        
        english_score = sum(1 for word in english_indicators if word in content_lower)
        spanish_score = sum(1 for word in spanish_indicators if word in content_lower)
        french_score = sum(1 for word in french_indicators if word in content_lower)
        
        if english_score >= spanish_score and english_score >= french_score:
            return 'en'
        elif spanish_score >= french_score:
            return 'es'
        elif french_score > 0:
            return 'fr'
        else:
            return 'unknown'
    
    def parse_structure(self, content: str) -> List[Dict[str, Any]]:
        """Parse text structure into sections."""
        if not content:
            return []
        
        sections = []
        paragraphs = content.split('\n\n')  # Split by double newlines
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Simple heuristic: if paragraph is short and has no punctuation at end, it's likely a heading
            lines = paragraph.split('\n')
            first_line = lines[0].strip()
            
            if (len(lines) == 1 and  # Single line
                len(first_line) < 60 and  # Not too long
                len(first_line) > 2 and   # Not too short
                not first_line.endswith(('.', '!', '?', ':', ';'))):  # No ending punctuation
                
                # Treat as heading
                sections.append({
                    'content': first_line,
                    'type': ContentType.HEADING,
                    'level': 1
                })
            else:
                # Treat as paragraph
                sections.append({
                    'content': paragraph,
                    'type': ContentType.PARAGRAPH
                })
        return sections
    
    def get_parser_info(self) -> Dict[str, Any]:
        """Get information about this parser."""
        return {
            'name': 'TXT Parser',
            'version': '1.0.0',
            'supported_formats': [fmt.value for fmt in self.supported_formats],
            'features': [
                'Encoding detection',
                'Basic structure parsing',
                'Language detection',
                'Metadata extraction'
            ]
        }