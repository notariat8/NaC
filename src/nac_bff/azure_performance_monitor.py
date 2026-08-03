from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol
import urllib.parse

from .azure_activation import FUNCTION_APP, LOCATION, RESOURCE_GROUP, SUBSCRIPTION_ID


SCHEMA_VERSION = "nac.m365-azure-bff-performance-monitor-observation/v1"
API_VERSION = "2023-10-01"
METRIC_NAMESPACE = "Microsoft.Web/sites"
METRIC_NAMES = (
    "OnDemandFunctionExecutionUnits",
    "OnDemandFunctionExecutionCount",
    "AlwaysReadyFunctionExecutionUnits",
    "AlwaysReadyUnits",
    "AlwaysReadyFunctionExecutionCount",
)
AGGREGATION = "Total"
INTERVAL = "PT1M"
AUTO_ADJUST_TIMEGRAIN = False
VALIDATE_DIMENSIONS = True
DIMENSION_NAME = "Instance"
INGESTION_LAG_SECONDS = 300
MIN_WINDOW_SECONDS = 60
MAX_WINDOW_SECONDS = 24 * 60 * 60
EXECUTION_UNITS_PER_GB_SECOND = Decimal("1024000")
ATTRIBUTION_SCOPE = (
    "app_wide_delta_is_conservative_and_not_attributable_solely_to_test_traffic"
)
INGESTION_LAG_POLICY = "window_end_at_least_300_seconds_before_observation"

_RESOURCE_ID = (
    f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
    f"/providers/Microsoft.Web/sites/{FUNCTION_APP}"
)
_METRICS_ENDPOINT = (
    f"https://management.azure.com{_RESOURCE_ID}"
    "/providers/Microsoft.Insights/metrics"
)
_TOP_LEVEL_KEYS = {
    "cost",
    "timespan",
    "interval",
    "value",
    "namespace",
    "resourceregion",
}
_METRIC_KEYS = {
    "id",
    "type",
    "name",
    "displayDescription",
    "unit",
    "timeseries",
    "errorCode",
}
_LOCALIZABLE_STRING_KEYS = {"value", "localizedValue"}
_SERIES_KEYS = {"metadatavalues", "data"}
_METADATA_KEYS = {"name", "value"}
_POINT_KEYS = {"timeStamp", "total"}
_COUNT_METRICS = {
    "OnDemandFunctionExecutionCount",
    "AlwaysReadyUnits",
    "AlwaysReadyFunctionExecutionCount",
}
_ALWAYS_READY_METRICS = {
    "AlwaysReadyFunctionExecutionUnits",
    "AlwaysReadyUnits",
    "AlwaysReadyFunctionExecutionCount",
}


class AzureRestCommandPort(Protocol):
    """Injected read command boundary; implementations own authentication."""

    def run(self, argv: object) -> Mapping[str, Any]: ...


class AzurePerformanceMonitorError(ValueError):
    """Stable, value-free failure suitable for redacted evidence."""


@dataclass(frozen=True, slots=True)
class _MetricAggregate:
    total: Decimal
    series_count: int
    data_point_count: int


@dataclass(frozen=True, slots=True)
class AzurePerformanceObservation:
    requested_timespan: str
    returned_timespan: str
    on_demand_execution_units: Decimal
    on_demand_execution_count: Decimal
    always_ready_execution_units: Decimal
    always_ready_units: Decimal
    always_ready_execution_count: Decimal
    observed_execution_units_gb_seconds: Decimal
    series_counts: Mapping[str, int]
    data_point_counts: Mapping[str, int]
    monitor_binding_sha256: str
    monitor_evidence_sha256: str

    def as_redacted_dict(self) -> dict[str, Any]:
        metrics = {
            name: {
                "total": _decimal_text(getattr(self, _METRIC_ATTRIBUTES[name])),
                "series_count": self.series_counts[name],
                "data_point_count": self.data_point_counts[name],
            }
            for name in METRIC_NAMES
        }
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "PASSED",
            "requested_timespan": self.requested_timespan,
            "returned_timespan": self.returned_timespan,
            "metric_namespace": METRIC_NAMESPACE,
            "metric_names": list(METRIC_NAMES),
            "aggregation": AGGREGATION,
            "interval": INTERVAL,
            "auto_adjust_timegrain": AUTO_ADJUST_TIMEGRAIN,
            "validate_dimensions": VALIDATE_DIMENSIONS,
            "dimension": DIMENSION_NAME,
            "ingestion_lag_seconds": INGESTION_LAG_SECONDS,
            "ingestion_lag_policy": INGESTION_LAG_POLICY,
            "attribution_scope": ATTRIBUTION_SCOPE,
            "execution_units_per_gb_second": _decimal_text(
                EXECUTION_UNITS_PER_GB_SECOND
            ),
            "observed_execution_units_gb_seconds": _decimal_text(
                self.observed_execution_units_gb_seconds
            ),
            "metrics": metrics,
            "monitor_binding_sha256": self.monitor_binding_sha256,
            "monitor_evidence_sha256": self.monitor_evidence_sha256,
        }


