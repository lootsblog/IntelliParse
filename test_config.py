"""Tests for configuration system."""

import pytest
import tempfile
import yaml
from pathlib import Path
import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import ConverterConfig, OutputFormat, ChunkingStrategy
from src.core.exceptions import ConfigurationError


def test_default_config():
    """Test default configuration creation."""
    config = ConverterConfig()
    
    assert config.parsing.preserve_formatting is True
    assert config.output.format == OutputFormat.MULTI_FILE
    assert config.output.chunking_strategy == ChunkingStrategy.SMART
    assert config.verbose is False
    assert config.log_level == "INFO"


def test_config_from_dict():
    """Test configuration creation from dictionary."""
    config_dict = {
        'parsing': {
            'preserve_formatting': False,
            'extract_images': True
        },
        'output': {
            'format': 'single_file',
            'chunking_strategy': 'by_headings'
        },
        'verbose': True,
        'debug': True
    }
    
    config = ConverterConfig.from_dict(config_dict)
    
    assert config.parsing.preserve_formatting is False
    assert config.parsing.extract_images is True
    assert config.output.format == OutputFormat.SINGLE_FILE
    assert config.output.chunking_strategy == ChunkingStrategy.BY_HEADINGS
    assert config.verbose is True
    assert config.debug is True


def test_config_to_dict():
    """Test configuration serialization to dictionary."""
    config = ConverterConfig()
    config.verbose = True
    config.parsing.extract_images = True
    
    config_dict = config.to_dict()
    
    assert config_dict['verbose'] is True
    assert config_dict['parsing']['extract_images'] is True
    assert config_dict['output']['format'] == 'multi_file'


def test_config_file_operations():
    """Test saving and loading configuration files."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_path = f.name
    
    try:
        # Create and save config
        config = ConverterConfig()
        config.verbose = True
        config.parsing.extract_images = True
        config.save_to_file(config_path)
        
        # Load config
        loaded_config = ConverterConfig.from_file(config_path)
        
        assert loaded_config.verbose is True
        assert loaded_config.parsing.extract_images is True
        
    finally:
        Path(config_path).unlink()


def test_config_validation():
    """Test configuration validation."""
    # Valid config should pass
    config = ConverterConfig()
    config.validate()  # Should not raise
    
    # Invalid config should fail
    config.parsing.minimum_section_length = -1
    with pytest.raises(ConfigurationError):
        config.validate()


def test_path_methods():
    """Test path generation methods."""
    config = ConverterConfig()
    config.output.output_directory = "test_output"
    config.output.file_prefix = "doc"
    
    # Test output path
    output_path = config.get_output_path("test.md")
    assert output_path == Path("test_output/doc_test.md")
    
    # Test temp path
    temp_path = config.get_temp_path("temp.txt")
    assert temp_path == Path("temp/temp.txt")


def test_custom_settings():
    """Test custom settings handling."""
    config_dict = {
        'parsing': {'preserve_formatting': True},
        'custom_option': 'custom_value',
        'another_custom': 123
    }
    
    config = ConverterConfig.from_dict(config_dict)
    
    assert config.custom_settings['custom_option'] == 'custom_value'
    assert config.custom_settings['another_custom'] == 123


if __name__ == "__main__":
    # Run tests manually
    try:
        test_default_config()
        test_config_from_dict()
        test_config_to_dict()
        test_config_file_operations()
        test_config_validation()
        test_path_methods()
        test_custom_settings()
        
        print("✅ All configuration tests passed!")
        print("🚀 Ready for Task 1.4 - Base Architecture!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()