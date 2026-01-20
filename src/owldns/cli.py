import asyncio
import shutil
import subprocess
import sys
import time

import click
import uvloop
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from owldns.server import OwlDNSServer
from owldns.utils import load_hosts
from owldns import setup_logger, logger


def run_tests():
    """Programmatically runs pytest with coverage settings via subprocess."""
    logger.info("Running OwlDNS coverage tests (including HTML report)...")
    try:
        # We run pytest as a subprocess to ensure coverage tracks all imports correctly
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=owldns",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "tests/"
        ]
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        sys.exit(1)


def start_server(host, port, upstream, hosts_file):
    """Initializes and runs the DNS server."""
    # Load records from the specified hosts file
    records = load_hosts(hosts_file)

    # Initialize and run the server
    server = OwlDNSServer(host=host, port=port,
                          records=records, upstream=upstream)

    try:
        asyncio.run(server.start(), loop_factory=uvloop.new_event_loop)
    except KeyboardInterrupt:
        logger.info("OwlDNS stopped.")
    except Exception as e:
        logger.error("Error: %s", e)


def run_reloader(ctx_args):
    """Starts a watchdog observer to restart the process on file changes."""
    class ReloadHandler(FileSystemEventHandler):
        """Restarts the subprocess when a .py file is modified."""

        def __init__(self, cmd):
            self.cmd = cmd
            self.process = None
            self.restart()

        def restart(self):
            if self.process:
                self.process.terminate()
                self.process.wait()
            logger.info("Change detected, restarting OwlDNS...")
            self.process = subprocess.Popen(self.cmd)

        def on_any_event(self, event):
            if event.is_directory or not event.src_path.endswith('.py'):
                return
            self.restart()

    # Construct the command to restart (keeping all arguments)
    base_cmd = "owldns"
    if not shutil.which("owldns"):
        cmd = [sys.executable, "-m", "owldns.cli"] + ctx_args
    else:
        cmd = [base_cmd] + ctx_args

    handler = ReloadHandler(cmd)
    observer = Observer()
    observer.schedule(handler, path='.', recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    finally:
        observer.join()
        if handler.process:
            handler.process.terminate()


@click.group(invoke_without_command=True)
@click.option("--log-level", default="INFO",
              type=click.Choice(["DEBUG", "INFO", "WARNING",
                                "ERROR", "CRITICAL"], case_sensitive=False),
              help="Set the logging level (default: INFO)")
@click.pass_context
def cli(ctx, log_level):
    """OwlDNS - A lightweight async DNS server."""
    ctx.ensure_object(dict)
    ctx.obj['log_level'] = log_level


@cli.command()
def test():
    """Run coverage tests (generates HTML report)."""
    logger.info("Running OwlDNS coverage tests (including HTML report)...")
    try:
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=owldns",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "tests/"
        ]
        result = subprocess.run(cmd, check=False)
        sys.exit(result.returncode)
    except Exception as e:
        logger.error("Error running tests: %s", e)
        sys.exit(1)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
@click.option("--port", type=int, default=5353, help="Port to bind (default: 5353)")
@click.option("--upstream", default="8.8.8.8", help="Upstream DNS server (default: 8.8.8.8)")
@click.option("--hosts-file", default="/etc/hosts", type=click.Path(exists=True),
              help="Path to a hosts-style file for static mappings (default: /etc/hosts)")
@click.option("--debug", is_flag=True, help="Enable debug mode (auto-reload + DEBUG log level)")
@click.pass_context
def run(ctx, host, port, upstream, hosts_file, debug):
    """Run the DNS server."""
    log_level = ctx.obj['log_level']
    reload = False

    if debug:
        log_level = "DEBUG"
        reload = True

    setup_logger(level=log_level)

    if reload:
        run_reloader(sys.argv[1:])
    else:
        start_server(host, port, upstream, hosts_file)


def main():
    """Entry point wrapper to handle default command."""
    # To maintain previous "default to run" behavior, we inject 'run' if no subcommand.
    if len(sys.argv) == 1:
        sys.argv.append("run")
    elif len(sys.argv) > 1 and sys.argv[1] not in ["run", "test", "--help", "-h"]:
        if not sys.argv[1].startswith("-"):
            sys.argv.insert(1, "run")

    # Click uses its own sys.argv handling when cli() is called
    cli()


if __name__ == "__main__":
    main()
