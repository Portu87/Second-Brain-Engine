"""Small result models shared by the CLI and validators."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Severity = Literal["error", "warning"]


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    severity: Severity
    message: str
    path: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ValidationReport:
    findings: tuple[Finding, ...]

    @property
    def ok(self) -> bool:
        return not any(item.severity == "error" for item in self.findings)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(item for item in self.findings if item.severity == "error")

    @property
    def warnings(self) -> tuple[Finding, ...]:
        return tuple(item for item in self.findings if item.severity == "warning")

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "findings": [item.as_dict() for item in self.findings],
        }
