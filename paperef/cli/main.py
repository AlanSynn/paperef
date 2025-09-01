
"""
PaperRef main CLI interface using Typer
"""

import glob
import sys
import traceback
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from paperef.core.bibtex_generator import BibTeXGenerator
from paperef.core.pdf_processor import PDFProcessor
from paperef.utils.config import Config
from paperef.utils.file_utils import ensure_directory
from paperef.utils.logging_config import get_logger, setup_logging

console = Console()
app = typer.Typer(
    name="paperef",
    help="PDF to Markdown converter with automatic BibTeX generation",
    add_completion=False,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    input_files: list[Path] = typer.Argument(
        None,
        help="Input PDF file(s) or glob pattern",
    ),
    output_dir: Path = typer.Option(
        "./papers",
        "--output-dir",
        "-o",
        help="Output directory",
        file_okay=False,
        dir_okay=True,
    ),
    image_mode: str = typer.Option(
        "placeholder",
        "--image-mode",
        help="Image processing mode",
        callback=lambda x: x if x in ["placeholder", "vlm"] else typer.BadParameter("Must be 'placeholder' or 'vlm'"),
    ),
    bibtex_only: bool = typer.Option(
        False,
        "--bibtex-only",
        help="Generate BibTeX only (skip MD conversion)",
    ),
    bibtex_enhanced: bool = typer.Option(
        False,
        "--bibtex-enhanced",
        help="Enable DOI enrichment and field optimization",
    ),
    bibtex_clean: bool = typer.Option(
        False,
        "--bibtex-clean",
        help="Clean empty fields and unnecessary items",
    ),
    cache_dir: Path = typer.Option(
        "./cache",
        "--cache-dir",
        help="Cache directory path",
        file_okay=False,
        dir_okay=True,
    ),
    # Removed: --batch option (sequential processing is default for multiple inputs)
    create_folders: bool = typer.Option(
        True,
        "--create-folders/--no-create-folders",
        help="Create title-based folders automatically",
    ),
    folder_template: str = typer.Option(
        "{title}",
        "--folder-template",
        help="Folder name template",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output",
    ),
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        help="Interactive mode for BibTeX ambiguity resolution",
    ),
    skip_pdf: bool = typer.Option(
        False,
        "--skip-pdf",
        help="Skip PDF conversion if markdown file already exists",
    ),
):
    """
    Process PDF files to Markdown with BibTeX generation.
    """
    # If no input files provided, show help
    if ctx.invoked_subcommand is None and (input_files is None or len(input_files) == 0):
        typer.echo(ctx.get_help())
        return

    # Filter out option-like arguments from input files
    if input_files:
        filtered_files = []
        for f in input_files:
            if isinstance(f, str) and f.startswith("-"):
                continue  # Skip option-like arguments
            filtered_files.append(f)
        input_files = filtered_files if filtered_files else None

    if not input_files:
        console.print("[red]Error: No input files provided[/red]")
        console.print("Usage: paperef [OPTIONS] INPUT_FILES...")
        return

    # Create configuration
    config = Config(
        output_dir=str(output_dir),
        image_mode=image_mode,
        bibtex_only=bibtex_only,
        bibtex_enhanced=bibtex_enhanced,
        bibtex_clean=bibtex_clean,
        cache_dir=str(cache_dir),
        create_folders=create_folders,
        folder_template=folder_template,
        verbose=verbose,
        interactive=interactive,
        no_interactive=not interactive,
        skip_pdf=skip_pdf
    )

    # Set up logging
    log_file = Path(config.cache_dir) / "paperef.log" if config.verbose else None
    setup_logging(config, log_file)
    get_logger("cli")

    # Validate and expand input files
    valid_files = validate_input_files(input_files)

    # Create output and cache directories
    ensure_directory(config.output_dir)
    ensure_directory(config.cache_dir)

    console.print(f"[bold blue]PaperRef v{__import__('paperef').__version__}[/bold blue]")
    console.print(f"Processing {len(valid_files)} PDF file(s)")
    console.print()

    # Initialize processors
    processor = PDFProcessor(config)
    bibtex_gen = BibTeXGenerator(config)

    # Process files
    success_count = 0
    total_count = len(valid_files)

    # Process files sequentially (batch removed)
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Processing files...", total=total_count)

        for pdf_path in valid_files:
            if process_single_file(pdf_path, config, processor, bibtex_gen):
                success_count += 1
            progress.advance(task)

    # Summary of results
    console.print()
    console.print(f"[bold green]Completed: {success_count}/{total_count} files processed successfully[/bold green]")

    if success_count < total_count:
        console.print(f"[yellow]Warning: {total_count - success_count} files failed to process[/yellow]")

    # Exit with appropriate code
    sys.exit(0 if success_count > 0 else 1)


def validate_input_files(input_files: list[Path]) -> list[Path]:
    """Validate input files and expand glob patterns"""
    valid_files = []

    for file_pattern in input_files:
        if file_pattern.is_file() and file_pattern.suffix.lower() == ".pdf":
            valid_files.append(file_pattern)
        elif "*" in str(file_pattern) or "?" in str(file_pattern):
            # Glob pattern processing
            matches = glob.glob(str(file_pattern))
            for match in matches:
                match_path = Path(match)
                if match_path.is_file() and match_path.suffix.lower() == ".pdf":
                    valid_files.append(match_path)
        else:
            console.print(f"[red]Warning: {file_pattern} is not a valid PDF file[/red]")

    if not valid_files:
        console.print("[red]Error: No valid PDF files found[/red]")
        typer.Exit(1)

    return valid_files


def process_single_file(
    pdf_path: Path,
    config: Config,
    processor: PDFProcessor,
    bibtex_gen: BibTeXGenerator
) -> bool:
    """Process a single PDF file"""
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
                with open(md_file, encoding="utf-8") as f:
                    markdown_content = f.read()
            else:

                with console.status("[bold green]Converting PDF to Markdown..."):
                    markdown_content, image_paths = processor.convert_to_markdown(
                        pdf_path, output_dir, config.image_mode
                    )


                with open(md_file, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

                console.print(f"[green]✓ Markdown saved: {md_file}[/green]")

                if image_paths:
                    console.print(f"[green]✓ Images extracted: {len(image_paths)} files[/green]")


        with console.status("[bold green]Generating main paper BibTeX..."):
            bibtex_content = bibtex_gen.generate_from_pdf(pdf_path, config, output_dir)

        if bibtex_content:
            console.print(f"[green]✓ Main paper BibTeX saved: {output_dir}/paper.bib[/green]")


            if not config.bibtex_only and markdown_content:
                with console.status("[bold green]Generating references BibTeX file..."):
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
            console.print(traceback.format_exc())
        return False


if __name__ == "__main__":
    app()
