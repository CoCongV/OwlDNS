import asyncio
from dnslib import DNSRecord, QTYPE, RR, A
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

        # Only handle A records for simplicity as requested
        if qtype == QTYPE.A:
            if qname in self.records:
                reply.add_answer(
                    RR(qname, QTYPE.A, rdata=A(self.records[qname])))
                return reply.pack()

        # If not found locally, forward to upstream
        if self.upstream:
            try:
                return await self.forward(data)
            except Exception as e:
                print(f"Upstream forwarding error for {qname}: {e}")

        return reply.pack()

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
