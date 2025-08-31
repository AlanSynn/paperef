"""
File I/O utility module
"""

import json
from pathlib import Path
from typing import Any


def ensure_directory(path: Path) -> None:
    """Create directory if it doesn't exist"""
    path.mkdir(parents=True, exist_ok=True)


def load_cache(cache_file: Path) -> dict[str, Any]:
    """Load data from cache file"""
    if not cache_file.exists():
        return {}

    try:
        with cache_file.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_cache(cache_file: Path, data: dict[str, Any]) -> None:
    """Save data to cache file"""
    ensure_directory(cache_file.parent)

    try:
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # Ignore cache save failure


def get_file_hash(file_path: Path) -> str:
    """Calculate file hash"""
    import hashlib

    hash_sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()[:8]


def sanitize_filename(filename: str) -> str:
    """Remove unsafe characters from filename"""
    import re

    # Allowable characters: alphabet, numbers, hyphen, underscore, period
    sanitized = re.sub(r"[^\w\.-]", "_", filename)

    # Reduce consecutive underscores to one
    sanitized = re.sub(r"_+", "_", sanitized)

    # Remove leading and trailing spaces and underscores
    sanitized = sanitized.strip("_ ")

    return sanitized or "unnamed"


def get_unique_filename(directory: Path, base_name: str, extension: str = "") -> str:
    """Create unique filename within directory"""
    if extension and not extension.startswith("."):
        extension = f".{extension}"

    counter = 1
    filename = f"{base_name}{extension}"

    while (directory / filename).exists():
        filename = f"{base_name}_{counter}{extension}"
        counter += 1

    return filename


def read_text_file(file_path: Path, encoding: str = "utf-8") -> str | None:
    """Read text file"""
    try:
        with file_path.open(encoding=encoding) as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def write_text_file(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """Write text file"""
    try:
        ensure_directory(file_path.parent)
        with file_path.open("w", encoding=encoding) as f:
            f.write(content)
        return True
    except OSError:
        return False


def copy_file(src: Path, dst: Path) -> bool:
    """Copy file"""
    try:
        ensure_directory(dst.parent)
        import shutil
        shutil.copy2(src, dst)
        return True
    except OSError:
        return False


def get_pdf_title(pdf_path: Path) -> str | None:
    """Extract title metadata from PDF file"""
    try:
        import fitz

        with fitz.open(pdf_path) as doc:
            metadata = doc.metadata
            title = metadata.get("title", "").strip()


            if not title and len(doc) > 0:
                page = doc[0]
                text = page.get_text()


                lines = text.split("\n")
                for line_text in lines[:5]:
                    stripped_line = line_text.strip()
                    if len(stripped_line) > 10 and not stripped_line.isupper():
                        title = stripped_line
                        break

            return title if title else None

    except ImportError:

        return None
    except Exception:
        return None
