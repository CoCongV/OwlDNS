import asyncio
import argparse
import sys
from .server import OwlDNSServer


def start_server(args):
    """Initializes and runs the DNS server with provided arguments."""
    # Parse static records into a dictionary
    records = {}
    if args.record:
        for r in args.record:
            try:
                domain, ip = r.split("=", 1)
                records[domain] = ip
            except ValueError:
                print(
                    f"Warning: Invalid record format '{r}'. Expected 'domain=ip'.")
    else:
        # Default example record if none provided
        records = {"example.com": "1.2.3.4"}

    # Initialize and run the server
    server = OwlDNSServer(host=args.host, port=args.port,
                          records=records, upstream=args.upstream)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nOwlDNS stopped.")
    except Exception as e:
        print(f"Error: {e}")


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
            print("Change detected, restarting OwlDNS...")
            self.process = subprocess.Popen(self.cmd)

        def on_any_event(self, event):
            if event.is_directory or not event.src_path.endswith('.py'):
                return
            self.restart()

    # Construct the command to restart (stripping --reload)
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
    Parses arguments and starts the DNS server.
    """
    parser = argparse.ArgumentParser(
        description="OwlDNS - A lightweight async DNS server")

    # Selection of host and port for binding
    parser.add_argument("--host", default="127.0.0.1",
                        help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5353,
                        help="Port to bind (default: 5353 for non-root testing)")

    # Upstream DNS server for forwarding queries
    parser.add_argument("--upstream", default="8.8.8.8",
                        help="Upstream DNS server (default: 8.8.8.8)")

    # Static DNS records (A and AAAA records)
    parser.add_argument("--record", action="append",
                        help="Static records in format domain=ip (e.g. example.com=1.2.3.4 or example.com=::1)")

    parser.add_argument("--reload", action="store_true",
                        help="Auto-reload on code changes (development only)")

    args = parser.parse_args()

    if args.reload:
        run_reloader()
    else:
        start_server(args)
