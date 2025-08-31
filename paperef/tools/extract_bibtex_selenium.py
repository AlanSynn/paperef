#!/usr/bin/env python3
"""
BibTeX extractor using Selenium WebDriver to interact with Google Scholar.
Based on the approach from bib_collector but adapted for our markdown format.
"""

import argparse
import json
import os
import re
import sys
import time
import random
from dataclasses import dataclass
from typing import List, Optional, Dict

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from tqdm import tqdm


# Configuration
CACHE_PATH_DEFAULT = os.path.join("tools", ".bib_cache.json")
GOOGLE_SCHOLAR_URL = "https://scholar.google.com"


@dataclass
class Reference:
    """Represents a reference from markdown."""
    raw_line: str
    title: Optional[str]
    year: Optional[int]


class GoogleScholarScraper:
    """Google Scholar scraper using Selenium."""
    
    def __init__(self, headless: bool = True, wait_min: float = 0.3, wait_max: float = 0.7):
        self.wait_min = wait_min
        self.wait_max = wait_max
        self.driver = self._setup_driver(headless)
        self.wait = WebDriverWait(self.driver, 8)
    
    def _setup_driver(self, headless: bool) -> webdriver.Chrome:
        """Setup Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-images")  # Skip loading images
        chrome_options.add_argument("--disable-javascript")  # Skip JavaScript when possible
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-extensions")
        
        # User agent to look more like a real browser
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
    def _random_wait(self) -> None:
        """Wait for a random amount of time to appear more human-like."""
        wait_time = random.uniform(self.wait_min, self.wait_max)
        time.sleep(wait_time)
    
    def search_paper(self, title: str, year: Optional[int] = None) -> Optional[str]:
        """
        Search for a paper on Google Scholar and return BibTeX.
        
        Args:
            title: Paper title
            year: Optional publication year
            
        Returns:
            BibTeX string if found, None otherwise
        """
        try:
            print(f"Searching: {title[:50]}...", file=sys.stderr)
            
            # Go to Google Scholar
            self.driver.get(GOOGLE_SCHOLAR_URL)
            self._random_wait()
            
            # Find search box
            search_box = self.wait.until(EC.presence_of_element_located((By.NAME, "q")))
            
            # Build search query
            query = f'"{title}"'
            if year:
                query += f" {year}"
            
            # Clear and search
            search_box.clear()
            search_box.send_keys(query)
            
            # Click search button
            search_btn = self.driver.find_element(By.NAME, "btnG")
            search_btn.click()
            
            self._random_wait()
            
            # Check for CAPTCHA
            if "captcha" in self.driver.page_source.lower():
                print("CAPTCHA detected - manual intervention may be needed", file=sys.stderr)
                # Check if running in headless mode by looking at chrome options
                chrome_options = self.driver.capabilities.get('chrome', {}).get('chromedriverVersion', '')
                if '--headless' not in str(self.driver.capabilities):
                    print("Browser is visible - please solve CAPTCHA manually", file=sys.stderr)
                    input("Please solve the CAPTCHA and press Enter to continue...")
                else:
                    return None
            
            # Look for the first result's cite button
            cite_buttons = self.driver.find_elements(By.CLASS_NAME, "gs_or_cit")
            if not cite_buttons:
                print(f"No citation button found for: {title}", file=sys.stderr)
                return None
            
            # Click the first cite button
            cite_buttons[0].click()
            self._random_wait()
            
            # Find BibTeX link in the citation popup
            try:
                bibtex_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "BibTeX")
                if not bibtex_links:
                    print(f"BibTeX link not found for: {title}", file=sys.stderr)
                    return None
                
                # Click BibTeX link
                bibtex_links[0].click()
                self._random_wait()
                
                # Get the BibTeX text
                try:
                    # Try to find the BibTeX in a <pre> tag with very short timeout
                    short_wait = WebDriverWait(self.driver, 3)
                    bibtex_element = short_wait.until(EC.presence_of_element_located((By.TAG_NAME, "pre")))
                    bibtex_text = bibtex_element.text
                    
                    print(f"Successfully retrieved BibTeX for: {title[:30]}...", file=sys.stderr)
                    return bibtex_text
                    
                except TimeoutException:
                    # If no <pre> tag, try to get all text from body
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    text = body.text
                    if text.startswith("@"):
                        return text
                    else:
                        print(f"No BibTeX content found for: {title}", file=sys.stderr)
                        return None
                
            except Exception as e:
                print(f"Error getting BibTeX for {title}: {e}", file=sys.stderr)
                return None
                
        except TimeoutException:
            print(f"Timeout while searching for: {title}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error searching for {title}: {e}", file=sys.stderr)
            return None
    
    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()


def load_cache(cache_path: str) -> Dict[str, str]:
    """Load cache from JSON file."""
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache_path: str, cache: Dict[str, str]) -> None:
    """Save cache to JSON file."""
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def extract_references(markdown_text: str) -> List[str]:
    """Extract reference lines from markdown."""
    lines = markdown_text.splitlines()
    refs_started = False
    ref_lines: List[str] = []
    
    for line in lines:
        if not refs_started and line.strip().lower() == "## references":
            refs_started = True
            continue
        if refs_started:
            if line.strip().startswith("## ") and line.strip().lower() != "## references":
                break
            if line.strip().startswith("-"):
                ref_lines.append(line.rstrip())
    
    return ref_lines


def parse_reference(line: str) -> Reference:
    """Parse a reference line to extract title and year."""
    clean = line.lstrip("- ")
    title = None
    year = None
    
    # Look for year pattern
    year_match = re.search(r'\b(19\d{2}|20\d{2})[a-z]?\b', clean)
    if year_match:
        year = int(year_match.group(1))
        
        # Extract title - typically after year, before next period
        after_year = clean[year_match.end():].strip()
        after_year = re.sub(r'^[.\s]+', '', after_year)
        
        # Get first sentence as title
        title_match = re.match(r'^([^.]+)\.', after_year)
        if title_match:
            title = title_match.group(1).strip()
            title = re.sub(r'\s+', ' ', title)
            # Remove trailing punctuation
            title = re.sub(r'[,;:]+$', '', title)
    
    # If no title found, try different approach
    if not title:
        # Pattern: Author(s). (Year). Title. 
        pattern = r'^[^.]+\.\s*(?:\(\d{4}\))?\s*([^.]+)\.'
        match = re.match(pattern, clean)
        if match:
            title = match.group(1).strip()
            title = re.sub(r'\s+', ' ', title)
    
    return Reference(raw_line=line, title=title, year=year)


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(description="Extract BibTeX using Selenium and Google Scholar")
    parser.add_argument("--input", required=True, help="Input markdown file (absolute path)")
    parser.add_argument("--output", required=True, help="Output .bib file (absolute path)")
    parser.add_argument("--cache", default=CACHE_PATH_DEFAULT, help="Cache file path")
    parser.add_argument("--sleep-min", type=float, default=0.5, help="Minimum wait time between requests")
    parser.add_argument("--sleep-max", type=float, default=1.0, help="Maximum wait time between requests")
    parser.add_argument("--turbo", action="store_true", help="Ultra-fast mode (0.1-0.3s delays)")
    parser.add_argument("--max", type=int, default=-1, help="Max references to process (-1 = all)")
    parser.add_argument("--refresh", action="store_true", help="Ignore cache and fetch fresh")
    parser.add_argument("--show-browser", action="store_true", help="Show browser (non-headless mode)")
    parser.add_argument("--start-from", type=int, default=0, help="Start from reference index (for resume)")
    args = parser.parse_args()
    
    # Validate paths
    if not os.path.isabs(args.input) or not os.path.isabs(args.output):
        print("Error: Please use absolute paths for --input and --output", file=sys.stderr)
        return 2
    
    # Load cache
    cache = {} if args.refresh else load_cache(args.cache)
    
    # Read markdown
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            md_text = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}", file=sys.stderr)
        return 1
    
    # Extract references
    ref_lines = extract_references(md_text)
    if not ref_lines:
        print("No references found in markdown file", file=sys.stderr)
        return 1
    
    # Parse references
    parsed = [parse_reference(line) for line in ref_lines]
    if args.max > 0:
        parsed = parsed[:args.max]
    
    # Start from specified index
    if args.start_from > 0:
        parsed = parsed[args.start_from:]
        print(f"Starting from reference #{args.start_from}", file=sys.stderr)
    
    # Setup scraper
    if args.turbo:
        # Ultra-fast mode
        scraper = GoogleScholarScraper(
            headless=not args.show_browser,
            wait_min=0.1,
            wait_max=0.3
        )
    else:
        scraper = GoogleScholarScraper(
            headless=not args.show_browser,
            wait_min=args.sleep_min,
            wait_max=args.sleep_max
        )
    
    try:
        # Process references
        output_chunks = []
        
        for i, ref in enumerate(tqdm(parsed, desc="Fetching BibTeX")):
            if not ref.title:
                print(f"Skipping reference without title: {ref.raw_line[:50]}...", file=sys.stderr)
                continue
            
            # Check cache
            cache_key = f"{ref.title}::{ref.year or ''}"
            if not args.refresh and cache.get(cache_key):
                if cache[cache_key]:  # Skip empty entries
                    output_chunks.append(cache[cache_key])
                continue
            
            # Fetch BibTeX
            bibtex = scraper.search_paper(ref.title, ref.year)
            
            if bibtex:
                cache[cache_key] = bibtex
                output_chunks.append(bibtex)
                print(f"✓ Got BibTeX for: {ref.title[:40]}...", file=sys.stderr)
            else:
                cache[cache_key] = ""  # Cache failures
                print(f"✗ Failed to get BibTeX for: {ref.title[:40]}...", file=sys.stderr)
            
            # Save cache periodically
            if i % 5 == 0:
                save_cache(args.cache, cache)
        
    finally:
        # Clean up
        scraper.close()
        save_cache(args.cache, cache)
    
    # Write output
    if not output_chunks:
        print("No BibTeX entries could be retrieved", file=sys.stderr)
        return 1
    
    try:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("\n\n".join(chunk.strip() for chunk in output_chunks) + "\n")
        
        print(f"Successfully wrote {len(output_chunks)} BibTeX entries to {args.output}")
        return 0
        
    except Exception as e:
        print(f"Error writing output file: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())