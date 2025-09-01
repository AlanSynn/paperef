# PaperRef 📄➡️📝

**Production-ready PDF to Markdown converter with intelligent BibTeX generation and automated organization**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

PaperRef is a comprehensive solution that transforms academic PDF papers into well-structured Markdown while automatically generating complete BibTeX citations. Features intelligent folder organization, and DOI enrichment.

## ✨ Features

### 🔄 Advanced PDF Processing
- **High-Quality Conversion**: Docling-powered PDF-to-Markdown with LLM-friendly structure
- **Title Extraction**: Multiple fallback strategies for accurate title detection
- **Image Processing**: Placeholder mode (default) with optional VLM integration
- **Metadata Extraction**: Complete extraction of title, authors, abstract, DOI, and keywords

### 📚 BibTeX Generation
- **Multi-Source BibTeX Search**: OpenAlex API (primary) + Google Scholar (fallback)
- **DOI Enrichment**: Automatic DOI discovery and metadata completion via Crossref
- **Google Scholar Style Keys**: `Author+Year+FirstWord` format with collision handling
- **Field Optimization**: Empty field cleanup, publisher address mapping, ACM page formatting
- **Publisher Integration**: Automatic address mapping for ACM, IEEE, Springer, etc.
- **Complete Metadata**: DOI, journal, volume, pages, publisher, abstract extraction

### 🗂️ Smart Organization & Management
- **Automatic Folder Creation**: Title-based folder generation with duplicate handling
- **Standardized Structure**: Organized layout with artifacts/, references/, metadata
- **Batch Processing**: Parallel processing with progress bars and error recovery
- **Caching System**: Caching with TTL for API optimization
- **File Management**: Automatic cleanup, validation, and folder structure maintenance

### 🛡️ Production-Ready Features
- **Comprehensive Error Handling**: Structured error logging with recovery strategies
- **Performance Monitoring**: Operation timing and resource usage tracking
- **Type Safety**: Full type hints and validation
- **Cross-Platform**: Windows, macOS, Linux support with filesystem safety
- **Modular Architecture**: Clean separation of concerns for maintainability

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
- **Python**: 3.12+
- **Dependencies**: Docling, OpenAlex API, Selenium (optional for Google Scholar fallback)

## 📖 Usage

### Basic Conversion
```bash
# Convert single PDF to Markdown with BibTeX
paperef research_paper.pdf
```

### Advanced Options
```bash
paperef research_paper.pdf \
  --output-dir ./my_papers \
  --image-mode placeholder \
  --bibtex-enhanced \
  --create-folders \
  --verbose

# BibTeX-only processing with DOI enrichment
paperef research_paper.pdf --bibtex-only --bibtex-enhanced

# Multiple files (processed sequentially)
paperef *.pdf --output-dir ./processed_papers --verbose

# Clean BibTeX output with field optimization
paperef research_paper.pdf --bibtex-clean --bibtex-enhanced

# Non-interactive mode for automated processing
paperef research_paper.pdf --no-interactive
```

### Multiple Files
```bash
# Process all PDFs in current directory (sequential)
paperef *.pdf --output-dir ./processed_papers

# Process PDFs from specific directory (sequential)
paperef /path/to/pdfs/*.pdf --output-dir ./output
```

### Output Structure
```
papers/
└── UTAP_Unique_Topologies_for_Acoustic_Propagation/
    ├── paper.md                    # Converted Markdown
    ├── paper.bib                   # Main paper BibTeX (DOI enriched)
    ├── references.bib              # All reference BibTeX entries
    ├── metadata.json               # Processing metadata and statistics
    ├── README.md                   # Auto-generated folder documentation
    ├── artifacts/                  # Extracted images
    │   ├── image_000001.png
    │   └── ...
    └── references/                 # Individual reference BibTeX files
        ├── Rod2017utap.bib
        ├── Collins2017utap.bib
        └── ...
```

