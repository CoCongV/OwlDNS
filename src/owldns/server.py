import asyncio
from owldns.resolver import Resolver
from owldns.utils import logger


class OwlDNSProtocol(asyncio.DatagramProtocol):
    """
    Asyncio DatagramProtocol for handling UDP DNS queries.
    """

    def __init__(self, resolver):
        self.resolver = resolver
        self.transport = None

    def connection_made(self, transport):
        """Called when the transport is established."""
        self.transport = transport

    def datagram_received(self, data, addr):
        """Asynchronously handles incoming UDP datagrams."""
        asyncio.create_task(self.handle_query(data, addr))

    async def handle_query(self, data, addr):
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

    def __init__(self, host="0.0.0.0", port=53, records=None, upstream="8.8.8.8"):
        self.host = host
        self.port = port
        self.resolver = Resolver(records, upstream)
        self.transport = None
        self.protocol = None

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
