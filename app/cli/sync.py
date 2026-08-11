import click
import asyncio
from app.agent.workflow import run_agent
from app.errors.exceptions import AuthRequiredError, find_auth_error

@click.command(name="sync")
def sync():
    """
    Fetches new emails and syncs job application updates to Google Sheets
    """
    click.secho("==========================", fg="cyan")
    click.secho("   Starting Automation", fg="cyan", bold=True)
    click.secho("==========================", fg="cyan")

    try:
        result = asyncio.run(run_agent())        
        final_output = result.get("final_output")
        
        if final_output and len(final_output) > 0:
            click.secho(f"Success! Processed {len(final_output)} job updates.", fg="green")
        else:
            click.secho("No new job updates found.", fg="yellow")
    
    except Exception as exc:
        if find_auth_error(exc):
            click.secho(
                "\nAuthentication Required: Google authentication is required.",
                fg="red",
                bold=True,
            )
            click.secho(
                "Please run `auth` command to authenticate, and then re-run sync.",
                fg="yellow",
            )
        else:
            click.secho(
                "Automation Failed!",
                fg="red",
                bold=True,
            )
            click.secho(str(exc), fg="red")
    