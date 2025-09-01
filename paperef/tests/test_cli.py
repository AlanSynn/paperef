"""
Test suite for CLI functionality
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from paperef.cli.main import app
from paperef.utils.config import Config


@pytest.fixture
def runner():
    """Create CLI runner"""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_config():
    """Create mock configuration"""
    return Config(
        output_dir="./test_output",
        image_mode="placeholder",
        bibtex_only=False,
        bibtex_enhanced=False,
        bibtex_clean=False,
        cache_dir="./test_cache",
        create_folders=True,
        folder_template="{title}",
        verbose=False,
        interactive=True,
        no_interactive=False,
        skip_pdf=False
    )


class TestCLI:
    """Test CLI commands"""

    def test_cli_help(self, runner):
        """Test CLI help command"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "PDF to Markdown converter" in result.stdout
        assert "process" in result.stdout

    def test_cli_help(self, runner):
        """Test CLI help"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "PDF to Markdown converter" in result.stdout
        assert "--output-dir" in result.stdout
        assert "--image-mode" in result.stdout
        assert "--bibtex-only" in result.stdout

    def test_cli_no_files(self, runner):
        """Test CLI with no input files"""
        result = runner.invoke(app, [])
        # Should show help when no files provided
        assert result.exit_code == 0
        assert "PDF to Markdown converter" in result.stdout

    def test_cli_nonexistent_file(self, runner, temp_dir):
        """Test CLI with non-existent file"""
        nonexistent_file = temp_dir / "nonexistent.pdf"
        result = runner.invoke(app, [str(nonexistent_file)])

        # Should fail with error message
        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_cli_invalid_file_type(self, runner, temp_dir):
        """Test CLI with invalid file type"""
        invalid_file = temp_dir / "test.txt"
        invalid_file.write_text("Not a PDF")

        result = runner.invoke(app, [str(invalid_file)])
        # Should fail with error message
        assert result.exit_code == 1
        assert "Error" in result.stdout

    def test_cli_with_custom_options(self, runner):
        """Test CLI with custom options - just test option parsing"""
        result = runner.invoke(app, ["--help"])

        # Just verify that help works with all our options
        assert result.exit_code == 0
        assert "--output-dir" in result.stdout
        assert "--image-mode" in result.stdout
        assert "--bibtex-only" in result.stdout


class TestCLIOptions:
    """Test CLI option parsing and validation"""

    def test_image_mode_help(self, runner):
        """Test that image mode option is shown in help"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "image-mode" in result.stdout
        assert "placeholder" in result.stdout

    def test_boolean_flags_help(self, runner):
        """Test that boolean flags are shown in help"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--bibtex-only" in result.stdout
        assert "--verbose" in result.stdout
