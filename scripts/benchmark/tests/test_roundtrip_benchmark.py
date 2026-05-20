"""Tests for roundtrip benchmark."""


from scripts.benchmark.roundtrip_benchmark import aggregate_stats


class TestAggregateStats:
    def test_basic_stats(self):
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = aggregate_stats(latencies)
        assert result.iterations == 5
        assert result.min_ms == 10.0
        assert result.max_ms == 50.0
        assert result.mean_ms == 30.0
        assert result.median_ms == 30.0

    def test_p95_p99(self):
        latencies = list(range(1, 101))  # 1..100
        result = aggregate_stats(latencies)
        assert result.p95_ms == 95
        assert result.p99_ms == 99

    def test_single_value(self):
        result = aggregate_stats([42.0])
        assert result.iterations == 1
        assert result.min_ms == 42.0
        assert result.max_ms == 42.0
        assert result.stddev_ms == 0.0

    def test_sorted_output(self):
        latencies = [50.0, 10.0, 30.0, 20.0, 40.0]
        result = aggregate_stats(latencies)
        assert result.latencies_ms == [10.0, 20.0, 30.0, 40.0, 50.0]
