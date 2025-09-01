"""
Configuration management module
"""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Paper2MD configuration class"""

    # Basic settings
    output_dir: str = "./papers"
    cache_dir: str = "./cache"

    # Image processing settings
    image_mode: str = "placeholder"  # "placeholder" | "vlm"

    # BibTeX settings
    bibtex_only: bool = False
    bibtex_enhanced: bool = False
    bibtex_clean: bool = False

    # Folder management settings
    create_folders: bool = True
    folder_template: str = "{title}"

    # Operation settings
    verbose: bool = False
    interactive: bool = True
    no_interactive: bool = False
    skip_pdf: bool = False

    # BibTeX key generation settings
    bibtex_key_style: str = "google"  # "google" | "standard"

    # Google Scholar settings
    scholar_wait_min: float = 0.5
    scholar_wait_max: float = 1.0
    scholar_headless: bool = True

    # DOI enrichment settings
    doi_timeout: int = 20
    doi_rate_limit: float = 0.2

    def __post_init__(self):
        """Validate and initialize settings"""

        self.output_dir = Path(self.output_dir)
        self.cache_dir = Path(self.cache_dir)


        if self.image_mode not in ["placeholder", "vlm"]:
            msg = f"Invalid image_mode: {self.image_mode}"
            raise ValueError(msg)


        if self.bibtex_key_style not in ["google", "standard"]:
            msg = f"Invalid bibtex_key_style: {self.bibtex_key_style}"
            raise ValueError(msg)

    @property
    def cache_file(self) -> Path:
        """Cache file path"""
        return self.cache_dir / ".bib_cache.json"

    @property
    def artifacts_dir_name(self) -> str:
        """Artifacts directory name"""
        return "artifacts"

    def get_folder_name(self, title: str) -> str:
        """Create folder name from title"""
        if not title:
            return "untitled"

        # Remove special characters and convert spaces to underscores
        clean_title = re.sub(r"[^\w\s-]", "", title)
        clean_title = re.sub(r"\s+", "_", clean_title.strip())

        # Apply template
        return self.folder_template.format(title=clean_title[:50])  # 길이 제한
