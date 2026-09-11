"""Common contract for validate-skill execution adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class AdapterError(ValueError):
    """Raised when an adapter cannot safely construct an invocation."""


@dataclass(frozen=True)
class RunnerRequest:
    """Inputs shared by every supported agent client."""

    prompt: str
    workspace: Path
    output_path: Path
    skill_name: str | None = None
    network_profile: str = "isolated"
    allowed_domains: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.network_profile not in {"isolated", "network"}:
            raise AdapterError(f"unsupported network profile: {self.network_profile}")
        if self.network_profile == "network" and not self.allowed_domains:
            raise AdapterError("network profile requires at least one allowed domain")


@dataclass(frozen=True)
class RunnerSpec:
    """A process invocation ready for the synchronous case-runner gate."""

    command: tuple[str, ...]
    environment: dict[str, str] = field(default_factory=dict)


def domains_from_dependencies(dependencies: tuple[str, ...]) -> tuple[str, ...]:
    """Return hostnames from declared dependency URLs."""
    from urllib.parse import urlparse

    domains = []
    for dependency in dependencies:
        hostname = urlparse(dependency).hostname
        if hostname and hostname not in domains:
            domains.append(hostname)
    return tuple(domains)


class RunnerAdapter(Protocol):
    """Build a backend-specific process invocation."""

    name: str

    def build(self, request: RunnerRequest) -> RunnerSpec:
        ...
