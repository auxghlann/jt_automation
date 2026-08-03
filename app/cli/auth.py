import click
from app.services.google_auth import get_credentials


@click.command(name="auth")
def auth():
    """Manually trigger the Google Authentication flow."""
    click.secho("Starting Google Authentication flow...", fg="cyan")
    
    try:
        # This function will automatically open the browser if needed
        # and save the new token to token.json
        get_credentials(interactive=True)
        click.secho("Authentication successful! token.json is ready.", fg="green")
    except Exception as e:
        click.secho("Authentication failed!", fg="red", bold=True)
        click.secho(f"Error: {e}", fg="red")
