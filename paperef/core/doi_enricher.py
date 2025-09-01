"""
DOI Enricher Module
Enhances BibTeX entries by finding DOIs and updating/normalizing fields
"""

import re
import time
from typing import Any

import requests


class DOIEnricher:
    """DOI 기반 BibTeX 보강 클래스"""

    def __init__(self, contact_email: str = "alansynn@gatech.edu"):
        """Initialize DOIEnricher"""
        self.contact_email = contact_email
        self.crossref_base = "https://api.crossref.org/works"
        self.openalex_base = "https://api.openalex.org/works"
        self.request_timeout = 20
        self.rate_limit_sleep = 0.2

        # Publisher 주소 매핑
        self.publisher_address = {
            "Association for Computing Machinery": "New York, NY, USA",
            "ACM": "New York, NY, USA",
            "IEEE": "Piscataway, NJ, USA",
            "Springer": "Cham, Switzerland",
            "Springer Nature": "Cham, Switzerland",
            "Elsevier": "Amsterdam, Netherlands",
            "PMLR": None,
            "Morgan & Claypool": "San Rafael, CA, USA",
            "MIT Press": "Cambridge, MA, USA",
            "Cambridge University Press": "Cambridge, UK",
            "Oxford University Press": "Oxford, UK",
            "Taylor & Francis": "Abingdon, UK",
            "Wiley": "Hoboken, NJ, USA",
        }

        # Venue to publisher mapping (축약된 버전)
        self.venue_to_publisher = {
            "chi": "ACM", "uist": "ACM", "cscw": "ACM", "ubicomp": "ACM",
            "siggraph": "ACM", "icml": "ACM", "neurips": "ACM",
            "icra": "IEEE", "iros": "IEEE", "rss": "IEEE",
        }

        # User-Agent 설정
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"Paper2MD/0.1.0 (https://github.com/alansynn/paperef; mailto:{contact_email})",
            "Accept": "application/json"
        })

    def enrich_bibtex(self, bibtex: str) -> str:
        """
        BibTeX 항목을 DOI로 보강합니다.

        Args:
            bibtex: 원본 BibTeX 문자열

        Returns:
            보강된 BibTeX 문자열
        """
        try:
            # BibTeX 파싱
            import bibtexparser
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            db = bibtexparser.loads(bibtex, parser)

            if not db.entries:
                return bibtex

            entry = db.entries[0]
            entry.get("ID", "")
            entry.get("ENTRYTYPE", "article")

            # DOI 검색
            title = entry.get("title", "").strip("{}")
            authors = self._extract_authors_from_entry(entry)
            year = entry.get("year", "").strip("{}")

            doi = entry.get("doi", "").strip("{}")
            if doi:
                # 기존 DOI가 있으면 검증 및 보강
                enriched_data = self._fetch_doi_metadata(doi)
            else:
                # DOI 검색
                doi = self.search_doi(title, authors, year)
                enriched_data = self._fetch_doi_metadata(doi) if doi else None

            # 메타데이터로 BibTeX 보강
            if enriched_data:
                self._update_entry_with_metadata(entry, enriched_data)

            # Publisher 주소 추가
            self._add_publisher_address(entry)

            # BibTeX 재생성 (일관된 형식)
            writer = bibtexparser.bwriter.BibTexWriter()
            writer.indent = "  "
            writer.align_values = False  # 값 정렬 비활성화로 일관성 유지

            # 새로운 BibTeX 생성
            new_db = bibtexparser.bibdatabase.BibDatabase()
            new_db.entries = [entry]

            return bibtexparser.dumps(new_db, writer).strip()

        except Exception as e:
            print(f"Error enriching BibTeX: {e}")
            return bibtex

    def search_doi(self, title: str, authors: list[str] | None = None, year: str | None = None,
                   existing_doi: str | None = None) -> str | None:
        """
        DOI를 검색합니다.

        Args:
            title: 논문 제목
            authors: 저자 목록
            year: 출판 연도
            existing_doi: 기존 DOI (검증용)

        Returns:
            찾은 DOI 또는 None
        """
        if existing_doi:
            # 기존 DOI 검증
            if self._validate_doi(existing_doi):
                return existing_doi

        # Crossref 검색
        try:
            doi = self._search_crossref(title, authors, year)
            if doi:
                return doi
        except Exception as e:
            print(f"Crossref search failed: {e}")

        # OpenAlex 검색 (fallback)
        try:
            doi = self._search_openalex(title, authors, year)
            if doi:
                return doi
        except Exception as e:
            print(f"OpenAlex search failed: {e}")

        return None

    def _search_crossref(self, title: str, authors: list[str] | None = None, year: str | None = None) -> str | None:
        """Crossref API에서 DOI 검색"""
        if not title:
            return None

        params = {
            "query.title": title,
            "rows": 5
        }

        if year:
            params["query.published"] = year

        time.sleep(self.rate_limit_sleep)

        response = self.session.get(
            f"{self.crossref_base}",
            params=params,
            timeout=self.request_timeout
        )
        response.raise_for_status()

        data = response.json()
        items = data.get("message", {}).get("items", [])

        if not items:
            return None

        # 가장 관련성 높은 결과 선택
        best_match = self._find_best_match(items, title, year)
        if best_match:
            return best_match.get("DOI")

        return None

    def _search_openalex(self, title: str, authors: list[str] | None = None, year: str | None = None) -> str | None:
        """OpenAlex API에서 DOI 검색"""
        if not title:
            return None

        params = {
            "search": title,
            "per_page": 5,
            "select": "id,title,authorships,publication_year,doi"
        }

        if year:
            params["filter"] = f"publication_year:{year}"

        time.sleep(self.rate_limit_sleep)

        response = self.session.get(
            f"{self.openalex_base}",
            params=params,
            timeout=self.request_timeout
        )
        response.raise_for_status()

        data = response.json()
        works = data.get("results", [])

        if not works:
            return None

        # 가장 관련성 높은 결과 선택
        best_match = self._find_best_match_openalex(works, title, year)
        if best_match:
            doi = best_match.get("doi", "").replace("https://doi.org/", "")
            return doi if doi else None

        return None

    def _find_best_match(self, items: list, target_title: str, target_year: str | None = None) -> dict | None:
        """Crossref 결과 중 가장 적합한 항목 찾기"""
        from difflib import SequenceMatcher

        best_item = None
        best_score = 0.0

        target_title_lower = target_title.lower()

        for item in items:
            item_title = item.get("title", [""])[0] if isinstance(item.get("title"), list) else item.get("title", "")
            item_title_lower = item_title.lower()

            # 제목 유사도 계산
            title_similarity = SequenceMatcher(None, target_title_lower, item_title_lower).ratio()

            # 연도 매칭 점수
            year_score = 0.0
            if target_year:
                item_year = str(item.get("published-print", {}).get("date-parts", [[None]])[0][0] or "")
                if item_year == target_year:
                    year_score = 1.0

            # 총점 계산
            score = title_similarity * 0.8 + year_score * 0.2

            if score > best_score and score > 0.6:  # 최소 유사도 threshold
                best_score = score
                best_item = item

        return best_item

    def _find_best_match_openalex(self, works: list, target_title: str, target_year: str | None = None) -> dict | None:
        """OpenAlex 결과 중 가장 적합한 항목 찾기"""
        from difflib import SequenceMatcher

        best_work = None
        best_score = 0.0

        target_title_lower = target_title.lower()

        for work in works:
            work_title = work.get("title", "").lower()

            # 제목 유사도 계산
            title_similarity = SequenceMatcher(None, target_title_lower, work_title).ratio()

            # 연도 매칭 점수
            year_score = 0.0
            if target_year:
                work_year = str(work.get("publication_year", ""))
                if work_year == target_year:
                    year_score = 1.0

            # 총점 계산
            score = title_similarity * 0.8 + year_score * 0.2

            if score > best_score and score > 0.6:
                best_score = score
                best_work = work

        return best_work

    def _fetch_doi_metadata(self, doi: str) -> dict[str, Any] | None:
        """DOI로부터 메타데이터 가져오기"""
        try:
            time.sleep(self.rate_limit_sleep)

            response = self.session.get(
                f"{self.crossref_base}/{doi}",
                timeout=self.request_timeout
            )
            response.raise_for_status()

            data = response.json()
            return data.get("message")

        except Exception as e:
            print(f"Error fetching DOI metadata for {doi}: {e}")
            return None

    def _update_entry_with_metadata(self, entry: dict, metadata: dict) -> None:
        """BibTeX entry를 메타데이터로 업데이트"""
        # DOI 추가
        if "DOI" in metadata and not entry.get("doi"):
            entry["doi"] = metadata["DOI"]

        # Publisher 추가
        if "publisher" in metadata and not entry.get("publisher"):
            entry["publisher"] = metadata["publisher"]

        # 저자 정보 보강
        if "author" in metadata and not entry.get("author"):
            authors = []
            for author in metadata["author"][:10]:  # 최대 10명
                given = author.get("given", "")
                family = author.get("family", "")
                if family and given:
                    authors.append(f"{family}, {given}")
                elif family:
                    authors.append(family)
                elif given:
                    authors.append(given)

            if authors:
                entry["author"] = " and ".join(authors)

        # 저널/컨퍼런스 정보
        if "container-title" in metadata and not entry.get("journal") and not entry.get("booktitle"):
            container = metadata["container-title"]
            if isinstance(container, list) and container:
                container = container[0]

            # BibTeX 타입에 따라 필드 결정
            entry_type = entry.get("ENTRYTYPE", "article")
            if entry_type == "article":
                entry["journal"] = container
            elif entry_type in ["inproceedings", "conference"]:
                entry["booktitle"] = container

        # 볼륨, 이슈, 페이지 정보
        if "volume" in metadata and not entry.get("volume"):
            entry["volume"] = str(metadata["volume"])

        if "issue" in metadata and not entry.get("issue"):
            entry["issue"] = str(metadata["issue"])

        if "page" in metadata and not entry.get("pages"):
            entry["pages"] = metadata["page"]

    def update_publisher_address(self, bibtex: str) -> str:
        """
        BibTeX에 publisher 주소 정보를 추가합니다.

        Args:
            bibtex: BibTeX 문자열

        Returns:
            주소 정보가 추가된 BibTeX 문자열
        """
        try:
            import bibtexparser
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            db = bibtexparser.loads(bibtex, parser)

            if not db.entries:
                return bibtex

            entry = db.entries[0]

            # Publisher 주소 추가
            self._add_publisher_address(entry)

            # BibTeX 재생성 (일관된 형식)
            writer = bibtexparser.bwriter.BibTexWriter()
            writer.indent = "  "
            writer.align_values = False

            new_db = bibtexparser.bibdatabase.BibDatabase()
            new_db.entries = [entry]

            return bibtexparser.dumps(new_db, writer).strip()

        except Exception as e:
            print(f"Error updating publisher address: {e}")
            return bibtex

    def _add_publisher_address(self, entry: dict) -> None:
        """BibTeX entry에 publisher 주소 추가"""
        publisher = entry.get("publisher", "").strip("{}")

        if not publisher or entry.get("address"):
            return

        # 직접 매핑
        address = self.publisher_address.get(publisher)
        if address:
            entry["address"] = address
            return

        # Venue 기반 매핑
        venue = entry.get("booktitle", "").strip("{}").lower()
        if venue:
            for venue_pattern, pub in self.venue_to_publisher.items():
                if venue_pattern in venue:
                    address = self.publisher_address.get(pub)
                    if address:
                        entry["address"] = address
                        entry["publisher"] = pub
                        break

    def _extract_authors_from_entry(self, entry: dict) -> list[str]:
        """BibTeX entry에서 저자 목록 추출"""
        author_str = entry.get("author", "")
        if not author_str:
            return []

        # " and "로 분리
        authors = [a.strip() for a in author_str.split(" and ") if a.strip()]

        # 각 저자의 이름 정리
        cleaned_authors = []
        for author in authors:
            # "Last, First" 형식에서 Last name만 추출
            if "," in author:
                last_name = author.split(",")[0].strip()
                cleaned_authors.append(last_name)
            else:
                # "First Last" 형식
                name_parts = author.split()
                if name_parts:
                    cleaned_authors.append(name_parts[-1])  # Last name

        return cleaned_authors

    def _validate_doi(self, doi: str) -> bool:
        """DOI 형식 검증"""
        doi_pattern = r"^10\.\d{4,9}/[-._;()/:\w]+$"
        return bool(re.match(doi_pattern, doi))

    def _normalize_acm_pages(self, bibtex: str) -> str:
        """
        ACM 스타일 페이지 (138:1--138:12)를 articleno와 numpages로 변환

        Args:
            bibtex: BibTeX 문자열

        Returns:
            정규화된 BibTeX 문자열
        """
        try:
            import bibtexparser
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            db = bibtexparser.loads(bibtex, parser)

            if not db.entries:
                return bibtex

            entry = db.entries[0]
            pages = entry.get("pages", "").strip("{}")

            # ACM 스타일 페이지 패턴 (예: 138:1--138:12)
            acm_pattern = r"^(\d+):(\d+)--(\d+):(\d+)$"
            match = re.match(acm_pattern, pages)

            if match:
                start_article = int(match.group(1))
                start_page = int(match.group(2))
                end_article = int(match.group(3))
                end_page = int(match.group(4))

                # 같은 article 번호인지 확인
                if start_article == end_article:
                    entry["articleno"] = str(start_article)
                    num_pages = end_page - start_page + 1
                    entry["numpages"] = str(num_pages)

                    # pages 필드 제거
                    if "pages" in entry:
                        del entry["pages"]

            # BibTeX 재생성 (일관된 형식)
            writer = bibtexparser.bwriter.BibTexWriter()
            writer.indent = "  "
            writer.align_values = False

            new_db = bibtexparser.bibdatabase.BibDatabase()
            new_db.entries = [entry]

            return bibtexparser.dumps(new_db, writer).strip()

        except Exception as e:
            print(f"Error normalizing ACM pages: {e}")
            return bibtex


