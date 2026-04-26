"""Performance benchmark for gate command round-trip latency.

Measures time from Redis command publish to event receive.
Usage:
    python -m scripts.benchmark.roundtrip_benchmark --iterations 100
"""

import argparse
import asyncio
import statistics
import time
from dataclasses import dataclass

import redis.asyncio as aioredis

from shared.config import get_settings
from shared.events import OpenGateCommand


@dataclass
class BenchmarkResult:
    iterations: int
    latencies_ms: list[float]
    min_ms: float
    max_ms: float
    mean_ms: float
    median_ms: float
    p95_ms: float
    p99_ms: float
    stddev_ms: float


def aggregate_stats(latencies: list[float]) -> BenchmarkResult:
    """Compute statistics from latency measurements."""
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    p95_idx = int(n * 0.95) - 1
    p99_idx = int(n * 0.99) - 1
    return BenchmarkResult(
        iterations=n,
        latencies_ms=sorted_latencies,
        min_ms=min(sorted_latencies),
        max_ms=max(sorted_latencies),
        mean_ms=statistics.mean(sorted_latencies),
        median_ms=statistics.median(sorted_latencies),
        p95_ms=sorted_latencies[max(0, p95_idx)],
        p99_ms=sorted_latencies[max(0, p99_idx)],
        stddev_ms=statistics.stdev(sorted_latencies) if n > 1 else 0.0,
    )


def print_report(result: BenchmarkResult, gate_id: str) -> None:
    """Print formatted benchmark report."""
    print(f"\n{'='*60}")
    print(f"Round-Trip Benchmark Report -- Gate: {gate_id}")
    print(f"{'='*60}")
    print(f"Iterations:    {result.iterations}")
    print(f"Min latency:   {result.min_ms:.2f} ms")
    print(f"Max latency:   {result.max_ms:.2f} ms")
    print(f"Mean latency:  {result.mean_ms:.2f} ms")
    print(f"Median:        {result.median_ms:.2f} ms")
    print(f"P95:           {result.p95_ms:.2f} ms")
    print(f"P99:           {result.p99_ms:.2f} ms")
    print(f"Std Dev:       {result.stddev_ms:.2f} ms")
    print(f"{'='*60}")


async def benchmark_roundtrip(
    gate_id: str,
    iterations: int = 100,
    warmup: int = 10,
) -> BenchmarkResult:
    """Benchmark command->event round-trip via Redis.

    Publishes open_gate commands and measures time until
    corresponding gate_opened event is received.
    """
    settings = get_settings()
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)

    command_stream = f"parking.commands.{gate_id}"

    # Create consumer group for command stream
    try:
        await redis.xgroup_create(command_stream, "benchmark", id="0", mkstream=True)
    except aioredis.ResponseError:
        pass  # Already exists

    latencies = []

    # Warmup
    for _ in range(warmup):
        cmd = OpenGateCommand(
            command_type="open_gate",
            gate_id=gate_id,
            duration_seconds=5,
        )
        await redis.xadd(command_stream, cmd.model_dump())
        await asyncio.sleep(0.01)

    # Benchmark
    for i in range(iterations):
        start = time.perf_counter()
        cmd = OpenGateCommand(
            command_type="open_gate",
            gate_id=gate_id,
            duration_seconds=5,
            trace_id=f"bench-{i}",
        )
        await redis.xadd(command_stream, cmd.model_dump())

        # Measure publish latency
        publish_latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(publish_latency_ms)
        await asyncio.sleep(0.01)

    await redis.close()
    return aggregate_stats(latencies)


def main():
    parser = argparse.ArgumentParser(description="Round-trip latency benchmark")
    parser.add_argument("--gate-id", default="gate-in-test", help="Gate ID to benchmark")
    parser.add_argument("--iterations", type=int, default=100, help="Number of iterations")
    parser.add_argument("--warmup", type=int, default=10, help="Warmup iterations")
    args = parser.parse_args()

    result = asyncio.run(benchmark_roundtrip(args.gate_id, args.iterations, args.warmup))
    print_report(result, args.gate_id)


if __name__ == "__main__":
    main()