## 🔧 Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output-dir` | Output directory | `./papers` |
| `--image-mode` | Image processing mode (`placeholder`, `vlm`) | `placeholder` |
| `--bibtex-enhanced` | DOI enrichment and field optimization | `false` |
| `--bibtex-clean` | Clean empty fields and optimize BibTeX | `false` |
| `--create-folders` | Auto-create title-based folders | `true` |
| `--folder-template` | Folder naming template | `{title}` |
| `--interactive` | Interactive BibTeX selection | `true` |
| `--no-interactive` | Non-interactive mode | `false` |
| `--skip-pdf` | Skip PDF conversion if MD exists | `false` |
| `--bibtex-only` | Generate BibTeX only | `false` |
| `--verbose` | Detailed output and logging | `false` |
| (removed) | Batch processing | — |
| `--cache-dir` | Cache directory for API responses | `./cache` |

### Cache & Performance
- **Automatic caching** of API responses with TTL
- **Batch processing** with parallel execution
- **Progress tracking** for long operations
- **Error recovery** and detailed logging

## 🏗️ Architecture

```
paperef/
├── cli/                    # Command-line interface
│   └── main.py            # Typer-based CLI with Rich UI
├── core/                   # Core processing modules
│   ├── pdf_processor.py    # Docling-powered PDF processing
│   ├── bibtex_generator.py # BibTeX generation & key creation
│   ├── doi_enricher.py     # DOI enrichment & field optimization
│   ├── folder_manager.py   # Auto folder creation & management
│   ├── cache_manager.py    # Intelligent caching system
│   └── (removed) batch_processor.py  # Batch processing removed
├── bibtex/                 # BibTeX sources & scrapers
│   └── scholar_scraper.py  # OpenAlex + Google Scholar integration
├── utils/                  # Utilities & infrastructure
│   ├── config.py          # Configuration management
│   ├── file_utils.py      # File operations & validation
│   ├── logging_config.py  # Enhanced logging & error handling
│   └── performance.py     # Performance monitoring
└── tests/                 # Comprehensive test suite
    ├── test_*.py         # 143+ unit & integration tests
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

### Enhanced BibTeX Entry (with DOI Enrichment)
```bibtex
@inproceedings{Rod2017utap,
  title={UTAP: Unique Topologies for Acoustic Propagation},
  author={Rod, Jan and Collins, David and Wessolek, Daniel},
  booktitle={Proceedings of the 2017 ACM International Conference on Interactive Surfaces and Spaces},
  pages={138--147},
  year={2017},
  organization={ACM},
  doi={10.1145/3132272.3132277},
  address={New York, NY, USA},
  publisher={Association for Computing Machinery}
}
```

### Optimized BibTeX Entry (Field Cleanup)
```bibtex
@article{Bjelonic2023learning,
  title={Learning-Based Design and Control for Quadrupedal Robots With Parallel-Elastic Actuators},
  author={Bjelonic, Filip and Lee, Joonho and Arm, Philip and Sako, Dhionis and Tateo, Davide and Peters, Jan and Hutter, Marco},
  journal={IEEE Robotics and Automation Letters},
  volume={8},
  number={3},
  pages={1611--1618},
  year={2023},
  doi={10.1109/LRA.2023.3234809},
  publisher={Institute of Electrical and Electronics Engineers},
  address={Piscataway, NJ, USA}
}
```

### BibTeX Key Generation
- **Format**: `FirstAuthorLastName+Year+FirstWordOfTitle`
- **Example**: `Rod2017utap`, `Hammond2020msketch`, `Bjelonic2023learning`

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Docling](https://github.com/DS4SD/docling) for high-quality PDF processing
- [OpenAlex](https://openalex.org/) for comprehensive academic metadata
- [Crossref](https://www.crossref.org/) for DOI resolution and metadata
- [Google Scholar](https://scholar.google.com/) for BibTeX data and fallbacks
- [bibtexparser](https://github.com/sciunto-org/python-bibtexparser) for BibTeX handling
- [Rich](https://github.com/Textualize/rich) for beautiful terminal interfaces
- [Loguru](https://github.com/Delgan/loguru) for advanced logging
- Built with [uv](https://github.com/astral-sh/uv) for fast Python package management

*Built with ❤️ by Alan*
