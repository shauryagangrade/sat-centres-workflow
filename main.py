"""
SAT Centre Updater - Main Entry Point

Rich-powered CLI interface for the SAT Centre Updater pipeline.
Supports both interactive menu mode and command-line argument mode.

Usage:
    python main.py                  # Interactive menu
    python main.py --full           # Full pipeline
    python main.py --paste-curl     # Interactive cURL paste
    python main.py --curl-file X    # cURL from file
    python main.py --download       # Download only
    python main.py --normalize      # Normalize only
    python main.py --geocode        # Geocode only
    python main.py --validate       # Validate only
    python main.py --update         # Update dataset only
    python main.py --reports        # Generate reports only
    python main.py --resume         # Resume failed centres
"""

import argparse
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Optional


# Setup logging before imports that might fail
def setup_logging(log_level: str = "INFO") -> None:
    """Configure logging to file and console."""
    from config import settings

    log_dir = settings.PATHS.LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"sat_updater_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sat_updater",
        description="SAT Centre Updater — Automatically download, geocode, and update SAT examination centres.",
    )

    # Pipeline modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--full", action="store_true", help="Run the full pipeline end-to-end"
    )
    mode_group.add_argument(
        "--download", action="store_true", help="Download SAT data only"
    )
    mode_group.add_argument(
        "--normalize", action="store_true", help="Normalize downloaded data only"
    )
    mode_group.add_argument(
        "--geocode", action="store_true", help="Geocode centres only"
    )
    mode_group.add_argument(
        "--validate", action="store_true", help="Validate geocoded centres only"
    )
    mode_group.add_argument(
        "--update", action="store_true", help="Update the final dataset only"
    )
    mode_group.add_argument(
        "--reports", action="store_true", help="Generate reports only"
    )
    mode_group.add_argument(
        "--resume", action="store_true", help="Resume failed centres from previous run"
    )

    # cURL input
    curl_group = parser.add_mutually_exclusive_group()
    curl_group.add_argument(
        "--paste-curl", action="store_true", help="Paste cURL interactively"
    )
    curl_group.add_argument(
        "--curl-file", type=str, help="Path to file containing cURL command"
    )

    # Options
    parser.add_argument(
        "--force-geocode", action="store_true", help="Force re-geocoding of all centres"
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )
    parser.add_argument(
        "--confidence", type=float, help="Override confidence threshold"
    )
    parser.add_argument("--workers", type=int, help="Override max geocoding workers")
    parser.add_argument(
        "--transform",
        action="store_true",
        help="Apply schema transformation after normalize",
    )
    parser.add_argument(
        "--sample-json",
        type=str,
        help="Path to file containing sample JSON for schema transformation",
    )

    return parser


def interactive_menu() -> None:
    """Display and handle the interactive Rich-powered menu."""
    try:
        from rich.console import Console
        from rich.prompt import Prompt
        from rich.table import Table
    except ImportError:
        print("Error: 'rich' package not installed. Run: pip install rich")
        return

    console = Console()

    menu_options = [
        ("1", "Download SAT Data"),
        ("2", "Normalize"),
        ("3", "Geocode"),
        ("4", "Validate"),
        ("5", "Update Dataset"),
        ("6", "Reports"),
        ("7", "Resume Failed"),
        ("8", "Full Pipeline"),
        ("9", "Transform to Custom Schema"),
        ("0", "Exit"),
    ]

    while True:
        console.print()
        table = Table(
            title="SAT Centre Updater", show_header=False, border_style="cyan"
        )
        table.add_column("Option", style="bold yellow", width=8)
        table.add_column("Action", style="white")

        for num, action in menu_options:
            table.add_row(num, action)

        console.print(table)

        choice = Prompt.ask(
            "\n[bold cyan]Select option[/bold cyan]",
            choices=[opt[0] for opt in menu_options],
            default="0",
        )

        if choice == "0":
            console.print("[green]Goodbye![/green]")
            break
        elif choice == "1":
            run_download_interactive()
        elif choice == "2":
            run_normalize()
        elif choice == "3":
            run_geocode()
        elif choice == "4":
            run_validate()
        elif choice == "5":
            run_update()
        elif choice == "6":
            run_reports()
        elif choice == "7":
            run_resume()
        elif choice == "8":
            run_full_pipeline_interactive()
        elif choice == "9":
            run_transform_interactive()


