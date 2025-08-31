"""
설정 관리 모듈
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Paper2MD 설정 클래스"""

    # 기본 설정
    output_dir: str = "./papers"
    cache_dir: str = "./cache"

    # 이미지 처리 설정
    image_mode: str = "placeholder"  # "placeholder" | "vlm"

    # BibTeX 설정
    bibtex_only: bool = False
    bibtex_enhanced: bool = False
    bibtex_clean: bool = False

    # 폴더 관리 설정
    create_folders: bool = True
    folder_template: str = "{title}"

    # 동작 설정
    verbose: bool = False
    interactive: bool = True
    no_interactive: bool = False
    skip_pdf: bool = False

    # BibTeX 키 생성 설정
    bibtex_key_style: str = "google"  # "google" | "standard"

    # Google Scholar 설정
    scholar_wait_min: float = 0.5
    scholar_wait_max: float = 1.0
    scholar_headless: bool = True

    # DOI 보강 설정
    doi_timeout: int = 20
    doi_rate_limit: float = 0.2

    def __post_init__(self):
        """설정 검증 및 초기화"""

        self.output_dir = Path(self.output_dir)
        self.cache_dir = Path(self.cache_dir)


        if self.image_mode not in ["placeholder", "vlm"]:
            raise ValueError(f"Invalid image_mode: {self.image_mode}")


        if self.bibtex_key_style not in ["google", "standard"]:
            raise ValueError(f"Invalid bibtex_key_style: {self.bibtex_key_style}")

    @property
    def cache_file(self) -> Path:
        """캐시 파일 경로"""
        return self.cache_dir / ".bib_cache.json"

    @property
    def artifacts_dir_name(self) -> str:
        """아티팩트 디렉토리명"""
        return "artifacts"

    def get_folder_name(self, title: str) -> str:
        """제목으로부터 폴더명 생성"""
        if not title:
            return "untitled"

        # 특수문자 제거 및 공백을 언더스코어로 변환
        import re
        clean_title = re.sub(r'[^\w\s-]', '', title)
        clean_title = re.sub(r'\s+', '_', clean_title.strip())

        # 템플릿 적용
        return self.folder_template.format(title=clean_title[:50])  # 길이 제한
