#!/bin/python3

# Global
import sys
from typing import Callable, Awaitable, TypeVar, Tuple, Optional, Any
from datetime import datetime, timezone
import signal
import json
import asyncio
import functools
import time
import argparse
import textwrap
import ipaddress
import re
import pathlib
import logging

# External
import aioping
import aiohttp
import aiofiles
import structlog


# Build
LOG: structlog.stdlib.BoundLogger = structlog.get_logger()


def configure_logging(
    service_name: str,
    log_level: str = "INFO",
) -> None:
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        # wrapper_class=AsyncBoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service_name)
    return None


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

PROTOCOL_DEFAULT_SCHEDULERS_CONFIGURATIONS: dict[str, dict[str, float]] = {
    "icmp": {
        "interval": 2.0,
        "timeout": 2.0,
    },
    "tcp": {
        "interval": 5.0,
        "timeout": 2.0,
    },
    "udp": {
        "interval": 5.0,
        "timeout": 2.0,
    },
    "http": {
        "interval": 5.0,
        "timeout": 2.0,
    },
}


PROTOCOL_DEFAULT_CONFIGURATIONS: dict[str, dict[str, Any]] = {
    "icmp": {
        "host": "[host]",
    },
    "tcp": {
        "host": "[host]",
        "port": 80,
    },
    "udp": {
        "host": "[host]",
        "port": 53,
    },
    "http": {
        "url": "[url]",
    },
}


async def collect(
    protocol: str,
    func: Callable[..., asyncio.Future],
    queue: asyncio.Queue,
    **kwargs,
):
    latency, status, err = await func(**kwargs)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "protocol": protocol,
        "target": kwargs.get("host", kwargs.get("url", None)),
        "duration_ms": latency,
        "status": status,
        "reason": err,
    }
    await queue.put(record)


async def invoke_scheduler_with_protocol(
    *,
    protocol: str,
    queue: asyncio.Queue,
    stop_event: asyncio.Event,
    func: Callable[..., Awaitable[Tuple[Optional[float], str, Optional[str]]]],
    interval: float,
    timeout: float,
    **func_kwargs,
):

    # Build
    loop = asyncio.get_running_loop()
    next_tick = loop.time()
    run_idx = 0
    structlog.contextvars.bind_contextvars(protocol=protocol)
    await LOG.ainfo(f"Run experiment for protocol {protocol}")

    # Run
    while not stop_event.is_set():
        next_tick += interval

        try:
            await LOG.ainfo(f"Start collect metrics using {func.__name__} function")
            structlog.contextvars.bind_contextvars(run_id=run_idx)
            await asyncio.wait_for(
                collect(
                    protocol=protocol,
                    queue=queue,
                    func=func,
                    **func_kwargs,
                ),
                # Add 0.5 seconds to the timeout to account for the time it takes
                # to collect the latency measurement and enqueue the record
                timeout=timeout + 0.5,
            )
        except Exception:
            pass
        finally:
            await LOG.ainfo("Push record into queue")
            run_idx += 1

        await asyncio.sleep(max(0, next_tick - loop.time()))


async def write_batch_records_with_jsonl(
    *,
    output: str,
    batch_size: int = 5,
    flush_interval: float = float(5.0),
    protocol_queues: dict[str, asyncio.Queue],
    stop_event: asyncio.Event,
):

    # Set
    buffers: dict[str, list] = {p: [] for p in protocol_queues}

    async with aiofiles.open(output, "a") as _file:
        while not stop_event.is_set() or any(not q.empty() for q in protocol_queues.values()):
            for proto, queue in protocol_queues.items():
                try:
                    item = queue.get_nowait()
                except asyncio.QueueEmpty:
                    continue

                buffers[proto].append(item)
                queue.task_done()

                if len(buffers[proto]) >= batch_size:
                    await _file.write(
                        "\n".join(json.dumps(r) for r in buffers[proto]) + "\n"
                    )
                    buffers[proto].clear()

            await asyncio.sleep(flush_interval)

        # final flush
        for buf in buffers.values():
            if buf:
                await _file.write("\n".join(json.dumps(r) for r in buf) + "\n")


def install_signal_handlers(event: asyncio.Event):

    def _handler(signum, frame):
        event.set()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


