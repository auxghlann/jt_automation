import click
from app.services.google_auth import get_credentials
from app.logger import get_logger

logger = get_logger("cli.auth")


@click.command(name="auth")
def auth():
    """Manually trigger the Google Authentication flow."""
    logger.info("Manual Google Authentication flow initiated.")
    click.secho("Starting Google Authentication flow...", fg="cyan")
    
    try:
        # This function will automatically open the browser if needed
        # and save the new token to token.json
        get_credentials(interactive=True)
        logger.info("Google Authentication successful. token.json generated.")
        click.secho("Authentication successful! token.json is ready.", fg="green")
    except Exception as e:
        logger.exception("Google Authentication failed: %s", e)
        click.secho("Authentication failed!", fg="red", bold=True)
        click.secho(f"Error: {e}", fg="red")
        click.secho("Check logs/app.log for details.", fg="yellow")
