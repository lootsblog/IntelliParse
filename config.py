"""Configuration management for document converter."""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

from ..core.exceptions import ConfigurationError


class OutputFormat(Enum):
    """Supported output formats."""
    SINGLE_FILE = "single_file"
    MULTI_FILE = "multi_file"
    HIERARCHICAL = "hierarchical"


class ChunkingStrategy(Enum):
    """Document chunking strategies."""
    NONE = "none"
    BY_HEADINGS = "by_headings"
    BY_SECTIONS = "by_sections"
    BY_SIZE = "by_size"
    SMART = "smart"


@dataclass
class ParsingConfig:
    """Configuration for document parsing."""
    preserve_formatting: bool = True
    extract_images: bool = False
    extract_tables: bool = True
    detect_code_blocks: bool = True
    merge_adjacent_paragraphs: bool = True
    minimum_section_length: int = 10
    encoding: str = "utf-8"


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""
    add_ai_metadata: bool = True
    generate_cross_references: bool = True
    detect_document_structure: bool = True
    enhance_tables: bool = True
    generate_toc: bool = True
    validate_content: bool = True


@dataclass
class OutputConfig:
    """Configuration for output generation."""
    format: OutputFormat = OutputFormat.MULTI_FILE
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.SMART
    output_directory: str = "output"
    file_prefix: str = ""
    add_timestamps: bool = True
    create_index: bool = True
    preserve_original_structure: bool = True
    max_file_size_mb: int = 10


@dataclass
class ValidationConfig:
    """Configuration for content validation."""
    check_content_integrity: bool = True
    validate_markdown: bool = True
    check_links: bool = True
    validate_tables: bool = True
    strict_mode: bool = False


@dataclass
class ConverterConfig:
    """Main configuration class for the document converter."""
    
    # Sub-configurations
    parsing: ParsingConfig = field(default_factory=ParsingConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    
    # Global settings
    verbose: bool = False
    debug: bool = False
    log_level: str = "INFO"
    max_workers: int = 4
    temp_directory: str = "temp"
    
    # Custom settings
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ConverterConfig':
        """Load configuration from YAML file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            return cls.from_dict(config_data)
        
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ConverterConfig':
        """Create configuration from dictionary."""
        try:
            # Extract sub-configurations
            parsing_config = ParsingConfig(**config_dict.get('parsing', {}))
            processing_config = ProcessingConfig(**config_dict.get('processing', {}))
            output_config = OutputConfig(**config_dict.get('output', {}))
            validation_config = ValidationConfig(**config_dict.get('validation', {}))
            
            # Handle enums
            if 'output' in config_dict:
                output_data = config_dict['output']
                if 'format' in output_data:
                    output_config.format = OutputFormat(output_data['format'])
                if 'chunking_strategy' in output_data:
                    output_config.chunking_strategy = ChunkingStrategy(output_data['chunking_strategy'])
            
            # Create main config
            config = cls(
                parsing=parsing_config,
                processing=processing_config,
                output=output_config,
                validation=validation_config
            )
            
            # Set global settings
            for key, value in config_dict.items():
                if key not in ['parsing', 'processing', 'output', 'validation']:
                    if hasattr(config, key):
                        setattr(config, key, value)
                    else:
                        config.custom_settings[key] = value
            
            return config
            
        except Exception as e:
            raise ConfigurationError(f"Error creating configuration from dict: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'parsing': {
                'preserve_formatting': self.parsing.preserve_formatting,
                'extract_images': self.parsing.extract_images,
                'extract_tables': self.parsing.extract_tables,
                'detect_code_blocks': self.parsing.detect_code_blocks,
                'merge_adjacent_paragraphs': self.parsing.merge_adjacent_paragraphs,
                'minimum_section_length': self.parsing.minimum_section_length,
                'encoding': self.parsing.encoding
            },
            'processing': {
                'add_ai_metadata': self.processing.add_ai_metadata,
                'generate_cross_references': self.processing.generate_cross_references,
                'detect_document_structure': self.processing.detect_document_structure,
                'enhance_tables': self.processing.enhance_tables,
                'generate_toc': self.processing.generate_toc,
                'validate_content': self.processing.validate_content
            },
            'output': {
                'format': self.output.format.value,
                'chunking_strategy': self.output.chunking_strategy.value,
                'output_directory': self.output.output_directory,
                'file_prefix': self.output.file_prefix,
                'add_timestamps': self.output.add_timestamps,
                'create_index': self.output.create_index,
                'preserve_original_structure': self.output.preserve_original_structure,
                'max_file_size_mb': self.output.max_file_size_mb
            },
            'validation': {
                'check_content_integrity': self.validation.check_content_integrity,
                'validate_markdown': self.validation.validate_markdown,
                'check_links': self.validation.check_links,
                'validate_tables': self.validation.validate_tables,
                'strict_mode': self.validation.strict_mode
            },
            'verbose': self.verbose,
            'debug': self.debug,
            'log_level': self.log_level,
            'max_workers': self.max_workers,
            'temp_directory': self.temp_directory,
            'custom_settings': self.custom_settings
        }
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to YAML file."""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.to_dict(), f, default_flow_style=False, indent=2)
        except Exception as e:
            raise ConfigurationError(f"Error saving configuration: {e}")
    
    def validate(self) -> None:
        """Validate configuration settings."""
        errors = []
        
        # Validate parsing config
        if self.parsing.minimum_section_length < 0:
            errors.append("minimum_section_length must be >= 0")
        
        # Validate output config
        if self.output.max_file_size_mb <= 0:
            errors.append("max_file_size_mb must be > 0")
        
        if self.max_workers <= 0:
            errors.append("max_workers must be > 0")
        
        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_log_levels:
            errors.append(f"log_level must be one of: {valid_log_levels}")
        
        if errors:
            raise ConfigurationError("Configuration validation failed: " + "; ".join(errors))
    
    def get_output_path(self, filename: str = None) -> Path:
        """Get full output path for a file."""
        output_dir = Path(self.output.output_directory)
        
        if filename:
            if self.output.file_prefix:
                filename = f"{self.output.file_prefix}_{filename}"
            return output_dir / filename
        
        return output_dir
    
    def get_temp_path(self, filename: str = None) -> Path:
        """Get full temp path for a file."""
        temp_dir = Path(self.temp_directory)
        
        if filename:
            return temp_dir / filename
        
        return temp_dir


# Default configuration instance
DEFAULT_CONFIG = ConverterConfig()


def load_config(config_path: str = None) -> ConverterConfig:
    """Load configuration from file or return default."""
    if config_path and Path(config_path).exists():
        return ConverterConfig.from_file(config_path)
    
    # Check for default config files
    default_paths = [
        "config.yaml",
        "config.yml",
        "converter_config.yaml",
        ".converter_config.yaml"
    ]
    
    for path in default_paths:
        if Path(path).exists():
            return ConverterConfig.from_file(path)
    
    # Return default configuration
    return DEFAULT_CONFIG