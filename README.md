# OwlDNS

🦉 A lightweight, extremely concise, async DNS server implemented in Python.

## Features

- **Antigravity Style**: Minimalistic and decoupled code.
- **Asyncio**: High-performance handling of DNS queries using Python's native `asyncio`.
- **Custom Resolver**: Supports static A record lookups from a Python dictionary.
- **Upstream Forwarding**: Automatically forwards unknown requests to an upstream DNS (e.g., 8.8.8.8).
- **Easy Installation**: Packaged with Poetry/Pip for easy distribution.

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd OwlDNS

# Install dependencies
pip install .
```

## Usage

### CLI

Start the server with default settings (port 5353, example.com -> 1.2.3.4):

```bash
owldns
```

Specify custom host, port, upstream, and records:

```bash
owldns --host 0.0.0.0 --port 53 --upstream 1.1.1.1 --record example.com=9.9.9.9 --record test.lan=192.168.1.100
```

### Programmatic

```python
import asyncio
from owldns import OwlDNSServer

async def run():
    server = OwlDNSServer(
        host="127.0.0.1", 
        port=5353, 
        records={"hello.world": "10.0.0.1"},
        upstream="8.8.8.8"
    )
    await server.start()

if __name__ == "__main__":
    asyncio.run(run())
```

## Development

Requires Python 3.9+ and `dnslib`.
