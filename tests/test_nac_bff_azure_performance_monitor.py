from __future__ import annotations

import copy
from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import json
import math
import unittest

from nac_bff.azure_performance_monitor import (
    ATTRIBUTION_SCOPE,
    AzurePerformanceMonitorAdapter,
    AzurePerformanceMonitorError,
)


START = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
END = datetime(2026, 8, 3, 12, 2, tzinfo=UTC)
NOW = datetime(2026, 8, 3, 12, 10, tzinfo=UTC)
METRICS = (
    "OnDemandFunctionExecutionUnits",
    "OnDemandFunctionExecutionCount",
    "AlwaysReadyFunctionExecutionUnits",
    "AlwaysReadyUnits",
    "AlwaysReadyFunctionExecutionCount",
)
RESOURCE_ID = (
    "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
    "resourceGroups/rg-nac-bff-test/providers/Microsoft.Web/sites/"
    "func-nac-bff-test-funktion8"
)
EXPECTED_URL = (
    "https://management.azure.com"
    f"{RESOURCE_ID}/providers/Microsoft.Insights/metrics"
    "?api-version=2023-10-01"
    "&metricnamespace=Microsoft.Web%2Fsites"
    "&metricnames=OnDemandFunctionExecutionUnits,"
    "OnDemandFunctionExecutionCount,AlwaysReadyFunctionExecutionUnits,"
    "AlwaysReadyUnits,AlwaysReadyFunctionExecutionCount"
    "&aggregation=Total"
    "&interval=PT1M"
    "&timespan=2026-08-03T12%3A00%3A00Z%2F2026-08-03T12%3A02%3A00Z"
    "&AutoAdjustTimegrain=false"
    "&ValidateDimensions=true"
    "&%24filter=Instance%20eq%20%27%2A%27"
)


class _AzureRestPort:
    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv: object) -> dict[str, object]:
        self.commands.append(tuple(argv))
        return {
            "ok": True,
            "status": "PASSED",
            "code": "AZURE_CLI_COMMAND_PASSED",
            "command": "rest",
            "data": copy.deepcopy(self.payload),
        }


def _series(instance: str, totals: list[tuple[str, object]]) -> dict[str, object]:
    return {
        "metadatavalues": [
            {
                "name": {"value": "Instance", "localizedValue": "Instance"},
                "value": instance,
            }
        ],
        "data": [
            {"timeStamp": timestamp, "total": total}
            for timestamp, total in totals
        ],
    }


def _metric(name: str, series: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": f"{RESOURCE_ID}/providers/Microsoft.Insights/metrics/{name}",
        "type": "Microsoft.Insights/metrics",
        "name": {"value": name, "localizedValue": name},
        "displayDescription": f"Synthetic fixture for {name}",
        "unit": "Count",
        "timeseries": series,
        "errorCode": "Success",
    }


def _response() -> dict[str, object]:
    zero = _series("instance-a", [("2026-08-03T12:00:00Z", 0)])
    return {
        "cost": 5,
        "timespan": "2026-08-03T12:00:00Z/2026-08-03T12:02:00Z",
        "interval": "PT1M",
        "value": [
            _metric(
                METRICS[0],
                [
                    _series("instance-a", [("2026-08-03T12:00:00Z", 1_024_000)]),
                    _series(
                        "instance-b",
                        [
                            ("2026-08-03T12:00:00Z", 512_000),
                            ("2026-08-03T12:01:00Z", 512_000),
                        ],
                    ),
                ],
            ),
            _metric(
                METRICS[1],
                [
                    _series("instance-a", [("2026-08-03T12:00:00Z", 2)]),
                    _series("instance-b", [("2026-08-03T12:01:00Z", 3)]),
                ],
            ),
            _metric(METRICS[2], [copy.deepcopy(zero)]),
            _metric(METRICS[3], [copy.deepcopy(zero)]),
            _metric(METRICS[4], [copy.deepcopy(zero)]),
        ],
        "namespace": "Microsoft.Web/sites",
        "resourceregion": "germanywestcentral",
    }


