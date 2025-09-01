"""
Test FolderManager - TDD approach
Tests for PDF title-based automatic folder creation system
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from paperef.core.folder_manager import FolderManager


class TestFolderManager:
    """Test cases for FolderManager class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def folder_manager(self):
        """Create FolderManager instance"""
        return FolderManager()

    def test_create_paper_folder_normal_title(self, folder_manager, temp_dir):
        """Test folder creation with normal paper title"""
        title = "UTAP: Unique Topologies for Acoustic Propagation"
        expected_name = "UTAP_Unique_Topologies_for_Acoustic_Propagation"

        result_path = folder_manager.create_paper_folder(title, temp_dir)

        assert result_path.name == expected_name
        assert result_path.exists()
        assert result_path.is_dir()
        assert result_path.parent == temp_dir

    def test_create_paper_folder_special_chars(self, folder_manager, temp_dir):
        """Test folder creation with special characters in title"""
        title = "M.Sketch: Augmenting Sketching Tools with Interactive Machine Learning?"
        expected_name = "M_Sketch_Augmenting_Sketching_Tools_with_Interactive_Machine_Learning"

        result_path = folder_manager.create_paper_folder(title, temp_dir)

        assert result_path.name == expected_name
        assert result_path.exists()

    def test_create_paper_folder_empty_title(self, folder_manager, temp_dir):
        """Test folder creation with empty title"""
        title = ""
        expected_name = "untitled"

        result_path = folder_manager.create_paper_folder(title, temp_dir)

        assert result_path.name == expected_name
        assert result_path.exists()

    def test_create_paper_folder_whitespace_title(self, folder_manager, temp_dir):
        """Test folder creation with whitespace-only title"""
        title = "   \n\t  "
        expected_name = "untitled"

        result_path = folder_manager.create_paper_folder(title, temp_dir)

        assert result_path.name == expected_name
        assert result_path.exists()

    def test_create_paper_folder_long_title(self, folder_manager, temp_dir):
        """Test folder creation with very long title"""
        title = ("A Very Long Paper Title That Exceeds The Normal Length Limit And "
                 "Should Be Truncated Accordingly In The Folder Name Generation Process")
        result_path = folder_manager.create_paper_folder(title, temp_dir)

        # Should be truncated to reasonable length
        assert len(result_path.name) <= 80  # Reasonable max length
        assert result_path.exists()

    def test_create_paper_folder_duplicate_names(self, folder_manager, temp_dir):
        """Test folder creation with duplicate names"""
        title = "Test Paper Title"

        # Create first folder
        path1 = folder_manager.create_paper_folder(title, temp_dir)
        assert path1.name == "Test_Paper_Title"

        # Create second folder with same title
        path2 = folder_manager.create_paper_folder(title, temp_dir)
        assert path2.name == "Test_Paper_Title_1"

        # Create third folder
        path3 = folder_manager.create_paper_folder(title, temp_dir)
        assert path3.name == "Test_Paper_Title_2"

        # All should exist and be different
        assert path1.exists()
        assert path2.exists()
        assert path3.exists()
        assert path1 != path2 != path3

    def test_create_paper_folder_unicode_chars(self, folder_manager, temp_dir):
        """Test folder creation with Unicode characters"""
        title = "Übermensch: A Study in Human-AI Interaction"
        expected_name = "Ubermensch_A_Study_in_Human_AI_Interaction"

        result_path = folder_manager.create_paper_folder(title, temp_dir)

        assert result_path.name == expected_name
        assert result_path.exists()

    def test_create_paper_folder_multiple_colons(self, folder_manager, temp_dir):
        """Test folder creation with multiple colons"""
        title = "Paper: Subtitle: Another Subtitle"
        expected_name = "Paper_Subtitle_Another_Subtitle"

        result_path = folder_manager.create_paper_folder(title, temp_dir)

        assert result_path.name == expected_name
        assert result_path.exists()

    def test_get_folder_structure_empty_folder(self, folder_manager, temp_dir):
        """Test getting folder structure for empty folder"""
        paper_dir = temp_dir / "test_paper"
        paper_dir.mkdir()

        structure = folder_manager.get_folder_structure(paper_dir)

        expected = {
            "paper_dir": paper_dir,
            "paper_md": None,
            "paper_bib": None,
            "references_dir": None,
            "artifacts_dir": None,
            "exists": True
        }
        assert structure == expected

    def test_get_folder_structure_complete_folder(self, folder_manager, temp_dir):
        """Test getting folder structure for complete paper folder"""
        paper_dir = temp_dir / "test_paper"
        paper_dir.mkdir()

        # Create typical folder structure
        (paper_dir / "paper.md").write_text("# Test")
        (paper_dir / "paper.bib").write_text("@article{test}")
        (paper_dir / "references").mkdir()
        (paper_dir / "artifacts").mkdir()

        structure = folder_manager.get_folder_structure(paper_dir)

        assert structure["paper_dir"] == paper_dir
        assert structure["paper_md"] == paper_dir / "paper.md"
        assert structure["paper_bib"] == paper_dir / "paper.bib"
        assert structure["references_dir"] == paper_dir / "references"
        assert structure["artifacts_dir"] == paper_dir / "artifacts"
        assert structure["exists"] is True

    def test_get_folder_structure_nonexistent_folder(self, folder_manager, temp_dir):
        """Test getting folder structure for nonexistent folder"""
        nonexistent_dir = temp_dir / "nonexistent"

        structure = folder_manager.get_folder_structure(nonexistent_dir)

        expected = {
            "paper_dir": nonexistent_dir,
            "paper_md": None,
            "paper_bib": None,
            "references_dir": None,
            "artifacts_dir": None,
            "exists": False
        }
        assert structure == expected

    def test_cleanup_empty_folders(self, folder_manager, temp_dir):
        """Test cleanup of empty folders"""
        # Create some folders
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        nested_empty = empty_dir / "nested_empty"
        nested_empty.mkdir()

        # Create folder with file
        has_file_dir = temp_dir / "has_file"
        has_file_dir.mkdir()
        (has_file_dir / "file.txt").write_text("content")

        # Cleanup empty folders
        folder_manager.cleanup_empty_folders(temp_dir)

        # Empty directories should be removed
        assert not empty_dir.exists()
        assert not nested_empty.exists()

        # Directory with file should remain
        assert has_file_dir.exists()
        assert (has_file_dir / "file.txt").exists()

    def test_cleanup_empty_folders_nested(self, folder_manager, temp_dir):
        """Test cleanup of nested empty folders"""
        # Create nested empty structure
        level1 = temp_dir / "level1"
        level2 = level1 / "level2"
        level3 = level2 / "level3"

        level3.mkdir(parents=True)

        folder_manager.cleanup_empty_folders(temp_dir)

        # All empty directories should be removed
        assert not level1.exists()
        assert not level2.exists()
        assert not level3.exists()

    def test_create_paper_folder_output_dir_creation(self, folder_manager, temp_dir):
        """Test that output directory is created if it doesn't exist"""
        output_dir = temp_dir / "new_output_dir" / "papers"
        title = "Test Paper"

        result_path = folder_manager.create_paper_folder(title, output_dir)

        assert output_dir.exists()
        assert result_path.parent == output_dir
        assert result_path.exists()

    @patch("pathlib.Path.mkdir")
    def test_create_paper_folder_permission_error(self, mock_mkdir, folder_manager, temp_dir):
        """Test handling of permission errors during folder creation"""
        mock_mkdir.side_effect = PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            folder_manager.create_paper_folder("Test", temp_dir)

    @pytest.mark.parametrize(("input_title", "expected_name"), [
        ("Normal Title", "Normal_Title"),
        ("Title with-dashes", "Title_with_dashes"),
        ("Title.with.dots", "Title_with_dots"),
        ("Title (with parentheses)", "Title_(with_parentheses)"),
        ("Title [with brackets]", "Title_[with_brackets]"),
        ("Title/with/slashes", "Title_with_slashes"),
        ("Title|with|pipes", "Title_with_pipes"),
        ("Title*with*asterisks", "Title_with_asterisks"),
        ("Title?with?questions", "Title_with_questions"),
        ("Title<with>angles", "Title_with_angles"),
        ("Title:with:colons", "Title_with_colons"),
        ('Title"with"quotes', "Title_with_quotes"),
        ("Title'with'apostrophes", "Title_with_apostrophes"),
        ("   Title with spaces   ", "Title_with_spaces"),
        ("Title\nwith\nnewlines", "Title_with_newlines"),
        ("Title\twith\ttabs", "Title_with_tabs"),
    ])
    def test_folder_name_validation(self, folder_manager, tmp_path, input_title, expected_name):
        """Test folder name validation and sanitization"""
        result_path = folder_manager.create_paper_folder(input_title, tmp_path)
        assert result_path.name == expected_name
