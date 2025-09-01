"""
Comprehensive test suite for PDFProcessor
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from paperef.core.pdf_processor import PDFMetadata, PDFProcessor, get_file_hash_from_bytes
from paperef.utils.config import Config


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


@pytest.fixture
def mock_docling_processor():
    """Create realistic mock for Docling processor"""
    # Mock DocumentConverter
    mock_converter = Mock()
    mock_converter.convert = Mock()

    # Mock document result
    mock_result = Mock()
    mock_document = Mock()
    mock_document.text = "# Test Document\n\nThis is test content."
    mock_document.tables = []
    mock_document.figures = []
    mock_document.export_to_markdown = Mock(return_value="# Test Document\n\nThis is test content.")
    mock_document.get_images = Mock(return_value=[])

    mock_result.document = mock_document

    mock_converter.convert.return_value = mock_result

    return mock_converter


@pytest.fixture
def mock_fitz_document():
    """Create mock for PyMuPDF document"""
    mock_doc = Mock()
    mock_doc.__len__ = Mock(return_value=1)

    # Mock page
    mock_page = Mock()
    mock_page.get_text = Mock(return_value="Test page content")
    mock_page.search_for = Mock(return_value=[])

    mock_doc.__getitem__ = Mock(return_value=mock_page)
    mock_doc.close = Mock()

    return mock_doc


@pytest.fixture
def mock_pdf_path(temp_dir):
    """Create mock PDF path"""
    pdf_path = temp_dir / "test_paper.pdf"
    # Create a minimal valid PDF file for testing (shortened version)
    minimal_pdf_content = (
        b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        b"2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
        b"3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n"
        b"/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\n"
        b"BT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n0000000200 00000 n \n"
        b"trailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF"
    )
    pdf_path.write_bytes(minimal_pdf_content)
    return pdf_path


class TestPDFMetadata:
    """Test PDFMetadata dataclass"""

    def test_pdf_metadata_initialization(self):
        """Test PDFMetadata initialization with default values"""
        metadata = PDFMetadata()

        assert metadata.title is None
        assert metadata.authors == []
        assert metadata.year is None
        assert metadata.doi is None
        assert metadata.abstract is None
        assert metadata.keywords == []

    def test_pdf_metadata_with_values(self):
        """Test PDFMetadata with provided values"""
        metadata = PDFMetadata(
            title="Test Paper",
            authors=["Author A", "Author B"],
            year=2023,
            doi="10.1234/test",
            abstract="Test abstract",
            keywords=["test", "paper"]
        )

        assert metadata.title == "Test Paper"
        assert metadata.authors == ["Author A", "Author B"]
        assert metadata.year == 2023
        assert metadata.doi == "10.1234/test"
        assert metadata.abstract == "Test abstract"
        assert metadata.keywords == ["test", "paper"]


class TestPDFProcessor:
    """Test PDFProcessor class"""

    def test_init_success(self, mock_config):
        """Test successful initialization"""
        with patch("builtins.__import__") as mock_import:
            # Mock successful import
            mock_module = Mock()
            mock_import.return_value = mock_module
            mock_module.DocumentConverter = Mock()

            processor = PDFProcessor(mock_config)
            assert processor.config == mock_config

    def test_init_docling_import_error(self, mock_config):
        """Test initialization with Docling import error"""
        # Create processor with flag to raise import errors
        processor = PDFProcessor.__new__(PDFProcessor)
        processor._raise_import_error = True

        with patch("builtins.__import__", side_effect=ImportError("Docling not found")):
            with pytest.raises(ImportError, match="Docling is required"):
                processor._init_docling()

    def test_extract_title_from_metadata(self, mock_config, mock_pdf_path):
        """Test title extraction from PDF metadata"""
        processor = PDFProcessor(mock_config)

        with patch("fitz.open") as mock_fitz:
            mock_doc = Mock()
            mock_doc.metadata = {"title": "Test Title from Metadata"}
            mock_fitz.return_value.__enter__.return_value = mock_doc

            title = processor.extract_title(mock_pdf_path)
            assert title == "Test Title from Metadata"

    def test_extract_title_from_text_patterns(self, mock_config, mock_fitz_document):
        """Test title extraction from PDF text using patterns"""
        processor = PDFProcessor(mock_config)

        # Set up mock document for title extraction
        mock_page = mock_fitz_document.__getitem__.return_value
        mock_page.get_text.return_value = "TEST TITLE FROM TEXT\n\nAbstract: This is an abstract..."

        with patch("fitz.open", return_value=mock_fitz_document):
            mock_pdf_path = Mock()
            title = processor.extract_title(mock_pdf_path)

            # Should extract title from text patterns
            assert "TEST TITLE" in title or "Abstract:" in title

    def test_extract_title_fallback_from_filename(self, mock_config, temp_dir):
        """Test title extraction fallback to filename"""
        processor = PDFProcessor(mock_config)
        pdf_path = temp_dir / "Test_Paper_With_Underlines.pdf"

        # Mock empty document (no pages)
        mock_doc = Mock()
        mock_doc.metadata = {"title": ""}
        mock_doc.__len__ = Mock(return_value=0)  # No pages

        with patch("fitz.open", return_value=mock_doc):
            title = processor.extract_title(pdf_path)
            assert "Test Paper With Underlines" in title

    def test_extract_metadata_complete(self, mock_config, mock_fitz_document):
        """Test complete metadata extraction"""
        processor = PDFProcessor(mock_config)

        # Set up mock document metadata
        mock_fitz_document.metadata = {
            "title": "Test Paper",
            "creationDate": "2023-01-15"
        }

        # Set up mock page content for DOI and abstract
        mock_page = mock_fitz_document.__getitem__.return_value
        mock_page.get_text.return_value = """
        DOI: 10.1234/test-doi

        Abstract
        This is a test abstract for the paper.
        It contains multiple sentences.

        Keywords: machine learning, testing
        """

        # Mock a fake PDF path for testing
        fake_pdf_path = Path("/fake/path/test.pdf")

        with patch("fitz.open") as mock_fitz_open:
            mock_fitz_open.return_value.__enter__.return_value = mock_fitz_document
            mock_fitz_open.return_value.__exit__.return_value = None

            metadata = processor.extract_metadata(fake_pdf_path)

            assert metadata.title == "Test Paper"
            assert metadata.doi == "10.1234/test-doi"
            expected_abstract = (
                "This is a test abstract for the paper.\n        "
                "It contains multiple sentences."
            )
            assert metadata.abstract == expected_abstract
            assert metadata.keywords == ["machine learning", "testing"]

    def test_extract_year_from_metadata(self, mock_config):
        """Test year extraction from various metadata fields"""
        processor = PDFProcessor(mock_config)

        # Skip if docling is not available (since processor initialization might fail)
        if processor.docling_processor is None:
            pytest.skip("Docling not available")

        # Test creation date - PDF format
        metadata = {"creationDate": "20230115120000"}
        year = processor._extract_year_from_metadata(metadata)
        assert year == 2023

        # Test producer field
        metadata = {"producer": "Test Producer 2022"}
        year = processor._extract_year_from_metadata(metadata)
        assert year == 2022

        # Test no year found
        metadata = {"title": "No year here"}
        year = processor._extract_year_from_metadata(metadata)
        assert year is None

    def test_extract_doi_from_pdf(self, mock_config, mock_fitz_document):
        """Test DOI extraction from PDF text"""
        processor = PDFProcessor(mock_config)

        # Test valid DOI
        mock_page = mock_fitz_document.__getitem__.return_value
        mock_page.get_text.return_value = "Some text with DOI: 10.1234/test-doi-123 here"

        doi = processor._extract_doi_from_pdf(mock_fitz_document)
        assert doi == "10.1234/test-doi-123"

        # Test no DOI found
        mock_page.get_text.return_value = "No DOI in this text"
        doi = processor._extract_doi_from_pdf(mock_fitz_document)
        assert doi is None

    def test_extract_abstract_from_pdf(self, mock_config, mock_fitz_document):
        """Test abstract extraction from PDF text"""
        processor = PDFProcessor(mock_config)

        # Test abstract extraction
        mock_page = mock_fitz_document.__getitem__.return_value
        mock_page.get_text.return_value = """
        Title: Test Paper

        Abstract
        This is the abstract content.
        It has multiple lines and paragraphs.

        Introduction
        This is the introduction.
        """

        abstract = processor._extract_abstract_from_pdf(mock_fitz_document)
        assert abstract == "This is the abstract content.\n        It has multiple lines and paragraphs."

        # Test no abstract found
        mock_page.get_text.return_value = "No abstract section here"
        abstract = processor._extract_abstract_from_pdf(mock_fitz_document)
        assert abstract is None

    def test_convert_to_markdown_success(self, mock_config, temp_dir, mock_docling_processor):
        """Test successful PDF to markdown conversion"""
        processor = PDFProcessor(mock_config)
        processor.docling_processor = mock_docling_processor

        # Create a real test file
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_text("fake pdf content")

        output_dir = temp_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Mock metadata extraction
        with patch.object(processor, "extract_metadata") as mock_extract:
            mock_extract.return_value = Mock(title="Test Paper", authors=[], year=None, doi=None, abstract=None, keywords=[])

            markdown_content, image_paths = processor.convert_to_markdown(
                pdf_file, output_dir, "placeholder"
            )

            assert "# Test Document" in markdown_content
            assert "This is test content." in markdown_content
            assert image_paths == []
            mock_docling_processor.convert.assert_called_once_with(pdf_file)

    def test_convert_to_markdown_with_images(self, mock_config, temp_dir, mock_docling_processor):
        """Test PDF conversion with image extraction"""
        processor = PDFProcessor(mock_config)
        processor.docling_processor = mock_docling_processor

        # Create test files
        pdf_file = temp_dir / "test.pdf"
        pdf_file.write_text("fake pdf content")
        output_dir = temp_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Mock image object
        mock_image = Mock()
        mock_image.get_image.return_value = Mock()
        mock_image.image_name = "test_image.png"

        mock_result = mock_docling_processor.convert.return_value
        mock_result.document.get_images.return_value = [mock_image]
        mock_result.document.export_to_markdown.return_value = "# Content with ![image](test_image.png)"

        with patch.object(processor, "_process_images_placeholder") as mock_process_images:
            mock_process_images.return_value = [output_dir / "test_image.png"]

            markdown_content, image_paths = processor.convert_to_markdown(
                pdf_file, output_dir, "placeholder"
            )

            assert "# Content" in markdown_content
            assert len(image_paths) == 1
            assert "test_image.png" in str(image_paths[0])

    def test_clean_markdown_content(self, mock_config):
        """Test markdown content cleaning"""
        processor = PDFProcessor(mock_config)

        # Skip if docling is not available (since processor initialization might fail)
        if processor.docling_processor is None:
            pytest.skip("Docling not available")

        dirty_content = """# Title

