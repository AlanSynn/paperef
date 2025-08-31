"""
bib_doi_enricher.py
-------------------
Enrich BibTeX entries by finding DOIs (via Crossref, fallback OpenAlex) and
updating/normalizing fields for ACM/IEEE/Springer, including publisher/address,
pages vs articleno+numpages, volume/number, etc.

Usage:
  python bib_doi_enricher.py input.bib -o output.bib
  python bib_doi_enricher.py input.bib -o output.bib --acm-pages-to-article
  python bib_doi_enricher.py input.bib -o output.bib --prefer-openalex
  python bib_doi_enricher.py input.bib -o output.bib --non-interactive

Dependencies:
  pip install bibtexparser requests rich

Notes:
  - Set CONTACT_EMAIL to your email for Crossref/OpenAlex User-Agent (politeness & higher quotas).
  - This script is interactive by default: it prompts for ambiguous matches and missing fields.
  - For ACM-style entries like "138:1--138:12", --acm-pages-to-article converts to
    articleno=138, numpages=12 and removes pages.
"""

import argparse
import re
import sys
import time
import json
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlencode

import requests
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from difflib import SequenceMatcher

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' not installed. Install with 'pip install rich' for better UI. Falling back to basic prompts.", file=sys.stderr)

# Initialize console if rich is available
console = Console() if RICH_AVAILABLE else None

# --- Configuration ---

CONTACT_EMAIL = "alansynn@gatech.edu"  # change this!
CROSSREF_BASE = "https://api.crossref.org/works"
OPENALEX_BASE = "https://api.openalex.org/works"
REQUEST_TIMEOUT = 20
RATE_LIMIT_SLEEP = 0.2  # seconds between API calls

