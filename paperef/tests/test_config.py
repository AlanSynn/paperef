"""
Test suite for Config class
"""

from pathlib import Path

import pytest

from paperef.utils.config import Config


class TestConfig:
    """Test Config class"""

    def test_config_initialization_default(self):
        """Test Config initialization with default values"""
        config = Config()

        assert config.output_dir == Path("./papers")
        assert config.image_mode == "placeholder"
        assert config.bibtex_only is False
        assert config.bibtex_enhanced is False
        assert config.bibtex_clean is False
        assert config.cache_dir == Path("./cache")
        assert config.create_folders is True
        assert config.folder_template == "{title}"
        assert config.verbose is False
        assert config.interactive is True
        assert config.no_interactive is False
        assert config.skip_pdf is False

    def test_config_initialization_custom(self):
        """Test Config initialization with custom values"""
        config = Config(
            output_dir="/custom/output",
            image_mode="vlm",
            bibtex_only=True,
            bibtex_enhanced=True,
            bibtex_clean=True,
            cache_dir="/custom/cache",
            create_folders=False,
            folder_template="{author}_{year}",
            verbose=True,
            interactive=False,
            no_interactive=True,
            skip_pdf=True
        )

        assert config.output_dir == Path("/custom/output")
        assert config.image_mode == "vlm"
        assert config.bibtex_only is True
        assert config.bibtex_enhanced is True
        assert config.bibtex_clean is True
        assert config.cache_dir == Path("/custom/cache")
        assert config.create_folders is False
        assert config.folder_template == "{author}_{year}"
        assert config.verbose is True
        assert config.interactive is False
        assert config.no_interactive is True
        assert config.skip_pdf is True

    def test_config_validation_valid_image_mode(self):
        """Test config validation with valid image mode"""
        config = Config(image_mode="placeholder")
        # Should not raise any exception
        assert config.image_mode == "placeholder"

        config = Config(image_mode="vlm")
        assert config.image_mode == "vlm"

    def test_config_validation_invalid_image_mode(self):
        """Test config validation with invalid image mode"""
        with pytest.raises(ValueError, match="Invalid image_mode"):
            Config(image_mode="invalid")

    def test_config_validation_valid_bibtex_style(self):
        """Test config validation with valid bibtex key style"""
        config = Config(bibtex_key_style="google")
        assert config.bibtex_key_style == "google"

        config = Config(bibtex_key_style="standard")
        assert config.bibtex_key_style == "standard"

    def test_config_validation_invalid_bibtex_style(self):
        """Test config validation with invalid bibtex key style"""
        with pytest.raises(ValueError, match="Invalid bibtex_key_style"):
            Config(bibtex_key_style="invalid")

    def test_config_properties(self):
        """Test config properties"""
        config = Config(
            output_dir="/test/output",
            cache_dir="/test/cache"
        )

        assert config.cache_file == Path("/test/cache") / ".bib_cache.json"