def run_download_interactive() -> None:
    """Run the download step with interactive cURL input."""
    try:
        from rich.console import Console
        from rich.panel import Panel
    except ImportError:
        print("Error: 'rich' package not installed. Run: pip install rich")
        return

    console = Console()
    console.print(
        Panel("[bold]Paste your browser cURL command below[/bold]", border_style="cyan")
    )
    console.print(
        "[dim]Tip: Copy from Chrome DevTools Network tab > Right-click request > Copy as cURL[/dim]\n"
    )

    curl_lines: List[str] = []
    console.print("[dim]Paste cURL command (press Enter twice when done):[/dim]")
    while True:
        try:
            line = input()
            if line == "" and curl_lines:
                break
            curl_lines.append(line)
        except EOFError:
            break

    curl_command = "\n".join(curl_lines)

    if not curl_command.strip():
        console.print("[red]No cURL command provided.[/red]")
        return

    console.print("\n[bold]Processing...[/bold]\n")
    run_download(curl_command)


def run_full_pipeline_interactive() -> None:
    """Run the full pipeline with interactive cURL input."""
    run_download_interactive()
    run_normalize()
    run_geocode()
    run_validate()
    run_update()
    run_reports()


def run_transform_interactive() -> None:
    """Run the schema transform step with interactive sample JSON input."""
    try:
        from rich.console import Console
        from rich.panel import Panel
    except ImportError:
        print("Error: 'rich' package not installed. Run: pip install rich")
        return

    console = Console()
    console.print(
        Panel(
            "[bold]Paste a sample JSON excerpt showing the fields you want[/bold]\n"
            "[dim]The system will infer which fields to extract from the data[/dim]\n"
            "[dim]Tip: Paste a single JSON object with the keys you need[/dim]",
            border_style="cyan",
        )
    )

    json_lines: List[str] = []
    console.print("[dim]Paste sample JSON (press Enter twice when done):[/dim]")
    brace_count = 0
    while True:
        try:
            line = input()
            if line.strip() == "" and json_lines:
                break
            json_lines.append(line)
            brace_count += line.count("{") - line.count("}")
            # Auto-close if braces are balanced after pasting
            if (
                brace_count == 0
                and json_lines
                and any("{" in item for item in json_lines)
            ):
                break
        except EOFError:
            break

    sample_str = "\n".join(json_lines)

    if not sample_str.strip():
        console.print("[red]No sample JSON provided.[/red]")
        return

    try:
        import json

        sample = json.loads(sample_str)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        return

    if not isinstance(sample, dict):
        console.print(
            "[red]Sample must be a JSON object, not a list or primitive.[/red]"
        )
        return

    console.print("\n[bold]Processing schema transformation...[/bold]\n")
    run_transform(sample_json=sample)


# ---- Pipeline Step Runners ----


