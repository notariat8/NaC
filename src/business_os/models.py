from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ProcessDocument:
    path: Path
    content: dict[str, Any]

    @property
    def process_type(self) -> str:
        return str(self.content["process_type"])

    @property
    def request_id(self) -> str:
        return str(self.content["request_id"])

    @property
    def status(self) -> str:
        return str(self.content["status"])

    @property
    def year(self) -> int:
        return int(self.content["year"])

    @property
    def idempotency_key(self) -> str:
        return str(self.content["idempotency_key"])


@dataclass(slots=True)
class ValidationResult:
    document: ProcessDocument
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors
