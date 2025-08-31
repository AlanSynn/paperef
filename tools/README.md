# Research Tools

Collection of tools for processing research papers and extracting bibliographic information.

## Available Tools

### 1. BibTeX Extractor (Selenium-based) - **RECOMMENDED**

**File**: `extract_bibtex_selenium.py`

Extracts BibTeX citations from Google Scholar using Selenium WebDriver. This is the most reliable method as it directly interacts with Google Scholar's web interface.

**Features:**
- Direct Google Scholar interaction via browser automation
- Handles CAPTCHAs (manual intervention when needed)
- Caches results to avoid repeated queries
- Supports both headless and visible browser modes
- Ultra-fast turbo mode for quick processing
- Resume from specific reference index

**Usage:**

```bash
# Basic usage (headless mode)
uv run python tools/extract_bibtex_selenium.py \
  --input /absolute/path/to/source.md \
  --output /absolute/path/to/output.bib

# Show browser for manual CAPTCHA solving
uv run python tools/extract_bibtex_selenium.py \
  --input /absolute/path/to/source.md \
  --output /absolute/path/to/output.bib \
  --show-browser

# Ultra-fast turbo mode
uv run python tools/extract_bibtex_selenium.py \
  --input /absolute/path/to/source.md \
  --output /absolute/path/to/output.bib \
  --turbo --show-browser

# Custom speed settings
uv run python tools/extract_bibtex_selenium.py \
  --input /absolute/path/to/source.md \
  --output /absolute/path/to/output.bib \
  --sleep-min 0.5 --sleep-max 1.0 --show-browser

# Process only first 5 references
uv run python tools/extract_bibtex_selenium.py \
  --input /absolute/path/to/source.md \
  --output /absolute/path/to/output.bib \
  --max 5 --show-browser

# Resume from reference #10
uv run python tools/extract_bibtex_selenium.py \
  --input /absolute/path/to/source.md \
  --output /absolute/path/to/output.bib \
  --start-from 10 --show-browser
```

**Options:**
- `--sleep-min/--sleep-max`: Control wait times between requests (default: 0.5-1.0s)
- `--turbo`: Ultra-fast mode with 0.1-0.3s delays
- `--show-browser`: Show browser window (useful for CAPTCHA solving)
- `--max N`: Process only first N references
- `--start-from N`: Resume from reference index N
- `--refresh`: Ignore cache and fetch fresh
- `--cache PATH`: Custom cache file path

### 2. DOI-based BibTeX Extractor

**File**: `extract_doi_bibtex.py`

Extracts BibTeX citations by searching for DOIs and fetching from publishers' APIs.

**Usage:**
```bash
uv run python tools/extract_doi_bibtex.py \
  --input /absolute/path/to/source.md \
  --output /absolute/path/to/output.bib
```

### 3. Section Extractor

**File**: `extract_sections.py`

Extracts specific sections (abstract, introduction, conclusion, etc.) from research papers.

**Usage:**
```bash
uv run python tools/extract_sections.py \
  --input /absolute/path/to/paper.md \
  --sections abstract,introduction,conclusion
```

## Installation

1. Install dependencies:
```bash
uv pip install -r tools/requirements.txt
```

2. For Selenium-based extractor, install ChromeDriver:
```bash
# macOS
brew install chromedriver

# Or download from https://chromedriver.chromium.org/
```

## Input Format

All tools expect markdown files with a `## REFERENCES` section containing references in this format:

```markdown
## REFERENCES

- Author1, A., & Author2, B. (2023). Paper Title. Conference/Journal Name.
- Author3, C. (2022). Another Paper Title. Journal Name, 15(3), 123-145.
```

## Output Format

- **BibTeX files** (`.bib`): Raw BibTeX entries separated by blank lines
- **Markdown files** (`.md`): BibTeX entries wrapped in code blocks

## Cache System

All tools use a JSON cache file (`.bib_cache.json`) to store fetched results and avoid repeated queries. Use `--refresh` to ignore cache and fetch fresh data.

## Troubleshooting

### Google Scholar Issues
- **CAPTCHA**: Use `--show-browser` to manually solve CAPTCHAs
- **Rate limiting**: Increase `--sleep-min/--sleep-max` values
- **No results**: Check if paper titles are correctly parsed from references

### Performance Tips
- Use `--turbo` for fastest processing (risk of rate limiting)
- Process in batches with `--max` option
- Use cache effectively (don't use `--refresh` unless necessary)
- Resume interrupted runs with `--start-from`

### ChromeDriver Issues
- Ensure ChromeDriver version matches your Chrome browser
- Update ChromeDriver: `brew upgrade chromedriver` (macOS)

## Best Practices

1. **Start small**: Test with `--max 3` first
2. **Show browser**: Use `--show-browser` for initial runs to monitor progress
3. **Be respectful**: Use reasonable sleep times to avoid overwhelming Google Scholar
4. **Cache results**: Don't use `--refresh` unless necessary
5. **Resume interrupted runs**: Use `--start-from` to continue where you left off

## Example Workflow

```bash
# 1. Test with first 3 references
uv run python tools/extract_bibtex_selenium.py \
  --input paper.md --output test.bib --max 3 --show-browser

# 2. Process all references (using cache from step 1)
uv run python tools/extract_bibtex_selenium.py \
  --input paper.md --output complete.bib --show-browser

# 3. If interrupted, resume from where it stopped
uv run python tools/extract_bibtex_selenium.py \
  --input paper.md --output complete.bib --start-from 25 --show-browser
```