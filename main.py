import click
import shlex
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style

from app.cli.sync import sync
from app.cli.auth import auth
from app.logger import setup_logging, get_logger

setup_logging()
logger = get_logger("main")

#  CLI entrypoint
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Job Tracker CLI"""
    if ctx.invoked_subcommand is None:
        interactive_loop() # invoke loop function

cli.add_command(sync)
cli.add_command(auth)

# app loop function
def interactive_loop():
    """Custom interactive shell powered by prompt_toolkit."""

    completer = WordCompleter(['sync', 'auth', 'exit', 'quit', 'help'], ignore_case=True)
    style = Style.from_dict({
        'prompt': 'ansicyan bold',
        'intro': 'ansigreen bold',
        'warning': 'ansiyellow',
        'error': 'ansired bold'
    })
    session = PromptSession(completer=completer, style=style)
    
    # Intro Message
    print()
    session.app.print_text(HTML('<intro>========================================</intro>\n'))
    session.app.print_text(HTML('<intro>   WELCOME TO JT AUTOMATION SHELL       </intro>\n'))
    session.app.print_text(HTML('<intro>========================================</intro>\n'))
    session.app.print_text(HTML('<warning>Type commands like "sync", "auth", or "exit" to quit.</warning>\n\n'))
    
    while True:
        try:
            text = session.prompt(HTML('<prompt>jt-automation></prompt> '))
            text = text.strip()
            
            if not text:
                continue
                
            if text.lower() in ('exit', 'quit'):
                logger.info("User requested exit.")
                break
                
            # Parse input properly handling quotes
            args = shlex.split(text)
            logger.info("Executing command: %s", text)
            
            # Route to Click
            try:
                cli.main(args=args, standalone_mode=False)
            except click.exceptions.UsageError as e:
                logger.warning("Usage error for command '%s': %s", text, e.message)
                session.app.print_text(HTML(f'<error>Usage error: {e.message}</error>\n'))
            except click.exceptions.ClickException as e:
                logger.warning("Click exception for command '%s': %s", text, e.message)
                session.app.print_text(HTML(f'<error>Error: {e.message}</error>\n'))
            except click.exceptions.Exit:
                # Raised by --help
                pass
            except Exception as e:
                logger.exception("Unhandled error executing command '%s': %s", text, e)
                session.app.print_text(HTML(f'<error>Execution failed: {e}. Check logs/app.log for details.</error>\n'))
                
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully without killing the shell
            continue
        except EOFError:
            # Handle Ctrl+D
            break
            
    logger.info("Interactive session ended.")
    session.app.print_text(HTML('<warning>Goodbye!</warning>\n'))


if __name__ == "__main__":
    cli()
