import asyncio
import os
import shutil
import subprocess
import sys
import time

import click
import uvloop
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from owldns.server import OwlDNSServer
from owldns.utils import load_hosts, load_config
from owldns import setup_logger, logger
from owldns.config import config as owl_config, update_config


def run_tests() -> None:
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
        logger.error("Error running tests: %s", e)
        sys.exit(1)


def start_server(host: str, port: int, upstream: str, hosts_file: str) -> None:
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


def run_reloader(ctx_args: list[str]) -> None:
    """Starts a watchdog observer to restart the process on file changes."""
    class ReloadHandler(FileSystemEventHandler):
        """Restarts the subprocess when a .py file is modified."""

        def __init__(self, cmd):
            self.cmd = cmd
            self.process = None
            logger.info("Starting OwlDNS with auto-reload...")
            self.restart()

        def restart(self):
            if self.process:
                self.process.terminate()
                self.process.wait()

            # Pass environment variable to child to prevent reloader recursion
            env = os.environ.copy()
            env["OWLDNS_RELOAD_CHILD"] = "1"
            self.process = subprocess.Popen(self.cmd, env=env)

        def on_any_event(self, event):
            if event.is_directory or not event.src_path.endswith('.py'):
                return

            # Filter out noise like __pycache__, .git, .venv
            if any(x in event.src_path for x in ('.git', '__pycache__', '.venv', '.pytest_cache')):
                return

            logger.info(
                "Change detected in %s, restarting OwlDNS...", event.src_path)
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
@click.option("--config", type=click.Path(exists=True), help="Path to TOML config file")
@click.option("--log-level",
              type=click.Choice(["DEBUG", "INFO", "WARNING",
                                "ERROR", "CRITICAL"], case_sensitive=False),
              help="Set the logging level (default: INFO)")
@click.pass_context
def cli(ctx, config: str | None, log_level: str | None):
    """OwlDNS - A lightweight async DNS server."""
    ctx.ensure_object(dict)

    # Rename local config param to config_file to avoid global shadowing
    config_file = config
    config_data = {}
    if config_file:
        config_data = load_config(config_file)
        ctx.default_map = config_data
        update_config(config_data)

    # Priority: CLI argument > TOML config > Default "INFO"
    # Priority: CLI argument > TOML config > Default "INFO"
    if log_level is None:
        log_level = owl_config.get("log_level", "INFO")

    ctx.obj['log_level'] = log_level


@cli.command()
def test() -> None:
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
@click.pass_context
def run(ctx: click.Context, host: str, port: int) -> None:
    """Run the DNS server."""
    # Use global config with local overrides from Click
    config_run = owl_config.get("run", {})
    upstream = config_run.get("upstream", "1.1.1.1")
    hosts_file = config_run.get("hosts_file", "/etc/hosts")
    debug = config_run.get("debug", False)

    log_level = ctx.obj['log_level']
    reload = False

    if debug:
        log_level = "DEBUG"
        reload = True

    setup_logger(level=log_level)

    if reload and os.environ.get("OWLDNS_RELOAD_CHILD") != "1":
        run_reloader(sys.argv[1:])
    else:
        start_server(host, port, upstream, hosts_file)


def main() -> None:
    """Entry point wrapper to handle default command."""
    # Smarter default command injection:
    # We want to support 'owldns' -> 'owldns run'
    # And 'owldns --config f.toml' -> 'owldns --config f.toml run'
    if len(sys.argv) == 1:
        sys.argv.append("run")
    else:
        # Check if dynamic subcommands are present
        subcommands = ["run", "test"]
        has_subcommand = any(arg in subcommands for arg in sys.argv)
        if not has_subcommand and not any(arg in ["--help", "-h"] for arg in sys.argv):
            # If no subcommand found and no help flag, append 'run' at the end
            # This ensures global options like --config are kept before the command
            sys.argv.append("run")

    # Click uses its own sys.argv handling when cli() is called
    cli()  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