_METRIC_ATTRIBUTES = {
    "OnDemandFunctionExecutionUnits": "on_demand_execution_units",
    "OnDemandFunctionExecutionCount": "on_demand_execution_count",
    "AlwaysReadyFunctionExecutionUnits": "always_ready_execution_units",
    "AlwaysReadyUnits": "always_ready_units",
    "AlwaysReadyFunctionExecutionCount": "always_ready_execution_count",
}


class AzurePerformanceMonitorAdapter:
    """Read-only Azure Monitor adapter for the single bound Function App."""

    def __init__(
        self,
        command_port: AzureRestCommandPort,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._command_port = command_port
        self._clock = clock or (lambda: datetime.now(UTC))

    def observe(
        self,
        window_start_utc: datetime,
        window_end_utc: datetime,
    ) -> AzurePerformanceObservation:
        requested_timespan = _validate_window(window_start_utc, window_end_utc)
        now = self._clock()
        if not _is_utc_datetime(now):
            raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_CLOCK_INVALID")
        if window_end_utc > now - timedelta(seconds=INGESTION_LAG_SECONDS):
            raise AzurePerformanceMonitorError(
                "PERFORMANCE_MONITOR_WINDOW_NOT_SETTLED"
            )

        url = build_metrics_url(window_start_utc, window_end_utc)
        command = ("rest", "--method", "get", "--url", url)
        try:
            result = self._command_port.run(command)
        except Exception:
            raise AzurePerformanceMonitorError(
                "PERFORMANCE_MONITOR_READ_FAILED"
            ) from None
        if (
            not isinstance(result, Mapping)
            or result.get("ok") is not True
            or not isinstance(result.get("data"), Mapping)
        ):
            raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_READ_FAILED")

        returned_timespan, aggregates = _parse_response(
            result["data"],
            requested_timespan=requested_timespan,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
        )
        if any(aggregates[name].total != 0 for name in _ALWAYS_READY_METRICS):
            raise AzurePerformanceMonitorError(
                "PERFORMANCE_MONITOR_ALWAYS_READY_NONZERO"
            )

        observed_execution_units = (
            aggregates["OnDemandFunctionExecutionUnits"].total
            + aggregates["AlwaysReadyFunctionExecutionUnits"].total
        ) / EXECUTION_UNITS_PER_GB_SECOND
        binding = {
            "schema_version": SCHEMA_VERSION,
            "resource_id": _RESOURCE_ID,
            "request_command": list(command),
            "requested_timespan": requested_timespan,
            "returned_timespan": returned_timespan,
            "metric_namespace": METRIC_NAMESPACE,
            "metric_names": list(METRIC_NAMES),
            "aggregation": AGGREGATION,
            "interval": INTERVAL,
            "auto_adjust_timegrain": AUTO_ADJUST_TIMEGRAIN,
            "validate_dimensions": VALIDATE_DIMENSIONS,
            "dimension": DIMENSION_NAME,
            "ingestion_lag_seconds": INGESTION_LAG_SECONDS,
            "ingestion_lag_policy": INGESTION_LAG_POLICY,
            "attribution_scope": ATTRIBUTION_SCOPE,
        }
        binding_sha256 = _sha256_json(binding)
        evidence = _redacted_evidence_payload(
            requested_timespan=requested_timespan,
            returned_timespan=returned_timespan,
            aggregates=aggregates,
            observed_execution_units=observed_execution_units,
            binding_sha256=binding_sha256,
        )
        return AzurePerformanceObservation(
            requested_timespan=requested_timespan,
            returned_timespan=returned_timespan,
            on_demand_execution_units=(
                aggregates["OnDemandFunctionExecutionUnits"].total
            ),
            on_demand_execution_count=(
                aggregates["OnDemandFunctionExecutionCount"].total
            ),
            always_ready_execution_units=(
                aggregates["AlwaysReadyFunctionExecutionUnits"].total
            ),
            always_ready_units=aggregates["AlwaysReadyUnits"].total,
            always_ready_execution_count=(
                aggregates["AlwaysReadyFunctionExecutionCount"].total
            ),
            observed_execution_units_gb_seconds=observed_execution_units,
            series_counts=MappingProxyType(
                {name: aggregates[name].series_count for name in METRIC_NAMES}
            ),
            data_point_counts=MappingProxyType(
                {name: aggregates[name].data_point_count for name in METRIC_NAMES}
            ),
            monitor_binding_sha256=binding_sha256,
            monitor_evidence_sha256=_sha256_json(evidence),
        )

    def read(
        self,
        window_start_utc: datetime,
        window_end_utc: datetime,
    ) -> AzurePerformanceObservation:
        return self.observe(window_start_utc, window_end_utc)


def build_metrics_url(
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> str:
    timespan = _validate_window(window_start_utc, window_end_utc)
    query = (
        ("api-version", API_VERSION),
        ("metricnamespace", METRIC_NAMESPACE),
        ("metricnames", ",".join(METRIC_NAMES)),
        ("aggregation", AGGREGATION),
        ("interval", INTERVAL),
        ("timespan", timespan),
        ("AutoAdjustTimegrain", "false"),
        ("ValidateDimensions", "true"),
        ("$filter", "Instance eq '*'"),
    )
    encoded = "&".join(
        f"{urllib.parse.quote(key, safe='')}="
        f"{urllib.parse.quote(value, safe=',' if key == 'metricnames' else '')}"
        for key, value in query
    )
    return f"{_METRICS_ENDPOINT}?{encoded}"


def _validate_window(start: datetime, end: datetime) -> str:
    if not _is_utc_datetime(start) or not _is_utc_datetime(end):
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_WINDOW_INVALID")
    if any((start.second, start.microsecond, end.second, end.microsecond)):
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_WINDOW_INVALID")
    duration = (end - start).total_seconds()
    if not MIN_WINDOW_SECONDS <= duration <= MAX_WINDOW_SECONDS:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_WINDOW_INVALID")
    return f"{_timestamp_text(start)}/{_timestamp_text(end)}"


def _is_utc_datetime(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() == timedelta(0)
    )


def _timestamp_text(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_response(
    response: Mapping[str, Any],
    *,
    requested_timespan: str,
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> tuple[str, dict[str, _MetricAggregate]]:
    if set(response) != _TOP_LEVEL_KEYS:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_RESPONSE_INVALID")
    cost = response.get("cost")
    if type(cost) is not int or cost < 0:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_RESPONSE_INVALID")
    returned_timespan = response.get("timespan")
    if not isinstance(returned_timespan, str) or returned_timespan != requested_timespan:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_TIMESPAN_MISMATCH")
    if (
        response.get("interval") != INTERVAL
        or response.get("namespace") != METRIC_NAMESPACE
        or response.get("resourceregion") != LOCATION
    ):
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_RESPONSE_INVALID")
    metrics = response.get("value")
    if not isinstance(metrics, list):
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_RESPONSE_INVALID")
    metric_names = [
        item.get("name", {}).get("value")
        if isinstance(item, Mapping) and isinstance(item.get("name"), Mapping)
        else None
        for item in metrics
    ]
    if len(metrics) != len(METRIC_NAMES) or tuple(metric_names) != METRIC_NAMES:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_METRIC_SET_INVALID")

    aggregates: dict[str, _MetricAggregate] = {}
    for name, metric in zip(METRIC_NAMES, metrics, strict=True):
        aggregates[name] = _parse_metric(
            metric,
            expected_name=name,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
        )
    return returned_timespan, aggregates


def _parse_metric(
    metric: object,
    *,
    expected_name: str,
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> _MetricAggregate:
    if not isinstance(metric, Mapping) or set(metric) != _METRIC_KEYS:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_RESPONSE_INVALID")
    expected_id = (
        f"{_RESOURCE_ID}/providers/Microsoft.Insights/metrics/{expected_name}"
    )
    if (
        metric.get("id") != expected_id
        or metric.get("type") != "Microsoft.Insights/metrics"
        or metric.get("unit") != "Count"
        or metric.get("errorCode") != "Success"
        or not isinstance(metric.get("displayDescription"), str)
        or not metric["displayDescription"]
        or not _valid_localizable_string(metric.get("name"), expected_name)
    ):
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_METRIC_INVALID")
    series_items = metric.get("timeseries")
    if not isinstance(series_items, list) or not series_items:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_SERIES_AMBIGUOUS")

    instance_values: set[str] = set()
    total = Decimal(0)
    point_count = 0
    for series in series_items:
        instance, series_total, series_points = _parse_series(
            series,
            window_start_utc=window_start_utc,
            window_end_utc=window_end_utc,
        )
        if instance in instance_values:
            raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_DIMENSION_INVALID")
        instance_values.add(instance)
        total += series_total
        point_count += series_points
    if expected_name in _COUNT_METRICS and total != total.to_integral_value():
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_VALUE_INVALID")
    return _MetricAggregate(total, len(series_items), point_count)


def _parse_series(
    series: object,
    *,
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> tuple[str, Decimal, int]:
    if not isinstance(series, Mapping) or set(series) != _SERIES_KEYS:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_RESPONSE_INVALID")
    metadata = series.get("metadatavalues")
    if not isinstance(metadata, list) or len(metadata) != 1:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_DIMENSION_INVALID")
    dimension = metadata[0]
    if (
        not isinstance(dimension, Mapping)
        or set(dimension) != _METADATA_KEYS
        or not _valid_localizable_string(dimension.get("name"), DIMENSION_NAME)
        or not isinstance(dimension.get("value"), str)
        or not dimension["value"]
        or len(dimension["value"]) > 256
    ):
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_DIMENSION_INVALID")
    points = series.get("data")
    if not isinstance(points, list) or not points:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_SERIES_AMBIGUOUS")

    timestamps: set[str] = set()
    total = Decimal(0)
    for point in points:
        if not isinstance(point, Mapping) or set(point) != _POINT_KEYS:
            raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_RESPONSE_INVALID")
        timestamp = point.get("timeStamp")
        parsed_timestamp = _parse_timestamp(timestamp)
        if (
            parsed_timestamp is None
            or timestamp in timestamps
            or not window_start_utc <= parsed_timestamp < window_end_utc
        ):
            raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_TIMESTAMP_INVALID")
        timestamps.add(timestamp)
        total += _decimal_value(point.get("total"))
    return dimension["value"], total, len(points)


def _valid_localizable_string(value: object, expected: str) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == _LOCALIZABLE_STRING_KEYS
        and value.get("value") == expected
        and isinstance(value.get("localizedValue"), str)
        and bool(value["localizedValue"])
    )


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) != 20:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    if parsed.second != 0 or parsed.microsecond != 0:
        return None
    return parsed


def _decimal_value(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_VALUE_INVALID")
    try:
        converted = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise AzurePerformanceMonitorError(
            "PERFORMANCE_MONITOR_VALUE_INVALID"
        ) from None
    if not converted.is_finite() or converted < 0:
        raise AzurePerformanceMonitorError("PERFORMANCE_MONITOR_VALUE_INVALID")
    return converted


def _redacted_evidence_payload(
    *,
    requested_timespan: str,
    returned_timespan: str,
    aggregates: Mapping[str, _MetricAggregate],
    observed_execution_units: Decimal,
    binding_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASSED",
        "requested_timespan": requested_timespan,
        "returned_timespan": returned_timespan,
        "metric_namespace": METRIC_NAMESPACE,
        "metric_names": list(METRIC_NAMES),
        "aggregation": AGGREGATION,
        "interval": INTERVAL,
        "auto_adjust_timegrain": AUTO_ADJUST_TIMEGRAIN,
        "validate_dimensions": VALIDATE_DIMENSIONS,
        "dimension": DIMENSION_NAME,
        "ingestion_lag_seconds": INGESTION_LAG_SECONDS,
        "ingestion_lag_policy": INGESTION_LAG_POLICY,
        "attribution_scope": ATTRIBUTION_SCOPE,
        "execution_units_per_gb_second": _decimal_text(
            EXECUTION_UNITS_PER_GB_SECOND
        ),
        "observed_execution_units_gb_seconds": _decimal_text(
            observed_execution_units
        ),
        "metrics": {
            name: {
                "total": _decimal_text(aggregates[name].total),
                "series_count": aggregates[name].series_count,
                "data_point_count": aggregates[name].data_point_count,
            }
            for name in METRIC_NAMES
        },
        "monitor_binding_sha256": binding_sha256,
    }


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == 0:
        return "0"
    return format(normalized, "f")


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


AzurePerformanceMonitor = AzurePerformanceMonitorAdapter
MonitorObservation = AzurePerformanceObservation
