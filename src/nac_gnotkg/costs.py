from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Any


CENT = Decimal("0.01")
BASE_LIMIT = Decimal("500")
MINIMUM_FEE = Decimal("15.00")
SOURCE_REFS = (
    "GNotKG § 3",
    "GNotKG § 34",
    "GNotKG § 35",
    "GNotKG Anlage 1",
    "GNotKG Anlage 2",
)
TABLE_CAPS = {
    "A": Decimal("30000000"),
    "B": Decimal("60000000"),
}


@dataclass(frozen=True, slots=True)
class FeeTier:
    upper: Decimal | None
    step: Decimal
    increment: Decimal


TABLE_A_TIERS: tuple[FeeTier, ...] = (
    FeeTier(Decimal("2000"), Decimal("500"), Decimal("21.00")),
    FeeTier(Decimal("10000"), Decimal("1000"), Decimal("22.50")),
    FeeTier(Decimal("25000"), Decimal("3000"), Decimal("30.50")),
    FeeTier(Decimal("50000"), Decimal("5000"), Decimal("40.50")),
    FeeTier(Decimal("200000"), Decimal("15000"), Decimal("140.00")),
    FeeTier(Decimal("500000"), Decimal("30000"), Decimal("210.00")),
    FeeTier(None, Decimal("50000"), Decimal("210.00")),
)
TABLE_B_TIERS: tuple[FeeTier, ...] = (
    FeeTier(Decimal("2000"), Decimal("500"), Decimal("4.00")),
    FeeTier(Decimal("10000"), Decimal("1000"), Decimal("6.00")),
    FeeTier(Decimal("25000"), Decimal("3000"), Decimal("8.00")),
    FeeTier(Decimal("50000"), Decimal("5000"), Decimal("10.00")),
    FeeTier(Decimal("200000"), Decimal("15000"), Decimal("27.00")),
    FeeTier(Decimal("500000"), Decimal("30000"), Decimal("50.00")),
    FeeTier(Decimal("5000000"), Decimal("50000"), Decimal("80.00")),
    FeeTier(Decimal("10000000"), Decimal("200000"), Decimal("130.00")),
    FeeTier(Decimal("20000000"), Decimal("250000"), Decimal("150.00")),
    FeeTier(Decimal("30000000"), Decimal("500000"), Decimal("280.00")),
    FeeTier(None, Decimal("1000000"), Decimal("120.00")),
)


@dataclass(frozen=True, slots=True)
class FeeQuote:
    business_value: Decimal
    effective_business_value: Decimal
    table: str
    fee_rate: Decimal
    base_fee: Decimal
    fee_amount: Decimal
    minimum_fee_applied: bool
    cap_applied: bool
    kv_number: str = ""
    usecase_slug: str = ""
    source_refs: tuple[str, ...] = SOURCE_REFS
    schema_version: str = "nac.gnotkg-cost-quote/v0.1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "usecase_slug": self.usecase_slug,
            "kv_number": self.kv_number,
            "business_value": _format_decimal(self.business_value),
            "effective_business_value": _format_decimal(self.effective_business_value),
            "table": self.table,
            "fee_rate": _format_rate(self.fee_rate),
            "base_fee": _format_decimal(self.base_fee),
            "fee_amount": _format_decimal(self.fee_amount),
            "minimum_fee_applied": self.minimum_fee_applied,
            "cap_applied": self.cap_applied,
            "source_refs": list(self.source_refs),
            "review_boundary": "Technischer Kostenentwurf; finale notarielle Kostenprüfung bleibt erforderlich.",
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)


def calculate_value_fee(business_value: Decimal | int | str, table: str) -> Decimal:
    """Calculate one GNotKG value fee for table A or B."""

    normalized_table = _normalize_table(table)
    value = _apply_table_cap(_positive_decimal(business_value, "business_value"), normalized_table)
    fee = Decimal("40.00") if normalized_table == "A" else Decimal("15.00")
    tiers = TABLE_A_TIERS if normalized_table == "A" else TABLE_B_TIERS
    current_upper = BASE_LIMIT

    if value <= BASE_LIMIT:
        return _money(fee)

    for tier in tiers:
        tier_upper = value if tier.upper is None else min(value, tier.upper)
        if tier_upper > current_upper:
            started_steps = ((tier_upper - current_upper) / tier.step).to_integral_value(
                rounding=ROUND_CEILING
            )
            fee += started_steps * tier.increment
        if tier.upper is None or value <= tier.upper:
            break
        current_upper = tier.upper

    return _money(fee)


def quote_fee(
    business_value: Decimal | int | str,
    table: str,
    fee_rate: Decimal | int | str,
    kv_number: str = "",
    usecase_slug: str = "",
) -> FeeQuote:
    rate = _positive_decimal(fee_rate, "fee_rate")
    value = _positive_decimal(business_value, "business_value")
    normalized_table = _normalize_table(table)
    effective_value = _apply_table_cap(value, normalized_table)
    base_fee = calculate_value_fee(effective_value, normalized_table)
    calculated_fee = _money(base_fee * rate)
    minimum_fee_applied = calculated_fee < MINIMUM_FEE
    fee_amount = MINIMUM_FEE if minimum_fee_applied else calculated_fee

    return FeeQuote(
        business_value=_money(value),
        effective_business_value=_money(effective_value),
        table=normalized_table,
        fee_rate=rate,
        base_fee=base_fee,
        fee_amount=_money(fee_amount),
        minimum_fee_applied=minimum_fee_applied,
        cap_applied=effective_value != value,
        kv_number=str(kv_number),
        usecase_slug=str(usecase_slug),
    )


def _normalize_table(table: str) -> str:
    normalized = str(table).strip().upper()
    if normalized not in {"A", "B"}:
        raise ValueError("table muss A oder B sein")
    return normalized


def _positive_decimal(value: Decimal | int | str, field_name: str) -> Decimal:
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
    if decimal_value <= 0:
        raise ValueError(f"{field_name} muss größer als 0 sein")
    return decimal_value


def _apply_table_cap(value: Decimal, table: str) -> Decimal:
    cap = TABLE_CAPS[table]
    return cap if value > cap else value


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _format_decimal(value: Decimal) -> str:
    return f"{_money(value):.2f}"


def _format_rate(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")
