import asyncio
from owldns.resolver import Resolver
from owldns.utils import logger


class OwlDNSProtocol(asyncio.DatagramProtocol):
    """
    Asyncio DatagramProtocol for handling UDP DNS queries.
    """

    def __init__(self, resolver: Resolver):
        self.resolver: Resolver = resolver
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        """Called when the transport is established."""
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]):
        """Asynchronously handles incoming UDP datagrams."""
        asyncio.create_task(self.handle_query(data, addr))

    async def handle_query(self, data: bytes, addr: tuple[str, int]) -> None:
        """Processes a DNS query and sends the response back to the client."""
        try:
            response = await self.resolver.resolve(data)
            if response:
                self.transport.sendto(response, addr)
        except Exception as e:
            logger.error("Error handling query from %s: %s", addr, e)


class OwlDNSServer:
    """
    The main DNS server class that manages the resolver and the network endpoint.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 53,
                 records: dict[str, list[str]] | None = None, upstream: str = "1.1.1.1"):
        self.host: str = host
        self.port: int = port
        self.resolver: Resolver = Resolver(records, upstream)
        self.transport: asyncio.DatagramTransport | None = None
        self.protocol: OwlDNSProtocol | None = None

    async def start(self):
        """Starts the async UDP DNS server."""
        loop = asyncio.get_running_loop()
        logger.info("OwlDNS starting on %s:%d...", self.host, self.port)

        # Create the UDP endpoint
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: OwlDNSProtocol(self.resolver),
            local_addr=(self.host, self.port)
        )

        try:
            # Keep the server running until cancelled
            await asyncio.Future()
        finally:
            if self.transport:
                self.transport.close()
