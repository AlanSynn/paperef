"""
Test DOIEnricher - TDD approach
Tests for DOI enrichment system and BibTeX field optimization
"""

from unittest.mock import Mock, patch

import pytest

from paperef.core.doi_enricher import BibTeXFieldOptimizer, DOIEnricher


class TestDOIEnricher:
    """Test cases for DOIEnricher class"""

    @pytest.fixture
    def doi_enricher(self):
        """Create DOIEnricher instance"""
        return DOIEnricher()

    def test_init(self, doi_enricher):
        """Test DOIEnricher initialization"""
        assert doi_enricher is not None
        assert hasattr(doi_enricher, "enrich_bibtex")
        assert hasattr(doi_enricher, "search_doi")
        assert hasattr(doi_enricher, "update_publisher_address")

    def test_search_doi_by_title_success(self, doi_enricher):
        """Test DOI search by title - successful case"""
        # Mock the API response
        mock_response = {
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

        with patch.object(doi_enricher.session, "get") as mock_get:
            mock_resp = Mock()
            mock_resp.json.return_value = mock_response
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            result = doi_enricher.search_doi("Test Paper Title", ["John Doe"], 2023)

            assert result == "10.1145/example.doi"
            mock_get.assert_called()

    def test_search_doi_by_title_no_results(self, doi_enricher):
        """Test DOI search by title - no results"""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"message": []}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = doi_enricher.search_doi("Nonexistent Paper", [], None)

            assert result is None

    def test_search_doi_by_title_api_error(self, doi_enricher, mock_session):
        """Test DOI search by title - API error"""
        doi_enricher.session = mock_session

        # Mock API error
        mock_session.get.side_effect = Exception("API Error")

        result = doi_enricher.search_doi("Test Paper", [], None)

        assert result is None

    def test_search_doi_by_doi_direct(self, doi_enricher):
        """Test DOI search by existing DOI"""
        doi = "10.1145/example.doi"

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "message": {
                    "DOI": doi,
                    "title": ["Test Paper"],
                    "publisher": "ACM"
                }
            }
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = doi_enricher.search_doi("Test Paper", [], None, existing_doi=doi)

            assert result == doi

    def test_enrich_bibtex_with_doi(self, doi_enricher):
        """Test BibTeX enrichment with DOI"""
        bibtex_input = """@article{test2023,
  title={Test Paper},
  author={Doe, John},
  year={2023}
}"""

        # Mock DOI search
        with patch.object(doi_enricher, "search_doi") as mock_search:
            mock_search.return_value = "10.1145/example.doi"

            # Mock DOI metadata fetch
            mock_metadata = {
                "DOI": "10.1145/example.doi",
                "title": ["Test Paper"],
                "author": [{"given": "John", "family": "Doe"}],
                "published-print": {"date-parts": [[2023]]},
                "publisher": "ACM",
                "container-title": ["CHI Conference"],
                "volume": "25",
                "issue": "1",
                "page": "100-110"
            }

            with patch.object(doi_enricher, "_fetch_doi_metadata") as mock_fetch:
                mock_fetch.return_value = mock_metadata

                result = doi_enricher.enrich_bibtex(bibtex_input)

                # Check for enriched fields (allowing both formats)
                assert ("doi = {10.1145/example.doi}" in result or
                        "doi={10.1145/example.doi}" in result)
                assert ("publisher = {ACM}" in result or
                        "publisher={ACM}" in result)
                assert ("journal = {CHI Conference}" in result or
                        "journal={CHI Conference}" in result)
                assert ("volume = {25}" in result or
                        "volume={25}" in result)

    def test_enrich_bibtex_no_doi_found(self, doi_enricher):
        """Test BibTeX enrichment when no DOI is found"""
        bibtex_input = """@article{test2023,
  title={Test Paper},
  author={Doe, John},
  year={2023}
}"""

        with patch.object(doi_enricher, "search_doi") as mock_search:
            mock_search.return_value = None

            result = doi_enricher.enrich_bibtex(bibtex_input)

            # Should return BibTeX with proper formatting
            assert "@article{test2023," in result
            assert "title" in result or "title=" in result
            assert "author" in result or "author=" in result
            assert "year" in result or "year=" in result

    def test_update_publisher_address_known_publisher(self, doi_enricher):
        """Test publisher address update for known publisher"""
        bibtex_input = """@inproceedings{test2023,
  title={Test Paper},
  publisher={ACM}
}"""

        result = doi_enricher.update_publisher_address(bibtex_input)

        assert "address = {New York, NY, USA}" in result

    def test_update_publisher_address_unknown_publisher(self, doi_enricher):
        """Test publisher address update for unknown publisher"""
        bibtex_input = """@inproceedings{test2023,
  title={Test Paper},
  publisher={Unknown Publisher}
}"""

        result = doi_enricher.update_publisher_address(bibtex_input)

        # Should not add address for unknown publisher
        assert "address=" not in result

    def test_update_publisher_address_no_publisher(self, doi_enricher, sample_bibtex):
        """Test publisher address update when no publisher field"""
        result = doi_enricher.update_publisher_address(sample_bibtex)

        # Should format the BibTeX but not add publisher address
        assert "@article{test2023," in result
        assert "title" in result or "title=" in result
        assert "publisher" not in result

    def test_normalize_acm_pages(self, doi_enricher, sample_bibtex_acm_pages):
        """Test ACM-style page normalization"""
        result = doi_enricher._normalize_acm_pages(sample_bibtex_acm_pages)

        # Check for normalized fields (allowing both formats)
        assert ("articleno = {138}" in result or "articleno={138}" in result)
        assert ("numpages = {12}" in result or "numpages={12}" in result)
        assert "pages=" not in result

    def test_normalize_regular_pages(self, doi_enricher):
        """Test regular page format (should remain unchanged)"""
        bibtex_input = """@article{test2023,
      title={Test Paper},
      pages={100-110}
    }"""

        result = doi_enricher._normalize_acm_pages(bibtex_input)

        # Should preserve regular pages format
        assert ("pages = {100-110}" in result or "pages={100-110}" in result)
        assert "articleno=" not in result
        assert "numpages=" not in result


