"""
Common test fixtures and configurations for all tests
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from paperef.core.pdf_processor import PDFMetadata
from paperef.utils.config import Config


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    return Path(tempfile.mkdtemp())
    # Cleanup is handled by pytest


@pytest.fixture
def mock_config():
    """Create comprehensive mock configuration"""
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


@pytest.fixture
def mock_pdf_metadata():
    """Create mock PDF metadata"""
    return PDFMetadata(
        title="Test Paper Title",
        authors=["John Doe", "Jane Smith"],
        year=2023,
        doi="10.1145/test.doi",
        abstract="This is a test abstract for the paper.",
        keywords=["test", "paper", "research"]
    )


@pytest.fixture
def mock_fitz_document():
    """Create comprehensive mock for PyMuPDF document"""
    mock_doc = MagicMock()
    mock_doc.metadata = {
        "title": "Test Paper",
        "creationDate": "2023-01-15"
    }

    # Mock page
    mock_page = MagicMock()
    mock_page.get_text.return_value = """
    DOI: 10.1234/test-doi

    Abstract
    This is the abstract content.
    It has multiple lines and paragraphs.

    Keywords: machine learning, testing
    """
    mock_page.search_for.return_value = []

    mock_doc.__len__.return_value = 1
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.close = MagicMock()

    return mock_doc


@pytest.fixture
def mock_docling_processor():
    """Create comprehensive mock for Docling processor"""
    mock_converter = MagicMock()
    mock_converter.convert = MagicMock()

    # Mock document result with proper structure
    mock_result = MagicMock()
    mock_document = MagicMock()
    mock_document.text = "# Test Document\n\nThis is test content."
    mock_document.tables = []
    mock_document.figures = []
    mock_document.export_to_markdown.return_value = "# Test Document\n\nThis is test content."
    mock_document.get_images.return_value = []

    mock_result.document = mock_document

    mock_converter.convert.return_value = mock_result

    return mock_converter


@pytest.fixture
def mock_path_obj():
    """Create mock Path object that supports operations"""
    mock_path = MagicMock(spec=Path)
    mock_path.__str__.return_value = "/mock/path/test.pdf"
    mock_path.__truediv__ = MagicMock(return_value=Mock())
    mock_path.__fspath__.return_value = "/mock/path/test.pdf"
    mock_path.exists.return_value = True
    mock_path.is_file.return_value = True
    mock_path.suffix = ".pdf"
    mock_path.stem = "test"
    mock_path.name = "test.pdf"
    return mock_path


@pytest.fixture
def mock_session():
    """Create mock requests session"""
    mock_sess = MagicMock()

    # Mock successful response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {
            "items": [
                {
                    "DOI": "10.1145/example.doi",
                    "title": ["Test Paper Title"],
                    "author": [{"given": "John", "family": "Doe"}],
                    "published-print": {"date-parts": [[2023]]},
                    "publisher": "ACM",
                    "container-title": ["CHI Conference"]
                }
            ]
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200

    mock_sess.get.return_value = mock_response
    mock_sess.post.return_value = mock_response

    return mock_sess


@pytest.fixture
def sample_bibtex():
    """Sample BibTeX content for testing"""
    return """@article{test2023,
  title={Test Paper},
  author={Doe, John},
  year={2023}
}"""


@pytest.fixture
def sample_bibtex_with_doi():
    """Sample BibTeX with DOI"""
    return """@article{test2023,
  title={Test Paper},
  author={Doe, John},
  year={2023},
  doi={10.1145/example.doi}
}"""


@pytest.fixture
def sample_bibtex_acm_pages():
    """Sample BibTeX with ACM-style pages"""
    return """@inproceedings{test2023,
  title={Test Paper},
  author={Doe, John},
  pages={138:1--138:12}
}"""


@pytest.fixture
def sample_bibtex_with_special_chars():
    """Sample BibTeX with special characters"""
    return """@article{test2023,
  title={Paper & More},
  abstract={Some text with 100% success}
}"""

