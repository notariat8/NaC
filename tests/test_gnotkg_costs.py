from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from nac_gnotkg.costs import calculate_value_fee, quote_fee
from nac_gnotkg.views import build_cost_review_view


REPO_ROOT = Path(__file__).resolve().parents[1]


class GNotKGCostTests(unittest.TestCase):
    def test_calculates_known_table_a_values_from_annex_2(self) -> None:
        examples = {
            "500": "40.00",
            "1000": "61.00",
            "3000": "125.50",
            "50000": "638.00",
            "200000": "2038.00",
            "500000": "4138.00",
            "3000000": "14638.00",
            "10000000": "44038.00",
        }

        for business_value, expected_fee in examples.items():
            with self.subTest(business_value=business_value):
                fee = calculate_value_fee(Decimal(business_value), table="A")
                self.assertEqual(fee, Decimal(expected_fee))

    def test_calculates_known_table_b_values_from_annex_2(self) -> None:
        examples = {
            "500": "15.00",
            "1000": "19.00",
            "3000": "33.00",
            "50000": "165.00",
            "200000": "435.00",
            "500000": "935.00",
            "3000000": "4935.00",
            "10000000": "11385.00",
        }

        for business_value, expected_fee in examples.items():
            with self.subTest(business_value=business_value):
                fee = calculate_value_fee(Decimal(business_value), table="B")
                self.assertEqual(fee, Decimal(expected_fee))

    def test_quote_applies_fee_rate_and_minimum_fee(self) -> None:
        quote = quote_fee(
            business_value=Decimal("1000"),
            table="A",
            fee_rate=Decimal("2.0"),
            kv_number="21100",
            usecase_slug="immobilienkaufvertrag",
        )

        self.assertEqual(quote.base_fee, Decimal("61.00"))
        self.assertEqual(quote.fee_amount, Decimal("122.00"))
        self.assertEqual(quote.minimum_fee_applied, False)
        self.assertEqual(quote.kv_number, "21100")
        self.assertEqual(quote.usecase_slug, "immobilienkaufvertrag")
        self.assertIn("GNotKG § 34", quote.source_refs)
        self.assertIn("GNotKG § 35", quote.source_refs)

        minimum_quote = quote_fee(
            business_value=Decimal("500"),
            table="B",
            fee_rate=Decimal("0.1"),
            kv_number="25100",
        )
        self.assertEqual(minimum_quote.fee_amount, Decimal("15.00"))
        self.assertEqual(minimum_quote.minimum_fee_applied, True)

    def test_business_value_caps_are_applied_from_section_35(self) -> None:
        capped_a = quote_fee(Decimal("30000001"), table="A", fee_rate=Decimal("1.0"))
        capped_b = quote_fee(Decimal("60000001"), table="B", fee_rate=Decimal("1.0"))

        self.assertEqual(calculate_value_fee(Decimal("30000001"), table="A"), Decimal("128038.00"))
        self.assertEqual(calculate_value_fee(Decimal("60000001"), table="B"), Decimal("26585.00"))
        self.assertEqual(capped_a.effective_business_value, Decimal("30000000.00"))
        self.assertEqual(capped_b.effective_business_value, Decimal("60000000.00"))
        self.assertEqual(capped_a.cap_applied, True)
        self.assertEqual(capped_b.cap_applied, True)

    def test_quote_json_is_deterministic_and_string_decimal_based(self) -> None:
        quote = quote_fee(
            business_value=Decimal("500000"),
            table="A",
            fee_rate=Decimal("1.0"),
            kv_number="21100",
        )
        payload = json.loads(quote.to_json())

        self.assertEqual(payload["schema_version"], "nac.gnotkg-cost-quote/v0.1")
        self.assertEqual(payload["business_value"], "500000.00")
        self.assertEqual(payload["effective_business_value"], "500000.00")
        self.assertEqual(payload["base_fee"], "4138.00")
        self.assertEqual(payload["fee_amount"], "4138.00")
        self.assertNotIn("float", quote.to_json().lower())

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            calculate_value_fee(Decimal("0"), table="A")
        with self.assertRaises(ValueError):
            calculate_value_fee(Decimal("500"), table="C")
        with self.assertRaises(ValueError):
            quote_fee(Decimal("500"), table="A", fee_rate=Decimal("0"))

    def test_cost_review_view_contains_no_mandate_values(self) -> None:
        view = build_cost_review_view(REPO_ROOT, "immobilienkaufvertrag")

        self.assertEqual(view["schema_version"], "nac.gnotkg-cost-review/v0.1")
        self.assertEqual(view["usecase_slug"], "immobilienkaufvertrag")
        self.assertEqual(view["rendering"]["preferred_renderer"], "xyflow")
        self.assertIn("gate.gnotkg_cost_review", {node["id"] for node in view["nodes"]})
        self.assertIn("cost.business_value", {node["id"] for node in view["nodes"]})
        self.assertTrue(all(node["editable"] is False for node in view["nodes"]))
        self.assertFalse(_contains_key(view, "value"))
        self.assertTrue(view["guardrails"]["real_mandate_data_in_git"] is False)


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