PUBLISHER_ADDRESS = {
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

# Venue to publisher mapping
VENUE_TO_PUBLISHER = {
    "chi": "ACM",
    "sigchi": "ACM",
    "uist": "ACM",
    "cscw": "ACM",
    "ubicomp": "ACM",
    "teachable": "ACM",
    "dis": "ACM",
    "nordichi": "ACM",
    "chi play": "ACM",
    "idc": "ACM",
    "assets": "ACM",
    "iui": "ACM",
    "gi": "ACM",
    "group": "ACM",
    "pervasive": "ACM",
    "mobilehci": "ACM",
    "automotiveui": "ACM",
    "tvx": "ACM",
    "iss": "ACM",
    "its": "ACM",
    "tangible": "ACM",
    "tei": "ACM",
    "nime": "ACM",
    "mm": "ACM",
    "siggraph": "ACM",
    "sigir": "ACM",
    "kdd": "ACM",
    "icml": "ACM",
    "neurips": "ACM",
    "iccv": "ACM",
    "cvpr": "ACM",
    "eccv": "ACM",
    "acl": "ACM",
    "emnlp": "ACM",
    "naacl": "ACM",
    "icra": "IEEE",
    "iros": "IEEE",
    "rss": "IEEE",
    "icassp": "IEEE",
    "icip": "IEEE",
    "infocom": "IEEE",
    "globecom": "IEEE",
    "wcnc": "IEEE",
    "icc": "IEEE",
    "sigcomm": "ACM",
    "nsdi": "ACM",
    "osdi": "ACM",
    "sosp": "ACM",
    "eurographics": "ACM",
    "graphics interface": "ACM",
    "pacific graphics": "ACM",
    "symposium on geometry processing": "ACM",
    "computer graphics forum": "Wiley",
    "computers & graphics": "Elsevier",
    "computer aided geometric design": "Elsevier",
    "cad computer aided design": "Elsevier",
    "journal of computational design and engineering": "Oxford University Press",
    "international journal of human-computer studies": "Elsevier",
    "human-computer interaction": "Taylor & Francis",
    "interactions": "ACM",
    "tochi": "ACM",
    "ijhcs": "Elsevier",
    "behaviour & information technology": "Taylor & Francis",
    "computers in human behavior": "Elsevier",
    "pervasive and mobile computing": "Elsevier",
    "ubicomp adjunct": "ACM",
    "ubicomp proceedings": "ACM",
    "ubicomp '": "ACM",
    "chi '": "ACM",
    "uist '": "ACM",
    "cscw '": "ACM",
    "dis '": "ACM",
    "teachable '": "ACM",
    "idc '": "ACM",
    "chi play '": "ACM",
    "assets '": "ACM",
    "iui '": "ACM",
    "gi '": "ACM",
    "group '": "ACM",
    "pervasive '": "ACM",
    "mobilehci '": "ACM",
    "automotiveui '": "ACM",
    "tvx '": "ACM",
    "iss '": "ACM",
    "its '": "ACM",
    "tangible '": "ACM",
    "tei '": "ACM",
    "nime '": "ACM",
    "mm '": "ACM",
    "siggraph '": "ACM",
    "sigir '": "ACM",
    "kdd '": "ACM",
    "icml '": "ACM",
    "neurips '": "ACM",
    "iccv '": "ACM",
    "eccv '": "ACM",
    "acl '": "ACM",
    "emnlp '": "ACM",
    "naacl '": "ACM",
    "icra '": "IEEE",
    "iros '": "IEEE",
    "rss '": "IEEE",
    "icassp '": "IEEE",
    "icip '": "IEEE",
    "infocom '": "IEEE",
    "globecom '": "IEEE",
    "wcnc '": "IEEE",
    "icc '": "IEEE",
    "sigcomm '": "ACM",
    "nsdi '": "ACM",
    "osdi '": "ACM",
    "sosp '": "ACM",
    "eurographics '": "ACM",
    "graphics interface '": "ACM",
    "pacific graphics '": "ACM",
    "symposium on geometry processing '": "ACM",
}

# --- Interactive helpers ---

def prompt_text(message: str, default: str = "") -> str:
    if RICH_AVAILABLE:
        return Prompt.ask(message, default=default)
    else:
        if default:
            response = input(f"{message} (default: {default}): ").strip()
            return response if response else default
        else:
            return input(f"{message}: ").strip()

def prompt_confirm(message: str, default: bool = True) -> bool:
    if RICH_AVAILABLE:
        return Confirm.ask(message, default=default)
    else:
        response = input(f"{message} (y/n, default {'y' if default else 'n'}): ").strip().lower()
        if not response:
            return default
        return response in ('y', 'yes', 'true', '1')

def display_candidates(candidates: List[Dict[str, Any]], title: str, authors: List[str], year: Optional[int]) -> int:
    if not RICH_AVAILABLE:
        print(f"Candidates for '{title}':")
        for i, cand in enumerate(candidates):
            doi = cand.get("DOI", "N/A")
            cr_title = (cand.get("title") or [""])[0]
            print(f"{i+1}. DOI: {doi}, Title: {cr_title}")
        choice = int(input("Choose candidate (1-n) or 0 to skip: ")) - 1
        return choice if 0 <= choice < len(candidates) else -1
    else:
        table = Table(title=f"Candidates for '{title}'")
        table.add_column("Index", style="cyan", no_wrap=True)
        table.add_column("DOI", style="magenta")
        table.add_column("Title")
        table.add_column("Authors")
        table.add_column("Year")
        table.add_column("Publisher")
        for i, cand in enumerate(candidates):
            doi = cand.get("DOI", "N/A")
            cr_title = (cand.get("title") or [""])[0][:50] + "..." if len((cand.get("title") or [""])[0]) > 50 else (cand.get("title") or [""])[0]
            cr_auth = ", ".join([a.get("family", "") for a in (cand.get("author") or []) if isinstance(a, dict)])[:30] + "..." if len([a.get("family", "") for a in (cand.get("author") or []) if isinstance(a, dict)]) > 30 else ", ".join([a.get("family", "") for a in (cand.get("author") or []) if isinstance(a, dict)])
            cr_year = str(year_from_crossref(cand)) if year_from_crossref(cand) else "N/A"
            cr_pub = cand.get("publisher", "N/A")
            table.add_row(str(i+1), doi, cr_title, cr_auth, cr_year, cr_pub)
        console.print(table)
        choice = Prompt.ask("Choose candidate (1-n) or 0 to skip", default="0")
        try:
            idx = int(choice) - 1
            return idx if 0 <= idx < len(candidates) else -1
        except ValueError:
            return -1

# --- Helpers ---

def norm_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def simplify_title(t: str) -> str:
    t = norm_whitespace(t).lower()
    # remove punctuation
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return norm_whitespace(t)

def author_lastnames(authors_field: str) -> List[str]:
    if not authors_field:
        return []
    
    # Handle LaTeX accents before processing
    # Common LaTeX accent commands
    accents = {
        r'{\i}': 'i',
        r'{\\i}': 'i', 
        r'{\c s}': 'ş',
        r'{\c c}': 'ç',
        r'{\'a}': 'á',
        r'{\'e}': 'é',
        r'{\'i}': 'í',
        r'{\'o}': 'ó',
        r'{\'u}': 'ú',
        r'{\"a}': 'ä',
        r'{\"o}': 'ö',
        r'{\"u}': 'ü',
        r'{\^a}': 'â',
        r'{\^e}': 'ê',
        r'{\^i}': 'î',
        r'{\^o}': 'ô',
        r'{\^u}': 'û',
    }
    
    for latex, char in accents.items():
        authors_field = authors_field.replace(latex, char)
    
    parts = [a.strip() for a in authors_field.split(" and ") if a.strip()]
    lastnames = []
    for p in parts:
        # handle {Sitthi-amorn}, Pitchaya
        p = p.strip("{} ")
        if "," in p:
            last = p.split(",", 1)[0].strip("{} ")
        else:
            last = p.split()[-1].strip("{} ")
        
        # Unicode normalization for better matching - handle common issues
        # Convert common Unicode characters to ASCII equivalents
        unicode_map = {
            'ı': 'i',  # dotless i
            'ş': 's',  # s with cedilla
            'ç': 'c',  # c with cedilla
            'ğ': 'g',  # g with breve
            'ö': 'o',  # o with diaeresis
            'ü': 'u',  # u with diaeresis
            'İ': 'i',  # capital dotless i
            'Ş': 's',  # capital s with cedilla
            'Ç': 'c',  # capital c with cedilla
            'Ğ': 'g',  # capital g with breve
            'Ö': 'o',  # capital o with diaeresis
            'Ü': 'u',  # capital u with diaeresis
        }
        for unicode_char, ascii_char in unicode_map.items():
            last = last.replace(unicode_char, ascii_char)
        lastnames.append(last.lower())
    return lastnames

def title_similarity(a: str, b: str) -> float:
    a2, b2 = simplify_title(a), simplify_title(b)
    if not a2 or not b2:
        return 0.0
    
    # If one title is much shorter, check if it's a substring of the other
    if len(a2) > len(b2) * 2:
        # b2 is much shorter, check if it's contained in a2
        if b2 in a2:
            return 0.8  # High score for substring match
    elif len(b2) > len(a2) * 2:
        # a2 is much shorter, check if it's contained in b2
        if a2 in b2:
            return 0.8  # High score for substring match
    
    # Standard similarity
    base_sim = SequenceMatcher(None, a2, b2).ratio()
    
    # Boost score if key terms match
    a_words = set(a2.split())
    b_words = set(b2.split())
    if a_words and b_words:
        intersection = a_words & b_words
        word_overlap = len(intersection) / max(len(a_words), len(b_words))
        # Combine sequence similarity with word overlap
        return 0.7 * base_sim + 0.3 * word_overlap
    
    return base_sim

def year_from_crossref(item: Dict[str, Any]) -> Optional[int]:
    # Crossref 'issued' or 'published-print' structure: {"date-parts": [[YYYY, MM, DD]]}
    for key in ("issued", "published-print", "published-online"):
        if key in item and "date-parts" in item[key] and item[key]["date-parts"]:
            y = item[key]["date-parts"][0][0]
            try:
                return int(y)
            except Exception:
                pass
    return None

def safe_get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def best_candidate_by_score(cands: List[Dict[str, Any]], title: str, authors: List[str], year: Optional[int], publisher: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], float]:
    best = None
    best_score = 0.0
    for it in cands:
        cr_title_list = it.get("title") or []
        cr_title = cr_title_list[0] if cr_title_list else ""
        sim = title_similarity(title, cr_title)
        
        # Debug for specific cases
        if "dowry" in title.lower() and "dowry" in cr_title.lower():
            print(f"  Debug: Original title: '{title}'")
            print(f"  Debug: Crossref title: '{cr_title}'")
            print(f"  Debug: Title similarity: {sim:.2f}")

        cr_year = year_from_crossref(it)
        year_score = 1.0 if (year and cr_year and abs(cr_year - year) <= 1) else 0.0

        cr_auth_last = [ (a.get("family") or "").lower() for a in (it.get("author") or []) if isinstance(a, dict) ]
        # Apply Unicode normalization to Crossref authors too
        unicode_map = {
            'ı': 'i',  # dotless i
            'ş': 's',  # s with cedilla
            'ç': 'c',  # c with cedilla
            'ğ': 'g',  # g with breve
            'ö': 'o',  # o with diaeresis
            'ü': 'u',  # u with diaeresis
            'İ': 'i',  # capital dotless i
            'Ş': 's',  # capital s with cedilla
            'Ç': 'c',  # capital c with cedilla
            'Ğ': 'g',  # capital g with breve
            'Ö': 'o',  # capital o with diaeresis
            'Ü': 'u',  # capital u with diaeresis
        }
        cr_auth_last = [name.translate(str.maketrans(unicode_map)) for name in cr_auth_last]
        if authors:
            inter = set(authors) & set(cr_auth_last)
            author_score = min(1.0, len(inter) / max(1, min(len(authors), 3)))
        else:
            author_score = 0.0
        
        # Debug for specific cases
        if "dowry" in title.lower() and "dowry" in cr_title.lower():
            print(f"  Debug: Original authors: {authors}")
            print(f"  Debug: Crossref authors: {cr_auth_last}")
            print(f"  Debug: Author intersection: {inter}")
            print(f"  Debug: Author score: {author_score:.2f}")

        # Publisher matching - more flexible
        cr_publisher = (it.get("publisher") or "").lower().strip()
        pub_score = 0.0
        if publisher and cr_publisher:
            pub_lower = publisher.lower().strip()
            # Exact match
            if pub_lower == cr_publisher:
                pub_score = 1.0
            # Contains match
            elif pub_lower in cr_publisher or cr_publisher in pub_lower:
                pub_score = 1.0
            # Common abbreviations
            elif (("acm" in pub_lower or "association for computing machinery" in pub_lower) and 
                  ("acm" in cr_publisher or "association for computing machinery" in cr_publisher)):
                pub_score = 1.0
            elif (("ieee" in pub_lower or "institute of electrical and electronics engineers" in pub_lower) and 
                  ("ieee" in cr_publisher or "institute of electrical and electronics engineers" in cr_publisher)):
                pub_score = 1.0
            elif (("springer" in pub_lower or "springer nature" in pub_lower) and 
                  ("springer" in cr_publisher or "springer nature" in cr_publisher)):
                pub_score = 1.0
            elif (("elsevier" in pub_lower) and ("elsevier" in cr_publisher)):
                pub_score = 1.0
            elif (("wiley" in pub_lower) and ("wiley" in cr_publisher)):
                pub_score = 1.0
            elif (("taylor" in pub_lower and "francis" in pub_lower) and 
                  ("taylor" in cr_publisher and "francis" in cr_publisher)):
                pub_score = 1.0
            elif (("oxford" in pub_lower and "press" in pub_lower) and 
                  ("oxford" in cr_publisher and "press" in cr_publisher)):
                pub_score = 1.0
            elif (("cambridge" in pub_lower and "press" in pub_lower) and 
                  ("cambridge" in cr_publisher and "press" in cr_publisher)):
                pub_score = 1.0

        score = 0.5*sim + 0.2*author_score + 0.15*year_score + 0.15*pub_score
        if score > best_score:
            best, best_score = it, score
    return best, best_score

