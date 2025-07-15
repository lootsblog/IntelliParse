"""Enhanced PDF parser using PyMuPDF, pdfplumber, and Pillow."""

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image
import io
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import re
import time

from .base import BaseParser
from ..core.document import DocumentFormat, ContentType
from ..core.exceptions import DocumentParsingError
from ..utils.logger import get_logger


class EnhancedPDFParser(BaseParser):
    """Enhanced PDF parser with image extraction and precise table handling."""
    
    def __init__(self, config):
        super().__init__(config)
        self.supported_formats = [DocumentFormat.PDF]
        self.logger = get_logger(f"{self.__class__.__name__}")
        
        # Extraction tracking
        self.images_extracted = []
        self.tables_extracted = []
        self.processing_stats = {
            'pages_processed': 0,
            'images_found': 0,
            'tables_found': 0,
            'fallback_used': None,
            'extraction_method': 'PyMuPDF+pdfplumber',
            'processing_time': 0
        }
        
        # Create output directories
        self._setup_output_directories()
    
    def _setup_output_directories(self):
        """Set up directories for extracted content."""
        try:
            self.images_dir = self.config.get_output_path("extracted_images")
            self.tables_dir = self.config.get_output_path("extracted_tables")
            
            self.images_dir.mkdir(parents=True, exist_ok=True)
            self.tables_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.debug(f"Created output directories: {self.images_dir}, {self.tables_dir}")
            
        except Exception as e:
            self.logger.warning(f"Could not create output directories: {e}")
            # Use temp directory as fallback
            self.images_dir = self.config.get_temp_path("images")
            self.tables_dir = self.config.get_temp_path("tables")
    
    def get_supported_formats(self) -> List[DocumentFormat]:
        """Return supported document formats."""
        return self.supported_formats
    
    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() == '.pdf'
    
    def _extract_content(self, file_path: Path) -> str:
        """Extract content using enhanced PDF parsing pipeline."""
        start_time = time.time()
        self.logger.info(f"Starting enhanced PDF extraction for: {file_path}")
        
        try:
            # Primary extraction with PyMuPDF
            content = self._extract_with_pymupdf(file_path)
            self.processing_stats['extraction_method'] = 'PyMuPDF+pdfplumber'
            
        except Exception as e:
            self.logger.error(f"PyMuPDF extraction failed: {e}")
            self.logger.info("Attempting fallback to pdfplumber-only extraction")
            
            try:
                content = self._extract_with_pdfplumber_only(file_path)
                self.processing_stats['fallback_used'] = 'pdfplumber-only'
                
            except Exception as e2:
                self.logger.error(f"pdfplumber extraction failed: {e2}")
                self.logger.info("Attempting final fallback to PyPDF2")
                
                content = self._extract_with_pypdf2_fallback(file_path)
                self.processing_stats['fallback_used'] = 'PyPDF2'
        
        self.processing_stats['processing_time'] = time.time() - start_time
        
        if not self.validate_content(content):
            raise DocumentParsingError(f"No valid content extracted from PDF: {file_path}")
        
        self.logger.info(f"PDF extraction completed in {self.processing_stats['processing_time']:.2f}s")
        self.logger.info(f"Extraction stats: {self.processing_stats}")
        
        return content
    
    def _extract_with_pymupdf(self, file_path: Path) -> str:
        """Primary extraction method using PyMuPDF."""
        self.logger.info("Using PyMuPDF for primary extraction")
        
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(str(file_path))
            self.logger.debug(f"Opened PDF with PyMuPDF: {len(doc)} pages")
            
            if doc.is_encrypted:
                self.logger.warning("PDF is encrypted, attempting to decrypt")
                if not doc.authenticate(""):
                    raise DocumentParsingError("Cannot decrypt encrypted PDF")
                self.logger.info("Successfully decrypted PDF")
            
            all_content = []
            doc_name = file_path.stem
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_content = self._process_page_with_pymupdf(page, page_num + 1, doc_name)
                all_content.append(page_content)
                self.processing_stats['pages_processed'] += 1
            
            doc.close()
            
            # Enhance tables with pdfplumber if tables were detected
            if self.processing_stats['tables_found'] > 0:
                self.logger.info(f"Detected {self.processing_stats['tables_found']} tables, enhancing with pdfplumber")
                enhanced_content = self._enhance_tables_with_pdfplumber(file_path, all_content)
                return '\n\n'.join(enhanced_content)
            
            return '\n\n'.join(all_content)
            
        except Exception as e:
            self.logger.error(f"PyMuPDF extraction error: {e}")
            raise
    
    def _process_page_with_pymupdf(self, page, page_num: int, doc_name: str) -> str:
        """Process a single page with PyMuPDF."""
        self.logger.debug(f"Processing page {page_num} with PyMuPDF")
        
        page_content = []
        
        # Add page marker
        if self.config.processing.detect_document_structure:
            page_content.append(f"--- PAGE {page_num} ---")
        
        # Extract text
        text = page.get_text()
        if text.strip():
            cleaned_text = self._clean_page_text(text)
            page_content.append(cleaned_text)
            self.logger.debug(f"Extracted {len(cleaned_text)} characters from page {page_num}")
        else:
            self.logger.debug(f"No text found on page {page_num}")
        
        # Extract images
        if self.config.parsing.extract_images:
            image_placeholders = self._extract_page_images_pymupdf(page, page_num, doc_name)
            page_content.extend(image_placeholders)
        
        # Detect tables (basic detection, enhanced later)
        if self.config.parsing.extract_tables:
            table_markers = self._detect_tables_basic(text, page_num)
            page_content.extend(table_markers)
        
        return '\n'.join(page_content)
    
    def _extract_page_images_pymupdf(self, page, page_num: int, doc_name: str) -> List[str]:
        """Extract images from page using PyMuPDF."""
        image_placeholders = []
        
        try:
            image_list = page.get_images()
            self.logger.debug(f"Found {len(image_list)} images on page {page_num}")
            
            for img_index, img in enumerate(image_list):
                try:
                    # Get image data
                    xref = img[0]
                    base_image = page.parent.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Create filename
                    image_filename = f"{doc_name}_p{page_num:03d}_img_{img_index + 1:03d}.{image_ext}"
                    image_path = self.images_dir / image_filename
                    
                    # Process and save image
                    self._process_and_save_image(image_bytes, image_path, page_num, img_index + 1)
                    
                    # Create placeholder
                    placeholder = f"![Image {img_index + 1} from page {page_num}]({image_path.name})"
                    image_placeholders.append(placeholder)
                    
                    # Track extraction
                    self.images_extracted.append({
                        'page': page_num,
                        'index': img_index + 1,
                        'filename': image_filename,
                        'path': str(image_path),
                        'format': image_ext
                    })
                    
                    self.processing_stats['images_found'] += 1
                    self.logger.debug(f"Extracted image: {image_filename}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to extract image {img_index + 1} from page {page_num}: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Error extracting images from page {page_num}: {e}")
        
        return image_placeholders
    
    def _process_and_save_image(self, image_bytes: bytes, output_path: Path, page_num: int, img_index: int):
        """Process and save extracted image using Pillow."""
        try:
            self.logger.debug(f"Processing image {img_index} from page {page_num}")
            
            # Open image with Pillow
            image = Image.open(io.BytesIO(image_bytes))
            original_size = image.size
            
            self.logger.debug(f"Original image size: {original_size}")
            
            # Apply processing based on configuration
            processed_image = self._apply_image_processing(image)
            
            # Save processed image
            processed_image.save(output_path, optimize=True)
            
            self.logger.debug(f"Saved processed image: {output_path}")
            self.logger.debug(f"Final image size: {processed_image.size}")
            
        except Exception as e:
            self.logger.error(f"Failed to process image {img_index} from page {page_num}: {e}")
            # Save raw image as fallback
            try:
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)
                self.logger.info(f"Saved raw image as fallback: {output_path}")
            except Exception as e2:
                self.logger.error(f"Failed to save raw image: {e2}")
                raise
    
    def _apply_image_processing(self, image: Image.Image) -> Image.Image:
        """Apply image processing with Pillow."""
        self.logger.debug("Applying image processing")
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            self.logger.debug(f"Converting image from {image.mode} to RGB")
            image = image.convert('RGB')
        
        # Apply smart resizing
        max_width = 1200
        max_height = 900
        
        if image.width > max_width or image.height > max_height:
            self.logger.debug(f"Resizing image from {image.size}")
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            self.logger.debug(f"Resized to {image.size}")
        
        # Ensure minimum size
        min_size = 100
        if image.width < min_size or image.height < min_size:
            self.logger.debug("Image too small, upscaling")
            scale_factor = max(min_size / image.width, min_size / image.height)
            new_size = (int(image.width * scale_factor), int(image.height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image
    
    def _detect_tables_basic(self, text: str, page_num: int) -> List[str]:
        """Basic table detection for later enhancement."""
        table_markers = []
        
        try:
            lines = text.split('\n')
            potential_table_lines = []
            
            for line in lines:
                # Look for lines with multiple columns (tabs or multiple spaces)
                if re.search(r'\t|\s{3,}', line) and len(line.split()) > 2:
                    potential_table_lines.append(line)
            
            if len(potential_table_lines) >= 2:
                self.processing_stats['tables_found'] += 1
                marker = f"[TABLE_DETECTED_PAGE_{page_num}_{len(self.tables_extracted) + 1}]"
                table_markers.append(marker)
                
                # Store table info for later enhancement
                self.tables_extracted.append({
                    'page': page_num,
                    'marker': marker,
                    'preview_lines': potential_table_lines[:3],
                    'total_lines': len(potential_table_lines)
                })
                
                self.logger.debug(f"Basic table detected on page {page_num}: {len(potential_table_lines)} rows")
                
        except Exception as e:
            self.logger.warning(f"Error in basic table detection for page {page_num}: {e}")
        
        return table_markers
    
    def _enhance_tables_with_pdfplumber(self, file_path: Path, content_pages: List[str]) -> List[str]:
        """Enhance table extraction using pdfplumber."""
        self.logger.info("Enhancing table extraction with pdfplumber")
        
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                enhanced_content = []
                
                for page_idx, page_content in enumerate(content_pages):
                    if f"[TABLE_DETECTED_PAGE_{page_idx + 1}" in page_content:
                        self.logger.debug(f"Enhancing tables on page {page_idx + 1}")
                        enhanced_page = self._extract_tables_from_page(
                            pdf.pages[page_idx], page_content, page_idx + 1
                        )
                        enhanced_content.append(enhanced_page)
                    else:
                        enhanced_content.append(page_content)
                
                self.logger.info("Table enhancement completed")
                return enhanced_content
                
        except Exception as e:
            self.logger.error(f"Table enhancement failed: {e}")
            self.logger.info("Returning content with basic table detection")
            return content_pages
    
    def _extract_tables_from_page(self, pdf_page, page_content: str, page_num: int) -> str:
        """Extract tables from a specific page using pdfplumber."""
        try:
            tables = pdf_page.extract_tables()
            self.logger.debug(f"pdfplumber found {len(tables)} tables on page {page_num}")
            
            enhanced_content = page_content
            
            for table_idx, table in enumerate(tables):
                if table and len(table) > 1:  # Valid table with header and data
                    markdown_table = self._convert_table_to_markdown(table, page_num, table_idx + 1)
                    
                    # Replace marker with actual table
                    marker = f"[TABLE_DETECTED_PAGE_{page_num}_{table_idx + 1}]"
                    enhanced_content = enhanced_content.replace(marker, markdown_table)
                    
                    self.logger.debug(f"Converted table {table_idx + 1} on page {page_num} to markdown")
            
            return enhanced_content
            
        except Exception as e:
            self.logger.warning(f"Failed to extract tables from page {page_num}: {e}")
            return page_content
    
    def _convert_table_to_markdown(self, table: List[List], page_num: int, table_idx: int) -> str:
        """Convert table data to markdown format."""
        try:
            if not table or len(table) < 2:
                return f"[Table {table_idx} on page {page_num}: No data]"
            
            markdown_lines = []
            
            # Header row
            header = table[0]
            header_cleaned = [str(cell).strip() if cell else "" for cell in header]
            markdown_lines.append("| " + " | ".join(header_cleaned) + " |")
            
            # Separator row
            separator = "|" + "|".join([" --- " for _ in header_cleaned]) + "|"
            markdown_lines.append(separator)
            
            # Data rows
            for row in table[1:]:
                row_cleaned = [str(cell).strip() if cell else "" for cell in row]
                # Pad row to match header length
                while len(row_cleaned) < len(header_cleaned):
                    row_cleaned.append("")
                markdown_lines.append("| " + " | ".join(row_cleaned[:len(header_cleaned)]) + " |")
            
            markdown_table = "\n".join(markdown_lines)
            self.logger.debug(f"Created markdown table: {len(table)} rows, {len(header_cleaned)} columns")
            
            return f"\n{markdown_table}\n"
            
        except Exception as e:
            self.logger.error(f"Failed to convert table to markdown: {e}")
            return f"[Table {table_idx} on page {page_num}: Conversion failed]"
    
    def _extract_with_pdfplumber_only(self, file_path: Path) -> str:
        """Fallback extraction using only pdfplumber."""
        self.logger.info("Using pdfplumber-only extraction as fallback")
        
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                all_content = []
                
                for page_num, page in enumerate(pdf.pages):
                    self.logger.debug(f"Processing page {page_num + 1} with pdfplumber")
                    
                    # Extract text
                    text = page.extract_text()
                    if text:
                        cleaned_text = self._clean_page_text(text)
                        all_content.append(f"--- PAGE {page_num + 1} ---\n{cleaned_text}")
                    
                    # Extract tables
                    tables = page.extract_tables()
                    for table_idx, table in enumerate(tables):
                        if table:
                            markdown_table = self._convert_table_to_markdown(table, page_num + 1, table_idx + 1)
                            all_content.append(markdown_table)
                            self.processing_stats['tables_found'] += 1
                    
                    self.processing_stats['pages_processed'] += 1
                
                return '\n\n'.join(all_content)
                
        except Exception as e:
            self.logger.error(f"pdfplumber-only extraction failed: {e}")
            raise
    
    def _extract_with_pypdf2_fallback(self, file_path: Path) -> str:
        """Final fallback using PyPDF2."""
        self.logger.warning("Using PyPDF2 as final fallback - limited functionality")
        
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if pdf_reader.is_encrypted:
                    try:
                        pdf_reader.decrypt("")
                    except Exception:
                        raise DocumentParsingError("Cannot decrypt PDF with PyPDF2")
                
                all_text = []
                for page_num, page in enumerate(pdf_reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        cleaned_text = self._clean_page_text(text)
                        all_text.append(f"--- PAGE {page_num + 1} ---\n{cleaned_text}")
                    
                    self.processing_stats['pages_processed'] += 1
                
                return '\n\n'.join(all_text)
                
        except Exception as e:
            self.logger.error(f"PyPDF2 fallback failed: {e}")
            raise DocumentParsingError(f"All PDF extraction methods failed for {file_path}")
    
    def _clean_page_text(self, text: str) -> str:
        """Clean extracted text from PDF page."""
        if not text:
            return ""
        
        # Fix hyphenated words split across lines FIRST (before other processing)
        text = re.sub(r'(\w)-\s*\n(\w)', r'\1\2', text)  # line-\nbreaks -> linebreaks
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix other common PDF extraction issues
        text = re.sub(r'\n+', '\n', text)  # Multiple newlines to single
        text = text.replace('\r', '\n')  # Normalize line endings
        
        # Remove standalone page numbers
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not (line.isdigit() and len(line) < 4):  # Skip standalone page numbers
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from PDF."""
        self.logger.debug("Extracting PDF metadata")
        
        try:
            # Try PyMuPDF first
            doc = fitz.open(str(file_path))
            metadata = doc.metadata
            
            extracted_metadata = {
                'title': metadata.get('title', file_path.stem),
                'author': metadata.get('author'),
                'creator': metadata.get('creator'),
                'producer': metadata.get('producer'),
                'created_date': metadata.get('creationDate'),
                'modified_date': metadata.get('modDate'),
                'page_count': len(doc),  # This should work
                'is_encrypted': doc.is_encrypted,
                'pdf_version': f"{doc.pdf_version()[0]}.{doc.pdf_version()[1]}" if hasattr(doc, 'pdf_version') else "unknown"
            }
            
            doc.close()
            
            # Add processing stats
            extracted_metadata.update({
                'extraction_method': self.processing_stats['extraction_method'],
                'images_extracted': self.processing_stats['images_found'],
                'tables_extracted': self.processing_stats['tables_found'],
                'processing_time': self.processing_stats['processing_time']
            })
            
            self.logger.debug(f"Extracted metadata: {extracted_metadata}")
            return extracted_metadata
            
        except Exception as e:
            self.logger.warning(f"Metadata extraction failed: {e}")
            return {
                'title': file_path.stem,
                'page_count': 1,  # Default to 1 instead of 0
                'extraction_method': 'fallback'
            }
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """Get comprehensive extraction summary."""
        return {
            'processing_stats': self.processing_stats,
            'images_extracted': self.images_extracted,
            'tables_extracted': self.tables_extracted,
            'output_directories': {
                'images': str(self.images_dir),
                'tables': str(self.tables_dir)
            }
        }
    
    def save_extraction_metadata(self, output_dir: Path):
        """Save extraction metadata to JSON file."""
        try:
            metadata_file = output_dir / "extraction_metadata.json"
            metadata = self.get_extraction_summary()
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            self.logger.info(f"Saved extraction metadata to: {metadata_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save extraction metadata: {e}")
    
    def get_parser_info(self) -> Dict[str, Any]:
        """Get parser information."""
        return {
            'name': 'Enhanced PDF Parser',
            'version': '2.0.0',
            'libraries': ['PyMuPDF', 'pdfplumber', 'Pillow', 'PyPDF2'],
            'supported_formats': [fmt.value for fmt in self.supported_formats],
            'features': [
                'High-quality text extraction',
                'Actual image extraction and processing',
                'Precise table conversion to markdown',
                'Multi-library fallback system',
                'Comprehensive logging',
                'Metadata preservation'
            ],
            'capabilities': {
                'text_extraction': 'PyMuPDF primary, pdfplumber fallback',
                'image_extraction': 'PyMuPDF + Pillow processing',
                'table_extraction': 'pdfplumber with markdown conversion',
                'fallback_chain': 'PyMuPDF -> pdfplumber -> PyPDF2'
            }
        }