"""
PaperRef: Integrated PDF to Markdown converter with automatic BibTeX generation for academic papers
"""

__version__ = "0.1.0"
__author__ = "Alan Synn"
__email__ = "alan@alansynn.com"

from .core.bibtex_generator import BibTeXEntry, BibTeXGenerator
from .core.pdf_processor import PDFMetadata, PDFProcessor
from .utils.config import Config
from .utils.file_utils import (
    copy_file,
    ensure_directory,
    get_file_hash,
    get_pdf_title,
    load_cache,
    read_text_file,
    sanitize_filename,
    save_cache,
    write_text_file,
)
from .utils.logging_config import get_logger, setup_logging

__all__ = [
    "BibTeXEntry",
    "BibTeXGenerator",
    "Config",
    "PDFMetadata",
    # Core classes
    "PDFProcessor",
    "__author__",
    "__email__",
    # Metadata
    "__version__",
    "copy_file",
    # Utility functions
    "ensure_directory",
    "get_file_hash",
    "get_logger",
    "get_pdf_title",
    "load_cache",
    "read_text_file",
    "sanitize_filename",
    "save_cache",
    # Logging
    "setup_logging",
    "write_text_file",
]
