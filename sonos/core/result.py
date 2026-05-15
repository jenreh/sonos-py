"""CommandResult and ErrorDetail — uniform JSON-serialisable response envelope."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorDetail:
    code: str
    message: str
    candidates: list[dict[str, Any]] = field(default_factory=list)
    remediation: str | None = None
    requires_confirmation: bool = False
    suggested_arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.candidates:
            d["candidates"] = self.candidates
        if self.remediation:
            d["remediation"] = self.remediation
        if self.requires_confirmation:
            d["requires_confirmation"] = True
            d["suggested_arguments"] = self.suggested_arguments
        return d


@dataclass
class CommandResult:
    ok: bool
    action: str
    target: dict[str, Any] | None = None
    media: dict[str, Any] | None = None
    scope: str | None = None
    data: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    error: ErrorDetail | None = None

    # Non-zero exit code to use when ok=False.
    exit_code: int = 1

    @classmethod
    def success(
        cls,
        action: str,
        *,
        target: dict[str, Any] | None = None,
        media: dict[str, Any] | None = None,
        scope: str | None = None,
        data: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> CommandResult:
        return cls(
            ok=True,
            action=action,
            target=target,
            media=media,
            scope=scope,
            data=data,
            warnings=warnings or [],
        )

    @classmethod
    def failure(
        cls,
        action: str,
        *,
        code: str,
        message: str,
        exit_code: int = 1,
        candidates: list[dict[str, Any]] | None = None,
        remediation: str | None = None,
        requires_confirmation: bool = False,
        suggested_arguments: dict[str, Any] | None = None,
    ) -> CommandResult:
        return cls(
            ok=False,
            action=action,
            exit_code=exit_code,
            error=ErrorDetail(
                code=code,
                message=message,
                candidates=candidates or [],
                remediation=remediation,
                requires_confirmation=requires_confirmation,
                suggested_arguments=suggested_arguments or {},
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"ok": self.ok, "action": self.action}
        if self.target:
            d["target"] = self.target
        if self.media:
            d["media"] = self.media
        if self.scope:
            d["scope"] = self.scope
        if self.data:
            d.update(self.data)
        if self.warnings:
            d["warnings"] = self.warnings
        if self.error:
            d["error"] = self.error.to_dict()
        return d
