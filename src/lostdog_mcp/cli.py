"""LostDog Deep Search CLI — interactive case management."""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import typer
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from .config import Settings
from .server import main as server_main
from .storage.db import get_engine, get_session
from .storage.models import CaseRow, CandidateRow  # noqa: F401
from .schemas import MissingDogCase
from .services.case_service import case_create, case_get, case_list, case_to_schema
from .services.candidate_service import candidate_list, candidate_score, candidate_mark
from .services.crawl_service import crawl_run, crawl_digest
from .services.export_service import case_export_bundle

app = typer.Typer(help="LostDog Deep Search — find your missing dog")
console = Console()


def _settings() -> Settings:
    return Settings.from_env()


def _init_db() -> str:
    s = _settings()
    get_engine(s.db_url)
    return s.db_url


# ── Server & diagnostics ────────────────────────────────────────────────

@app.command()
def doctor() -> None:
    """Check configuration and database connectivity."""
    settings = _settings()
    console.print(Panel("[bold]LostDog MCP Doctor[/bold]", style="blue"))
    console.print(f"  Environment:  {settings.env}")
    console.print(f"  Database:     {settings.db_url}")
    console.print(f"  Evidence dir: {settings.evidence_dir}")
    console.print(f"  Cases dir:    {settings.cases_dir}")
    console.print(f"  Browser mode: {'ENABLED' if settings.enable_browser_session else 'disabled'}")

    # Test DB
    try:
        db_url = _init_db()
        with get_session(db_url) as session:
            cases = case_list(session)
        console.print(f"  Active cases: {len(cases)}")
        console.print("[green]  All checks passed.[/green]")
    except Exception as e:
        console.print(f"[red]  DB error: {e}[/red]")


@app.command()
def serve() -> None:
    """Start the MCP server (JSON-RPC over stdio)."""
    server_main()


# ── Case management ─────────────────────────────────────────────────────

@app.command()
def intake(
    title: str = typer.Option(None, help="Case title"),
    location: str = typer.Option(None, help="Last seen location"),
    breed: str = typer.Option(None, help="Breed guess"),
    sex: str = typer.Option("unknown", help="Sex: female, male, unknown"),
    lat: float = typer.Option(None, help="Last seen latitude"),
    lng: float = typer.Option(None, help="Last seen longitude"),
    chip: str = typer.Option("unknown", help="Chip status: chipped, not_chipped, unknown"),
    collar: str = typer.Option("unknown", help="Collar status: wearing, not_wearing, unknown"),
    notes: str = typer.Option(None, help="Owner notes"),
) -> None:
    """Create a new missing-dog case (interactive if no options given)."""
    db_url = _init_db()

    if not title:
        console.print(Panel("[bold]Missing Dog Case Intake[/bold]", style="red"))
        title = Prompt.ask("Dog's name or case title")
        location = Prompt.ask("Last seen location (address, city, state)")
        breed = Prompt.ask("Breed (best guess)", default="unknown")
        sex = Prompt.ask("Sex", choices=["female", "male", "unknown"], default="unknown")
        chip = Prompt.ask("Chip status", choices=["chipped", "not_chipped", "unknown"], default="unknown")
        collar = Prompt.ask("Collar status", choices=["wearing", "not_wearing", "unknown"], default="unknown")
        notes = Prompt.ask("Any notes (medical, behavior, etc.)", default="")

        lat_str = Prompt.ask("Last seen latitude (leave blank to skip)", default="")
        lng_str = Prompt.ask("Last seen longitude (leave blank to skip)", default="")
        lat = float(lat_str) if lat_str else None
        lng = float(lng_str) if lng_str else None

    case_data = MissingDogCase(
        title=title,
        last_seen_at=datetime.now(),
        last_seen_location=location or "",
        breed_guess=breed,
        sex=sex,
        chip_status=chip,
        collar_status=collar,
        owner_notes=notes,
    )

    with get_session(db_url) as session:
        row = case_create(session, case_data, lat=lat, lng=lng)
        console.print(f"\n[green]Case created![/green] ID: [bold]{row.id}[/bold]")
        console.print(f"  Title: {row.title}")
        console.print(f"  Location: {row.last_seen_location}")


