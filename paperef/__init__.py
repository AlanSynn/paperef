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
    # Core classes
    "PDFProcessor",
    "PDFMetadata",
    "BibTeXGenerator",
    "BibTeXEntry",
    "Config",

    # Utility functions
    "ensure_directory",
    "load_cache",
    "save_cache",
    "get_file_hash",
    "sanitize_filename",
    "read_text_file",
    "write_text_file",
    "copy_file",
    "get_pdf_title",

    # Logging
    "setup_logging",
    "get_logger",

    # Metadata
    "__version__",
    "__author__",
    "__email__",
]
