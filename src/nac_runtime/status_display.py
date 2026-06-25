from __future__ import annotations

from typing import Any

from nac_runtime.status_presenter import present_first_matter_status
from nac_runtime.status_read_model import ProcessEventReader, build_first_matter_status


def build_first_matter_status_display(*, store: ProcessEventReader, process_instance_id: str) -> dict[str, Any]:
    """Build the safe browser display model from runtime process events."""
    status = build_first_matter_status(store=store, process_instance_id=process_instance_id)
    return present_first_matter_status(status)
