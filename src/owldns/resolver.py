from __future__ import annotations
import asyncio
from dnslib import DNSRecord, QTYPE, RR, A, AAAA
import socket
from owldns.utils import logger


class Resolver:
    """
    DNS Resolver that handles local record lookup and upstream forwarding.
    """

    def __init__(self, records: dict[str, str] | None = None, upstream: str | None = "1.1.1.1"):
        self.records: dict[str, str] = records or {}
        self.upstream: str | None = upstream

    async def resolve(self, data: bytes) -> bytes:
        """
        Parses the DNS query and attempts to resolve it locally or via upstream.
        """
        request: DNSRecord = DNSRecord.parse(data)
        reply: DNSRecord = request.reply()
        qname: str = str(request.q.qname).rstrip('.')
        qtype: int = request.q.qtype

        # TODO: Implement GeoDNS & Split-Horizon Routing based on client IP

        # Handle local A and AAAA record lookups
        matching_domain: str | None = None
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
                logger.error("Upstream forwarding error for %s: %s", qname, e)

        return reply.pack()

    async def forward(self, data: bytes) -> bytes:
        """
        Forwards the DNS query to an upstream DNS server via UDP.
        """
        loop = asyncio.get_running_loop()
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
