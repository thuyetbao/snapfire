#!/bin/python3

# Global
from typing import Callable, Awaitable, TypeVar, Tuple, Optional
from datetime import datetime, timezone
import signal
import json
import asyncio
import functools
import time
import argparse
import textwrap
import ipaddress

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
    response_fut = loop.create_future()

    class ClientProtocol(asyncio.DatagramProtocol):
        def connection_made(self, transport):
            self.transport = transport
            self.transport.sendto(b"\x00")

        def datagram_received(self, data, addr):
            if not response_fut.done():
                response_fut.set_result(None)

        def error_received(self, exc):
            if not response_fut.done():
                response_fut.set_exception(exc)

    transport, _ = await loop.create_datagram_endpoint(
        ClientProtocol,
        remote_addr=(host, port),
    )

    try:
        await asyncio.wait_for(response_fut, timeout)
    finally:
        transport.close()


@measure_latency
async def run_http(url: str, timeout: float = 1.0) -> None:
    timeout_cfg = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
        async with session.get(url) as resp:
            resp.raise_for_status()


PROTOCOL_RUNNERS: dict[str, Callable[..., asyncio.Future]] = {
    "icmp": run_icmp,
    "tcp": run_tcp,
    "udp": run_udp,
    "http": run_http,
}


PROTOCOL_CONFIG = {
    "icmp": {
        "host": "[host]",
        "interval": 2.0,
        "timeout": 1.0,
    },
    "tcp": {
        "host": "[host]",
        "port": None,
        "interval": 5.0,
        "timeout": 1.5,
    },
    "udp": {
        "host": "[host]",
        "port": None,
        "interval": 15.0,
        "timeout": 1.0,
    },
    "http": {
        "host": "[host]",
        "port": None,
        "path": "/health",
        "scheme": "http",   # or https
        "interval": 30.0,
        "timeout": 3.0,
    },
}


async def collect(
    protocol: str,
    target: str,
    func: Callable[..., asyncio.Future],
    timeout: float,
    queue: asyncio.Queue,
    **kwargs,
):
    latency, status, err = await func(target, timeout, **kwargs)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "protocol": protocol,
        "target": target,
        "duration_ms": latency,
        "status": status,
        "reason": err,
    }
    await queue.put(record)


async def invoke_scheduler_by_protocol(
    *,
    protocol: str,
    ip: str,
    interval: float,
    timeout: float,
    queue: asyncio.Queue,
    stop_event: asyncio.Event,
    **kwargs,
):
    loop = asyncio.get_running_loop()
    next_tick = loop.time()

    # Search for protocol
    on_func = PROTOCOL_RUNNERS.get(protocol)
    on_protocol_config = kwargs or {}

    while not stop_event.is_set():
        next_tick += interval

        try:
            await asyncio.wait_for(
                collect(
                    func=on_func,
                    protocol=protocol,
                    ip=ip,
                    timeout=timeout,
                    queue=queue,
                    **on_protocol_config,
                ),
                # Add 0.5 seconds to the timeout to account for the time it takes
                # to collect the latency measurement and enqueue the record
                timeout=timeout + 0.5,
            )
        except Exception:
            pass

        await asyncio.sleep(max(0, next_tick - loop.time()))


async def batch_writer(
    *,
    output: str,
    protocol_queues: dict[str, asyncio.Queue],
    batch_size: int,
    flush_interval: float = 1.0,
    stop_event: asyncio.Event,
):
    buffers: dict[str, list] = {p: [] for p in protocol_queues}

    async with aiofiles.open(output, "a") as f:
        while not stop_event.is_set() or any(not q.empty() for q in protocol_queues.values()):
            for proto, queue in protocol_queues.items():
                try:
                    item = queue.get_nowait()
                except asyncio.QueueEmpty:
                    continue

                buffers[proto].append(item)
                queue.task_done()

                if len(buffers[proto]) >= batch_size:
                    await f.write(
                        "\n".join(json.dumps(r) for r in buffers[proto]) + "\n"
                    )
                    buffers[proto].clear()

            await asyncio.sleep(flush_interval)

        # final flush
        for buf in buffers.values():
            if buf:
                await f.write("\n".join(json.dumps(r) for r in buf) + "\n")


def install_signal_handlers(event: asyncio.Event):

    def _handler(signum, frame):
        event.set()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


async def build_schedulers(
    *,
    ip: str,
    output: str,
    configuration: dict,
    batch_size: int = 50,
):

    # The following is a list of all supported protocols
    protocols = ["icmp", "tcp", "udp", "http"]

    # Set
    stop_event = asyncio.Event()
    install_signal_handlers(event=stop_event)

    configuration = {
        "icmp": {"interval": 2.0, "timeout": 1.0},
        "tcp":  {"interval": 5.0, "timeout": 1.5, "port": 80},
        "udp":  {"interval": 15.0, "timeout": 1.0, "port": 53},
        "http": {"interval": 30.0, "timeout": 3.0, "path": "/"},
    }
    # host, port = target.rsplit(":", 1)
    # url = f"http://{target}"
    # _ = url

    # if protocol == "icmp":
    #     l

    # elif protocol in {"tcp", "udp"}:
    #     host, port = target.rsplit(":", 1)
    #     latency, status, err = await on_func(host, int(port), timeout)

    # elif protocol == "http":
    #     latency, status, err = await on_func(f"http://{target}", timeout)
    protocol_queues = {proto: asyncio.Queue() for proto in configuration}

    tasks = [
        asyncio.create_task(
            invoke_scheduler_by_protocol(
                protocol=proto,
                ip=ip,
                output=output,
                queue=protocol_queues[proto],
                interval=configuration[proto]["interval"],
                timeout=configuration[proto]["timeout"],
            )
        )
        for proto in protocols
    ]

    await asyncio.gather(*tasks, return_exceptions=True)

    for q in protocol_queues.values():
        await q.join()

    await asyncio.create_task(
        batch_writer(
            output=output,
            protocol_queues=protocol_queues,
            batch_size=batch_size,
            stop_event=stop_event,
        )
    )


def validate_ip_address(value: str) -> str:

    # Accept IP or hostname
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid address '{value}'. Expected IP address")
    else:
        return value


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
        "--ip",
        dest="ip",
        type=validate_ip_address,
        required=True,
        help="Target IP address"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output",
        type=str,
        default="latency.jsonl",
        help="Output JSONL file path. Default is %(default)s"
    )
    parser.add_argument(
        "--config",
        dest="config",
        type=str,
        default=float(5.0),
        help="Timeout per protocol (seconds). Default is %(default)s seconds"
    )
    args = parser.parse_args()

    asyncio.run(
        build_schedulers(
            ip=args.ip,
            output=args.output,
            config=args.config,
        )
    )