class AzurePerformanceMonitorTests(unittest.TestCase):
    def _observe(self, payload: object | None = None):
        port = _AzureRestPort(_response() if payload is None else payload)
        adapter = AzurePerformanceMonitorAdapter(port, clock=lambda: NOW)
        return port, adapter.observe(START, END)

    def assert_error(self, code: str, payload: object) -> None:
        adapter = AzurePerformanceMonitorAdapter(
            _AzureRestPort(payload), clock=lambda: NOW
        )
        with self.assertRaisesRegex(AzurePerformanceMonitorError, f"^{code}$"):
            adapter.observe(START, END)

    def test_exact_read_request_and_multi_instance_aggregation(self) -> None:
        port, observation = self._observe()

        self.assertEqual(
            port.commands,
            [("rest", "--method", "get", "--url", EXPECTED_URL)],
        )
        self.assertEqual(observation.on_demand_execution_units, Decimal("2048000"))
        self.assertEqual(observation.observed_execution_units_gb_seconds, Decimal("2"))
        self.assertEqual(observation.on_demand_execution_count, Decimal("5"))
        self.assertEqual(observation.always_ready_execution_units, Decimal("0"))
        self.assertEqual(observation.always_ready_units, Decimal("0"))
        self.assertEqual(observation.always_ready_execution_count, Decimal("0"))
        self.assertEqual(observation.series_counts[METRICS[0]], 2)
        self.assertEqual(observation.data_point_counts[METRICS[0]], 3)

    def test_unknown_response_shape_is_rejected_at_each_level(self) -> None:
        mutations = []
        top = _response()
        top["unexpected"] = True
        mutations.append(top)
        metric = _response()
        metric["value"][0]["unexpected"] = True
        mutations.append(metric)
        series = _response()
        series["value"][0]["timeseries"][0]["unexpected"] = True
        mutations.append(series)
        point = _response()
        point["value"][0]["timeseries"][0]["data"][0]["average"] = 1
        mutations.append(point)

        for payload in mutations:
            with self.subTest(payload=json.dumps(payload, sort_keys=True)[:80]):
                self.assert_error("PERFORMANCE_MONITOR_RESPONSE_INVALID", payload)

    def test_duplicate_or_missing_metric_is_rejected(self) -> None:
        duplicate = _response()
        duplicate["value"][-1] = copy.deepcopy(duplicate["value"][0])
        self.assert_error("PERFORMANCE_MONITOR_METRIC_SET_INVALID", duplicate)

        missing = _response()
        missing["value"].pop()
        self.assert_error("PERFORMANCE_MONITOR_METRIC_SET_INVALID", missing)

    def test_returned_timespan_drift_and_missing_total_are_rejected(self) -> None:
        drift = _response()
        drift["timespan"] = "2026-08-03T12:00:00Z/2026-08-03T12:03:00Z"
        self.assert_error("PERFORMANCE_MONITOR_TIMESPAN_MISMATCH", drift)

        missing_total = _response()
        del missing_total["value"][0]["timeseries"][0]["data"][0]["total"]
        self.assert_error("PERFORMANCE_MONITOR_RESPONSE_INVALID", missing_total)

    def test_negative_and_nonfinite_totals_are_rejected(self) -> None:
        for value in (-1, math.nan, math.inf, -math.inf):
            payload = _response()
            payload["value"][0]["timeseries"][0]["data"][0]["total"] = value
            with self.subTest(value=value):
                self.assert_error("PERFORMANCE_MONITOR_VALUE_INVALID", payload)

    def test_zero_series_and_zero_data_series_are_ambiguous(self) -> None:
        zero_series = _response()
        zero_series["value"][0]["timeseries"] = []
        self.assert_error("PERFORMANCE_MONITOR_SERIES_AMBIGUOUS", zero_series)

        zero_data = _response()
        zero_data["value"][0]["timeseries"][0]["data"] = []
        self.assert_error("PERFORMANCE_MONITOR_SERIES_AMBIGUOUS", zero_data)

    def test_only_instance_dimensions_and_unique_series_timestamps_are_allowed(self) -> None:
        wrong_dimension = _response()
        metadata = wrong_dimension["value"][0]["timeseries"][0]["metadatavalues"][0]
        metadata["name"]["value"] = "FunctionName"
        self.assert_error("PERFORMANCE_MONITOR_DIMENSION_INVALID", wrong_dimension)

        duplicate_timestamp = _response()
        data = duplicate_timestamp["value"][0]["timeseries"][0]["data"]
        data.append(copy.deepcopy(data[0]))
        self.assert_error("PERFORMANCE_MONITOR_TIMESTAMP_INVALID", duplicate_timestamp)

    def test_nonzero_always_ready_activity_is_blocked(self) -> None:
        for metric_index in (2, 3, 4):
            payload = _response()
            payload["value"][metric_index]["timeseries"][0]["data"][0]["total"] = 1
            with self.subTest(metric=METRICS[metric_index]):
                self.assert_error("PERFORMANCE_MONITOR_ALWAYS_READY_NONZERO", payload)

    def test_window_must_be_utc_minute_aligned_bounded_and_settled(self) -> None:
        adapter = AzurePerformanceMonitorAdapter(
            _AzureRestPort(_response()), clock=lambda: NOW
        )
        invalid_windows = (
            (START.replace(tzinfo=None), END),
            (START.replace(second=1), END),
            (END, START),
            (START, START),
            (START, START.replace(day=4, hour=12, minute=1)),
        )
        for start, end in invalid_windows:
            with self.subTest(start=start, end=end):
                with self.assertRaisesRegex(
                    AzurePerformanceMonitorError,
                    "^PERFORMANCE_MONITOR_WINDOW_INVALID$",
                ):
                    adapter.observe(start, end)

        unsettled = AzurePerformanceMonitorAdapter(
            _AzureRestPort(_response()),
            clock=lambda: datetime(2026, 8, 3, 12, 6, 59, tzinfo=UTC),
        )
        with self.assertRaisesRegex(
            AzurePerformanceMonitorError,
            "^PERFORMANCE_MONITOR_WINDOW_NOT_SETTLED$",
        ):
            unsettled.observe(START, END)

    def test_observation_is_aggregate_only_redacted_and_hash_deterministic(self) -> None:
        _, first = self._observe()
        _, second = self._observe()
        redacted = first.as_redacted_dict()
        serialized = json.dumps(redacted, sort_keys=True)

        changed_payload = _response()
        changed_payload["value"][1]["timeseries"][0]["data"][0]["total"] = 3
        _, changed = self._observe(changed_payload)

        self.assertEqual(first, second)
        self.assertEqual(redacted["attribution_scope"], ATTRIBUTION_SCOPE)
        self.assertEqual(redacted["requested_timespan"], redacted["returned_timespan"])
        self.assertEqual(redacted["auto_adjust_timegrain"], False)
        self.assertEqual(redacted["validate_dimensions"], True)
        self.assertEqual(redacted["ingestion_lag_seconds"], 300)
        self.assertRegex(redacted["monitor_binding_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(redacted["monitor_evidence_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(
            redacted["monitor_binding_sha256"],
            redacted["monitor_evidence_sha256"],
        )
        self.assertEqual(
            first.monitor_binding_sha256,
            changed.monitor_binding_sha256,
        )
        self.assertNotEqual(
            first.monitor_evidence_sha256,
            changed.monitor_evidence_sha256,
        )
        evidence_digest = redacted.pop("monitor_evidence_sha256")
        canonical_evidence = json.dumps(
            redacted,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        self.assertEqual(hashlib.sha256(canonical_evidence).hexdigest(), evidence_digest)
        for forbidden in (
            RESOURCE_ID,
            "management.azure.com",
            "instance-a",
            "instance-b",
            "Synthetic fixture",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
