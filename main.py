import asyncio
from app.agent.workflow import run_agent
from app.cli.sync import sync
from app.cli.auth import auth
import click

@click.group()
def cli():
    """Job Tracker CLI"""
    pass

cli.add_command(sync)
cli.add_command(auth)

if __name__ == "__main__":
    cli()
