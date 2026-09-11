"""Execution adapters for validate-skill case runners.

Adapters only construct an invocation. The validation coordinator remains
responsible for process lifetime, fixture isolation, completion records, and
reporting.
"""

from .claude import ClaudeAdapter
from .contract import AdapterError, RunnerRequest, RunnerSpec, domains_from_dependencies
from .codex import CodexAdapter
from .cursor import CursorAdapter
from .gemini import GeminiAdapter

__all__ = [
    "AdapterError",
    "ClaudeAdapter",
    "CodexAdapter",
    "CursorAdapter",
    "GeminiAdapter",
    "RunnerRequest",
    "RunnerSpec",
    "domains_from_dependencies",
]


def adapter_for(name: str):
    """Return a named foreground adapter."""
    adapters = {
        "codex": CodexAdapter,
        "claude": ClaudeAdapter,
        "cursor": CursorAdapter,
        "gemini": GeminiAdapter,
    }
    try:
        return adapters[name]()
    except KeyError as error:
        raise AdapterError(f"unknown runner adapter: {name}") from error
