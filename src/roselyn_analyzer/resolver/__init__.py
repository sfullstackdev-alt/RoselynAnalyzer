"""Resolver - Issue resolution utilities."""

from .sarif_reader import parse_sarif_result, read_sarif_results

__all__ = ["parse_sarif_result", "read_sarif_results"]
