from __future__ import annotations
import asyncio
from dnslib import DNSRecord, QTYPE, RR, A, AAAA
import socket
from owldns.types import DNSDict, UpstreamServer
from owldns.utils import logger


class Resolver:
    """
    DNS Resolver that handles local record lookup and upstream forwarding.
    """

    def __init__(self, records: DNSDict | None = None, upstreams: list[UpstreamServer] | None = None):
        self.records: DNSDict = records or {}
        self.upstreams: list[UpstreamServer] = upstreams if upstreams is not None else [
            {"address": "1.1.1.1", "group": None, "proxy": None}]

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
            ips = self.records[matching_domain]
            logger.debug("Local hit: %s [%s] -> %s",
                         qname, QTYPE.get(qtype), ips)
            if qtype == QTYPE.A:
                for ip in ips:
                    if ":" not in ip:  # IPv4
                        reply.add_answer(RR(qname, QTYPE.A, rdata=A(ip)))
                if reply.rr:
                    return reply.pack()
            elif qtype == QTYPE.AAAA:
                for ip in ips:
                    if ":" in ip:  # IPv6
                        reply.add_answer(RR(qname, QTYPE.AAAA, rdata=AAAA(ip)))
                if reply.rr:
                    return reply.pack()

        logger.debug("Local miss: %s [%s]", qname, QTYPE.get(qtype))

        # If not found locally, forward to configured upstreams
        for upstream in self.upstreams:
            upstream_ip = upstream["address"]
            if not upstream_ip:
                continue
            try:
                response = await self.forward(data, upstream_ip)
                # Parse response to extract IPs for logging
                resp_record = DNSRecord.parse(response)
                ips = [str(r.rdata)
                       for r in resp_record.rr if r.rtype in (QTYPE.A, QTYPE.AAAA)]
                logger.debug(
                    "Upstream hit (%s): %s [%s] -> %s", upstream_ip, qname, QTYPE.get(qtype), ips)
                return response
            except Exception as e:
                logger.warning("Upstream %s failed for %s: %s",
                               upstream_ip, qname, e)

        if self.upstreams:
            logger.error("All upstreams failed for %s", qname)

        return reply.pack()

    async def forward(self, data: bytes, upstream_ip: str) -> bytes:
        """
        Forwards the DNS query to a specific upstream DNS server via UDP.
        Supports both IPv4 and IPv6 upstream addresses.
        """
        loop = asyncio.get_running_loop()

        # Determine if upstream is IPv4 or IPv6
        is_ipv6: bool = ":" in upstream_ip
        family = socket.AF_INET6 if is_ipv6 else socket.AF_INET

        # UDP forwarding session
        with socket.socket(family, socket.SOCK_DGRAM) as sock:
            sock.setblocking(False)
            try:
                # Upstream DNS usually listens on port 53
                await loop.sock_connect(sock, (upstream_ip, 53))
                await loop.sock_sendall(sock, data)
                # Simple timeout for forwarding to avoid hanging
                return await asyncio.wait_for(loop.sock_recv(sock, 512), timeout=2.0)
            except asyncio.TimeoutError as e:
                raise RuntimeError(f"Upstream {upstream_ip} timeout") from e
            except Exception as e:
                raise RuntimeError(
                    f"Failed to forward to upstream {upstream_ip}: {e}") from e
