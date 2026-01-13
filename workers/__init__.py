"""Compatibility package for worker Lambdas used in tests."""

from src.rest_api.workers import agent_worker, delivery_worker

__all__ = ["agent_worker", "delivery_worker"]
