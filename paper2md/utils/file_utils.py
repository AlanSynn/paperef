"""
파일 I/O 유틸리티 모듈
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


def ensure_directory(path: Path) -> None:
    """디렉토리가 존재하지 않으면 생성"""
    path.mkdir(parents=True, exist_ok=True)


def load_cache(cache_file: Path) -> Dict[str, Any]:
    """캐시 파일에서 데이터 로드"""
    if not cache_file.exists():
        return {}

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_cache(cache_file: Path, data: Dict[str, Any]) -> None:
    """데이터를 캐시 파일에 저장"""
    ensure_directory(cache_file.parent)

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError:
        pass  # 캐시 저장 실패는 무시


def get_file_hash(file_path: Path) -> str:
    """파일의 해시값 계산"""
    import hashlib

    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()[:8]


def sanitize_filename(filename: str) -> str:
    """파일명에서 안전하지 않은 문자 제거"""
    import re

    # 허용되는 문자: 알파벳, 숫자, 하이픈, 언더스코어, 점
    sanitized = re.sub(r'[^\w\.-]', '_', filename)

    # 연속된 언더스코어를 하나로 줄임
    sanitized = re.sub(r'_+', '_', sanitized)

    # 앞뒤 공백 및 언더스코어 제거
    sanitized = sanitized.strip('_ ')

    return sanitized or "unnamed"


def get_unique_filename(directory: Path, base_name: str, extension: str = "") -> str:
    """디렉토리 내에서 고유한 파일명 생성"""
    if extension and not extension.startswith('.'):
        extension = f".{extension}"

    counter = 1
    filename = f"{base_name}{extension}"

    while (directory / filename).exists():
        filename = f"{base_name}_{counter}{extension}"
        counter += 1

    return filename


def read_text_file(file_path: Path, encoding: str = "utf-8") -> Optional[str]:
    """텍스트 파일 읽기"""
    try:
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except (IOError, UnicodeDecodeError):
        return None


def write_text_file(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """텍스트 파일 쓰기"""
    try:
        ensure_directory(file_path.parent)
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except IOError:
        return False


def copy_file(src: Path, dst: Path) -> bool:
    """파일 복사"""
    try:
        ensure_directory(dst.parent)
        import shutil
        shutil.copy2(src, dst)
        return True
    except IOError:
        return False


def get_pdf_title(pdf_path: Path) -> Optional[str]:
    """PDF 파일에서 제목 메타데이터 추출"""
    try:
        import fitz

        with fitz.open(pdf_path) as doc:
            metadata = doc.metadata
            title = metadata.get("title", "").strip()


            if not title and len(doc) > 0:
                page = doc[0]
                text = page.get_text()


                lines = text.split('\n')
                for line in lines[:5]:
                    line = line.strip()
                    if len(line) > 10 and not line.isupper():
                        title = line
                        break

            return title if title else None

    except ImportError:

        return None
    except Exception:
        return None
