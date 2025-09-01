"""
Folder Manager Module
Handles PDF title-based automatic folder creation and management
"""

import contextlib
import re
import time
from pathlib import Path
from typing import Any


class FolderManager:
    """PDF 제목 기반 자동 폴더 생성 및 관리 클래스"""

    def __init__(self):
        """Initialize FolderManager"""
        self.max_folder_name_length = 80

    def create_paper_folder(self, title: str, output_dir: Path) -> Path:
        """
        PDF 제목으로부터 폴더를 생성하고 경로를 반환합니다.

        Args:
            title: PDF 논문 제목
            output_dir: 출력 기본 디렉토리

        Returns:
            생성된 폴더의 Path 객체
        """
        # 출력 디렉토리가 존재하지 않으면 생성
        output_dir.mkdir(parents=True, exist_ok=True)

        # 제목으로부터 폴더명 생성
        folder_name = self._generate_folder_name(title)

        # 중복 방지를 위한 최종 폴더명 생성
        final_folder_name = self._resolve_duplicate_name(folder_name, output_dir)

        # 폴더 생성
        paper_folder = output_dir / final_folder_name
        paper_folder.mkdir(exist_ok=True)

        return paper_folder

    def _generate_folder_name(self, title: str) -> str:
        """
        제목으로부터 안전한 폴더명을 생성합니다.

        Args:
            title: 원본 제목

        Returns:
            정리된 폴더명
        """
        # 빈 제목 처리
        if not title or not title.strip():
            return "untitled"

        # 제목 정리
        clean_title = title.strip()

        # 유니코드 정규화 및 ASCII 변환
        import unicodedata
        clean_title = unicodedata.normalize("NFKD", clean_title)
        clean_title = clean_title.encode("ASCII", "ignore").decode("ASCII")

        # 파일 시스템 안전하지 않은 문자들을 밑줄로 변환
        # Windows와 Unix 모두에서 문제되는 문자들 처리
        unsafe_chars = r'[<>:"/\\|?*\x00-\x1f\'"-]'
        clean_title = re.sub(unsafe_chars, "_", clean_title)

        # 마침표(.)를 밑줄로 변환 (파일 확장자 구분 방지)
        clean_title = clean_title.replace(".", "_")

        # 추가 정리: 여러 공백을 하나로, 공백을 밑줄로
        clean_title = re.sub(r"\s+", "_", clean_title)

        # 연속된 밑줄을 하나로 정리
        clean_title = re.sub(r"_+", "_", clean_title)

        # 앞뒤 밑줄 제거
        clean_title = clean_title.strip("_")

        # 빈 문자열이 된 경우 처리
        if not clean_title:
            return "untitled"

        # 길이 제한 적용
        if len(clean_title) > self.max_folder_name_length:
            clean_title = clean_title[:self.max_folder_name_length].rstrip("_")

        return clean_title

    def _resolve_duplicate_name(self, base_name: str, output_dir: Path) -> str:
        """
        중복된 폴더명이 있을 경우 번호를 붙여서 해결합니다.

        Args:
            base_name: 기본 폴더명
            output_dir: 출력 디렉토리

        Returns:
            중복 해결된 폴더명
        """
        candidate_name = base_name
        counter = 1

        while (output_dir / candidate_name).exists():
            candidate_name = f"{base_name}_{counter}"
            counter += 1

            # 무한 루프 방지 (1000번까지 시도)
            if counter > 1000:
                import uuid
                candidate_name = f"{base_name}_{uuid.uuid4().hex[:8]}"
                break

        return candidate_name

    def get_folder_structure(self, paper_dir: Path) -> dict[str, Any]:
        """
        폴더 구조 정보를 반환합니다.

        Args:
            paper_dir: 논문 폴더 경로

        Returns:
            폴더 구조 정보 딕셔너리
        """
        structure = {
            "paper_dir": paper_dir,
            "paper_md": None,
            "paper_bib": None,
            "references_dir": None,
            "artifacts_dir": None,
            "exists": paper_dir.exists()
        }

        if not paper_dir.exists():
            return structure

        # 파일들 확인
        paper_md = paper_dir / "paper.md"
        paper_bib = paper_dir / "paper.bib"
        references_dir = paper_dir / "references"
        artifacts_dir = paper_dir / "artifacts"

        if paper_md.exists():
            structure["paper_md"] = paper_md
        if paper_bib.exists():
            structure["paper_bib"] = paper_bib
        if references_dir.exists() and references_dir.is_dir():
            structure["references_dir"] = references_dir
        if artifacts_dir.exists() and artifacts_dir.is_dir():
            structure["artifacts_dir"] = artifacts_dir

        return structure

    def cleanup_empty_folders(self, base_dir: Path):
        """
        빈 폴더들을 정리합니다.

        Args:
            base_dir: 정리할 기본 디렉토리
        """
        if not base_dir.exists():
            return

        # 재귀적으로 모든 하위 디렉토리 확인
        for path in sorted(base_dir.rglob("*"), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                try:
                    path.rmdir()
                except OSError:
                    # 권한 문제 등으로 삭제 실패한 경우 무시
                    pass

    def validate_folder_name(self, name: str) -> bool:
        """
        폴더명이 유효한지 검증합니다.

        Args:
            name: 검증할 폴더명

        Returns:
            유효하면 True, 아니면 False
        """
        if not name or not name.strip():
            return False

        # 파일 시스템 안전하지 않은 문자들 확인
        unsafe_chars = r'[<>:"/\\|?*\x00-\x1f]'
        if re.search(unsafe_chars, name):
            return False

        # 예약어 확인 (Windows)
        reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
        }

        if name.upper() in reserved_names:
            return False

        # 길이 확인
        if len(name) > 255:  # 일반적인 파일 시스템 제한
            return False

        return True

    def ensure_paper_folder_structure(self, paper_dir: Path) -> dict:
        """
        논문 폴더의 표준 구조를 확인하고 필요한 경우 생성합니다.

        Args:
            paper_dir: 논문 폴더 경로

        Returns:
            생성된 폴더들의 정보 딕셔너리
        """
        created_items = {
            "directories": [],
            "files": []
        }

        # 표준 폴더 구조
        standard_dirs = [
            "artifacts",      # 이미지 파일들
            "references",     # BibTeX 참조 파일들
            "sources"         # 원본 파일들 (선택사항)
        ]

        # 표준 파일들
        standard_files = [
            "paper.md",       # 메인 Markdown 파일
            "paper.bib",      # 메인 BibTeX 파일
            "metadata.json",  # 메타데이터 파일
            "README.md"       # 폴더 설명 파일
        ]

        # 디렉토리 생성
        for dir_name in standard_dirs:
            dir_path = paper_dir / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                created_items["directories"].append(str(dir_path))

        # 기본 파일들 생성 (없는 경우에만)
        for file_name in standard_files:
            file_path = paper_dir / file_name
            if not file_path.exists():
                if file_name == "README.md":
                    self._create_default_readme(file_path)
                elif file_name == "metadata.json":
                    self._create_default_metadata(file_path)
                else:
                    # 다른 파일들은 빈 파일로 생성
                    file_path.touch()
                created_items["files"].append(str(file_path))

        return created_items

    def validate_paper_folder_structure(self, paper_dir: Path) -> dict:
        """
        논문 폴더 구조의 유효성을 검증합니다.

        Args:
            paper_dir: 검증할 논문 폴더

        Returns:
            검증 결과 딕셔너리
        """
        validation = {
            "is_valid": True,
            "issues": [],
            "recommendations": []
        }

        if not paper_dir.exists():
            validation["is_valid"] = False
            validation["issues"].append("Paper directory does not exist")
            return validation

        # 필수 파일들 확인
        required_files = ["paper.md", "paper.bib"]
        for file_name in required_files:
            file_path = paper_dir / file_name
            if not file_path.exists():
                validation["issues"].append(f"Missing required file: {file_name}")
                validation["is_valid"] = False

        # 권장 폴더들 확인
        recommended_dirs = ["artifacts", "references"]
        for dir_name in recommended_dirs:
            dir_path = paper_dir / dir_name
            if not dir_path.exists():
                validation["recommendations"].append(f"Consider creating directory: {dir_name}")

        # artifacts 폴더에 파일이 있는지 확인
        artifacts_dir = paper_dir / "artifacts"
        if artifacts_dir.exists():
            image_files = list(artifacts_dir.glob("*.png")) + list(artifacts_dir.glob("*.jpg"))
            if not image_files:
                validation["recommendations"].append("No image files found in artifacts directory")

        return validation

    def cleanup_incomplete_folders(self, base_dir: Path, min_files: int = 2) -> list[str]:
        """
        불완전한 논문 폴더들을 정리합니다.

        Args:
            base_dir: 정리할 기본 디렉토리
            min_files: 최소 요구 파일 수

        Returns:
            삭제된 폴더들의 목록
        """
        deleted_folders = []

        if not base_dir.exists():
            return deleted_folders

        # 모든 하위 폴더 확인
        for folder in base_dir.iterdir():
            if not folder.is_dir():
                continue

            # 폴더 내 파일 수 확인
            file_count = sum(1 for item in folder.rglob("*") if item.is_file())

            # 최소 파일 수 미만인 경우 삭제
            if file_count < min_files:
                try:
                    import shutil
                    shutil.rmtree(folder)
                    deleted_folders.append(str(folder))
                except Exception as e:
                    print(f"Error deleting folder {folder}: {e}")

        return deleted_folders

    def generate_folder_summary(self, paper_dir: Path) -> dict:
        """
        논문 폴더의 요약 정보를 생성합니다.

        Args:
            paper_dir: 논문 폴더 경로

        Returns:
            폴더 요약 정보
        """
        summary = {
            "folder_name": paper_dir.name,
            "total_size": 0,
            "file_count": 0,
            "image_count": 0,
            "bib_files": [],
            "has_markdown": False,
            "has_bibtex": False,
            "last_modified": None
        }

        if not paper_dir.exists():
            return summary

        # 폴더 내 모든 파일 분석
        for file_path in paper_dir.rglob("*"):
            if not file_path.is_file():
                continue

            summary["file_count"] += 1

            # 파일 크기 합산
            with contextlib.suppress(OSError):
                summary["total_size"] += file_path.stat().st_size

            # 파일 타입별 카운트
            if file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif"]:
                summary["image_count"] += 1

            if file_path.suffix.lower() == ".bib":
                summary["bib_files"].append(file_path.name)

            if file_path.name == "paper.md":
                summary["has_markdown"] = True

            if file_path.name == "paper.bib":
                summary["has_bibtex"] = True

            # 마지막 수정 시간 업데이트
            try:
                mtime = file_path.stat().st_mtime
                if summary["last_modified"] is None or mtime > summary["last_modified"]:
                    summary["last_modified"] = mtime
            except OSError:
                pass

        return summary

    def _create_default_readme(self, readme_path: Path) -> None:
        """기본 README 파일 생성"""
        content = f"""# {readme_path.parent.name}

This folder contains processed academic paper data.

## Contents
- `paper.md`: Main paper content in Markdown format
- `paper.bib`: Main paper BibTeX citation
- `artifacts/`: Images and figures extracted from the paper
- `references/`: BibTeX files for all references cited in the paper
- `metadata.json`: Extracted metadata and processing information

## Processing Information
- Processed by: PaperRef
- Processing date: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
        readme_path.write_text(content, encoding="utf-8")

    def _create_default_metadata(self, metadata_path: Path) -> None:
        """기본 메타데이터 파일 생성"""
        import json
        metadata = {
            "processing_tool": "PaperRef",
            "processing_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "0.1.0",
            "structure": {
                "paper_md": "Main paper in Markdown format",
                "paper_bib": "Main paper BibTeX citation",
                "artifacts": "Extracted images and figures",
                "references": "BibTeX files for citations"
            }
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
