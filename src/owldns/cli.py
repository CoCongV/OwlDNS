import asyncio
import argparse
import sys
import uvloop
from owldns.server import OwlDNSServer
from owldns.utils import load_hosts
from owldns import setup_logger, logger


def run_tests():
    """Programmatically runs pytest with coverage settings via subprocess."""
    import subprocess
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


def start_server(args):
    """Initializes and runs the DNS server with provided arguments."""
    # Load records from the specified hosts file
    records = load_hosts(args.hosts_file)

    # Initialize and run the server
    server = OwlDNSServer(host=args.host, port=args.port,
                          records=records, upstream=args.upstream)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("OwlDNS stopped.")
    except Exception as e:
        logger.error(f"Error: {e}")


def run_reloader():
    """Starts a watchdog observer to restart the process on file changes."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    import subprocess
    import time

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

    # Construct the command to restart (stripping --reload)
    # We use "owldns" if available in PATH, otherwise fallback to python -m
    cmd = ["owldns"] + [arg for arg in sys.argv[1:] if arg != "--reload"]

    # Check if 'owldns' is in PATH, if not, use python -m
    import shutil
    if not shutil.which("owldns"):
        cmd = [sys.executable, "-m", "owldns.cli"] + \
            [arg for arg in sys.argv[1:] if arg != "--reload"]

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


def main():
    """
    Entry point for the OwlDNS command-line interface.
    """
    uvloop.install()

    parser = argparse.ArgumentParser(
        description="OwlDNS - A lightweight async DNS server")

    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO",
                                 "WARNING", "ERROR", "CRITICAL"],
                        help="Set the logging level (default: INFO)")

    # Use subparsers to handle 'run' and 'test'
    subparsers = parser.add_subparsers(
        dest="command", help="Command to execute")

    # 'run' command (default)
    run_parser = subparsers.add_parser(
        "run", help="Run the DNS server (default)")
    run_parser.add_argument("--host", default="127.0.0.1",
                            help="Host to bind (default: 127.0.0.1)")
    run_parser.add_argument("--port", type=int, default=5353,
                            help="Port to bind (default: 5353)")
    run_parser.add_argument("--upstream", default="8.8.8.8",
                            help="Upstream DNS server (default: 8.8.8.8)")
    run_parser.add_argument(
        "--hosts-file", default="/etc/hosts",
        help="Path to a hosts-style file for static mappings (default: /etc/hosts)")
    run_parser.add_argument("--reload", action="store_true",
                            help="Auto-reload on code changes (development only)")

    # 'test' command
    subparsers.add_parser(
        "test", help="Run coverage tests (generates HTML report)")

    # Backward compatibility: if no command is provided, default to 'run'
    # and re-parse arguments as if they were for 'run'.
    if len(sys.argv) > 1 and sys.argv[1] not in ["run", "test", "-h", "--help"]:
        sys.argv.insert(1, "run")

    args = parser.parse_args()

    # Initialize logger
    setup_logger(level=args.log_level)

    if args.command == "test":
        run_tests()
    elif args.command == "run" or args.command is None:
        if hasattr(args, 'reload') and args.reload:
            run_reloader()
        else:
            start_server(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
