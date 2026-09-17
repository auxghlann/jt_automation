import click
import asyncio
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn
)
from app.agent.workflow import run_agent
from app.errors.exceptions import AuthRequiredError, find_auth_error, format_exception_details
from app.logger import get_logger

console = Console()
logger = get_logger("cli.sync")

def format_sync_results(sync_report: dict, final_output: list) -> list[dict]:
    """Formats synchronization results from sheets service and final output into display items."""
    all_jobs = []
    for item in sync_report.get("appended", []):
        all_jobs.append({
            "action": "NEW",
            "color": "green",
            "company": item.get("company") or "Unknown",
            "title": item.get("title") or "Unknown",
            "location": item.get("location") or "",
            "status_str": f"[green]{item.get('status') or 'applied'}[/green]",
            "date": item.get("date") or "-",
            "summary": item.get("summary") or ""
        })
    for item in sync_report.get("updated", []):
        old_s = item.get("old_status") or "?"
        new_s = item.get("new_status") or "?"
        all_jobs.append({
            "action": "UPDATED",
            "color": "yellow",
            "company": item.get("company") or "Unknown",
            "title": item.get("title") or "Unknown",
            "location": item.get("location") or "",
            "status_str": f"[dim]{old_s}[/dim] -> [bold yellow]{new_s}[/bold yellow]",
            "date": item.get("date") or "-",
            "summary": item.get("summary") or ""
        })
    for item in sync_report.get("skipped", []):
        all_jobs.append({
            "action": "UNCHANGED",
            "color": "dim",
            "company": item.get("company") or "Unknown",
            "title": item.get("title") or "Unknown",
            "location": item.get("location") or "",
            "status_str": f"[dim]{item.get('status') or 'applied'}[/dim]",
            "date": item.get("date") or "-",
            "summary": item.get("summary") or ""
        })
    
    # Fallback if sync_report was empty but final_output exists
    if not all_jobs and final_output:
        for model in final_output:
            all_jobs.append({
                "action": "PROCESSED",
                "color": "cyan",
                "company": model.company_name or "Unknown",
                "title": model.job_title or "Unknown",
                "location": model.location or "",
                "status_str": f"[cyan]{model.status or 'applied'}[/cyan]",
                "date": model.date or "-",
                "summary": model.short_summary or ""
            })
    return all_jobs

def render_summary_table(all_jobs: list[dict]):
    """Renders a clean, compact Rich table of processed jobs."""
    table = Table(title="Job Application Processing Summary", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Action", justify="center")
    table.add_column("Company", style="bold")
    table.add_column("Job Title")
    table.add_column("Status", justify="center")
    table.add_column("Date", justify="center")

    for job in all_jobs:
        color = job["color"]
        table.add_row(
            f"[{color}]{job['action']}[/{color}]",
            job["company"],
            job["title"],
            job["status_str"],
            job["date"]
        )
    console.print()
    console.print(table)

def render_application_cards(all_jobs: list[dict]):
    """Renders each application in full detail using Rich Panels."""
    console.print()
    for job in all_jobs:
        color = job["color"]
        content_lines = [
            f"[bold]Company:[/bold] {job['company']}",
            f"[bold]Job Title:[/bold] {job['title']}",
            f"[bold]Status:[/bold] {job['status_str']}",
            f"[bold]Date:[/bold] {job['date']}",
        ]
        if job.get("location"):
            content_lines.append(f"[bold]Location:[/bold] {job['location']}")
        if job.get("summary"):
            content_lines.append(f"[bold]Summary:[/bold] {job['summary']}")

        panel = Panel(
            "\n".join(content_lines),
            title=f"[{color}][{job['action']}][/{color}] [bold]{job['company']}[/bold] - {job['title']}",
            title_align="left",
            border_style=color,
            box=box.ROUNDED,
            expand=False
        )
        console.print(panel)

@click.command(name="sync")
@click.option("--shrink", "-s", is_flag=True, default=False, help="Display condensed summary table without full application details.")
@click.option("--days", default=7, type=int, help="Number of days back to search for job application updates.")
def sync(shrink: bool, days: int):
    """
    Fetches new emails and syncs job application updates to Google Sheets
    """
    logger.info("Sync command initiated (days=%d, shrink=%s).", days, shrink)
    console.rule("[bold cyan]Starting Automation[/bold cyan]")

    result = None
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
            logger.info("Sync progress step: %s", description)
            progress.update(task_id, description=description, advance=advance)

        try:
            result = asyncio.run(run_agent(progress_callback=on_progress, days_ago=days))
            progress.update(task_id, completed=4, description="Automation completed.")
        except Exception as exc:
            progress.stop()
            if find_auth_error(exc):
                logger.warning("Authentication required during sync: %s", exc)
                console.print(
                    "\n[bold red]Authentication Required:[/bold red] Google authentication is required."
                )
                console.print(
                    "[yellow]Please run `auth` command to authenticate, and then re-run sync.[/yellow]"
                )
            else:
                err_details = format_exception_details(exc)
                logger.exception("Automation failed during sync. Root cause(s): %s", ", ".join(err_details))
                console.print("\n[bold red]Automation Failed![/bold red]")
                for err in err_details:
                    console.print(f"[red]• {err}[/red]")
                console.print("[dim]Check logs/app.log for the full traceback.[/dim]")
            return

    # Outside the Progress context: progress bar is completely stopped
    if not result:
        return

    final_output = result.get("final_output", [])
    sync_report = result.get("sync_report", {})
    all_jobs = format_sync_results(sync_report, final_output)

    appended_count = len(sync_report.get("appended", []))
    updated_count = len(sync_report.get("updated", []))
    skipped_count = len(sync_report.get("skipped", []))

    if all_jobs:
        logger.info(
            "Sync completed successfully. Total: %d, Appended: %d, Updated: %d, Unchanged: %d",
            len(all_jobs), appended_count, updated_count, skipped_count
        )
        console.print(
            f"\n[bold green]Sync Complete![/bold green] Total Processed: {len(all_jobs)} "
            f"([green]New: {appended_count}[/green], "
            f"[yellow]Updated: {updated_count}[/yellow], "
            f"[dim]Unchanged: {skipped_count}[/dim])"
        )
        if shrink:
            render_summary_table(all_jobs)
        else:
            render_application_cards(all_jobs)
    else:
        logger.info("Sync completed successfully with no new job updates.")
        console.print("\n[bold yellow]No new job updates found in inbox.[/bold yellow]")
    