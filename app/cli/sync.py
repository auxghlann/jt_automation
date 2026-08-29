import click
import asyncio
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn
)
from app.agent.workflow import run_agent
from app.errors.exceptions import AuthRequiredError, find_auth_error

console = Console()

@click.command(name="sync")
def sync():
    """
    Fetches new emails and syncs job application updates to Google Sheets
    """
    console.rule("[bold cyan]Starting Automation[/bold cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_id = progress.add_task("Initializing...", total=4)

        def on_progress(description: str, advance: int = 0):
            progress.update(task_id, description=description, advance=advance)

        try:
            result = asyncio.run(run_agent(progress_callback=on_progress))
            progress.update(task_id, completed=4, description="Automation completed.")
            
            final_output = result.get("final_output", [])
            if final_output and len(final_output) > 0:
                console.print(f"\n[bold green]Success![/bold green] Processed {len(final_output)} job updates.")
            else:
                console.print("\n[bold yellow]No new job updates found.[/bold yellow]")

        except Exception as exc:
            progress.stop()
            if find_auth_error(exc):
                console.print(
                    "\n[bold red]Authentication Required:[/bold red] Google authentication is required."
                )
                console.print(
                    "[yellow]Please run `auth` command to authenticate, and then re-run sync.[/yellow]"
                )
            else:
                console.print("\n[bold red]Automation Failed![/bold red]")
                console.print(f"[red]{exc}[/red]")
    