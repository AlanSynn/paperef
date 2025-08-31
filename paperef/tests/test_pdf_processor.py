"""
Comprehensive test suite for PDFProcessor
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from paperef.core.pdf_processor import PDFMetadata, PDFProcessor
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
def mock_pdf_path(temp_dir):
    """Create mock PDF path"""
    pdf_path = temp_dir / "test_paper.pdf"
    # Create a minimal valid PDF file for testing
    minimal_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Hello World) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000200 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n284\n%%EOF"
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

    @patch("paperef.core.pdf_processor.DocumentConverter")
    def test_init_success(self, mock_docling, mock_config):
        """Test successful initialization"""
        processor = PDFProcessor(mock_config)

        assert processor.config == mock_config
        assert processor.docling_processor is not None
        mock_docling.assert_called_once()

    @patch("paperef.core.pdf_processor.DocumentConverter")
    def test_init_docling_import_error(self, mock_docling, mock_config):
        """Test initialization with Docling import error"""
        mock_docling.side_effect = ImportError("Docling not found")

        with pytest.raises(ImportError, match="Docling is required"):
            PDFProcessor(mock_config)

    def test_extract_title_from_metadata(self, mock_config, mock_pdf_path):
        """Test title extraction from PDF metadata"""
        processor = PDFProcessor(mock_config)

        with patch("fitz.open") as mock_fitz:
            mock_doc = Mock()
            mock_doc.metadata = {"title": "Test Title from Metadata"}
            mock_fitz.return_value.__enter__.return_value = mock_doc

            title = processor.extract_title(mock_pdf_path)
            assert title == "Test Title from Metadata"

    def test_extract_title_from_text_patterns(self, mock_config, mock_pdf_path):
        """Test title extraction from PDF text using patterns"""
        processor = PDFProcessor(mock_config)

        with patch("fitz.open") as mock_fitz:
            mock_doc = Mock()
            mock_doc.metadata = {"title": ""}
            mock_page = Mock()
            mock_page.get_text.return_value = "TEST TITLE FROM TEXT\n\nAbstract: This is an abstract..."
            mock_doc.__len__.return_value = 1
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.return_value.__enter__.return_value = mock_doc

            title = processor.extract_title(mock_pdf_path)
            assert title == "TEST TITLE FROM TEXT"

    def test_extract_title_fallback_from_filename(self, mock_config, temp_dir):
        """Test title extraction fallback to filename"""
        processor = PDFProcessor(mock_config)
        pdf_path = temp_dir / "Test_Paper_With_Underlines.pdf"

        with patch("fitz.open") as mock_fitz:
            mock_doc = Mock()
            mock_doc.metadata = {"title": ""}
            mock_doc.__len__.return_value = 0  # No pages
            mock_fitz.return_value.__enter__.return_value = mock_doc

            title = processor.extract_title(pdf_path)
            assert title == "Test Paper With Underlines"

    def test_extract_metadata_complete(self, mock_config, mock_pdf_path):
        """Test complete metadata extraction"""
        processor = PDFProcessor(mock_config)

        with patch("fitz.open") as mock_fitz:
            mock_doc = Mock()
            mock_doc.metadata = {
                "title": "Test Paper",
                "creationDate": "2023-01-15"
            }

            # Mock pages for DOI and abstract extraction
            mock_page = Mock()
            mock_page.get_text.return_value = """
            DOI: 10.1234/test-doi

            Abstract
            This is a test abstract for the paper.
            It contains multiple sentences.

            Keywords: machine learning, testing
            """
            mock_doc.__len__.return_value = 1
            mock_doc.__getitem__.return_value = mock_page
            mock_fitz.return_value.__enter__.return_value = mock_doc

            metadata = processor.extract_metadata(mock_pdf_path)

            assert metadata.title == "Test Paper"
            assert metadata.doi == "10.1234/test-doi"
            assert metadata.abstract == "This is a test abstract for the paper.\n            It contains multiple sentences."
            assert metadata.keywords == ["machine learning", "testing"]

    def test_extract_year_from_metadata(self, mock_config):
        """Test year extraction from various metadata fields"""
        processor = PDFProcessor(mock_config)

        # Test creation date
        metadata = {"creationDate": "D:20230115120000"}
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

    def test_extract_doi_from_pdf(self, mock_config):
        """Test DOI extraction from PDF text"""
        processor = PDFProcessor(mock_config)

        mock_doc = Mock()
        mock_page = Mock()

        # Test valid DOI
        mock_page.get_text.return_value = "Some text with DOI: 10.1234/test-doi-123 here"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page

        doi = processor._extract_doi_from_pdf(mock_doc)
        assert doi == "10.1234/test-doi-123"

        # Test no DOI found
        mock_page.get_text.return_value = "No DOI in this text"
        doi = processor._extract_doi_from_pdf(mock_doc)
        assert doi is None

    def test_extract_abstract_from_pdf(self, mock_config):
        """Test abstract extraction from PDF text"""
        processor = PDFProcessor(mock_config)

        mock_doc = Mock()
        mock_page = Mock()

        # Test abstract extraction
        mock_page.get_text.return_value = """
        Title: Test Paper

        Abstract
        This is the abstract content.
        It has multiple lines and paragraphs.

        Introduction
        This is the introduction.
        """
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page

        abstract = processor._extract_abstract_from_pdf(mock_doc)
        assert abstract == "This is the abstract content.\n        It has multiple lines and paragraphs."

        # Test no abstract found
        mock_page.get_text.return_value = "No abstract section here"
        abstract = processor._extract_abstract_from_pdf(mock_doc)
        assert abstract is None

    @patch("paperef.core.pdf_processor.DocumentConverter")
    def test_convert_to_markdown_success(self, mock_docling_class, mock_config, mock_pdf_path, temp_dir):
        """Test successful PDF to markdown conversion"""
        # Mock Docling components
        mock_result = Mock()
        mock_result.document.export_to_markdown.return_value = "# Test Markdown Content"
        mock_result.document.get_images.return_value = []

        mock_converter = Mock()
        mock_converter.convert.return_value = mock_result
        mock_docling_class.return_value = mock_converter

        processor = PDFProcessor(mock_config)
        output_dir = temp_dir / "output"

        markdown_content, image_paths = processor.convert_to_markdown(
            mock_pdf_path, output_dir, "placeholder"
        )

        assert markdown_content == "# Test Markdown Content"
        assert image_paths == []
        mock_converter.convert.assert_called_once()

    @patch("paperef.core.pdf_processor.DocumentConverter")
    def test_convert_to_markdown_with_images(self, mock_docling_class, mock_config, mock_pdf_path, temp_dir):
        """Test PDF conversion with image extraction"""
        # Mock image object
        mock_image = Mock()
        mock_image.get_image.return_value = Mock()
        mock_image.image_name = "test_image.png"

        mock_result = Mock()
        mock_result.document.export_to_markdown.return_value = "# Content with ![image](test_image.png)"
        mock_result.document.get_images.return_value = [mock_image]

        mock_converter = Mock()
        mock_converter.convert.return_value = mock_result
        mock_docling_class.return_value = mock_converter

        processor = PDFProcessor(mock_config)
        output_dir = temp_dir / "output"

        with patch("PIL.Image.open") as mock_pil:
            mock_pil.return_value = Mock()
            markdown_content, image_paths = processor.convert_to_markdown(
                mock_pdf_path, output_dir, "placeholder"
            )

        assert len(image_paths) == 1
        assert "test_image.png" in str(image_paths[0])

    def test_clean_markdown_content(self, mock_config):
        """Test markdown content cleaning"""
        processor = PDFProcessor(mock_config)

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
        from paperef.core.pdf_processor import get_file_hash_from_bytes

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
