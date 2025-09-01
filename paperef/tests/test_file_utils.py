"""
Test suite for file utility functions
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from paperef.utils.file_utils import (
    copy_file,
    ensure_directory,
    get_file_hash,
    get_unique_filename,
    load_cache,
    read_text_file,
    sanitize_filename,
    save_cache,
    write_text_file,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


class TestDirectoryOperations:
    """Test directory operations"""

    def test_ensure_directory(self, temp_dir):
        """Test directory creation"""
        test_dir = temp_dir / "test_subdir" / "nested"
        ensure_directory(test_dir)
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_ensure_directory_existing(self, temp_dir):
        """Test directory creation when already exists"""
        ensure_directory(temp_dir)
        assert temp_dir.exists()


class TestCacheOperations:
    """Test cache operations"""

    def test_load_cache_file_exists(self, temp_dir):
        """Test loading cache from existing file"""
        cache_file = temp_dir / "test_cache.json"
        test_data = {"key1": "value1", "key2": {"nested": "data"}}

        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = load_cache(cache_file)
        assert result == test_data

    def test_load_cache_file_not_exists(self, temp_dir):
        """Test loading cache from non-existing file"""
        cache_file = temp_dir / "nonexistent_cache.json"
        result = load_cache(cache_file)
        assert result == {}

    def test_load_cache_invalid_json(self, temp_dir):
        """Test loading cache with invalid JSON"""
        cache_file = temp_dir / "invalid_cache.json"
        cache_file.write_text("invalid json content")

        result = load_cache(cache_file)
        assert result == {}

    def test_save_cache(self, temp_dir):
        """Test saving cache to file"""
        cache_file = temp_dir / "test_cache.json"
        test_data = {"key1": "value1", "key2": 42}

        save_cache(cache_file, test_data)

        # Verify file was created and contains correct data
        assert cache_file.exists()
        with cache_file.open(encoding="utf-8") as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data


class TestFileHash:
    """Test file hashing"""

    def test_get_file_hash(self, temp_dir):
        """Test file hash calculation"""
        test_file = temp_dir / "test.txt"
        test_content = b"Hello, World! This is test content for hashing."
        test_file.write_bytes(test_content)

        hash1 = get_file_hash(test_file)
        hash2 = get_file_hash(test_file)

        # Same file should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 8  # SHA256 truncated to 8 chars

    def test_get_file_hash_different_content(self, temp_dir):
        """Test different files produce different hashes"""
        file1 = temp_dir / "file1.txt"
        file2 = temp_dir / "file2.txt"

        file1.write_bytes(b"Content 1")
        file2.write_bytes(b"Content 2")

        hash1 = get_file_hash(file1)
        hash2 = get_file_hash(file2)

        assert hash1 != hash2


class TestFilenameOperations:
    """Test filename operations"""

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Normal filename should remain unchanged
        assert sanitize_filename("normal_file.pdf") == "normal_file.pdf"

        # Special characters should be replaced with underscores
        assert sanitize_filename("file:with*chars?.pdf") == "file_with_chars_.pdf"

        # Spaces should be replaced with underscores
        assert sanitize_filename("file with spaces.pdf") == "file_with_spaces.pdf"

    def test_sanitize_filename_empty(self):
        """Test filename sanitization with empty string"""
        assert sanitize_filename("") == "unnamed"

    def test_get_unique_filename_no_conflict(self, temp_dir):
        """Test unique filename when no conflict exists"""
        directory = temp_dir / "test_dir"
        directory.mkdir()

        filename = get_unique_filename(directory, "test", ".txt")
        assert filename == "test.txt"

    def test_get_unique_filename_with_conflict(self, temp_dir):
        """Test unique filename when conflict exists"""
        directory = temp_dir / "test_dir"
        directory.mkdir()

        # Create existing file
        existing_file = directory / "test.txt"
        existing_file.write_text("existing content")

        filename = get_unique_filename(directory, "test", ".txt")
        assert filename == "test_1.txt"

    def test_get_unique_filename_multiple_conflicts(self, temp_dir):
        """Test unique filename with multiple conflicts"""
        directory = temp_dir / "test_dir"
        directory.mkdir()

        # Create multiple existing files
        (directory / "test.txt").write_text("content 1")
        (directory / "test_1.txt").write_text("content 2")
        (directory / "test_2.txt").write_text("content 3")

        filename = get_unique_filename(directory, "test", ".txt")
        assert filename == "test_3.txt"


class TestFileReadWrite:
    """Test file read/write operations"""

    def test_read_text_file_exists(self, temp_dir):
        """Test reading existing text file"""
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!\nThis is a test file."
        test_file.write_text(test_content, encoding="utf-8")

        result = read_text_file(test_file)
        assert result == test_content

    def test_read_text_file_not_exists(self, temp_dir):
        """Test reading non-existing file"""
        nonexistent_file = temp_dir / "nonexistent.txt"
        result = read_text_file(nonexistent_file)
        assert result is None

    def test_read_text_file_encoding_error(self, temp_dir):
        """Test reading file with encoding error"""
        test_file = temp_dir / "test.txt"
        # Write some binary data that can't be decoded as UTF-8
        test_file.write_bytes(b"\xff\xfe\xfd")

        result = read_text_file(test_file, encoding="utf-8")
        assert result is None

    def test_write_text_file(self, temp_dir):
        """Test writing text file"""
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!\nThis is test content."

        success = write_text_file(test_file, test_content)
        assert success is True
        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == test_content

    def test_write_text_file_creates_directory(self, temp_dir):
        """Test writing text file creates parent directory"""
        test_file = temp_dir / "subdir" / "nested" / "test.txt"
        test_content = "Test content"

        success = write_text_file(test_file, test_content)
        assert success is True
        assert test_file.exists()
        assert test_file.parent.exists()
        assert test_file.read_text(encoding="utf-8") == test_content


class TestFileCopy:
    """Test file copy operations"""

    def test_copy_file_success(self, temp_dir):
        """Test successful file copy"""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "destination.txt"

        test_content = "Test content for copying"
        src_file.write_text(test_content, encoding="utf-8")

        success = copy_file(src_file, dst_file)
        assert success is True
        assert dst_file.exists()
        assert dst_file.read_text(encoding="utf-8") == test_content

    def test_copy_file_creates_directory(self, temp_dir):
        """Test file copy creates destination directory"""
        src_file = temp_dir / "source.txt"
        dst_file = temp_dir / "subdir" / "destination.txt"

        test_content = "Test content for copying"
        src_file.write_text(test_content, encoding="utf-8")

        success = copy_file(src_file, dst_file)
        assert success is True
        assert dst_file.exists()
        assert dst_file.parent.exists()
        assert dst_file.read_text(encoding="utf-8") == test_content

    def test_copy_file_nonexistent_source(self, temp_dir):
        """Test copying non-existing source file"""
        nonexistent_src = temp_dir / "nonexistent.txt"
        dst_file = temp_dir / "destination.txt"

        success = copy_file(nonexistent_src, dst_file)
        assert success is False
        assert not dst_file.exists()
