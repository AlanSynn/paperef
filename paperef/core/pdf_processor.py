"""
PDF processing and Docling integration module
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..utils.config import Config
from ..utils.file_utils import ensure_directory


@dataclass
class PDFMetadata:
    """PDF metadata"""
    title: str | None = None
    authors: list[str] = None
    year: int | None = None
    doi: str | None = None
    abstract: str | None = None
    keywords: list[str] = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []


class PDFProcessor:
    """PDF processing class"""

    def __init__(self, config: Config):
        self.config = config
        self.docling_processor = None
        self._init_docling()

    def _init_docling(self):
        """Initialize Docling processor"""
        try:
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.document_converter import DocumentConverter

            # PDF pipeline options
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True  # OCR enabled
            pipeline_options.do_table_structure = True  # Table structure recognition

            # Create document converter
            self.docling_processor = DocumentConverter(
                format_options={
                    "output_format": "markdown",
                    "do_ocr": True,
                    "do_table_structure": True,
                }
            )

        except ImportError as e:
            raise ImportError(
                "Docling is required for PDF processing. "
                "Install with: pip install docling"
            ) from e

    def extract_title(self, pdf_path: Path) -> str | None:
        """Extract title from PDF"""
        try:

            import fitz

            with fitz.open(pdf_path) as doc:
                metadata = doc.metadata
                title = metadata.get("title", "").strip()

                if title:
                    return title


                if len(doc) > 0:
                    page = doc[0]
                    text = page.get_text()


                    title_patterns = [
                        r"^([A-Z][^.!?\n]{20,80})[.!?\n]",
                        r"^(.+)\n={3,}",
                        r"^(.+)\n-{3,}",
                    ]

                    lines = text.split("\n")
                    for pattern in title_patterns:
                        for line in lines[:3]:
                            match = re.search(pattern, line.strip(), re.MULTILINE)
                            if match:
                                title = match.group(1).strip()
                                if len(title) > 10:
                                    return title

        except ImportError:

            pass
        except Exception:
            pass


        stem = pdf_path.stem

        title = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
        title = re.sub(r"_+", " ", title)
        title = title.replace("-", " ")

        return title.strip() if title.strip() else None

    def extract_metadata(self, pdf_path: Path) -> PDFMetadata:
        """Extract metadata from PDF - improved version"""
        metadata = PDFMetadata()

        try:
            import fitz

            with fitz.open(pdf_path) as doc:
                pdf_metadata = doc.metadata

                # Extract basic metadata
                metadata.title = pdf_metadata.get("title", "").strip() or self.extract_title(pdf_path)
                metadata.year = self._extract_year_from_metadata(pdf_metadata)

                # Try to extract DOI
                metadata.doi = self._extract_doi_from_pdf(doc)

                # Try to extract abstract
                metadata.abstract = self._extract_abstract_from_pdf(doc)

                # Try to extract author information
                metadata.authors = self._extract_authors_from_pdf(doc)

                # Try to extract keywords
                metadata.keywords = self._extract_keywords_from_pdf(doc)

        except Exception:
            pass

        return metadata

    def _extract_year_from_metadata(self, pdf_metadata: dict[str, Any]) -> int | None:
        """Extract year from metadata"""

        date_fields = ["creationDate", "modDate", "producer"]

        for field in date_fields:
            value = pdf_metadata.get(field, "")
            if value:

                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value))
                if year_match:
                    return int(year_match.group(1))

        return None

    def _extract_doi_from_pdf(self, doc) -> str | None:
        """Extract DOI from PDF"""
        doi_pattern = r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b"

        # Search for DOI on the first few pages
        for page_num in range(min(5, len(doc))):
            page = doc[page_num]
            text = page.get_text()

            match = re.search(doi_pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).lower()

        return None

    def _extract_abstract_from_pdf(self, doc) -> str | None:
        """Extract abstract from PDF"""

        if len(doc) > 0:
            page = doc[0]
            text = page.get_text()


            abstract_patterns = [
                r"Abstract\s*\n(.*?)(?:\n\n|\n[A-Z][a-z]+|\n\d+\.)",
                r"ABSTRACT\s*\n(.*?)(?:\n\n|\n[A-Z][a-z]+|\n\d+\.)",
                r"Summary\s*\n(.*?)(?:\n\n|\n[A-Z][a-z]+|\n\d+\.)",
            ]

            for pattern in abstract_patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    abstract = match.group(1).strip()
                    if len(abstract) > 50:
                        return abstract

        return None

    def _extract_authors_from_pdf(self, doc) -> list[str]:
        """Extract author information from PDF"""
        authors = []

        try:
            # Find author information on the first page
            if len(doc) > 0:
                page = doc[0]
                text = page.get_text()

                # Common author patterns
                author_patterns = [
                    r"Authors?:\s*([^\n]+)",
                    r"By\s+([^\n]+)",
                    r"Written by\s+([^\n]+)",
                    r"^([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)*)\s*\n",
                ]

                for pattern in author_patterns:
                    match = re.search(pattern, text, re.MULTILINE)
                    if match:
                        author_text = match.group(1).strip()
                        # Separate authors separated by comma or "and"
                        if "," in author_text:
                            authors = [a.strip() for a in author_text.split(",") if a.strip()]
                        elif " and " in author_text:
                            authors = [a.strip() for a in author_text.split(" and ") if a.strip()]
                        else:
                            authors = [author_text]

                        # Too many authors are excluded (not a paper)
                        if len(authors) <= 10:
                            break

        except Exception:
            pass

        return authors

    def _extract_keywords_from_pdf(self, doc) -> list[str]:
        """Extract keywords from PDF"""
        keywords = []

        try:

            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                text = page.get_text()


                keyword_patterns = [
                    r"Keywords?:\s*([^\n]+)",
                    r"Key words?:\s*([^\n]+)",
                    r"Subject classifications?:\s*([^\n]+)",
                ]

                for pattern in keyword_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        keyword_text = match.group(1).strip()

                        if "," in keyword_text:
                            keywords = [k.strip() for k in keyword_text.split(",") if k.strip()]
                        elif ";" in keyword_text:
                            keywords = [k.strip() for k in keyword_text.split(";") if k.strip()]
                        else:
                            keywords = [keyword_text]


                        if len(keywords) <= 20:
                            break

                if keywords:
                    break

        except Exception:
            pass

        return keywords

    def convert_to_markdown(
        self,
        pdf_path: Path,
        output_dir: Path,
        image_mode: str = "placeholder"
    ) -> tuple[str, list[Path]]:
        """
        Convert PDF to Markdown

        Args:
            pdf_path: Input PDF file path
            output_dir: Output directory
            image_mode: Image processing mode ("placeholder" | "vlm")

        Returns:
            Converted Markdown text and list of extracted image files
        """
        if not self.docling_processor:
            raise RuntimeError("Docling processor not initialized")

        try:

            result = self.docling_processor.convert(pdf_path)


            markdown_text = result.document.export_to_markdown()


            image_paths = []
            if image_mode == "vlm":
                image_paths = self._process_images_vlm(result, output_dir)
                markdown_text = self._enhance_markdown_with_vlm(markdown_text, result)
            else:
                image_paths = self._process_images_placeholder(result, output_dir)
                markdown_text = self._enhance_markdown_placeholder(markdown_text, result)


            metadata = self.extract_metadata(pdf_path)
            markdown_text = self._add_metadata_frontmatter(markdown_text, metadata)

            return markdown_text, image_paths

        except Exception as e:
            raise RuntimeError(f"Failed to convert PDF {pdf_path}: {e}") from e

    def _process_images_placeholder(
        self,
        docling_result,
        output_dir: Path
    ) -> list[Path]:
        """Process images in placeholder mode"""
        image_paths = []
        artifacts_dir = output_dir / self.config.artifacts_dir_name
        ensure_directory(artifacts_dir)

        try:
            # Extract and save images from Docling result
            for item in docling_result.document.body.content:
                if hasattr(item, "image") and item.image:
                    # Create image filename based on hash
                    image_hash = get_file_hash_from_bytes(item.image.get_image())
                    image_filename = f"image_{image_hash}.png"
                    image_path = artifacts_dir / image_filename

                    # Save image
                    with open(image_path, "wb") as f:
                        f.write(item.image.get_image())

                    image_paths.append(image_path)

        except Exception:
            pass  # Ignore image processing failure

        return image_paths

    def _process_images_vlm(
        self,
        docling_result,
        output_dir: Path
    ) -> list[Path]:
        """Process images in VLM mode (future implementation)"""


        return self._process_images_placeholder(docling_result, output_dir)

    def _enhance_markdown_placeholder(
        self,
        markdown_text: str,
        docling_result
    ) -> str:
        """Improve markdown in placeholder mode"""
        # Replace images with placeholder
        enhanced_text = markdown_text

        # Basic text improvement
        enhanced_text = self._clean_markdown_formatting(enhanced_text)

        return enhanced_text

    def _enhance_markdown_with_vlm(
        self,
        markdown_text: str,
        docling_result
    ) -> str:
        """Improve markdown in VLM mode (future implementation)"""

        return self._enhance_markdown_placeholder(markdown_text, docling_result)

    def _clean_markdown_formatting(self, text: str) -> str:
        """Clean markdown formatting"""
        # Clean consecutive empty lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Clean unnecessary spaces
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            # Remove trailing spaces
            line = line.rstrip()
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _add_metadata_frontmatter(
        self,
        markdown_text: str,
        metadata: PDFMetadata
    ) -> str:
        """Add YAML front matter"""
        frontmatter_lines = ["---"]

        if metadata.title:
            frontmatter_lines.append(f'title: "{metadata.title}"')
        if metadata.authors:
            authors_str = ", ".join(f'"{author}"' for author in metadata.authors)
            frontmatter_lines.append(f"authors: [{authors_str}]")
        if metadata.year:
            frontmatter_lines.append(f"year: {metadata.year}")
        if metadata.doi:
            frontmatter_lines.append(f'doi: "{metadata.doi}"')
        if metadata.keywords:
            keywords_str = ", ".join(f'"{kw}"' for kw in metadata.keywords)
            frontmatter_lines.append(f"keywords: [{keywords_str}]")

        frontmatter_lines.append("---")
        frontmatter_lines.append("")

        return "\n".join(frontmatter_lines) + markdown_text


def get_file_hash_from_bytes(data: bytes) -> str:
    """Calculate hash from byte data"""
    import hashlib
    return hashlib.md5(data).hexdigest()[:8]