def run_download(curl_command: Optional[str] = None, curl_file: Optional[str] = None) -> None:
    """Run the download step."""
    from rich.console import Console

    console = Console()

    try:
        from connectors.sat_connector import SatConnector

        connector = SatConnector()

        if curl_command:
            result = connector.download_only(curl_command=curl_command)
        elif curl_file:
            result = connector.download_only(curl_file=curl_file)
        else:
            console.print(
                "[red]No cURL source provided. Use --paste-curl or --curl-file.[/red]"
            )
            return

        if result.success:
            console.print("[green]Download successful![/green]")
            console.print(f"  Status: HTTP {result.status_code}")
            console.print(f"  Format: {result.response_format}")
            console.print(f"  Size: {len(result.content):,} bytes")
            console.print(f"  Saved: {result.file_path}")
        else:
            console.print(f"[red]Download failed: {result.error}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logging.getLogger(__name__).error(traceback.format_exc())


def run_normalize() -> None:
    """Run the normalize step."""
    from rich.console import Console

    console = Console()

    try:
        from processing.downloader import Downloader
        from processing.normalizer import Normalizer

        downloader = Downloader()
        normalizer = Normalizer()

        latest = downloader.get_latest_raw()
        if not latest:
            console.print("[red]No raw files found. Run download first.[/red]")
            return

        console.print(f"[bold]Normalizing: {latest.name}[/bold]")
        raw_data = latest.read_bytes()
        centres = normalizer.normalize(raw_data)
        path = normalizer.save(centres)
        console.print(f"[green]Normalized {len(centres)} centres -> {path}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logging.getLogger(__name__).error(traceback.format_exc())


def run_geocode(force: bool = False) -> None:
    """Run the geocode step."""
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn

    console = Console()

    try:
        from processing.geocoder import CentreGeocoder
        from processing.normalizer import Normalizer

        normalizer = Normalizer()
        centres = normalizer.load()

        if not centres:
            console.print("[red]No centres found. Run normalize first.[/red]")
            return

        console.print(f"[bold]Geocoding {len(centres)} centres...[/bold]")

        geocoder = CentreGeocoder(force=force)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Geocoding...", total=len(centres))
            results = geocoder.geocode_all(centres)
            progress.update(task, advance=len(centres))

        geocoded = sum(1 for r in results if r.geocoded)
        console.print(f"[green]Geocoded {geocoded}/{len(centres)} centres[/green]")
        normalizer.save(centres)

        stats = geocoder.stats
        console.print(f"  API calls: {sum(stats['provider_usage'].values())}")
        console.print(f"  Cache hits: {stats['cache_hits']}")

        geocoder.close()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logging.getLogger(__name__).error(traceback.format_exc())


def run_validate() -> None:
    """Run the validate step."""
    from rich.console import Console

    console = Console()

    try:
        from processing.normalizer import Normalizer
        from processing.validator import CentreValidator

        normalizer = Normalizer()
        centres = normalizer.load()

        if not centres:
            console.print("[red]No centres found. Run normalize/geocode first.[/red]")
            return

        console.print(f"[bold]Validating {len(centres)} centres...[/bold]")
        validator = CentreValidator()

        valid, failed = validator.validate(centres)
        summary = validator.get_summary(len(centres), valid, failed)

        console.print(f"[green]Valid: {summary.valid}[/green]")
        console.print(f"[red]Failed: {summary.failed}[/red]")
        if summary.wrong_country:
            console.print(f"  Wrong country: {summary.wrong_country}")
        if summary.missing_coords:
            console.print(f"  Missing coords: {summary.missing_coords}")
        if summary.duplicate_ids:
            console.print(f"  Duplicate IDs: {summary.duplicate_ids}")

        normalizer.save(valid)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logging.getLogger(__name__).error(traceback.format_exc())


def run_update() -> None:
    """Run the update step."""
    from rich.console import Console

    console = Console()

    try:
        from processing.normalizer import Normalizer
        from processing.updater import DatasetUpdater

        normalizer = Normalizer()
        new_centres = normalizer.load()

        if not new_centres:
            console.print("[red]No centres found to update.[/red]")
            return

        updater = DatasetUpdater()
        existing = updater.load_existing()

        console.print(
            f"[bold]Updating dataset: {len(existing)} existing + {len(new_centres)} new[/bold]"
        )
        merged, summary = updater.update(existing, new_centres)
        path = updater.save(merged)

        console.print(f"[green]Dataset updated: {path}[/green]")
        console.print(f"  New: {summary.new_centres}")
        console.print(f"  Updated: {summary.updated_centres}")
        console.print(f"  Removed: {summary.removed_centres}")
        console.print(f"  Unchanged: {summary.unchanged_centres}")

        dup_path = updater.export_duplicates(merged)
        if dup_path:
            console.print(f"[yellow]Duplicates found: {dup_path}[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logging.getLogger(__name__).error(traceback.format_exc())


def run_reports() -> None:
    """Run the reports step."""
    from rich.console import Console

    console = Console()

    try:
        from processing.exporter import PipelineStats, ReportExporter

        stats = PipelineStats(
            end_time=datetime.now(),
        )

        # Try to populate stats from existing data
        from processing.normalizer import Normalizer

        normalizer = Normalizer()
        centres = normalizer.load()
        stats.total_centres = len(centres)

        exporter = ReportExporter()
        paths = exporter.generate_all(stats)

        for name, path in paths.items():
            console.print(f"[green]Generated: {path}[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logging.getLogger(__name__).error(traceback.format_exc())


def run_resume() -> None:
    """Resume failed centres from a previous run."""
    from rich.console import Console

    console = Console()

    try:
        from processing.geocoder import CentreGeocoder
        from processing.normalizer import Normalizer

        normalizer = Normalizer()
        centres = normalizer.load()

        if not centres:
            console.print("[red]No centres found.[/red]")
            return

        # Find centres without coordinates
        ungeocoded = [c for c in centres if c.latitude is None or c.longitude is None]

        if not ungeocoded:
            console.print("[green]All centres are already geocoded![/green]")
            return

        console.print(f"[bold]Resuming {len(ungeocoded)} failed centres...[/bold]")

        geocoder = CentreGeocoder(force=True)
        results = geocoder.geocode_all(ungeocoded)

        geocoded = sum(1 for r in results if r.geocoded)
        console.print(
            f"[green]Geocoded {geocoded}/{len(ungeocoded)} failed centres[/green]"
        )
        normalizer.save(centres)

        geocoder.close()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logging.getLogger(__name__).error(traceback.format_exc())


def run_transform(sample_json: Optional[dict] = None, sample_json_file: Optional[str] = None) -> None:
    """Run the schema transform step."""
    import json

    from rich.console import Console

    console = Console()

    try:
        from processing.normalizer import Normalizer
        from processing.schema_transformer import SchemaTransformer

        normalizer = Normalizer()
        centres = normalizer.load()

        if not centres:
            console.print("[red]No centres found. Run normalize first.[/red]")
            return

        # Get the sample JSON
        sample = None
        if sample_json:
            sample = sample_json
        elif sample_json_file:
            sample_path = Path(sample_json_file)
            if not sample_path.exists():
                console.print(f"[red]File not found: {sample_json_file}[/red]")
                return
            sample = json.loads(sample_path.read_text(encoding="utf-8"))
        else:
            console.print(
                "[red]No sample JSON provided. Use --sample-json or paste interactively.[/red]"
            )
            return

        if not isinstance(sample, dict):
            console.print("[red]Sample must be a JSON object.[/red]")
            return

        console.print(f"[bold]Transforming {len(centres)} centres...[/bold]")
        console.print(f"[dim]Sample fields: {', '.join(sample.keys())}[/dim]")

        transformer = SchemaTransformer()

        # Infer schema
        schema_map = transformer.infer_schema(sample, centres)

        # Show inferred mapping
        from rich.table import Table

        table = Table(title="Inferred Field Mappings", border_style="cyan")
        table.add_column("Output Field", style="bold yellow")
        table.add_column("Source", style="green")

        for user_field, source in schema_map.items():
            table.add_row(user_field, str(source))

        console.print(table)
        console.print()

        # Transform and save
        transformed = transformer.transform(centres, sample, schema_map)
        path = transformer.save(transformed)
        console.print(
            f"[green]Transformed {len(transformed)} records -> {path}[/green]"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logging.getLogger(__name__).error(traceback.format_exc())


def run_full_pipeline(
    curl_command: Optional[str] = None,
    curl_file: Optional[str] = None,
    force: bool = False,
    transform: bool = False,
    sample_json: Optional[dict] = None,
    sample_json_file: Optional[str] = None,
) -> None:
    """Run the entire pipeline end-to-end."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    start_time = datetime.now()
    console.print(
        Panel("[bold]SAT Centre Updater — Full Pipeline[/bold]", border_style="cyan")
    )

    # Step 1: Download
    console.print("\n[bold cyan]Step 1/7: Download[/bold cyan]")
    if curl_command or curl_file:
        run_download(curl_command=curl_command, curl_file=curl_file)
    else:
        console.print("[yellow]No cURL source. Skipping download.[/yellow]")

    # Step 2: Normalize
    console.print("\n[bold cyan]Step 2/7: Normalize[/bold cyan]")
    run_normalize()

    # Step 3: Geocode
    console.print("\n[bold cyan]Step 3/7: Geocode[/bold cyan]")
    run_geocode(force=force)

    # Step 4: Validate
    console.print("\n[bold cyan]Step 4/7: Validate[/bold cyan]")
    run_validate()

    # Step 5: Update
    console.print("\n[bold cyan]Step 5/7: Update Dataset[/bold cyan]")
    run_update()

    # Step 6: Reports
    console.print("\n[bold cyan]Step 6/7: Reports[/bold cyan]")
    run_reports()

    # Step 7: Schema Transform (optional)
    if transform:
        console.print("\n[bold cyan]Step 7/7: Schema Transform[/bold cyan]")
        run_transform(sample_json=sample_json, sample_json_file=sample_json_file)
    else:
        console.print("\n[bold cyan]Step 7/7: Schema Transform[/bold cyan]")
        console.print("[yellow]Skipped (use --transform to enable)[/yellow]")

    elapsed = (datetime.now() - start_time).total_seconds()
    console.print(f"\n[bold green]Pipeline completed in {elapsed:.1f}s[/bold green]")


def main() -> None:
    """Main entry point."""
    parser = get_parser()
    args = parser.parse_args()

    setup_logging(args.log_level)

    logger = logging.getLogger(__name__)
    logger.info("SAT Centre Updater started")

    # Apply config overrides
    if args.confidence:
        from config import settings

        settings.GEOCODING.CONFIDENCE_THRESHOLD = args.confidence

    if args.workers:
        from config import settings

        settings.GEOCODING.MAX_WORKERS = args.workers

    try:
        if args.full:
            run_full_pipeline(
                curl_file=args.curl_file,
                force=args.force_geocode,
                transform=args.transform,
                sample_json_file=args.sample_json,
            )
        elif args.transform:
            run_transform(sample_json_file=args.sample_json)
        elif args.download:
            if args.paste_curl:
                run_download_interactive()
            else:
                run_download(curl_file=args.curl_file)
        elif args.normalize:
            run_normalize()
        elif args.geocode:
            run_geocode(force=args.force_geocode)
        elif args.validate:
            run_validate()
        elif args.update:
            run_update()
        elif args.reports:
            run_reports()
        elif args.resume:
            run_resume()
        else:
            interactive_menu()
    except KeyboardInterrupt:
        print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
