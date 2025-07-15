# DocuMD Converter

Universal document to AI-ready markdown converter that transforms PDF, DOCX, and TXT files into optimized markdown for AI consumption.

## Features

- **Universal Input**: Support for PDF, DOCX, and TXT files
- **AI-Optimized Output**: Markdown formatted for maximum AI efficiency  
- **Zero Content Loss**: Guaranteed content preservation with validation
- **Intelligent Processing**: Smart structure detection and content classification
- **Production Ready**: Built for scale with comprehensive error handling

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .

# Convert a document
python -m src.core.converter input.pdf --output output/