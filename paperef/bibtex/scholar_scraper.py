"""
BibTeX 스크래퍼 모듈
OpenAlex API 우선 사용, Google Scholar Selenium을 fallback으로 사용
"""

import os
import re
import sys
import time
import random
import requests
from typing import Optional, Dict, Any, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class OpenAlexScraper:
    """OpenAlex API BibTeX 스크래퍼"""

    def __init__(self):
        self.base_url = "https://api.openalex.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Paper2MD/0.1.0 (https://github.com/alansynn/paperef; mailto:alan@alansynn.com)',
            'Accept': 'application/json'
        })

    def search_paper(self, title: str, year: Optional[int] = None, doi: Optional[str] = None) -> Optional[str]:
        """
        OpenAlex에서 논문 검색 및 BibTeX 추출

        Args:
            title: 논문 제목
            year: 출판 연도 (선택사항)
            doi: DOI 정보 (선택사항)

        Returns:
            BibTeX 문자열 또는 None
        """
        try:
            print(f"Searching OpenAlex: {title[:50]}...", file=sys.stderr)

            # DOI가 있는 경우 DOI로 직접 검색
            if doi:
                print(f"Trying DOI search: {doi}", file=sys.stderr)
                try:
                    work = self._search_by_doi(doi)
                    if work:
                        bibtex = self._generate_bibtex_from_work(work)
                        if bibtex:
                            print(f"Successfully retrieved BibTeX from OpenAlex (DOI) for: {title[:30]}...", file=sys.stderr)
                            return bibtex
                        else:
                            print(f"Failed to generate BibTeX from DOI search result for: {doi}", file=sys.stderr)
                    else:
                        print(f"DOI search returned no results for: {doi}, falling back to title search", file=sys.stderr)
                except Exception as e:
                    print(f"DOI search failed for {doi}: {e}, falling back to title search", file=sys.stderr)

            # 제목 기반 검색 (간단한 search 파라미터 사용)
            params = {
                'search': title,
                'per_page': 10,
                'select': 'id,title,authorships,publication_year,biblio,doi,primary_location,type,locations'
            }

            # 년도 필터 추가
            if year:
                params['filter'] = f'publication_year:{year}'

            response = self.session.get(f"{self.base_url}/works", params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            works = data.get('results', [])

            if not works:
                print(f"No results found in OpenAlex for: {title}", file=sys.stderr)
                return None

            # 가장 관련성 높은 결과 선택
            best_work = self._find_best_match(works, title, year)
            if not best_work:
                best_work = works[0]  # 첫 번째 결과로 fallback

            # BibTeX 생성
            bibtex = self._generate_bibtex_from_work(best_work)
            if bibtex:
                print(f"Successfully retrieved BibTeX from OpenAlex for: {title[:30]}...", file=sys.stderr)
                return bibtex

        except requests.RequestException as e:
            print(f"OpenAlex API error: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error searching OpenAlex for {title}: {e}", file=sys.stderr)

        return None

    def _search_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """DOI로 OpenAlex에서 직접 검색"""
        try:

            doi = doi.replace('https://doi.org/', '').strip()
            original_doi = doi


            if not doi:
                return None


            doi_variants = [
                doi,
                doi.replace('/', '%2F'),
                doi.replace('%2F', '/'),
            ]

            for doi_variant in doi_variants:
                try:
                    params = {
                        'filter': f'doi:"{doi_variant}"',
                        'select': 'id,title,authorships,publication_year,biblio,doi,primary_location,type,locations'
                    }

                    response = self.session.get(f"{self.base_url}/works", params=params, timeout=10)
                    response.raise_for_status()

                    data = response.json()
                    works = data.get('results', [])

                    if works:
                        print(f"DOI search successful for variant: {doi_variant}", file=sys.stderr)
                        return works[0]
                except Exception as variant_error:
                    print(f"DOI variant {doi_variant} failed: {variant_error}", file=sys.stderr)
                    continue


            print(f"All DOI variants failed for: {original_doi}", file=sys.stderr)
            return None

        except Exception as e:
            print(f"Error searching by DOI {doi}: {e}", file=sys.stderr)
            return None

    def _find_best_match(self, works: List[Dict[str, Any]], target_title: str, target_year: Optional[int]) -> Optional[Dict[str, Any]]:
        """가장 관련성 높은 결과 찾기"""
        from difflib import SequenceMatcher

        best_work = None
        best_score = 0.0

        target_title_lower = target_title.lower()

        for work in works:
            work_title = work.get('title', '').lower()
            work_year = work.get('publication_year')

            # 제목 유사도 계산
            title_similarity = SequenceMatcher(None, target_title_lower, work_title).ratio()

            # 연도 매칭 점수
            year_score = 1.0 if (target_year and work_year and abs(work_year - target_year) <= 1) else 0.0

            # 종합 점수
            score = title_similarity * 0.8 + year_score * 0.2

            if score > best_score:
                best_score = score
                best_work = work

        return best_work if best_score > 0.6 else None

    def _generate_bibtex_from_work(self, work: Dict[str, Any]) -> Optional[str]:
        """OpenAlex work 데이터로부터 BibTeX 생성"""
        try:

            title = work.get('title', '')
            if not title:
                return None


            authorships = work.get('authorships', [])
            authors = []
            for authorship in authorships:
                author_data = authorship.get('author', {})
                display_name = author_data.get('display_name', '')

                if display_name:


                    if ',' in display_name:
                        authors.append(display_name)
                    else:

                        name_parts = display_name.split()
                        if len(name_parts) >= 2:
                            last_name = name_parts[-1]
                            first_names = ' '.join(name_parts[:-1])
                            authors.append(f"{last_name}, {first_names}")
                        else:
                            authors.append(display_name)
                else:

                    first_name = author_data.get('first_name', '')
                    last_name = author_data.get('last_name', '')
                    if last_name and first_name:
                        authors.append(f"{last_name}, {first_name}")
                    elif last_name:
                        authors.append(last_name)

            if not authors:
                authors = ['Unknown']


            year = work.get('publication_year')


            doi = work.get('doi', '').replace('https://doi.org/', '') if work.get('doi') else None


            primary_location = work.get('primary_location', {})
            venue_name = ''
            publisher = ''

            if primary_location:
                source = primary_location.get('source', {})
                if source:
                    venue_name = source.get('display_name', '')
                    publisher = source.get('host_organization_name', '') or source.get('host_organization', '')


            if not venue_name:
                locations = work.get('locations', [])
                if locations:
                    first_location = locations[0]
                    source = first_location.get('source', {})
                    if source:
                        venue_name = source.get('display_name', '')
                        publisher = source.get('host_organization_name', '') or source.get('host_organization', '')


            biblio = work.get('biblio', {})
            pages = biblio.get('first_page', '')
            last_page = biblio.get('last_page', '')
            if pages and last_page:
                pages = f"{pages}--{last_page}"


            volume = biblio.get('volume', '')
            issue = biblio.get('issue', '')


            work_type = work.get('type', 'article')
            bibtex_type = self._map_work_type_to_bibtex(work_type)


            bibtex_key = self._generate_bibtex_key(authors, year, title)


            bib_lines = [f"@{bibtex_type}{{{bibtex_key},"]
            bib_lines.append(f"  title={{{title}}},")
            bib_lines.append(f"  author={{{' and '.join(authors)}}},")
            if year:
                bib_lines.append(f"  year={{{year}}},")
            if doi:
                bib_lines.append(f"  doi={{{doi}}},")
            if venue_name:
                if bibtex_type == 'article':
                    bib_lines.append(f"  journal={{{venue_name}}},")
                elif bibtex_type in ['inproceedings', 'conference']:
                    bib_lines.append(f"  booktitle={{{venue_name}}},")
            if publisher:
                bib_lines.append(f"  publisher={{{publisher}}},")
            if pages:
                bib_lines.append(f"  pages={{{pages}}},")
            if volume:
                bib_lines.append(f"  volume={{{volume}}},")
            if issue:
                bib_lines.append(f"  number={{{issue}}},")
            bib_lines.append("}")

            return '\n'.join(bib_lines)

        except Exception as e:
            print(f"Error generating BibTeX from OpenAlex work: {e}", file=sys.stderr)
            return None

    def _map_work_type_to_bibtex(self, work_type: str) -> str:
        """OpenAlex work type을 BibTeX type으로 매핑"""
        type_mapping = {
            'article': 'article',
            'journal-article': 'article',
            'book-chapter': 'inbook',
            'book': 'book',
            'conference-paper': 'inproceedings',
            'conference': 'inproceedings',
            'proceedings-article': 'inproceedings',
            'dissertation': 'phdthesis',
            'report': 'techreport',
            'preprint': 'unpublished'
        }
        return type_mapping.get(work_type, 'article')

    def _generate_bibtex_key(self, authors: List[str], year: Optional[int], title: str) -> str:
        """BibTeX 키 생성 (Google Scholar 스타일)"""

        if authors:
            first_author = authors[0].split()[-1].lower()
        else:
            first_author = "unknown"


        clean_title = re.sub(r'[():-]', ' ', title).strip()
        title_words = re.findall(r'\b\w+\b', clean_title.lower())
        first_word = title_words[0] if title_words else "unknown"


        first_word = re.sub(r'[^a-z0-9]', '', first_word)


        key_parts = [part for part in [first_author, str(year) if year else "", first_word] if part]
        return "".join(key_parts)


class GoogleScholarScraper:
    """Google Scholar BibTeX 스크래퍼 (fallback)"""

    def __init__(self, headless: bool = True, wait_min: float = 1.0, wait_max: float = 2.0):
        self.wait_min = wait_min
        self.wait_max = wait_max
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 15)  # Increase timeout

    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """Chrome WebDriver 설정"""
        chrome_options = Options()

        if headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)


        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return driver

    def _random_wait(self) -> None:
        """무작위 대기 시간"""
        wait_time = random.uniform(self.wait_min, self.wait_max)
        time.sleep(wait_time)

    def search_paper(self, title: str, year: Optional[int] = None) -> Optional[str]:
        """
        Google Scholar에서 논문 검색 및 BibTeX 추출

        Args:
            title: 논문 제목
            year: 출판 연도 (선택사항)

        Returns:
            BibTeX 문자열 또는 None
        """
        try:
            print(f"Searching Google Scholar: {title[:50]}...", file=sys.stderr)

            # Google Scholar 접속
            self.driver.get("https://scholar.google.com")
            self._random_wait()

            # 검색창 찾기
            search_box = self.wait.until(EC.presence_of_element_located((By.NAME, "q")))

            # 검색 쿼리 구성
            query = f'"{title}"'
            if year:
                query += f" {year}"

            # 검색 실행
            search_box.clear()
            search_box.send_keys(query)

            # 검색 버튼 클릭
            search_btn = self.driver.find_element(By.NAME, "btnG")
            search_btn.click()

            self._random_wait()

            # CAPTCHA 확인
            if "captcha" in self.driver.page_source.lower():
                print("CAPTCHA detected - waiting longer and retrying", file=sys.stderr)
                time.sleep(5)  # Wait 5 seconds for potential auto-resolution
                self.driver.refresh()
                self._random_wait()

                # Check again after refresh
                if "captcha" in self.driver.page_source.lower():
                    print("CAPTCHA still present - skipping", file=sys.stderr)
                    return None

            # 첫 번째 결과의 인용 버튼 찾기
            cite_buttons = self.driver.find_elements(By.CLASS_NAME, "gs_or_cit")
            if not cite_buttons:
                print(f"No citation button found for: {title}", file=sys.stderr)
                return None

            # 첫 번째 인용 버튼 클릭
            cite_buttons[0].click()
            self._random_wait()

            # BibTeX 링크 찾기
            bibtex_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "BibTeX")
            if not bibtex_links:
                print(f"BibTeX link not found for: {title}", file=sys.stderr)
                return None

            # BibTeX 링크 클릭
            bibtex_links[0].click()
            self._random_wait()

            # BibTeX 텍스트 추출
            try:
                # <pre> 태그에서 BibTeX 찾기 (짧은 타임아웃)
                short_wait = WebDriverWait(self.driver, 3)
                bibtex_element = short_wait.until(EC.presence_of_element_located((By.TAG_NAME, "pre")))
                bibtex_text = bibtex_element.text

                print(f"Successfully retrieved BibTeX for: {title[:30]}...", file=sys.stderr)
                return bibtex_text

            except TimeoutException:
                # <pre> 태그가 없는 경우 body 텍스트 전체 확인
                body = self.driver.find_element(By.TAG_NAME, "body")
                text = body.text
                if text.startswith("@"):
                    return text
                else:
                    print(f"No BibTeX content found for: {title}", file=sys.stderr)
                    return None

        except TimeoutException:
            print(f"Timeout while searching for: {title}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error searching for {title}: {e}", file=sys.stderr)
            return None

    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()


