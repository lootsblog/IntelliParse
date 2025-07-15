"""Custom exceptions for the document converter."""


class DocumentConverterError(Exception):
    """Base exception for all converter errors."""
    pass


class DocumentParsingError(DocumentConverterError):
    """Raised when document parsing fails."""
    def __init__(self, message: str, file_path: str = None, parser_type: str = None):
        self.file_path = file_path
        self.parser_type = parser_type
        super().__init__(message)


class UnsupportedFormatError(DocumentConverterError):
    """Raised when document format is not supported."""
    def __init__(self, file_path: str, detected_format: str = None):
        self.file_path = file_path
        self.detected_format = detected_format
        message = f"Unsupported format for file: {file_path}"
        if detected_format:
            message += f" (detected: {detected_format})"
        super().__init__(message)


class ContentValidationError(DocumentConverterError):
    """Raised when content validation fails."""
    def __init__(self, message: str, validation_type: str = None):
        self.validation_type = validation_type
        super().__init__(message)


class ConfigurationError(DocumentConverterError):
    """Raised when configuration is invalid."""
    pass


class ConversionError(DocumentConverterError):
    """Raised when conversion process fails."""
    def __init__(self, message: str, stage: str = None):
        self.stage = stage
        super().__init__(message)