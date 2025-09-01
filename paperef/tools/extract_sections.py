#!/usr/bin/env python3
"""
Extract specific sections from research papers.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"

SECTION_DIRS = {
    "abstract": "abstract",
    "introduction": "introduction",
    "background-related-work": "background-related-work",
    "methods": "methods",
    "implementation-system": "implementation-system",
    "evaluation": "evaluation",
    "results": "results",
    "discussion": "discussion",
    "conclusion": "conclusion",
    "ethics": "ethics",
    "keywords": "keywords",
    "limitations": "limitations",
    "future-work": "future-work",
    "applications": "applications",
    "other": "other",
}

# Build synonyms map to normalized keys
SYNONYMS = {
    "abstract": {
        "abstract", "a b s t r a c t",
    },
    "introduction": {
        "introduction", "1 introduction", "1. introduction",
        "introducti on",  # occasional OCR spacing
    },
    "background-related-work": {
        "related work", "background", "background and related work",
        "literature review", "overview of related research", "2 background",
        "2 related work", "2. related work", "backgrounds & design rationale",
    },
    "methods": {
        "methods", "method", "materials and methods", "methodology", "study design",
        "evaluation methodology", "procedure", "measures", "participants",
    },
    "implementation-system": {
        "implementation", "system", "system overview", "design and implementation",
        "implementation details", "interface construction",
        "acoustic sweep sensing and interaction recognition",
        "sensing method", "problem formulation and parameterization",
        "algorithmic pipeline", "implementation and fabrication",
        "fabrication and new materials",
    },
    "evaluation": {
        "evaluation", "technical evaluation",
        "evaluation and results", "results and evaluation",
    },
    "results": {
        "results", "findings", "evaluation results",
    },
    "discussion": {
        "discussion", "analysis", "reflections and lessons learned",
    },
    "conclusion": {
        "conclusion", "conclusions", "concluding remarks", "future work and conclusion",
    },
    "limitations": {
        "limitations", "limitation", "threats to validity",
        "materials and manufacturing", "general limitations",
    },
    "future-work": {
        "future work", "future directions", "next steps",
    },
    "applications": {
        "applications", "possible applications", "use cases", "application scenarios",
    },
    "ethics": {
        "ethics", "ethical considerations", "ethics, inclusivity, and data governance",
    },
    "keywords": {
        "keywords", "author keywords",
        "acm classification keywords", "a r t i c l e i n f o",
    },
}

# Create reverse lookup map
LOOKUP = {}
for key, variants in SYNONYMS.items():
    for v in variants:
        LOOKUP[v] = key

HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*$")

NUM_PREFIX_RE = re.compile(r"^(\d+\.?\s*)+")

SPACES_ONLY_RE = re.compile(r"\s+")


def norm_title(title: str) -> str:
    t = title.strip().lower()
    # remove surrounding punctuation
    t = re.sub(r"[\u2013\u2014\-–—]*$", "", t).strip()
    # remove numbering prefixes like "1 ", "2.3 ", etc.
    t = NUM_PREFIX_RE.sub("", t)
    # collapse internal multiple spaces
    return SPACES_ONLY_RE.sub(" ", t).strip()


def map_section(title: str) -> str:
    t = norm_title(title)
    # exact match
    if t in LOOKUP:
        return LOOKUP[t]
    # partial contains checks
    for key, variants in SYNONYMS.items():
        for v in variants:
            if v in t:
                return key
    # heuristics for combined sections
    if "evaluation" in t and "result" in t:
        return "evaluation"
    return "other"


def split_sections(text: str):
    lines = text.splitlines()
    sections = []  # list of (title, start_idx, end_idx)
    current = None
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            title = m.group("title").strip()
            if current is not None:
                # close previous
                current[2] = i
                sections.append(tuple(current))
            current = [title, i + 1, len(lines)]  # start after heading line
    if current is not None:
        sections.append(tuple(current))
    return sections, lines


def is_paper_file(path: Path) -> bool:
    name = path.name
    if not name.endswith(".md"):
        return False
    if name.startswith("image_"):
        return False
    if name.endswith("_artifacts.md"):
        return False
    return name not in {"HCI_paper_writing_guide.md", "list.md"}


def write_section(out_dir: Path, paper: str, section_key: str, content: str):
    out_path = out_dir / SECTION_DIRS[section_key] / f"{paper} - {section_key}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content.strip() + "\n", encoding="utf-8")


def slugify(text: str) -> str:
    t = text.lower()
    t = re.sub(r"[^a-z0-9\-\s_]", "", t)
    t = re.sub(r"[\s_]+", "-", t).strip("-")
    return t[:80]


def main():
    md_files = [p for p in ROOT.iterdir() if is_paper_file(p)]
    for out_sub in SECTION_DIRS.values():
        (EXAMPLES / out_sub).mkdir(parents=True, exist_ok=True)

    for md in md_files:
        text = md.read_text(encoding="utf-8", errors="ignore")
        sections, lines = split_sections(text)
        paper_name = md.stem
        counters = dict.fromkeys(SECTION_DIRS.keys(), 0)
        last_canonical = None
        # If no headings found, treat whole file as other
        if not sections:
            write_section(EXAMPLES, paper_name, "other", text)
            continue
        for title, start, end in sections:
            mapped = map_section(title)
            if mapped != "other":
                last_canonical = mapped
            sect_key = mapped if mapped != "other" and mapped in SECTION_DIRS else (
                last_canonical if last_canonical else "other"
            )
            content = "\n".join(lines[start:end]).strip()
            if not content:
                continue
            # increment index to avoid overwrites for repeated sections
            counters[sect_key] += 1
            idx = counters[sect_key]
            slug = slugify(title)
            out_dir = EXAMPLES / SECTION_DIRS[sect_key]
            out_file = out_dir / f"{paper_name} - {sect_key} - {idx:02d}-{slug}.md"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file.write_text(f"## {title}\n\n{content}\n", encoding="utf-8")

    print(f"Processed {len(md_files)} files.")


if __name__ == "__main__":
    main()