Some content

---

More content

---

Even more content"""

        clean_content = processor._clean_markdown_content(dirty_content)

        # Should remove excessive separators
        assert clean_content.count("---") <= 2  # Keep at most 2 separators

    def test_add_metadata_frontmatter(self, mock_config):
        """Test adding YAML frontmatter to markdown"""
        processor = PDFProcessor(mock_config)

        # Skip if docling is not available (since processor initialization might fail)
        if processor.docling_processor is None:
            pytest.skip("Docling not available")

        metadata = PDFMetadata(
            title="Test Title",
            authors=["Author A", "Author B"],
            year=2023,
            doi="10.1234/test",
            keywords=["test", "markdown"]
        )

        markdown_content = "# Test Content"
        result = processor._add_metadata_frontmatter(markdown_content, metadata)

        assert result.startswith("---")
        assert 'title: "Test Title"' in result
        assert 'authors: ["Author A", "Author B"]' in result
        assert "year: 2023" in result
        assert 'doi: "10.1234/test"' in result
        assert 'keywords: ["test", "markdown"]' in result
        assert result.endswith("# Test Content")

    def test_file_hash_from_bytes(self):
        """Test file hash calculation from bytes"""
        test_data = b"test data for hashing"
        hash1 = get_file_hash_from_bytes(test_data)
        hash2 = get_file_hash_from_bytes(test_data)

        # Same data should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 8  # MD5 truncated to 8 chars

        # Different data should produce different hash
        different_data = b"different test data"
        hash3 = get_file_hash_from_bytes(different_data)
        assert hash1 != hash3


if __name__ == "__main__":
    pytest.main([__file__])
