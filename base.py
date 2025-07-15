"""Base parser interface for document converters."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
import time

from ..core.document import Document, DocumentFormat
from ..core.exceptions import DocumentParsingError, UnsupportedFormatError
from ..utils.config import ConverterConfig
from ..utils.logger import get_logger


class BaseParser(ABC):
    """Abstract base class for all document parsers."""
    
    def __init__(self, config: ConverterConfig):
        """Initialize parser with configuration."""
        self.config = config
        self.logger = get_logger(f"{self.__class__.__name__}")
        self.supported_formats: List[DocumentFormat] = []
        self.parsing_stats = {
            'files_processed': 0,
            'total_parse_time': 0.0,
            'errors': []
        }
    
    @abstractmethod
    def get_supported_formats(self) -> List[DocumentFormat]:
        """Return list of supported document formats."""
        pass
    
    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        pass
    
    @abstractmethod
    def _extract_content(self, file_path: Path) -> str:
        """Extract raw text content from document. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract document metadata. Must be implemented by subclasses."""
        pass
    
    def parse(self, file_path: Path) -> Document:
        """Parse a document file and return Document object."""
        start_time = time.time()
        
        # Validate file
        file_path = Path(file_path)
        if not file_path.exists():
            raise DocumentParsingError(f"File not found: {file_path}")
        
        if not self.can_parse(file_path):
            detected_format = self._detect_format(file_path)
            raise UnsupportedFormatError(str(file_path), detected_format)
        
        try:
            self.logger.info(f"Parsing document: {file_path}")
            
            # Extract content and metadata
            raw_content = self._extract_content(file_path)
            metadata_dict = self._extract_metadata(file_path)
            
            # Create document object
            document = Document(
                file_path=file_path,
                format=self._detect_format(file_path),
                raw_content=raw_content
            )
            
            # Set metadata
            for key, value in metadata_dict.items():
                if hasattr(document.metadata, key):
                    setattr(document.metadata, key, value)
                else:
                    document.metadata.custom_properties[key] = value
            
            # Update parsing stats
            parse_time = time.time() - start_time
            document.processing_stats.parsing_time = parse_time
            
            self._update_stats(parse_time, success=True)
            
            self.logger.info(f"Successfully parsed {file_path} in {parse_time:.2f}s")
            return document
            
        except Exception as e:
            parse_time = time.time() - start_time
            self._update_stats(parse_time, success=False, error=str(e))
            
            if isinstance(e, (DocumentParsingError, UnsupportedFormatError)):
                raise
            else:
                raise DocumentParsingError(
                    f"Failed to parse {file_path}: {str(e)}", 
                    str(file_path), 
                    self.__class__.__name__
                )
    
    def _detect_format(self, file_path: Path) -> DocumentFormat:
        """Detect document format from file extension."""
        suffix = file_path.suffix.lower()
        
        format_map = {
            '.pdf': DocumentFormat.PDF,
            '.docx': DocumentFormat.DOCX,
            '.doc': DocumentFormat.DOC,
            '.txt': DocumentFormat.TXT
        }
        
        return format_map.get(suffix, DocumentFormat.UNKNOWN)
    
    def _update_stats(self, parse_time: float, success: bool = True, error: str = None):
        """Update parsing statistics."""
        self.parsing_stats['files_processed'] += 1
        self.parsing_stats['total_parse_time'] += parse_time
        
        if not success and error:
            self.parsing_stats['errors'].append({
                'timestamp': time.time(),
                'error': error
            })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parsing statistics."""
        stats = self.parsing_stats.copy()
        if stats['files_processed'] > 0:
            stats['average_parse_time'] = stats['total_parse_time'] / stats['files_processed']
        else:
            stats['average_parse_time'] = 0.0
        
        return stats
    
    def reset_stats(self):
        """Reset parsing statistics."""
        self.parsing_stats = {
            'files_processed': 0,
            'total_parse_time': 0.0,
            'errors': []
        }
    
    def validate_content(self, content: str) -> bool:
        """Basic content validation."""
        if not content or not content.strip():
            return False
        
        # Check for minimum content length
        if len(content.strip()) < self.config.parsing.minimum_section_length:
            return False
        
        return True
    
    def preprocess_content(self, content: str) -> str:
        """Preprocess extracted content."""
        if not content:
            return ""
        
        # Basic cleanup
        content = content.strip()
        
        # Remove excessive whitespace if configured
        if self.config.parsing.merge_adjacent_paragraphs:
            # Replace multiple consecutive newlines with double newlines
            import re
            content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        return content


class ParserFactory:
    """Factory class for creating document parsers."""
    
    def __init__(self, config: ConverterConfig):
        self.config = config
        self.logger = get_logger("ParserFactory")
        self._parsers: Dict[str, BaseParser] = {}
    
    def register_parser(self, name: str, parser_class: type):
        """Register a parser class."""
        if not issubclass(parser_class, BaseParser):
            raise ValueError(f"Parser class must inherit from BaseParser: {parser_class}")
        
        self._parsers[name] = parser_class
        self.logger.debug(f"Registered parser: {name}")
    
    def get_parser(self, file_path: Path) -> BaseParser:
        """Get appropriate parser for a file."""
        file_path = Path(file_path)
        
        # Try each registered parser
        for name, parser_class in self._parsers.items():
            parser = parser_class(self.config)
            if parser.can_parse(file_path):
                self.logger.debug(f"Selected parser {name} for {file_path}")
                return parser
        
        # No parser found
        detected_format = self._detect_format(file_path)
        raise UnsupportedFormatError(str(file_path), detected_format)
    
    def _detect_format(self, file_path: Path) -> str:
        """Detect file format."""
        return file_path.suffix.lower()
    
    def get_supported_formats(self) -> List[str]:
        """Get list of all supported formats."""
        formats = set()
        for parser_class in self._parsers.values():
            parser = parser_class(self.config)
            for fmt in parser.get_supported_formats():
                formats.add(fmt.value)
        
        return sorted(list(formats))
    
    def list_parsers(self) -> Dict[str, List[str]]:
        """List all registered parsers and their supported formats."""
        parser_info = {}
        for name, parser_class in self._parsers.items():
            parser = parser_class(self.config)
            formats = [fmt.value for fmt in parser.get_supported_formats()]
            parser_info[name] = formats
        
        return parser_info