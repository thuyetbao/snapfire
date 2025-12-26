#!/bin/python3

# Global
import signal
from typing import Callable, Awaitable, TypeVar, Tuple, Optional
from datetime import datetime, timezone
import json
import asyncio
import functools
import time
import argparse
import textwrap

# External
import aioping
import aiohttp
import aiofiles


T = TypeVar("T")


def measure_latency(
    func: Callable[..., Awaitable[T]]
) -> Callable[..., Awaitable[Tuple[Optional[float], str, Optional[str]]]]:

    @functools.wraps(func)
    async def invoke(*args, **kwargs):
        start = time.perf_counter()
        try:
            _ = await func(*args, **kwargs)
        except TimeoutError:
            return None, "error", "timeout"
        except Exception as exc:
            return None, "error", str(exc)

        return (time.perf_counter() - start) * 1000, "success", None

    return invoke


@measure_latency
async def run_icmp(host: str, timeout: float = 1.0) -> None:
    await aioping.ping(host, timeout=timeout)


@measure_latency
async def run_tcp(host: str, port: int, timeout: float = 1.0) -> None:
    _, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port),
        timeout=timeout
    )
    writer.close()
    await writer.wait_closed()


@measure_latency
async def run_udp(host: str, port: int, timeout: float = 1.0) -> None:
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        asyncio.DatagramProtocol,
        remote_addr=(host, port)
    )
    transport.sendto(b"\x00")
    await asyncio.sleep(timeout)
    transport.close()


@measure_latency
async def run_http(url: str, timeout: float = 1.0) -> None:
    timeout_cfg = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()


PROTOCOL_RUNNERS = {
    "icmp": run_icmp,
    "tcp": run_tcp,
    "udp": run_udp,
    "http": run_http,
}


async def collect(protocol: str, target: str, timeout: float, output: str):
    on_func = PROTOCOL_RUNNERS.get(protocol)
    host, port = target.rsplit(":", 1)
    url = f"http://{target}"
    _ = url
    if protocol == "icmp":
        latency, status, err = await on_func(target, timeout)

    elif protocol in {"tcp", "udp"}:
        host, port = target.rsplit(":", 1)
        latency, status, err = await on_func(host, int(port), timeout)

    elif protocol == "http":
        latency, status, err = await on_func(f"http://{target}", timeout)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "protocol": protocol,
        "target": target,
        "latency_ms": latency,
        "status": status
    }
    async with aiofiles.open(output, "a") as _file:
        await _file.write(json.dumps(record) + "\n")


async def scheduler(
    target: str,
    timeout: float,
    output: str,
    interval: float
):
    protocols = ["icmp", "tcp", "udp", "http"]

    STOP_EVENT = asyncio.Event()
    WRITE_LOCK = asyncio.Lock()
    _ = WRITE_LOCK

    def _handle_signal(signum, frame):
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(STOP_EVENT.set)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # loop = asyncio.get_event_loop()
    # for sig in (signal.SIGINT, signal.SIGTERM):
    #     loop.add_signal_handler(sig, shutdown)

    while not STOP_EVENT.is_set():
        tasks = [
            asyncio.create_task(
                asyncio.wait_for(
                    collect(proto, target, timeout, output),
                    timeout=timeout + 0.5
                )
            )
            for proto in protocols
        ]

        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(interval)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog="python collector.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
        [Collector] Application to collect latency measurements

        Usage
        -----

        Build
        >>> python collector.py --target 8.8.8.8 --timeout 1 --interval 5 --output data/measurement.jsonl

        Help
        >>> python collector.py --help
        """),
        epilog="Copyright (c) of thuyetbao"
    )
    parser.add_argument(
        "--target",
        dest="target",
        type=str,
        required=True,
        help="Target host or URL"
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=float,
        default=1.0,
        help="Timeout per protocol (seconds). Default is %(default)s seconds"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output",
        type=str,
        default="latency.jsonl",
        help="Output JSONL file path. Default is %(default)s"
    )
    parser.add_argument(
        "--interval",
        dest="interval",
        type=float,
        default=5.0,
        help="Collection interval (seconds). Default is %(default)s seconds"
    )
    args = parser.parse_args()

    asyncio.run(
        scheduler(
            target=args.target,
            timeout=args.timeout,
            output=args.output,
            interval=args.interval
        )
    )

    # TODO: add heath on HTTP, add required config for instance
