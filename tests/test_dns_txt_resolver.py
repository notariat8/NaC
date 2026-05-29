from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class DnsTxtResolverTests(unittest.TestCase):
    def test_parse_txt_response_extracts_txt_values(self) -> None:
        from nac_identity.dns_txt import parse_dns_txt_response

        response = (
            b"\x12\x34\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"
            b"\x04_nac\x10kanzlei-notariat\x07example\x00\x00\x10\x00\x01"
            b"\xc0\x0c\x00\x10\x00\x01\x00\x00\x00\x3c\x00\x1f"
            b"\x1enac-domain-verification=abc123"
        )

        values = parse_dns_txt_response(response, expected_query_id=0x1234)

        self.assertEqual(values, ["nac-domain-verification=abc123"])

    def test_parse_txt_response_ignores_txt_for_other_answer_owner(self) -> None:
        from nac_identity.dns_txt import parse_dns_txt_response

        response = (
            b"\x12\x34\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"
            b"\x04_nac\x10kanzlei-notariat\x07example\x00\x00\x10\x00\x01"
            b"\x04_nac\x05other\x07example\x00\x00\x10\x00\x01\x00\x00\x00\x3c\x00\x1f"
            b"\x1enac-domain-verification=abc123"
        )

        values = parse_dns_txt_response(response, expected_query_id=0x1234)

        self.assertEqual(values, [])

    def test_parse_txt_response_rejects_truncated_rdata(self) -> None:
        from nac_identity.dns_txt import parse_dns_txt_response

        response = (
            b"\x12\x34\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00"
            b"\x04_nac\x10kanzlei-notariat\x07example\x00\x00\x10\x00\x01"
            b"\xc0\x0c\x00\x10\x00\x01\x00\x00\x00\x3c\x00\xff"
            b"\x1enac-domain-verification=abc123"
        )

        with self.assertRaisesRegex(ValueError, "dns_rdata_truncated"):
            parse_dns_txt_response(response, expected_query_id=0x1234)


if __name__ == "__main__":
    unittest.main()
