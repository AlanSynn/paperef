"""
BibTeX generation and key creation module
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..bibtex.scholar_scraper import BibTeXScraper
from ..utils.config import Config
from ..utils.file_utils import load_cache, save_cache


@dataclass
class BibTeXEntry:
    """BibTeX entry"""
    key: str
    entry_type: str
    fields: dict[str, Any]
    raw_bibtex: str | None = None


class BibTeXGenerator:
    """BibTeX generation class"""

    def __init__(self, config: Config):
        self.config = config
        self.cache = load_cache(config.cache_file)
        self.bibtex_scraper = BibTeXScraper(config)

    def generate_from_pdf(self, pdf_path: Path, config: Config, output_dir: Path) -> str | None:
        """Generate BibTeX from PDF and save to file - enhanced metadata"""
        try:
            # Extract metadata from PDF
            from .pdf_processor import PDFProcessor
            processor = PDFProcessor(config)
            metadata = processor.extract_metadata(pdf_path)

            if not metadata.title:
                return None

            # Search BibTeX (OpenAlex first, Google Scholar fallback)
            bibtex = self._search_bibtex(metadata.title, metadata.year, metadata.doi)

            if bibtex:
                # Use complete BibTeX from OpenAlex
                bibtex_str = bibtex
            else:
                # Create and enhance BibTeX entry
                entry = self._create_enhanced_bibtex_entry(metadata)
                bibtex_str = self._format_enhanced_bibtex_entry(entry)

            # Save to paper.bib file
            paper_bib_path = output_dir / "paper.bib"
            with open(paper_bib_path, "w", encoding="utf-8") as f:
                f.write(bibtex_str)

            # Save cache
            self._save_to_cache()

            return bibtex_str

        except Exception as e:
            print(f"Error generating BibTeX for {pdf_path}: {e}")
            return None

    def generate_from_markdown_references(
        self,
        markdown_content: str,
        output_dir: Path,
        config: Config
    ) -> str:
        """Extract references from Markdown and create consolidated BibTeX file"""
        try:

            references = self._extract_references_from_markdown(markdown_content)

            if not references:
                print("No references found in markdown")
                return ""


            all_bibtex_entries = []

            for ref_text in references:
                try:

                    ref_data = self._parse_reference(ref_text)
                    if not ref_data.get("title"):
                        continue


                    bibtex = self._search_bibtex(
                        ref_data["title"],
                        ref_data.get("year"),
                        ref_data.get("doi")
                    )

                    if bibtex:

                        all_bibtex_entries.append(bibtex)
                    else:

                        bibtex_key = self.generate_bibtex_key_google_style(
                            ref_data.get("authors", ["Unknown"]),
                            ref_data.get("year"),
                            ref_data["title"]
                        )


                        entry = BibTeXEntry(
                            key=bibtex_key,
                            entry_type="article",
                            fields={
                                "title": ref_data["title"],
                                "year": str(ref_data["year"]) if ref_data.get("year") else "",
                            }
                        )


                        if ref_data.get("authors"):
                            entry.fields["author"] = " and ".join(ref_data["authors"])


                        bibtex_str = self._format_bibtex_entry(entry)
                        all_bibtex_entries.append(bibtex_str)

                except Exception as e:
                    print(f"Error processing reference: {ref_text[:50]}...: {e}")
                    continue


            self._save_to_cache()


            if all_bibtex_entries:
                references_file = output_dir / "references.bib"
                with open(references_file, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(all_bibtex_entries) + "\n")

                return str(references_file)

            return ""

        except Exception as e:
            print(f"Error generating BibTeX from references: {e}")
            return ""

    def _extract_references_from_markdown(self, markdown_content: str) -> list[str]:
        """Markdown에서 REFERENCES 섹션 추출 - 개선된 버전"""
        lines = markdown_content.split("\n")
        references = []
        in_references = False
        current_ref = []

        for line in lines:
            line = line.strip()

            # REFERENCES section start
            if line.lower() == "## references":
                in_references = True
                continue

            if in_references:
                if line.startswith("## ") and line.lower() != "## references":
                    # Next section starts
                    break
                if line.startswith("- "):
                    # Save previous reference (existing format)
                    if current_ref:
                        references.append("\n".join(current_ref))
                        current_ref = []
                    # Start new reference
                    current_ref = [line]
                elif not line and current_ref:
                    # Save previous reference when empty line encountered (improved part)
                    references.append("\n".join(current_ref))
                    current_ref = []
                elif current_ref and line:
                    # Continue reference content
                    current_ref.append(line)
                elif not current_ref and line and len(line) > 20:
                    # Start new reference (when first line does not start with -)
                    # If starts with author name and has appropriate length
                    if any(word.endswith(",") for word in line.split()[:3]):  # Detect author pattern
                        current_ref = [line]

        # Save last reference
        if current_ref:
            references.append("\n".join(current_ref))

        # Filter empty references
        references = [ref for ref in references if ref.strip() and len(ref.strip()) > 50]

        return references

    def _parse_reference(self, ref_text: str) -> dict[str, Any]:
        """Parse reference text - improved version"""
        ref_data = {
            "title": "",
            "authors": [],
            "year": None,
            "doi": None
        }


        clean_text = ref_text.lstrip("- ").strip()


        doi = self._extract_doi_from_reference(clean_text)
        if doi:
            ref_data["doi"] = doi


        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", clean_text)
        if year_match:
            ref_data["year"] = int(year_match.group(1))
            year_pos = year_match.start()


            authors_part = clean_text[:year_pos].strip()
            if authors_part:

                authors_part = re.sub(r"[.()]+$", "", authors_part).strip()


                authors = self._parse_authors(authors_part)
                ref_data["authors"] = authors


            after_year = clean_text[year_pos + 4:].strip()
            after_year = re.sub(r"^[.\s()]+", "", after_year)


            title = self._extract_title_from_reference(after_year)
            ref_data["title"] = title
        else:

            ref_data["title"] = clean_text

        return ref_data

    def _parse_authors(self, authors_text: str) -> list[str]:
        """Parse author text - improved version"""
        authors = []

        # Handle multiple separators: comma, "and", "&", "et al."
        authors_text = authors_text.replace("&", "and")

        # Handle "et al."
        if "et al." in authors_text.lower():
            authors_text = authors_text.lower().split("et al.")[0].strip()

        # Separate by "and"
        if " and " in authors_text:
            author_parts = [part.strip() for part in authors_text.split(" and ") if part.strip()]
        else:
            author_parts = [authors_text]

        # Process authors separated by commas in each part
        for part in author_parts:
            if "," in part:
                # When separated by commas (multiple authors)
                sub_authors = [sub.strip() for sub in part.split(",") if sub.strip()]
                for sub_author in sub_authors:
                    if sub_author:
                        authors.append(self._normalize_author_name(sub_author))
            # Single author
            elif part.strip():
                authors.append(self._normalize_author_name(part.strip()))

        return authors

    def _normalize_author_name(self, author: str) -> str:
        """Normalize author name - for BibTeX key creation"""
        author = author.strip()


        if "," in author:
            return author.split(",")[0].strip()

        name_parts = author.split()
        if len(name_parts) >= 2:

            return name_parts[-1]
        return author

    def _extract_title_from_reference(self, text: str) -> str:
        """Extract title from reference - improved version"""
        # Extract title from typical reference format
        # Example: "Title." journal name, pages, etc.

        # Find title enclosed in quotes
        title_match = re.search(r'["""]+([^"""]+)["""]+', text)
        if title_match:
            return title_match.group(1).strip()

        # Extract first sentence ending with period (.)
        sentences = re.split(r"\.\s+", text)
        if sentences and len(sentences[0]) > 10:  # If not too short
            title = sentences[0].strip()
            # Remove journal name patterns (e.g., "Journal name,")
            title = re.sub(r",\s+[A-Z][a-zA-Z\s]+,\s*$", "", title)
            return title

        # Extract title of reasonable length from entire text
        words = text.split()
        if len(words) <= 15:  # Short title
            return text.strip()
        # Limit to first 15 words
        return " ".join(words[:15]).strip()

    def _extract_doi_from_reference(self, text: str) -> str | None:
        """Extract DOI from reference text"""

        doi_patterns = [
            r"https?://doi\.org/([^\s]+)",
            r"doi:\s*([^\s]+)",
            r"DOI:\s*([^\s]+)",
            r"\b(10\.\d{4,9}/[^\s]+)\b"
        ]

        for pattern in doi_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                doi = match.group(1) if len(match.groups()) > 0 else match.group(0)

                doi = re.sub(r"^https?://doi\.org/", "", doi)

                doi = doi.replace("%2F", "/").replace("%3A", ":")
                return doi.strip()

        return None

        return ref_data

    def _create_bibtex_entry(self, metadata) -> BibTeXEntry:
        """Create BibTeX entry from metadata"""
        # Generate BibTeX key
        bibtex_key = self.generate_bibtex_key_google_style(
            metadata.authors or ["Unknown"],
            metadata.year,
            metadata.title or "Unknown Title"
        )

        # Set basic fields
        fields = {
            "title": metadata.title or "Unknown Title",
        }

        if metadata.authors:
            fields["author"] = " and ".join(metadata.authors)
        if metadata.year:
            fields["year"] = str(metadata.year)
        if metadata.doi:
            fields["doi"] = metadata.doi

        return BibTeXEntry(
            key=bibtex_key,
            entry_type="article",  # Default
            fields=fields
        )

    def generate_bibtex_key_google_style(
        self,
        authors: list[str],
        year: int | None,
        title: str
    ) -> str:
        """
        Google Scholar style BibTeX key generation
        Author last name + Year + First word of title (special chars removed)
        """
        # Extract first author last name
        first_author = ""
        if authors:
            author = authors[0].strip()
            # Handle "Last, First" format
            if "," in author:
                first_author = author.split(",")[0].strip().lower()
            else:
                # Handle "First Last" format
                name_parts = author.split()
                if len(name_parts) >= 2:
                    # Usually last name is the last part
                    first_author = name_parts[-1].lower()
                else:
                    first_author = author.lower()

            # Remove any remaining punctuation and spaces
            first_author = re.sub(r"[^a-z0-9]", "", first_author)
        else:
            first_author = "unknown"

        # Year processing
        year_str = str(year) if year else ""

        # Extract first meaningful word from title (remove brackets, colons, etc.)
        clean_title = re.sub(r"[():-]", " ", title).strip()
        title_words = re.findall(r"\b\w+\b", clean_title.lower())

        first_word = ""
        if title_words:
            first_word = title_words[0]
            # Remove special characters and normalize
            first_word = re.sub(r"[^a-z0-9]", "", first_word)
        else:
            first_word = "unknown"

        # Combine parts: AuthorLastName + Year + FirstWord
        key_parts = [first_author, year_str, first_word]
        bibtex_key = "".join(key_parts)

        # Ensure key is not empty
        if not bibtex_key:
            bibtex_key = "unknown"

        return bibtex_key

    def _create_enhanced_bibtex_entry(self, metadata) -> BibTeXEntry:
        """Create BibTeX entry with metadata - enhanced version"""

        authors = metadata.authors or ["Unknown"]
        bibtex_key = self.generate_bibtex_key_google_style(
            authors=authors,
            year=metadata.year,
            title=metadata.title
        )


        fields = {
            "title": metadata.title,
            "year": str(metadata.year) if metadata.year else "",
        }


        if metadata.authors:

            formatted_authors = []
            for author in metadata.authors:

                if "," in author:
                    formatted_authors.append(author)
                else:
                    name_parts = author.split()
                    if len(name_parts) >= 2:

                        first_name = " ".join(name_parts[:-1])
                        last_name = name_parts[-1]
                        formatted_authors.append(f"{last_name}, {first_name}")
                    else:
                        formatted_authors.append(author)

            fields["author"] = " and ".join(formatted_authors)


        if metadata.doi:
            fields["doi"] = metadata.doi


        if metadata.abstract and len(metadata.abstract) > 50:
            fields["abstract"] = metadata.abstract


        if metadata.keywords:
            fields["keywords"] = ", ".join(metadata.keywords)

        return BibTeXEntry(
            key=bibtex_key,
            entry_type="article",
            fields=fields
        )

    def _format_enhanced_bibtex_entry(self, entry: BibTeXEntry) -> str:
        """Format enhanced BibTeX entry"""
        lines = [f"@{entry.entry_type}{{{entry.key},"]

        for key, value in entry.fields.items():
            if value:  # Exclude empty values
                # Escape special characters in BibTeX
                escaped_value = str(value).replace("&", "\\&").replace("%", "\\%")
                lines.append(f"  {key}={{{escaped_value}}}")

        lines.append("}")

        return "\n".join(lines)

    def _search_bibtex(self, title: str, year: int | None, doi: str | None = None) -> str | None:
        """Search for BibTeX (OpenAlex first, Google Scholar fallback)"""
        if not title:
            return None


        cache_key = f"{title}::{year or ''}::{doi or ''}"
        if self.cache.get(cache_key):
            return self.cache[cache_key]

        try:

            bibtex = self.bibtex_scraper.search_paper(title, year, doi)

            if bibtex:

                self.cache[cache_key] = bibtex
                return bibtex

            self.cache[cache_key] = ""

        except Exception as e:
            print(f"Error searching BibTeX: {e}")

        return None

    def _update_entry_from_bibtex(self, entry: BibTeXEntry, bibtex: str):
        """Update entry from BibTeX"""
        try:
            import bibtexparser

            # Parse BibTeX
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            db = bibtexparser.loads(bibtex, parser)

            if db.entries:
                bibtex_entry = db.entries[0]

                # Update entry type
                entry.entry_type = bibtex_entry.get("ENTRYTYPE", "article")

                # Update fields (only if existing value is missing)
                for key, value in bibtex_entry.items():
                    if key not in ["ENTRYTYPE", "ID"] and key not in entry.fields:
                        entry.fields[key] = value

                # Update BibTeX key
                if bibtex_entry.get("ID"):
                    entry.key = bibtex_entry["ID"]

        except Exception as e:
            print(f"Error parsing BibTeX: {e}")

    def _enhance_with_doi(self, entry: BibTeXEntry):
        """Enhance metadata with DOI (future implementation)"""



    def _format_bibtex_entry(self, entry: BibTeXEntry) -> str:
        """Format BibTeX entry to string"""
        try:
            import bibtexparser

            # Format using bibtexparser
            bib_database = bibtexparser.bibdatabase.BibDatabase()
            bib_database.entries = [{
                **entry.fields,
                "ENTRYTYPE": entry.entry_type,
                "ID": entry.key
            }]

            writer = bibtexparser.bwriter.BibTexWriter()
            writer.indent = "  "

            return bibtexparser.dumps(bib_database, writer).strip()

        except ImportError:
            # Manual formatting if bibtexparser is not available
            lines = [f"@{entry.entry_type}{{{entry.key},"]

            for key, value in entry.fields.items():
                if isinstance(value, str):
                    # Handle BibTeX special characters
                    value = value.replace("{", "\\{").replace("}", "\\}")
                    lines.append(f"  {key}={{{value}}},")
                else:
                    lines.append(f"  {key}={{{value}}},")

            lines.append("}")

            return "\n".join(lines)

    def _save_to_cache(self):
        """Save cache"""
        save_cache(self.config.cache_file, self.cache)

    def close(self):
        """Clean up resources"""
        if self.bibtex_scraper:
            self.bibtex_scraper.close()
