from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProcessDefinition:
    process_type: str
    schema_name: str
    allowed_statuses: tuple[str, ...]
    allowed_transitions: dict[str, tuple[str, ...]]
    review_statuses: tuple[str, ...] = ()


PROCESS_DEFINITIONS: dict[str, ProcessDefinition] = {
    "formation": ProcessDefinition(
        process_type="formation",
        schema_name="formation.schema.json",
        allowed_statuses=("draft", "validated", "needs_review", "approved", "executed", "archived"),
        allowed_transitions={
            "draft": ("validated",),
            "validated": ("needs_review", "approved"),
            "needs_review": ("approved", "draft"),
            "approved": ("executed",),
            "executed": ("archived",),
            "archived": (),
        },
        review_statuses=("needs_review",),
    ),
    "invoice": ProcessDefinition(
        process_type="invoice",
        schema_name="invoice.schema.json",
        allowed_statuses=("draft", "approved", "issued", "paid", "cancelled"),
        allowed_transitions={
            "draft": ("approved", "cancelled"),
            "approved": ("issued", "cancelled"),
            "issued": ("paid", "cancelled"),
            "paid": (),
            "cancelled": (),
        },
        review_statuses=("approved",),
    ),
    "bookkeeping": ProcessDefinition(
        process_type="bookkeeping",
        schema_name="bookkeeping.schema.json",
        allowed_statuses=("draft", "validated", "posted", "closed"),
        allowed_transitions={
            "draft": ("validated",),
            "validated": ("posted",),
            "posted": ("closed",),
            "closed": (),
        },
    ),
    "tax": ProcessDefinition(
        process_type="tax",
        schema_name="tax.schema.json",
        allowed_statuses=("draft", "prepared", "approved", "submitted", "archived"),
        allowed_transitions={
            "draft": ("prepared",),
            "prepared": ("approved", "draft"),
            "approved": ("submitted",),
            "submitted": ("archived",),
            "archived": (),
        },
        review_statuses=("approved", "submitted"),
    ),
}


def schema_path(repo_root: Path, process_type: str) -> Path:
    definition = PROCESS_DEFINITIONS[process_type]
    return repo_root / "schemas" / definition.schema_name