@app.command()
def cases() -> None:
    """List all active cases."""
    db_url = _init_db()
    with get_session(db_url) as session:
        rows = case_list(session)

    if not rows:
        console.print("[yellow]No active cases found.[/yellow]")
        return

    table = Table(title="Active Cases")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Location")
    table.add_column("Breed")
    table.add_column("Created")

    for r in rows:
        table.add_row(
            r.id, r.title, r.last_seen_location,
            r.breed_guess or "?", r.created_at.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@app.command()
def show(case_id: str) -> None:
    """Show details of a specific case."""
    db_url = _init_db()
    with get_session(db_url) as session:
        row = case_get(session, case_id)
        if not row:
            console.print(f"[red]Case {case_id} not found.[/red]")
            raise typer.Exit(1)

        console.print(Panel(f"[bold]{row.title}[/bold]", style="blue"))
        console.print(f"  ID:       {row.id}")
        console.print(f"  Status:   {row.status}")
        console.print(f"  Location: {row.last_seen_location}")
        if row.last_seen_lat and row.last_seen_lng:
            console.print(f"  Coords:   {row.last_seen_lat}, {row.last_seen_lng}")
        console.print(f"  Breed:    {row.breed_guess or 'unknown'}")
        console.print(f"  Sex:      {row.sex}")
        console.print(f"  Chip:     {row.chip_status}")
        console.print(f"  Collar:   {row.collar_status}")
        if row.medical_notes:
            console.print(f"  Medical:  {row.medical_notes}")
        if row.owner_notes:
            console.print(f"  Notes:    {row.owner_notes}")
        console.print(f"  Created:  {row.created_at}")
        console.print(f"  Updated:  {row.updated_at}")

        # Show candidate summary
        cands = candidate_list(session, case_id, limit=100)
        if cands:
            console.print(f"\n  [bold]Candidates:[/bold] {len(cands)} total")
            high = sum(1 for c in cands if c.final_score >= 0.5)
            console.print(f"  High confidence (>= 0.5): {high}")


# ── Search & crawl ──────────────────────────────────────────────────────

@app.command()
def search(
    case_id: str,
    radius: int = typer.Option(25, help="Search radius in miles"),
    days: int = typer.Option(14, help="Days back to search"),
) -> None:
    """Run a full search pass for a case."""
    db_url = _init_db()
    console.print(f"[bold]Searching for case {case_id}...[/bold]")

    with get_session(db_url) as session:
        start = time.time()
        rows = crawl_run(session, case_id, radius_miles=radius, days_back=days)
        elapsed = time.time() - start

        # Extract data while still in session
        results = [
            {"score": r.final_score, "title": r.title, "source": r.source_name, "location": r.location_text}
            for r in rows
        ]

    console.print(f"\n[green]Found {len(results)} candidates in {elapsed:.1f}s[/green]")

    if results:
        table = Table(title="Top Results")
        table.add_column("Score", style="bold")
        table.add_column("Title")
        table.add_column("Source")
        table.add_column("Location")

        for r in sorted(results, key=lambda x: x["score"], reverse=True)[:10]:
            score_color = "green" if r["score"] >= 0.5 else "yellow" if r["score"] >= 0.25 else "dim"
            table.add_row(
                f"[{score_color}]{r['score']:.3f}[/{score_color}]",
                r["title"][:60], r["source"], r["location"][:40],
            )
        console.print(table)


@app.command()
def leads(
    case_id: str,
    page: int = typer.Option(1, help="Page number"),
    limit: int = typer.Option(20, help="Results per page"),
) -> None:
    """List ranked candidate leads for a case."""
    db_url = _init_db()
    with get_session(db_url) as session:
        rows = candidate_list(session, case_id, page=page, limit=limit)
        items = [
            {"id": r.id, "score": r.final_score, "title": r.title, "source": r.source_name, "status": r.status}
            for r in rows
        ]

    if not items:
        console.print("[yellow]No candidates found.[/yellow]")
        return

    table = Table(title=f"Candidates for {case_id} (page {page})")
    table.add_column("#", style="dim")
    table.add_column("ID", style="cyan")
    table.add_column("Score", style="bold")
    table.add_column("Title")
    table.add_column("Source")
    table.add_column("Status")

    for i, r in enumerate(items, start=(page - 1) * limit + 1):
        score_color = "green" if r["score"] >= 0.5 else "yellow" if r["score"] >= 0.25 else "dim"
        status_color = "green" if r["status"] == "likely_match" else "red" if r["status"] == "false_positive" else "white"
        table.add_row(
            str(i), r["id"],
            f"[{score_color}]{r['score']:.3f}[/{score_color}]",
            r["title"][:50], r["source"],
            f"[{status_color}]{r['status']}[/{status_color}]",
        )
    console.print(table)


@app.command()
def review(candidate_id: str) -> None:
    """Review and score a specific candidate."""
    db_url = _init_db()
    with get_session(db_url) as session:
        breakdown = candidate_score(session, candidate_id)
        if not breakdown:
            console.print(f"[red]Candidate {candidate_id} not found.[/red]")
            raise typer.Exit(1)

        row = session.get(CandidateRow, candidate_id)

        console.print(Panel(f"[bold]{row.title}[/bold]", style="blue"))
        console.print(f"  Source:   {row.source_name}")
        console.print(f"  URL:      {row.source_url}")
        console.print(f"  Location: {row.location_text}")
        console.print(f"  Snippet:  {row.snippet[:300]}")
        console.print()

        score_table = Table(title="Score Breakdown")
        score_table.add_column("Component")
        score_table.add_column("Score", justify="right")

        score_table.add_row("Text", f"{breakdown.text_score:.3f}")
        score_table.add_row("Geo", f"{breakdown.geo_score:.3f}")
        score_table.add_row("Time", f"{breakdown.time_score:.3f}")
        score_table.add_row("Attributes", f"{breakdown.attribute_score:.3f}")
        score_table.add_row("Image", f"{breakdown.image_score:.3f}")
        score_table.add_row("Repost penalty", f"-{breakdown.repost_penalty:.3f}")
        score_table.add_row("[bold]Final[/bold]", f"[bold]{breakdown.final_score:.3f}[/bold]")
        console.print(score_table)

        console.print("\n[bold]Explanation:[/bold]")
        for line in breakdown.explanation:
            console.print(f"  - {line}")

        console.print(f"\n  Current status: {row.status}")


@app.command()
def mark(
    candidate_id: str,
    status: str = typer.Argument(help="Status: likely_match, false_positive, repost, follow_up, uncertain"),
    notes: str = typer.Option(None, help="Operator notes"),
) -> None:
    """Mark a candidate with a review status."""
    valid = {"likely_match", "false_positive", "repost", "follow_up", "uncertain"}
    if status not in valid:
        console.print(f"[red]Invalid status. Choose from: {', '.join(valid)}[/red]")
        raise typer.Exit(1)

    db_url = _init_db()
    with get_session(db_url) as session:
        row = candidate_mark(session, candidate_id, status, notes)
        if not row:
            console.print(f"[red]Candidate {candidate_id} not found.[/red]")
            raise typer.Exit(1)
        console.print(f"[green]Marked {candidate_id} as '{status}'[/green]")


# ── Export ───────────────────────────────────────────────────────────────

@app.command()
def export(case_id: str) -> None:
    """Export case bundle (markdown + JSON)."""
    db_url = _init_db()
    settings = _settings()
    with get_session(db_url) as session:
        result = case_export_bundle(session, case_id, output_dir=settings.cases_dir)
    console.print(f"[green]Exported {result['candidate_count']} candidates[/green]")
    console.print(f"  JSON:     {result['json_path']}")
    console.print(f"  Markdown: {result['md_path']}")


@app.command()
def digest(
    case_id: str,
    since: str = typer.Option(None, help="ISO datetime to filter from"),
) -> None:
    """Show digest of candidates for a case."""
    db_url = _init_db()
    since_dt = datetime.fromisoformat(since) if since else None
    with get_session(db_url) as session:
        result = crawl_digest(session, case_id, since=since_dt)

    console.print(Panel(f"[bold]Digest for {case_id}[/bold]", style="blue"))
    console.print(f"  Total candidates: {result['total_candidates']}")
    console.print(f"  [green]High confidence:[/green]   {result['high_confidence']}")
    console.print(f"  [yellow]Medium confidence:[/yellow] {result['medium_confidence']}")
    console.print(f"  [dim]Low confidence:[/dim]    {result['low_confidence']}")

    if result["top_leads"]:
        console.print("\n  [bold]Top leads:[/bold]")
        for lead in result["top_leads"]:
            console.print(f"    {lead['score']:.3f} — {lead['title']} ({lead['source']})")


# ── Setup ────────────────────────────────────────────────────────────────

@app.command()
def init() -> None:
    """Initialize data directories and database."""
    settings = _settings()
    for path_str in [settings.evidence_dir, settings.cases_dir, settings.screenshot_dir]:
        path = Path(path_str)
        path.mkdir(parents=True, exist_ok=True)
        console.print(f"  Created {path}")
    _init_db()
    console.print("[green]Initialization complete.[/green]")


# ── Monitoring ───────────────────────────────────────────────────────────

@app.command()
def monitor(
    case_id: str,
    interval: int = typer.Option(3600, help="Seconds between crawl passes"),
    count: int = typer.Option(0, help="Number of passes (0 = infinite)"),
) -> None:
    """Continuously monitor for new leads (scheduled crawling)."""
    db_url = _init_db()
    console.print(f"[bold]Monitoring case {case_id} every {interval}s[/bold]")
    console.print("Press Ctrl+C to stop.\n")

    passes = 0
    try:
        while count == 0 or passes < count:
            passes += 1
            console.print(f"[dim]Pass {passes} at {datetime.now().strftime('%H:%M:%S')}[/dim]")
            with get_session(db_url) as session:
                rows = crawl_run(session, case_id)
                new_high = [r for r in rows if r.final_score >= 0.5]
                console.print(f"  Found {len(rows)} candidates, {len(new_high)} high-confidence")
                if new_high:
                    for r in new_high:
                        console.print(f"  [green]{r.final_score:.3f}[/green] {r.title[:60]} ({r.source_name})")
            if count == 0 or passes < count:
                time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped.[/yellow]")


if __name__ == "__main__":
    app()
