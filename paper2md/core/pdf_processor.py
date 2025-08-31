"""
PDF 처리 및 Docling 통합 모듈
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

from ..utils.config import Config
from ..utils.file_utils import ensure_directory, get_file_hash, sanitize_filename


@dataclass
class PDFMetadata:
    """PDF 메타데이터"""
    title: Optional[str] = None
    authors: List[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []


class PDFProcessor:
    """PDF 처리 클래스"""

    def __init__(self, config: Config):
        self.config = config
        self.docling_processor = None
        self._init_docling()

    def _init_docling(self):
        """Docling 프로세서 초기화"""
        try:
            from docling.document_converter import DocumentConverter
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

            # PDF 파이프라인 옵션 설정
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True  # OCR 활성화
            pipeline_options.do_table_structure = True  # 표 구조 인식

            # 문서 변환기 생성
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

    def extract_title(self, pdf_path: Path) -> Optional[str]:
        """PDF에서 제목 추출"""
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
                        r'^([A-Z][^.!?\n]{20,80})[.!?\n]',
                        r'^(.+)\n={3,}',
                        r'^(.+)\n-{3,}',
                    ]

                    lines = text.split('\n')
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

        title = re.sub(r'([a-z])([A-Z])', r'\1 \2', stem)
        title = re.sub(r'_+', ' ', title)
        title = title.replace('-', ' ')

        return title.strip() if title.strip() else None

    def extract_metadata(self, pdf_path: Path) -> PDFMetadata:
        """PDF에서 메타데이터 추출 - 개선된 버전"""
        metadata = PDFMetadata()

        try:
            import fitz

            with fitz.open(pdf_path) as doc:
                pdf_metadata = doc.metadata

                # 기본 메타데이터 추출
                metadata.title = pdf_metadata.get("title", "").strip() or self.extract_title(pdf_path)
                metadata.year = self._extract_year_from_metadata(pdf_metadata)

                # DOI 추출 시도
                metadata.doi = self._extract_doi_from_pdf(doc)

                # 초록 추출 시도
                metadata.abstract = self._extract_abstract_from_pdf(doc)

                # 저자 정보 추출 시도
                metadata.authors = self._extract_authors_from_pdf(doc)

                # 키워드 추출 시도
                metadata.keywords = self._extract_keywords_from_pdf(doc)

        except Exception:
            pass

        return metadata

    def _extract_year_from_metadata(self, pdf_metadata: Dict[str, Any]) -> Optional[int]:
        """메타데이터에서 연도 추출"""

        date_fields = ["creationDate", "modDate", "producer"]

        for field in date_fields:
            value = pdf_metadata.get(field, "")
            if value:

                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', str(value))
                if year_match:
                    return int(year_match.group(1))

        return None

    def _extract_doi_from_pdf(self, doc) -> Optional[str]:
        """PDF에서 DOI 추출"""
        doi_pattern = r'\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b'

        # 첫 몇 페이지에서 DOI 검색
        for page_num in range(min(5, len(doc))):
            page = doc[page_num]
            text = page.get_text()

            match = re.search(doi_pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).lower()

        return None

    def _extract_abstract_from_pdf(self, doc) -> Optional[str]:
        """PDF에서 초록 추출"""

        if len(doc) > 0:
            page = doc[0]
            text = page.get_text()


            abstract_patterns = [
                r'Abstract\s*\n(.*?)(?:\n\n|\n[A-Z][a-z]+|\n\d+\.)',
                r'ABSTRACT\s*\n(.*?)(?:\n\n|\n[A-Z][a-z]+|\n\d+\.)',
                r'Summary\s*\n(.*?)(?:\n\n|\n[A-Z][a-z]+|\n\d+\.)',
            ]

            for pattern in abstract_patterns:
                match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                if match:
                    abstract = match.group(1).strip()
                    if len(abstract) > 50:
                        return abstract

        return None

    def _extract_authors_from_pdf(self, doc) -> List[str]:
        """PDF에서 저자 정보 추출"""
        authors = []

        try:
            # 첫 페이지에서 저자 정보 찾기
            if len(doc) > 0:
                page = doc[0]
                text = page.get_text()

                # 일반적인 저자 패턴들
                author_patterns = [
                    r'Authors?:\s*([^\n]+)',
                    r'By\s+([^\n]+)',
                    r'Written by\s+([^\n]+)',
                    r'^([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+)*)\s*\n',
                ]

                for pattern in author_patterns:
                    match = re.search(pattern, text, re.MULTILINE)
                    if match:
                        author_text = match.group(1).strip()
                        # 콤마나 "and"로 구분된 저자들 분리
                        if ',' in author_text:
                            authors = [a.strip() for a in author_text.split(',') if a.strip()]
                        elif ' and ' in author_text:
                            authors = [a.strip() for a in author_text.split(' and ') if a.strip()]
                        else:
                            authors = [author_text]

                        # 너무 많은 저자는 제외 (논문이 아닌 경우)
                        if len(authors) <= 10:
                            break

        except Exception:
            pass

        return authors

    def _extract_keywords_from_pdf(self, doc) -> List[str]:
        """PDF에서 키워드 추출"""
        keywords = []

        try:

            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                text = page.get_text()


                keyword_patterns = [
                    r'Keywords?:\s*([^\n]+)',
                    r'Key words?:\s*([^\n]+)',
                    r'Subject classifications?:\s*([^\n]+)',
                ]

                for pattern in keyword_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        keyword_text = match.group(1).strip()

                        if ',' in keyword_text:
                            keywords = [k.strip() for k in keyword_text.split(',') if k.strip()]
                        elif ';' in keyword_text:
                            keywords = [k.strip() for k in keyword_text.split(';') if k.strip()]
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
    ) -> Tuple[str, List[Path]]:
        """
        PDF를 Markdown으로 변환

        Args:
            pdf_path: 입력 PDF 파일 경로
            output_dir: 출력 디렉토리
            image_mode: 이미지 처리 모드 ("placeholder" | "vlm")

        Returns:
            변환된 Markdown 텍스트와 추출된 이미지 파일들의 경로 리스트
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
    ) -> List[Path]:
        """플레이스홀더 모드로 이미지 처리"""
        image_paths = []
        artifacts_dir = output_dir / self.config.artifacts_dir_name
        ensure_directory(artifacts_dir)

        try:
            # Docling 결과에서 이미지 추출 및 저장
            for item in docling_result.document.body.content:
                if hasattr(item, 'image') and item.image:
                    # 이미지 해시 기반 파일명 생성
                    image_hash = get_file_hash_from_bytes(item.image.get_image())
                    image_filename = f"image_{image_hash}.png"
                    image_path = artifacts_dir / image_filename

                    # 이미지 저장
                    with open(image_path, "wb") as f:
                        f.write(item.image.get_image())

                    image_paths.append(image_path)

        except Exception:
            pass  # 이미지 처리 실패는 무시

        return image_paths

    def _process_images_vlm(
        self,
        docling_result,
        output_dir: Path
    ) -> List[Path]:
        """VLM 모드로 이미지 처리 (미래 구현)"""


        return self._process_images_placeholder(docling_result, output_dir)

    def _enhance_markdown_placeholder(
        self,
        markdown_text: str,
        docling_result
    ) -> str:
        """플레이스홀더 모드로 마크다운 개선"""
        # 이미지 플레이스홀더로 교체
        enhanced_text = markdown_text

        # 기본적인 텍스트 개선
        enhanced_text = self._clean_markdown_formatting(enhanced_text)

        return enhanced_text

    def _enhance_markdown_with_vlm(
        self,
        markdown_text: str,
        docling_result
    ) -> str:
        """VLM으로 마크다운 개선 (미래 구현)"""

        return self._enhance_markdown_placeholder(markdown_text, docling_result)

    def _clean_markdown_formatting(self, text: str) -> str:
        """마크다운 포맷 정리"""
        # 연속된 빈 줄 정리
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 불필요한 공백 정리
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            # 줄 끝 공백 제거
            line = line.rstrip()
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _add_metadata_frontmatter(
        self,
        markdown_text: str,
        metadata: PDFMetadata
    ) -> str:
        """YAML front matter 추가"""
        frontmatter_lines = ["---"]

        if metadata.title:
            frontmatter_lines.append(f"title: \"{metadata.title}\"")
        if metadata.authors:
            authors_str = ", ".join(f"\"{author}\"" for author in metadata.authors)
            frontmatter_lines.append(f"authors: [{authors_str}]")
        if metadata.year:
            frontmatter_lines.append(f"year: {metadata.year}")
        if metadata.doi:
            frontmatter_lines.append(f"doi: \"{metadata.doi}\"")
        if metadata.keywords:
            keywords_str = ", ".join(f"\"{kw}\"" for kw in metadata.keywords)
            frontmatter_lines.append(f"keywords: [{keywords_str}]")

        frontmatter_lines.append("---")
        frontmatter_lines.append("")

        return "\n".join(frontmatter_lines) + markdown_text


def get_file_hash_from_bytes(data: bytes) -> str:
    """바이트 데이터의 해시값 계산"""
    import hashlib
    return hashlib.md5(data).hexdigest()[:8]