class TestBibTeXFieldOptimizer:
    """Test cases for BibTeXFieldOptimizer class"""

    @pytest.fixture
    def optimizer(self):
        """Create BibTeXFieldOptimizer instance"""
        return BibTeXFieldOptimizer()

    def test_init(self, optimizer):
        """Test BibTeXFieldOptimizer initialization"""
        assert optimizer is not None
        assert hasattr(optimizer, "optimize_entry")
        assert hasattr(optimizer, "clean_empty_fields")

    def test_clean_empty_fields(self, optimizer):
        """Test BibTeX field optimization"""
        bibtex_input = """@article{test2023,
  title={Test Paper},
  author={Doe, John},
  year={2023},
  note={Some note}
}"""

        result = optimizer.clean_empty_fields(bibtex_input)

        # Should keep all fields in proper format
        assert "title = {Test Paper}" in result or "title={Test Paper}" in result
        assert "author = {Doe, John}" in result or "author={Doe, John}" in result
        assert "note = {Some note}" in result or "note={Some note}" in result
        assert "year = {2023}" in result or "year={2023}" in result

    def test_optimize_entry_fields(self, optimizer):
        """Test field optimization for better BibTeX format"""
        bibtex_input = """@article{test2023,
  title={Test Paper},
  author={Doe, John},
  year={2023},
  journal={Journal Name},
  pages={100--110}
}"""

        result = optimizer.optimize_entry(bibtex_input)

        # Should maintain proper BibTeX format
        assert "@article{test2023," in result
        assert "}" in result
        assert "title = {Test Paper}" in result or "title={Test Paper}" in result

    def test_optimize_entry_with_missing_fields(self, optimizer, sample_bibtex):
        """Test optimization of BibTeX with missing required fields"""
        result = optimizer.optimize_entry(sample_bibtex)

        # Should identify and potentially add missing fields
        assert "@article{test2023," in result
        assert ("title = {Test Paper}" in result or "title={Test Paper}" in result)

    def test_validate_bibtex_format(self, optimizer):
        """Test BibTeX format validation"""
        valid_bibtex = """@article{test2023,
  title={Test Paper},
  author={Doe, John},
  year={2023}
}"""

        invalid_bibtex = """@article{test2023
  title={Test Paper}
  author={Doe, John}
  year={2023}
}"""

        assert optimizer._validate_bibtex_format(valid_bibtex) is True
        assert optimizer._validate_bibtex_format(invalid_bibtex) is False

    def test_escape_special_characters(self, optimizer, sample_bibtex_with_special_chars):
        """Test escaping special characters in BibTeX fields"""
        result = optimizer.optimize_entry(sample_bibtex_with_special_chars)

        # Should escape special characters
        assert ("title = {Paper \\& More}" in result or "title={Paper \\& More}" in result)
        assert ("abstract = {Some text with 100\\% success}" in result or
                "abstract={Some text with 100\\% success}" in result)