class BibTeXFieldOptimizer:
    """BibTeX 필드 최적화 클래스"""

    def __init__(self):
        """Initialize BibTeXFieldOptimizer"""

    def optimize_entry(self, bibtex: str) -> str:
        """
        BibTeX 항목을 최적화합니다.

        Args:
            bibtex: BibTeX 문자열

        Returns:
            최적화된 BibTeX 문자열
        """
        try:
            import bibtexparser
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            db = bibtexparser.loads(bibtex, parser)

            if not db.entries:
                return bibtex

            entry = db.entries[0]

            # 빈 필드 정리
            self.clean_empty_fields_dict(entry)

            # 특수 문자 이스케이프
            self._escape_special_characters(entry)

            # BibTeX 재생성 (일관된 형식)
            writer = bibtexparser.bwriter.BibTexWriter()
            writer.indent = "  "
            writer.align_values = False

            new_db = bibtexparser.bibdatabase.BibDatabase()
            new_db.entries = [entry]

            return bibtexparser.dumps(new_db, writer).strip()

        except Exception as e:
            print(f"Error optimizing BibTeX: {e}")
            return bibtex

    def clean_empty_fields(self, bibtex: str) -> str:
        """
        BibTeX에서 빈 필드를 정리합니다.

        Args:
            bibtex: BibTeX 문자열

        Returns:
            빈 필드가 정리된 BibTeX 문자열
        """
        try:
            import bibtexparser
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            db = bibtexparser.loads(bibtex, parser)

            if not db.entries:
                return bibtex

            entry = db.entries[0]
            self.clean_empty_fields_dict(entry)

            # BibTeX 재생성 (일관된 형식)
            writer = bibtexparser.bwriter.BibTexWriter()
            writer.indent = "  "
            writer.align_values = False

            new_db = bibtexparser.bibdatabase.BibDatabase()
            new_db.entries = [entry]

            return bibtexparser.dumps(new_db, writer).strip()

        except Exception as e:
            print(f"Error cleaning empty fields: {e}")
            return bibtex

    def clean_empty_fields_dict(self, entry: dict) -> None:
        """딕셔너리 형태의 BibTeX entry에서 빈 필드 정리"""
        fields_to_remove = []

        for key, value in entry.items():
            if key in ["ENTRYTYPE", "ID"]:
                continue

            # 빈 값 확인
            if (value is None or
                str(value).strip() in ["", "{}", ""] or
                (isinstance(value, str) and
                 (value.strip() == "" or
                  (len(value.strip()) <= 2 and "{}" in value.strip())))):
                fields_to_remove.append(key)

        # 빈 필드 제거
        for key in fields_to_remove:
            entry.pop(key, None)

    def _escape_special_characters(self, entry: dict) -> None:
        """BibTeX 필드에서 특수 문자 이스케이프"""
        for key, value in entry.items():
            if key in ["ENTRYTYPE", "ID"]:
                continue

            if isinstance(value, str):
                # BibTeX 특수 문자 이스케이프
                value = value.replace("&", "\\&")
                value = value.replace("%", "\\%")
                value = value.replace("$", "\\$")
                value = value.replace("#", "\\#")
                value = value.replace("_", "\\_")
                value = value.replace("{", "\\{")
                value = value.replace("}", "\\}")
                value = value.replace("~", "\\~{}")
                value = value.replace("^", "\\^{}")

                entry[key] = value

    def _validate_bibtex_format(self, bibtex: str) -> bool:
        """
        BibTeX 형식이 유효한지 검증합니다.

        Args:
            bibtex: 검증할 BibTeX 문자열

        Returns:
            유효하면 True, 아니면 False
        """
        try:
            import bibtexparser
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            db = bibtexparser.loads(bibtex, parser)

            return len(db.entries) > 0

        except Exception:
            return False
