"""Execution metrics and timing helpers."""

from __future__ import annotations

import functools
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from src.core.logger import logger


@dataclass
class ExecutionMetric:
    """Execution metric for a function."""

    function_name: str
    execution_time: float
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: str | None = None


class MetricsCollector:
    """Centralized metrics collector."""

    _instance: "MetricsCollector | None" = None

    def __new__(cls: type["MetricsCollector"]) -> "MetricsCollector":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = []
            cls._instance._counters = defaultdict(int)
        return cls._instance

    def record(self, metric: ExecutionMetric) -> None:
        """Record a metric entry."""
        self._metrics.append(metric)
        self._counters[f"{metric.function_name}_calls"] += 1
        if not metric.success:
            self._counters[f"{metric.function_name}_errors"] += 1

    def increment(self, counter_name: str, value: int = 1) -> None:
        """Increment a counter."""
        self._counters[counter_name] += value

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of collected metrics."""
        if not self._metrics:
            return {"total_calls": 0, "functions": {}}

        summary: dict[str, Any] = {
            "total_calls": len(self._metrics),
            "total_errors": sum(1 for m in self._metrics if not m.success),
            "functions": {},
        }

        by_function: dict[str, list[ExecutionMetric]] = defaultdict(list)
        for metric in self._metrics:
            by_function[metric.function_name].append(metric)

        for func_name, metrics in by_function.items():
            times = [m.execution_time for m in metrics]
            summary["functions"][func_name] = {
                "calls": len(metrics),
                "errors": sum(1 for m in metrics if not m.success),
                "avg_time_ms": sum(times) / len(times) * 1000,
                "max_time_ms": max(times) * 1000,
                "min_time_ms": min(times) * 1000,
            }

        return summary


def timed(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to measure execution time."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        collector = MetricsCollector()
        start = time.perf_counter()
        success = True
        error_msg = None

        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            success = False
            error_msg = str(exc)
            raise
        finally:
            elapsed = time.perf_counter() - start
            collector.record(
                ExecutionMetric(
                    function_name=func.__name__,
                    execution_time=elapsed,
                    success=success,
                    error_message=error_msg,
                )
            )

            if elapsed > 5:
                logger.warning("%s took %.2fs", func.__name__, elapsed)

    return wrapper