class BibTeXScraper:
    """통합 BibTeX 스크래퍼 (OpenAlex 우선, Google Scholar fallback)"""

    def __init__(self, config):
        self.config = config
        self.openalex_scraper = OpenAlexScraper()
        self.scholar_scraper = GoogleScholarScraper(
            headless=config.scholar_headless,
            wait_min=config.scholar_wait_min,
            wait_max=config.scholar_wait_max
        ) if config.interactive else None

    def search_paper(self, title: str, year: Optional[int] = None, doi: Optional[str] = None) -> Optional[str]:
        """
        BibTeX 검색 (OpenAlex 우선, Google Scholar fallback)

        Args:
            title: 논문 제목
            year: 출판 연도 (선택사항)
            doi: DOI 정보 (선택사항)

        Returns:
            BibTeX 문자열 또는 None
        """
        # 1. OpenAlex 검색 (항상 우선)
        print(f"Trying OpenAlex first for: {title[:50]}...", file=sys.stderr)
        bibtex = self.openalex_scraper.search_paper(title, year, doi)

        if bibtex:
            print("✓ Found BibTeX via OpenAlex", file=sys.stderr)
            return bibtex

        # 2. no-interactive 모드에서는 여기서 중단
        if self.config.no_interactive:
            print("No results from OpenAlex (non-interactive mode)", file=sys.stderr)
            return None

        # 3. Google Scholar fallback (interactive 모드에서만)
        if self.scholar_scraper:
            print(f"Trying Google Scholar fallback for: {title[:50]}...", file=sys.stderr)
            bibtex = self.scholar_scraper.search_paper(title, year)

            if bibtex:
                print("✓ Found BibTeX via Google Scholar", file=sys.stderr)
                return bibtex

        print(f"No BibTeX found for: {title}", file=sys.stderr)
        return None

    def close(self):
        """리소스 정리"""
        if self.scholar_scraper:
            self.scholar_scraper.close()
