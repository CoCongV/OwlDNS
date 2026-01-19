import asyncio
from dnslib import DNSRecord, QTYPE, RR, A, AAAA
import socket


class Resolver:
    """
    DNS Resolver that handles local record lookup and upstream forwarding.
    """

    def __init__(self, records=None, upstream="8.8.8.8"):
        self.records = records or {}
        self.upstream = upstream

    async def resolve(self, data):
        """
        Parses the DNS query and attempts to resolve it locally or via upstream.
        """
        request = DNSRecord.parse(data)
        reply = request.reply()
        qname = str(request.q.qname).rstrip('.')
        qtype = request.q.qtype

        # TODO: Implement GeoDNS & Split-Horizon Routing based on client IP

        # Handle local A and AAAA record lookups
        matching_domain = None
        if qname in self.records:
            matching_domain = qname
        else:
            # Check for wildcard matches (e.g., *.example.com)
            for pattern in self.records:
                if pattern.startswith("*."):
                    suffix = pattern[2:]
                    if qname.endswith(suffix) and (qname == suffix or qname.endswith("." + suffix)):
                        matching_domain = pattern
                        break

        if matching_domain:
            if qtype == QTYPE.A:
                reply.add_answer(
                    RR(qname, QTYPE.A, rdata=A(self.records[matching_domain])))
                return reply.pack()
            elif qtype == QTYPE.AAAA:
                reply.add_answer(
                    RR(qname, QTYPE.AAAA, rdata=AAAA(self.records[matching_domain])))
                return reply.pack()

        # If not found locally, forward to upstream
        if self.upstream:
            try:
                return await self.forward(data)
            except Exception as e:
                print(f"Upstream forwarding error for {qname}: {e}")

        return reply.pack()

    def load_hosts_file(self, file_path):
        """
        Parses a hosts-style file and adds records to the resolver.
        Standard format: IP domain1 [domain2 ...]
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        ip = parts[0]
                        for domain in parts[1:]:
                            self.records[domain] = ip
        except Exception as e:
            print(f"Error loading hosts file {file_path}: {e}")

    async def forward(self, data):
        """
        Forwards the DNS query to an upstream DNS server via UDP.
        """
        loop = asyncio.get_event_loop()
        # UDP forwarding session
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setblocking(False)
            try:
                # Upstream DNS usually listens on port 53
                await loop.sock_connect(sock, (self.upstream, 53))
                await loop.sock_sendall(sock, data)
                # Simple timeout for forwarding to avoid hanging
                return await asyncio.wait_for(loop.sock_recv(sock, 512), timeout=2.0)
            except asyncio.TimeoutError as e:
                raise RuntimeError("Upstream DNS timeout") from e
            except Exception as e:
                raise RuntimeError(
                    f"Failed to forward to upstream: {e}") from e
