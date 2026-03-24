from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from .config import Settings
from .server import main as server_main

app = typer.Typer(help="LostDog Deep Search MCP starter CLI")


@app.command()
def doctor() -> None:
    settings = Settings.from_env()
    print("[bold]LostDog MCP doctor[/bold]")
    print(settings)


@app.command()
def start() -> None:
    server_main()


@app.command()
def touch_data_dirs() -> None:
    settings = Settings.from_env()
    for path_str in [settings.evidence_dir, settings.cases_dir, settings.screenshot_dir]:
        path = Path(path_str)
        path.mkdir(parents=True, exist_ok=True)
        print(f"created {path}")


if __name__ == "__main__":
    app()