# --- Query functions ---

def query_crossref(title: str, authors: List[str], year: Optional[int], rows: int = 8) -> List[Dict[str, Any]]:
    # Clean title for API query - remove special characters that cause issues
    clean_title = re.sub(r'[{}()\[\]]', '', title)  # Remove braces, parentheses, brackets
    clean_title = re.sub(r'[^\w\s]', ' ', clean_title)  # Replace other punctuation with space
    clean_title = norm_whitespace(clean_title)

    params = {
        "query.title": clean_title,
        "rows": rows,
        "select": "DOI,title,author,issued,container-title,publisher,page,article-number,volume,issue,type",
    }
    # lightweight filter on year for precision
    if year:
        params["filter"] = f"from-pub-date:{year-1},until-pub-date:{year+1}"
    headers = {
        "User-Agent": f"bib-doi-enricher/1.0 (mailto:{CONTACT_EMAIL})"
    }
    r = requests.get(CROSSREF_BASE, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    items = safe_get(data, "message", "items", default=[]) or []
    time.sleep(RATE_LIMIT_SLEEP)
    return items

def fetch_doi_metadata(doi: str) -> Optional[Dict[str, Any]]:
    """Fetch full metadata for a DOI from Crossref."""
    if not doi:
        return None
    # Strip prefix if present
    doi = doi.replace("https://doi.org/", "")
    url = f"{CROSSREF_BASE}/{doi}"
    headers = {
        "User-Agent": f"bib-doi-enricher/1.0 (mailto:{CONTACT_EMAIL})"
    }
    try:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        item = safe_get(data, "message", default={})
        time.sleep(RATE_LIMIT_SLEEP)
        return item
    except requests.RequestException:
        return None

def query_openalex(title: str, authors: List[str], year: Optional[int], per_page: int = 8) -> List[Dict[str, Any]]:
    # Clean title for API query
    clean_title = re.sub(r'[{}()\[\]]', '', title)
    clean_title = re.sub(r'[^\w\s]', ' ', clean_title)
    clean_title = norm_whitespace(clean_title)

    # OpenAlex search by title; returns items with 'doi', 'authorships', 'host_venue', 'publication_year'
    params = {
        "filter": f"title.search:{clean_title}",
        "per_page": per_page,
    }
    headers = {
        "User-Agent": f"bib-doi-enricher/1.0 (mailto:{CONTACT_EMAIL})"
    }
    r = requests.get(OPENALEX_BASE, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    results = data.get("results", []) or []
    # map to crossref-like structure for reuse
    items = []
    for res in results:
        oa_title = res.get("title") or ""
        oa_year = res.get("publication_year")
        oa_doi = res.get("doi")
        oa_auth = [{"family": (a.get("author", {}) or {}).get("display_name", "").split()[-1]} for a in (res.get("authorships") or [])]
        host = res.get("host_venue") or {}
        pub = host.get("publisher")
        cont = [host.get("display_name")] if host.get("display_name") else []
        pages = res.get("biblio", {}).get("first_page")
        last_page = res.get("biblio", {}).get("last_page")
        if pages and last_page:
            pages = f"{pages}-{last_page}"
        items.append({
            "DOI": (oa_doi or "").replace("https://doi.org/", ""),
            "title": [oa_title],
            "author": oa_auth,
            "issued": {"date-parts": [[oa_year]]} if oa_year else None,
            "container-title": cont,
            "publisher": pub,
            "page": pages,
            "article-number": res.get("biblio", {}).get("article_number"),
            "volume": res.get("biblio", {}).get("volume"),
            "issue": res.get("biblio", {}).get("issue"),
            "type": res.get("type")
        })
    time.sleep(RATE_LIMIT_SLEEP)
    return items

# --- Enrichment logic ---

ACM_PAGES_RE = re.compile(r"^\s*(\d+)\s*:\s*1\s*[-–—]\s*\1\s*:\s*(\d+)\s*$")

def pages_to_articleno_numpages(pages: str) -> Optional[Tuple[str, str]]:
    """
    Convert '138:1--138:12' -> ('138','12'), else None
    """
    if not pages:
        return None
    m = ACM_PAGES_RE.match(pages.replace("--", "-"))
    if m:
        articleno, last = m.group(1), m.group(2)
        try:
            numpages = int(last)
            return str(articleno), str(numpages)
        except Exception:
            return None
    return None

def infer_publisher_from_venue(venue: str) -> Optional[str]:
    """Infer publisher from venue name."""
    if not venue:
        return None
    venue_lower = venue.lower()
    for key, pub in VENUE_TO_PUBLISHER.items():
        if key.lower() in venue_lower:
            return pub
    return None

def normalize_publisher_address(entry: Dict[str, Any]) -> None:
    pub = entry.get("publisher")
    if not pub:
        # Try to infer from venue
        venue = entry.get("booktitle") or entry.get("journal") or ""
        inferred = infer_publisher_from_venue(venue)
        if inferred:
            entry["publisher"] = inferred
            pub = inferred
    if not pub:
        return
    
    pub_lower = pub.strip().lower()
    pub_norm = pub
    
    # Normalize common publisher names
    if "association for computing machinery" in pub_lower or pub_lower == "acm":
        pub_norm = "Association for Computing Machinery"
    elif "institute of electrical and electronics engineers" in pub_lower or pub_lower == "ieee":
        pub_norm = "IEEE"
    elif "springer" in pub_lower:
        if "nature" in pub_lower:
            pub_norm = "Springer Nature"
        else:
            pub_norm = "Springer"
    elif "elsevier" in pub_lower:
        pub_norm = "Elsevier"
    elif "wiley" in pub_lower:
        pub_norm = "Wiley"
    elif "cambridge university press" in pub_lower or ("cambridge" in pub_lower and "press" in pub_lower):
        pub_norm = "Cambridge University Press"
    elif "oxford university press" in pub_lower or ("oxford" in pub_lower and "press" in pub_lower):
        pub_norm = "Oxford University Press"
    elif "taylor" in pub_lower and "francis" in pub_lower:
        pub_norm = "Taylor & Francis"
    
    entry["publisher"] = pub_norm
    
    # Fill address if known - more flexible matching
    for key, addr in PUBLISHER_ADDRESS.items():
        if key.lower() in pub_norm.lower() or pub_norm.lower() in key.lower():
            if addr and not entry.get("address"):
                entry["address"] = addr
                print(f"  Debug: Set address '{addr}' for publisher '{pub_norm}'")
                break
            break

def enrich_entry(entry: Dict[str, Any], best: Dict[str, Any], acm_pages_to_article: bool = False) -> Dict[str, Any]:
    # copy to avoid mutating input
    e = dict(entry)

    # DOI
    doi = best.get("DOI")
    if doi:
        e["doi"] = doi

    # Journal / container
    cont = best.get("container-title") or best.get("short-container-title") or []
    if isinstance(cont, str):
        cont = [cont]
    if cont and not e.get("journal") and e.get("ENTRYTYPE","").lower() == "article":
        e["journal"] = cont[0]

    # volume/issue (number)
    if best.get("volume") and not e.get("volume"):
        e["volume"] = str(best["volume"])
    if best.get("issue") or best.get("journal-issue", {}).get("issue"):
        issue = best.get("issue") or best.get("journal-issue", {}).get("issue")
        # Only add issue to @article; @inproceedings doesn't need number
        if e.get("ENTRYTYPE","").lower() == "article" and not e.get("number"):
            e["number"] = str(issue)

    # ISSN/ISBN
    if best.get("issn") and not e.get("issn") and e.get("ENTRYTYPE","").lower() == "article":
        issn_list = best["issn"]
        if isinstance(issn_list, list) and issn_list:
            e["issn"] = issn_list[0]  # Take first ISSN
    if best.get("isbn") and not e.get("isbn"):
        isbn_list = best["isbn"]
        if isinstance(isbn_list, list) and isbn_list:
            e["isbn"] = isbn_list[0]  # Take first ISBN

    # pages or article-number
    cr_pages = best.get("page") or best.get("pages")
    cr_artno = best.get("article-number")
    if acm_pages_to_article and e.get("pages"):
        conv = pages_to_articleno_numpages(e.get("pages",""))
        if conv:
            artno, nump = conv
            e.pop("pages", None)
            e["articleno"] = artno
            e["numpages"] = nump
    else:
        if cr_artno and not e.get("articleno"):
            e["articleno"] = str(cr_artno)
        if cr_pages and not e.get("pages"):
            # normalize separator
            e["pages"] = cr_pages.replace("–", "--").replace("—", "--").replace("-", "--")

    # publisher
    cr_pub = best.get("publisher")
    if cr_pub and not e.get("publisher"):
        e["publisher"] = cr_pub

    # normalize publisher & address if we can infer
    normalize_publisher_address(e)

    # If @inproceedings has both volume and number, drop number
    if e.get("ENTRYTYPE","").lower() == "inproceedings" and e.get("volume") and e.get("number"):
        e.pop("number", None)

    return e

# --- Main processing ---

def process_bibtex(input_path: str, output_path: str, prefer_openalex: bool = True, acm_pages_to_article: bool = False, min_score: float = 0.65, interactive: bool = True):
    with open(input_path, "r", encoding="utf-8") as f:
        parser = BibTexParser(common_strings=True)
        db = bibtexparser.load(f, parser=parser)

    updated = 0
    total = len(db.entries)
    for e in db.entries:
        title = e.get("title") or ""
        authors = author_lastnames(e.get("author",""))
        year = None
        try:
            year = int(str(e.get("year","")).strip()[:4])
        except Exception:
            pass

        if not title.strip():
            print(f"- Skipping {e.get('ID')} (no title)")
            continue

        already_has_doi = bool(e.get("doi"))
        print(f"* {e.get('ID')} | title='{title[:60]}{'...' if len(title)>60 else ''}' | DOI: {'yes' if already_has_doi else 'no'}")

        items: List[Dict[str, Any]] = []
        try:
            if prefer_openalex:
                items = query_openalex(title, authors, year)
                if not items:
                    items = query_crossref(title, authors, year)
            else:
                items = query_crossref(title, authors, year)
                if not items:
                    items = query_openalex(title, authors, year)
        except requests.HTTPError as ex:
            print(f"  ! HTTP error: {ex}")
            continue
        except requests.RequestException as ex:
            print(f"  ! Request error: {ex}")
            continue

        if not items:
            print("  ! No candidates found.")
            if interactive:
                # Prompt for manual DOI
                manual_doi = prompt_text("Enter DOI manually (or leave blank to skip)", "")
                if manual_doi:
                    manual_doi = manual_doi.replace("https://doi.org/", "")
                    e["doi"] = manual_doi
                    # Fetch full metadata for manual DOI
                    full_meta = fetch_doi_metadata(manual_doi)
                    if full_meta:
                        selected_item = full_meta
                        new_e = enrich_entry(e, selected_item, acm_pages_to_article=acm_pages_to_article)
                        if new_e != e:
                            e.clear()
                            e.update(new_e)
                            updated += 1
                    else:
                        updated += 1  # At least DOI was added
            continue

        publisher = e.get("publisher")
        best, score = best_candidate_by_score(items, title, authors, year, publisher)
        selected_item = best
        if interactive and (not best or score < min_score):
            print(f"  ! Low confidence match (score={score:.2f}). Showing candidates.")
            choice = display_candidates(items, title, authors, year)
            if choice >= 0:
                selected_item = items[choice]
                print(f"  + Selected DOI: {selected_item.get('DOI')}")
            else:
                print("  - Skipped.")
                continue
        elif not interactive and (not best or score < min_score):
            print(f"  ! Low confidence match (score={score:.2f}). Skipping.")
            continue
        else:
            print(f"  + Matched DOI: {best.get('DOI')} (score={score:.2f}) via {'OpenAlex' if prefer_openalex else 'Crossref'}")

        # Fetch full metadata if DOI is available
        if selected_item and selected_item.get("DOI"):
            doi_clean = selected_item["DOI"].replace("https://doi.org/", "")
            full_meta = fetch_doi_metadata(doi_clean)
            if full_meta:
                # Merge full metadata into selected_item
                selected_item.update(full_meta)

        new_e = enrich_entry(e, selected_item, acm_pages_to_article=acm_pages_to_article)

        # Prompt for missing fields if interactive
        if interactive:
            if not new_e.get("publisher"):
                pub = prompt_text("Enter publisher", "")
                if pub:
                    new_e["publisher"] = pub
                    normalize_publisher_address(new_e)
            if not new_e.get("address") and new_e.get("publisher"):
                addr = prompt_text("Enter address", "")
                if addr:
                    new_e["address"] = addr
            if not new_e.get("pages") and not new_e.get("articleno"):
                pages = prompt_text("Enter pages (or leave blank)", "")
                if pages:
                    new_e["pages"] = pages
            # Only prompt for volume if metadata contains it or if it's an article
            entry_type = new_e.get("ENTRYTYPE", "").lower()
            if not new_e.get("volume") and (entry_type == "article" or (selected_item and selected_item.get("volume"))):
                vol = prompt_text("Enter volume (or leave blank)", "")
                if vol:
                    new_e["volume"] = vol
            if not new_e.get("number") and entry_type == "article":
                num = prompt_text("Enter number/issue (or leave blank)", "")
                if num:
                    new_e["number"] = num

        # Apply update
        if new_e != e:
            e.clear()
            e.update(new_e)
            updated += 1

    # Write out
    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = ("ID",)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(bibtexparser.dumps(db, writer))

    print(f"\nDone. Updated {updated}/{total} entries. Wrote: {output_path}")

def main():
    ap = argparse.ArgumentParser(description="Enrich BibTeX with DOIs and publisher/address/pages normalization.")
    ap.add_argument("input", help="Input .bib path")
    ap.add_argument("-o", "--output", required=True, help="Output .bib path")
    ap.add_argument("--prefer-openalex", action="store_true", help="Query OpenAlex first, then Crossref")
    ap.add_argument("--acm-pages-to-article", action="store_true", help="Convert '138:1--138:12' to articleno/numpages")
    ap.add_argument("--min-score", type=float, default=0.72, help="Minimum match score to accept (0-1)")
    ap.add_argument("--non-interactive", action="store_true", help="Run without interactive prompts")
    args = ap.parse_args()

    if CONTACT_EMAIL == "youremail@example.com":
        print("WARNING: Please edit CONTACT_EMAIL in the script to your email for polite API usage.", file=sys.stderr)

    process_bibtex(args.input, args.output, prefer_openalex=args.prefer_openalex, acm_pages_to_article=args.acm_pages_to_article, min_score=args.min_score, interactive=not args.non_interactive)

if __name__ == "__main__":
    main()