async def run_measurements(
    *,
    ip: str,
    output: str,
    configuration: dict,
):

    # The supported protocols for latency measurement
    protocols = ["icmp", "tcp", "udp", "http"]

    # The batch size is the number of records to write to the file at once
    batch_size: int = 5

    # Checkpoint
    await LOG.ainfo(f"Starting collector for {ip} with {len(protocols)} protocols: {protocols}")

    # Match
    proto_arguments = {proto: {} for proto in protocols}
    for proto in protocols:
        for cfg_key, cfg_val in configuration.items():
            p_search_result = re.search(rf"^{re.escape(proto)}[-_](?P<config_key>.+)$", cfg_key)
            if p_search_result is None:
                continue
            arg_key, arg_val = p_search_result.group("config_key"), cfg_val
            proto_arguments[proto][arg_key] = arg_val

    # Build
    proto_schedulers = PROTOCOL_DEFAULT_SCHEDULERS_CONFIGURATIONS.copy()
    for proto in protocols:
        on_args = proto_arguments[proto]
        if "timeout" in on_args:
            proto_schedulers[proto]["timeout"] = on_args["timeout"]
        if "interval" in on_args:
            proto_schedulers[proto]["interval"] = on_args["interval"]

    # Build
    proto_configurations = PROTOCOL_DEFAULT_CONFIGURATIONS.copy()
    for proto in protocols:
        on_args = proto_arguments[proto]
        p_config = {}
        for fset in ("host", "port", "url", "path", "scheme"):
            if fset in on_args:
                p_config[fset] = on_args[fset]

        # Chain
        if proto in ("icmp", "tcp", "udp"):
            proto_configurations[proto]["host"] = ip
            if "port" in p_config:
                proto_configurations[proto]["port"] = p_config["port"]
        elif proto == "http":
            at_url = ip
            if "port" in p_config:
                at_url = ip + ":" + p_config["port"]
            if "path" in p_config:
                at_url = at_url + "/" + p_config["path"]
            if "scheme" in p_config:
                at_url = p_config["scheme"] + "://" + at_url
            proto_configurations[proto]["url"] = at_url

    await LOG.ainfo(f"With arguments: {proto_arguments}")
    await LOG.ainfo(f"With schedulers: {proto_schedulers}")
    await LOG.ainfo(f"With configurations: {proto_configurations}")
    await LOG.ainfo(f"With output: {output}")

    # Build
    proto_queues = {proto: asyncio.Queue() for proto in protocols}
    await LOG.ainfo("Set queues for protocols")

    # Set
    stop_event = asyncio.Event()
    install_signal_handlers(event=stop_event)
    await LOG.ainfo("Set stop event in the event loop")

    # Set
    task_write_result_to_jsonl = asyncio.create_task(
        write_batch_records_with_jsonl(
            output=output,
            protocol_queues=proto_queues,
            batch_size=batch_size,
            stop_event=stop_event,
        )
    )
    await LOG.ainfo(f"Set async writer task with batch size {batch_size} records")

    # Build
    tasks = [
        asyncio.create_task(
            invoke_scheduler_with_protocol(
                protocol=proto,
                queue=proto_queues[proto],
                stop_event=stop_event,
                func=PROTOCOL_RUNNERS[proto],
                interval=proto_schedulers[proto]["interval"],
                timeout=proto_schedulers[proto]["timeout"],
                **proto_configurations[proto],
            )
        )
        for proto in protocols
    ]
    await LOG.ainfo(f"Build {len(tasks)} tasks to invoke schedulers")

    # Wait
    await stop_event.wait()      # ← main blocking point

    for t in tasks:
        t.cancel()

    # Run
    await asyncio.gather(*tasks, return_exceptions=True)

    # Wait
    for q in proto_queues.values():
        await q.join()

    # Handle
    task_write_result_to_jsonl.cancel()
    await asyncio.gather(task_write_result_to_jsonl, return_exceptions=True)
    await LOG.ainfo("Flush write to output file")


def parse_argument_address(value: str) -> str:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid address '{value}'. Expected IP address")
    else:
        return value


def parse_argument_keyval(value: str):
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"Invalid key=value '{value}'. Expected key=value")
    key, val = value.split("=", 1)
    return key, val


def parse_argument_output_jsonl(value: str) -> str:
    if pathlib.Path(value).suffix != ".jsonl":
        raise argparse.ArgumentTypeError(f"Invalid file '{value}'. Expected JSONL file")
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
        >>> python collector.py \
                --ip 8.8.8.8 \
                --output data/measurement.jsonl \
                --set "tcp_port=80" \
                --set "udp_port=53" \
                --set "http_port=4200" --set "http_path=//health" --set "http_scheme=http"

        Note
        ----
        For [http_path] use escape characters for special characters with // and `"`

        Help
        >>> python collector.py --help
        """),
        epilog="Copyright (c) of thuyetbao"
    )
    parser.add_argument(
        "--ip", "--address",
        dest="ip",
        type=parse_argument_address,
        required=True,
        help="Target IP address"
    )
    parser.add_argument(
        "-o", "--output",
        dest="output",
        type=parse_argument_output_jsonl,
        default="latency.jsonl",
        help="Output JSONL file path. Default is %(default)s"
    )
    parser.add_argument(
        "--set",
        dest="config",
        action="append",
        type=parse_argument_keyval,
        help="Set config value (key=value)"
    )
    args = parser.parse_args()

    # Configure
    configure_logging(service_name="probe-collector", log_level="INFO")

    # Run
    asyncio.run(
        run_measurements(
            ip=args.ip,
            output=args.output,
            configuration={elem[0]: elem[1] for elem in args.config},
        )
    )
