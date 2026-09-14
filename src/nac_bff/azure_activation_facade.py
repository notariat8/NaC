from __future__ import annotations

from typing import Any

from .azure_activation_contract import (
    PLATFORM_BOUNDARY_SCHEMA_VERSION,
    PLATFORM_SECURITY_BACKEND_UNAVAILABLE,
    require_platform_security_backend,
)


def platform_blocked_payload() -> dict[str, Any]:
    return {
        "schema_version": PLATFORM_BOUNDARY_SCHEMA_VERSION,
        "status": "BLOCKED",
        "error": {"code": PLATFORM_SECURITY_BACKEND_UNAVAILABLE},
        "writes_started": False,
    }


def run_azure_bff_live_activation(*args: Any, **kwargs: Any) -> dict[str, Any]:
    require_platform_security_backend()
    from .azure_activation_runner import run_azure_bff_live_activation as backend

    return backend(*args, **kwargs)


def reconcile_azure_bff_live_activation_lock(
    *args: Any, **kwargs: Any
) -> dict[str, Any]:
    require_platform_security_backend()
    from .azure_activation_runner import (
        reconcile_azure_bff_live_activation_lock as backend,
    )

    return backend(*args, **kwargs)


def build_live_activation_execution_port(*args: Any, **kwargs: Any) -> Any:
    require_platform_security_backend()
    from .azure_activation_composition import (
        build_live_activation_execution_port as backend,
    )

    return backend(*args, **kwargs)


def build_interruption_reconciliation_ports(*args: Any, **kwargs: Any) -> Any:
    require_platform_security_backend()
    from .azure_activation_composition import (
        build_interruption_reconciliation_ports as backend,
    )

    return backend(*args, **kwargs)


def build_function_deployment_reconciliation_ports(
    *args: Any, **kwargs: Any
) -> Any:
    require_platform_security_backend()
    from .azure_activation_composition import (
        build_function_deployment_reconciliation_ports as backend,
    )

    return backend(*args, **kwargs)


__all__ = [
    "build_function_deployment_reconciliation_ports",
    "build_interruption_reconciliation_ports",
    "build_live_activation_execution_port",
    "platform_blocked_payload",
    "reconcile_azure_bff_live_activation_lock",
    "run_azure_bff_live_activation",
]
