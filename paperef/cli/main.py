
"""
Paper2MD 메인 CLI 인터페이스
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.pdf_processor import PDFProcessor
from ..core.bibtex_generator import BibTeXGenerator
from ..utils.config import Config
from ..utils.file_utils import ensure_directory

console = Console()


def parse_args() -> argparse.Namespace:
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="Paper2MD: PDF to Markdown converter with automatic BibTeX generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 기본 변환
  paperef input.pdf

  # 고급 옵션들
  paperef input.pdf --output-dir ./output --image-mode vlm --verbose

  # BibTeX만 생성
  paperef input.pdf --bibtex-only

  # 배치 처리
  paperef *.pdf --batch --output-dir ./papers
        """
    )

    parser.add_argument(
        "input_files",
        nargs="+",
        help="Input PDF file(s) or glob pattern"
    )

    parser.add_argument(
        "--output-dir",
        default="./papers",
        help="Output directory (default: ./papers)"
    )

    parser.add_argument(
        "--image-mode",
        choices=["placeholder", "vlm"],
        default="placeholder",
        help="Image processing mode: 'placeholder' (default, recommended) or 'vlm'"
    )

    parser.add_argument(
        "--bibtex-only",
        action="store_true",
        help="Generate BibTeX only (skip MD conversion)"
    )

    parser.add_argument(
        "--bibtex-enhanced",
        action="store_true",
        help="Enable DOI enrichment and field optimization"
    )

    parser.add_argument(
        "--bibtex-clean",
        action="store_true",
        help="Clean empty fields and unnecessary items"
    )

    parser.add_argument(
        "--cache-dir",
        default="./cache",
        help="Cache directory path"
    )

    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch process multiple files"
    )

    parser.add_argument(
        "--create-folders",
        action="store_true",
        default=True,
        help="Create title-based folders automatically"
    )

    parser.add_argument(
        "--folder-template",
        default="{title}",
        help="Folder name template (default: {title})"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output"
    )

    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Non-interactive mode for BibTeX ambiguity resolution"
    )

    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="Skip PDF conversion if markdown file already exists"
    )

    return parser.parse_args()


def validate_input_files(input_files: List[str]) -> List[Path]:
    """입력 파일 검증 및 Path 객체 변환"""
    valid_files = []

    for file_pattern in input_files:
        path = Path(file_pattern)

        if path.is_file() and path.suffix.lower() == ".pdf":
            valid_files.append(path)
        elif "*" in str(path) or "?" in str(path):
            # Glob 패턴 처리
            import glob
            matches = glob.glob(str(path))
            for match in matches:
                match_path = Path(match)
                if match_path.is_file() and match_path.suffix.lower() == ".pdf":
                    valid_files.append(match_path)
        else:
            console.print(f"[red]Warning: {path} is not a valid PDF file[/red]")

    if not valid_files:
        console.print("[red]Error: No valid PDF files found[/red]")
        sys.exit(1)

    return valid_files


def process_single_file(
    pdf_path: Path,
    config: Config,
    processor: PDFProcessor,
    bibtex_gen: BibTeXGenerator
) -> bool:
    """단일 PDF 파일 처리"""
    try:
        console.print(f"[blue]Processing: {pdf_path.name}[/blue]")


        if config.create_folders:

            title = processor.extract_title(pdf_path)
            if title:
                folder_name = config.folder_template.format(title=title)
                output_dir = Path(config.output_dir) / folder_name
            else:
                output_dir = Path(config.output_dir) / pdf_path.stem
        else:
            output_dir = Path(config.output_dir)

        ensure_directory(output_dir)


        markdown_content = None
        md_file = output_dir / "paper.md"

        if not config.bibtex_only:
            if config.skip_pdf and md_file.exists():

                console.print(f"[blue]⏭️  Skipping PDF conversion - using existing: {md_file}[/blue]")
                with open(md_file, "r", encoding="utf-8") as f:
                    markdown_content = f.read()
            else:

                with console.status("[bold green]Converting PDF to Markdown...") as status:
                    markdown_content, image_paths = processor.convert_to_markdown(
                        pdf_path, output_dir, config.image_mode
                    )


                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

                console.print(f"[green]✓ Markdown saved: {md_file}[/green]")

                if image_paths:
                    console.print(f"[green]✓ Images extracted: {len(image_paths)} files[/green]")


        with console.status("[bold green]Generating main paper BibTeX...") as status:
            bibtex_content = bibtex_gen.generate_from_pdf(pdf_path, config, output_dir)

        if bibtex_content:
            console.print(f"[green]✓ Main paper BibTeX saved: {output_dir}/paper.bib[/green]")


            if not config.bibtex_only and markdown_content:
                with console.status("[bold green]Generating references BibTeX file...") as status:
                    references_file = bibtex_gen.generate_from_markdown_references(
                        markdown_content, output_dir, config
                    )

                if references_file:
                    console.print(f"[green]✓ References BibTeX saved: {output_dir}/references.bib[/green]")
                else:
                    console.print("[yellow]⚠ No references BibTeX file generated[/yellow]")
        else:
            console.print("[yellow]⚠ No BibTeX entries generated[/yellow]")

        return True

    except Exception as e:
        console.print(f"[red]Error processing {pdf_path.name}: {e}[/red]")
        if config.verbose:
            import traceback
            console.print(traceback.format_exc())
        return False


def main() -> int:
    """메인 함수"""
    try:
        args = parse_args()

        # 설정 생성
        config = Config(
            output_dir=args.output_dir,
            image_mode=args.image_mode,
            bibtex_only=args.bibtex_only,
            bibtex_enhanced=args.bibtex_enhanced,
            bibtex_clean=args.bibtex_clean,
            cache_dir=args.cache_dir,
            create_folders=args.create_folders,
            folder_template=args.folder_template,
            verbose=args.verbose,
            interactive=not args.no_interactive,
            no_interactive=args.no_interactive,
            skip_pdf=args.skip_pdf
        )

        # 출력 디렉토리 생성
        ensure_directory(config.output_dir)
        ensure_directory(config.cache_dir)

        # 입력 파일 검증
        input_files = validate_input_files(args.input_files)

        console.print(f"[bold blue]Paper2MD v{__import__('paperef').__version__}[/bold blue]")
        console.print(f"Processing {len(input_files)} PDF file(s)")
        console.print()

        # 프로세서 초기화
        processor = PDFProcessor(config)
        bibtex_gen = BibTeXGenerator(config)

        # 파일 처리
        success_count = 0
        total_count = len(input_files)

        if len(input_files) == 1:
            # 단일 파일 처리
            if process_single_file(input_files[0], config, processor, bibtex_gen):
                success_count = 1
        else:
            # 배치 처리
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Processing files...", total=total_count)

                for pdf_path in input_files:
                    if process_single_file(pdf_path, config, processor, bibtex_gen):
                        success_count += 1
                    progress.advance(task)

        # 결과 요약
        console.print()
        console.print(f"[bold green]Completed: {success_count}/{total_count} files processed successfully[/bold green]")

        if success_count < total_count:
            console.print(f"[yellow]Warning: {total_count - success_count} files failed to process[/yellow]")

        return 0 if success_count > 0 else 1

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 130
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        if args.verbose:
            import traceback
            console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
