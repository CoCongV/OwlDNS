from __future__ import annotations
import asyncio
import time
import socket
import uvloop
from dnslib import DNSRecord


async def send_query(host: str, port: int, data: bytes) -> None:
    """Sends a single DNS query over UDP."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    loop = asyncio.get_running_loop()
    try:
        await loop.sock_sendall(sock, data)
        # We don't necessarily wait for response in a high-load injection test
        # but in a real latency test we would.
    finally:
        sock.close()


async def benchmark(count: int = 10000, concurrency: int = 100) -> None:
    host, port = "127.0.0.1", 5353
    q = DNSRecord.question("example.com")
    data = q.pack()

    print(
        f"🚀 Starting benchmark: {count} queries, concurrency {concurrency}...")

    start = time.perf_counter()

    for i in range(0, count, concurrency):
        tasks = [send_query(host, port, data)
                 for _ in range(min(concurrency, count - i))]
        await asyncio.gather(*tasks)

    end = time.perf_counter()
    duration = end - start

    print("-" * 40)
    print(f"🏁 Benchmark Complete")
    print(f"⏱️  Total Duration: {duration:.4f}s")
    print(f"📈 Estimated QPS: {count/duration:.2f}")
    print("-" * 40)

if __name__ == "__main__":
    # Use uvloop for the injector too for maximum performance
    asyncio.run(benchmark(10000, 500), loop_factory=uvloop.new_event_loop)
