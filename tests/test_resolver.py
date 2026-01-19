import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from dnslib import DNSRecord, QTYPE, RR, A
from owldns.resolver import Resolver


@pytest.mark.asyncio
async def test_resolve_local_record():
    records = {"example.com": "1.2.3.4"}
    resolver = Resolver(records=records)

    # Create a DNS A record query for example.com
    q = DNSRecord.question("example.com")
    data = q.pack()

    response_data = await resolver.resolve(data)
    response = DNSRecord.parse(response_data)

    assert len(response.rr) == 1
    assert str(response.rr[0].rdata) == "1.2.3.4"
    assert response.header.rcode == 0


@pytest.mark.asyncio
async def test_resolve_not_found_no_upstream():
    resolver = Resolver(records={}, upstream=None)

    q = DNSRecord.question("unknown.com")
    data = q.pack()

    response_data = await resolver.resolve(data)
    response = DNSRecord.parse(response_data)

    assert len(response.rr) == 0
    assert response.header.rcode == 0


@pytest.mark.asyncio
async def test_resolve_forward_to_upstream():
    resolver = Resolver(records={}, upstream="8.8.8.8")

    q = DNSRecord.question("google.com")
    data = q.pack()

    # Mocking the forward method to avoid real network calls
    with patch.object(Resolver, 'forward', new_callable=AsyncMock) as mock_forward:
        mock_forward.return_value = DNSRecord.question(
            "google.com").reply().pack()

        await resolver.resolve(data)
        mock_forward.assert_awaited_once_with(data)


@pytest.mark.asyncio
async def test_forward_error_handling():
    resolver = Resolver(records={}, upstream="8.8.8.8")
    q = DNSRecord.question("error.com")
    data = q.pack()

    with patch.object(Resolver, 'forward', new_callable=AsyncMock) as mock_forward:
        mock_forward.side_effect = Exception("Forwarding failed")

        # Should not raise exception but return empty reply (per current implementation)
        # and print error.
        response_data = await resolver.resolve(data)
        response = DNSRecord.parse(response_data)
        assert len(response.rr) == 0


@pytest.mark.asyncio
async def test_forward_real_logic():
    resolver = Resolver(records={}, upstream="8.8.8.8")
    data = b"query_data"

    with patch('socket.socket') as mock_sock:
        mock_sock_inst = mock_sock.return_value.__enter__.return_value
        loop = asyncio.get_event_loop()

        with patch.object(loop, 'sock_connect', new_callable=AsyncMock) as mock_connect, \
                patch.object(loop, 'sock_sendall', new_callable=AsyncMock) as mock_send, \
                patch.object(loop, 'sock_recv', new_callable=AsyncMock) as mock_recv:

            mock_recv.return_value = b"response_data"

            res = await resolver.forward(data)

            assert res == b"response_data"
            mock_connect.assert_awaited_once()
            mock_send.assert_awaited_once_with(mock_sock_inst, data)
            mock_recv.assert_awaited_once_with(mock_sock_inst, 512)

@pytest.mark.asyncio
async def test_forward_timeout():
    resolver = Resolver(records={}, upstream="8.8.8.8")
    data = b"query_data"
    
    with patch('socket.socket'):
        loop = asyncio.get_event_loop()
        with patch.object(loop, 'sock_connect', new_callable=AsyncMock),              patch.object(loop, 'sock_sendall', new_callable=AsyncMock),              patch.object(asyncio, 'wait_for', side_effect=asyncio.TimeoutError):
            
            with pytest.raises(RuntimeError, match="Upstream DNS timeout"):
                await resolver.forward(data)

@pytest.mark.asyncio
async def test_forward_generic_error():
    resolver = Resolver(records={}, upstream="8.8.8.8")
    data = b"query_data"
    
    with patch('socket.socket'):
        loop = asyncio.get_event_loop()
        with patch.object(loop, 'sock_connect', side_effect=Exception("Socket error")):
            with pytest.raises(RuntimeError, match="Failed to forward to upstream"):
                await resolver.forward(data)

@pytest.mark.asyncio
async def test_resolve_local_aaaa_record():
    records = {"ipv6.test": "::1"}
    resolver = Resolver(records=records)
    
    # Create a DNS AAAA record query for ipv6.test
    q = DNSRecord.question("ipv6.test", "AAAA")
    data = q.pack()
    
    response_data = await resolver.resolve(data)
    response = DNSRecord.parse(response_data)
    
    assert len(response.rr) == 1
    assert response.rr[0].rtype == QTYPE.AAAA
    assert str(response.rr[0].rdata) == "::1"
    assert response.header.rcode == 0

@pytest.mark.asyncio
async def test_resolve_wildcard_record():
    records = {"*.wild.test": "10.10.10.10"}
    resolver = Resolver(records=records)
    
    # Test sub-domain matching
    q1 = DNSRecord.question("abc.wild.test", "A")
    res1 = DNSRecord.parse(await resolver.resolve(q1.pack()))
    assert str(res1.rr[0].rdata) == "10.10.10.10"
    
    # Test multi-level sub-domain
    q2 = DNSRecord.question("123.abc.wild.test", "A")
    res2 = DNSRecord.parse(await resolver.resolve(q2.pack()))
    assert str(res2.rr[0].rdata) == "10.10.10.10"
    
    # Test exact suffix matching (wild.test should match *.wild.test)
    q3 = DNSRecord.question("wild.test", "A")
    res3 = DNSRecord.parse(await resolver.resolve(q3.pack()))
    assert str(res3.rr[0].rdata) == "10.10.10.10"

@pytest.mark.asyncio
async def test_load_hosts_file(tmp_path):
    hosts_content = """
    # Comments are ignored
    127.0.0.1  localhost mypc
    ::1        localhost
    192.168.1.5 server.local
    """
    hosts_file = tmp_path / "hosts"
    hosts_file.write_text(hosts_content)
    
    resolver = Resolver()
    resolver.load_hosts_file(str(hosts_file))
    
    assert resolver.records["localhost"] in ["127.0.0.1", "::1"]
    assert resolver.records["mypc"] == "127.0.0.1"
    assert resolver.records["server.local"] == "192.168.1.5"
