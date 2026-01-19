import asyncio
import argparse
from .server import OwlDNSServer


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

    # Static DNS records (A records only)
    parser.add_argument("--record", action="append",
                        help="Static records in format domain=ip (e.g. example.com=1.2.3.4)")

    args = parser.parse_args()

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
