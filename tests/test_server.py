from unittest.mock import AsyncMock
import asyncio
import pytest
from unittest.mock import MagicMock
from dnslib import DNSRecord
from owldns.server import OwlDNSProtocol, OwlDNSServer


@pytest.mark.asyncio
async def test_protocol_handles_query():
    resolver = MagicMock()
    resolver.resolve = AsyncMock(return_value=b"response")

    protocol = OwlDNSProtocol(resolver)
    transport = MagicMock()
    protocol.connection_made(transport)

    addr = ("127.0.0.1", 12345)
    protocol.datagram_received(b"query", addr)

    # Wait for the async task to complete
    await asyncio.sleep(0.1)

    resolver.resolve.assert_awaited_once_with(b"query")
    transport.sendto.assert_called_once_with(b"response", addr)

# Helper for AsyncMock since it's only in unittest.mock for 3.8+


@pytest.mark.asyncio
async def test_server_start_stop():
    server = OwlDNSServer(host="127.0.0.1", port=5354)

    # Start server in a task
    server_task = asyncio.create_task(server.start())

    # Give it a moment to bind
    await asyncio.sleep(0.5)

    assert server.transport is not None
    assert not server.transport.is_closing()

    # Clean up
    server.transport.close()
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_end_to_end_local_resolution():
    records = {"local.test": "127.0.0.1"}
    server = OwlDNSServer(host="127.0.0.1", port=5355, records=records)

    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.5)

    try:
        # Create a real DNS query
        q = DNSRecord.question("local.test")
        query_data = q.pack()

        # Send via UDP socket
        loop = asyncio.get_running_loop()

        class ClientProtocol(asyncio.DatagramProtocol):
            def __init__(self, message, done):
                self.message = message
                self.done = done
                self.transport = None

            def connection_made(self, transport):
                self.transport = transport
                self.transport.sendto(self.message)

            def datagram_received(self, data, addr):
                self.data = data
                self.transport.close()

            def connection_lost(self, exc):
                self.done.set_result(self.data)

        done = loop.create_future()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: ClientProtocol(query_data, done),
            remote_addr=("127.0.0.1", 5355)
        )

        response_data = await asyncio.wait_for(done, timeout=2.0)
        response = DNSRecord.parse(response_data)

        assert str(response.rr[0].rdata) == "127.0.0.1"

    finally:
        server.transport.close()
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

@pytest.mark.asyncio
async def test_protocol_handle_query_error():
    resolver = MagicMock()
    resolver.resolve = AsyncMock(side_effect=Exception("Resolution failed"))
    
    protocol = OwlDNSProtocol(resolver)
    addr = ("127.0.0.1", 12345)
    
    # Should catch exception and print it (lines 28-29 in server.py)
    await protocol.handle_query(b"data", addr)
