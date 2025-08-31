# PaperRef 📄➡️📝

**Integrated PDF to Markdown converter with automatic BibTeX generation for academic papers**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

PaperRef is a powerful tool that converts academic PDF papers to well-structured Markdown format while automatically extracting and generating complete BibTeX citations for all references.

## ✨ Features

### 🔄 PDF Processing
- **High-Quality Conversion**: Uses Docling for accurate PDF-to-Markdown conversion
- **Structured Output**: Preserves document structure, headings, tables, and formatting
- **Image Handling**: Flexible image processing with placeholder and VLM modes

### 📚 BibTeX Generation
- **Automatic Reference Extraction**: Parses REFERENCES sections from converted Markdown
- **Multi-Source BibTeX Search**: OpenAlex API (primary) + Google Scholar (fallback)
- **DOI-Based Search**: Prioritizes DOI when available for accurate matching
- **Google Scholar Style Keys**: Generates BibTeX keys in `Author+Year+FirstWord` format
- **Complete Metadata**: Extracts DOI, journal, volume, pages, publisher information

### 🗂️ Organization
- **Automatic Folder Creation**: Creates organized folder structure based on paper titles
- **Batch Processing**: Process multiple PDFs simultaneously
- **Flexible Output**: Customizable output directories and naming schemes

## 🚀 Installation

### Global Installation (Recommended)
```bash
# Install globally with uv (fast Python package manager)
uv tool install --python 3.12 git+https://github.com/alansynn/paperef.git

# Or install locally for development
uv tool install --python 3.12 .
```

### Virtual Environment Installation
```bash
# Create virtual environment (Python 3.10-3.12 recommended)
uv venv paperef_env --python 3.12
source paperef_env/bin/activate  # On Windows: paperef_env\Scripts\activate

# Install the package
uv pip install -e .
```

### Requirements
- **Python**: 3.10-3.12
- **Dependencies**: Docling, OpenAlex API, Selenium (optional for Google Scholar fallback)

## 📖 Usage

### Basic Conversion
```bash
# Convert single PDF to Markdown with BibTeX
paperef research_paper.pdf
```

### Advanced Options
```bash
# Full-featured conversion with verbose output
paperef research_paper.pdf \
  --output-dir ./my_papers \
  --image-mode placeholder \
  --bibtex-enhanced \
  --verbose

# Skip PDF conversion if Markdown already exists
paperef research_paper.pdf --skip-pdf

# BibTeX generation only
paperef research_paper.pdf --bibtex-only

# Interactive mode for manual BibTeX selection
paperef research_paper.pdf --interactive
```

### Batch Processing
```bash
# Process all PDFs in current directory
paperef *.pdf --batch --output-dir ./processed_papers

# Process PDFs from specific directory
paperef /path/to/pdfs/*.pdf --batch --output-dir ./output
```

### Output Structure
```
papers/
└── Paper Title/
    ├── paper.md                    # Converted Markdown
    ├── paper.bib                   # Main paper BibTeX
    ├── references.bib              # All reference BibTeX entries
    └── artifacts/                  # Extracted images
        ├── image_000001.png
        └── ...
```

## 🔧 Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output-dir` | Output directory | `./papers` |
| `--image-mode` | Image processing mode | `placeholder` |
| `--bibtex-enhanced` | Enhanced BibTeX generation | `false` |
| `--interactive` | Interactive BibTeX selection | `true` |
| `--skip-pdf` | Skip PDF conversion if MD exists | `false` |
| `--verbose` | Detailed output | `false` |
| `--batch` | Process multiple files | `false` |

## 🏗️ Architecture

```
paperef/
├── cli/                    # Command-line interface
│   └── main.py
├── core/                   # Core functionality
│   ├── pdf_processor.py    # PDF processing with Docling
│   └── bibtex_generator.py # BibTeX generation logic
├── bibtex/                 # BibTeX sources and scrapers
│   └── scholar_scraper.py  # OpenAlex + Google Scholar integration
├── utils/                  # Utilities
│   ├── config.py          # Configuration management
│   └── file_utils.py      # File operations
└── tests/                 # Test suite
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Submit a pull request

## 📋 Development

### Setup Development Environment
```bash
# Clone repository
git clone https://github.com/alansynn/paperef.git
cd paperef

# Install in development mode
uv pip install -e .

# Install development dependencies
uv pip install pytest black isort mypy
```

### Run Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=paperef
```

## 📚 BibTeX Examples

### Generated BibTeX Entry
```bibtex
@article{filip2023learning,
  title={Learning-Based Design and Control for Quadrupedal Robots With Parallel-Elastic Actuators},
  author={Bjelonic, Filip and Lee, Joonho and Arm, Philip and Sako, Dhionis and Tateo, Davide and Peters, Jan and Hutter, Marco},
  year={2023},
  doi={10.1109/lra.2023.3234809},
  journal={IEEE Robotics and Automation Letters},
  publisher={Institute of Electrical and Electronics Engineers},
  pages={1611--1618},
  volume={8},
  number={3},
}
```

### BibTeX Key Generation
- **Format**: `FirstAuthorLastName+Year+FirstWordOfTitle`
- **Example**: `Rod2017utap`, `Hammond2020msketch`, `Bjelonic2023learning`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Docling](https://github.com/DS4SD/docling) for PDF processing
- [OpenAlex](https://openalex.org/) for academic metadata
- [Google Scholar](https://scholar.google.com/) for BibTeX data
- Built with [uv](https://github.com/astral-sh/uv) for fast Python package management

---

**PaperRef** - Making academic paper processing automated and efficient! 🚀
