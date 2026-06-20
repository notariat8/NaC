from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-xnp-demo-contract.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-xnp-demo-contract.md",
}


class NotarkammerXnpDemoContractTests(unittest.TestCase):
    def test_contract_exists_in_german_and_english(self) -> None:
        for path in CONTRACT_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_contract_maps_public_xnp_facts_to_bpmn_boundaries(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in CONTRACT_DOCS.values())

        required_terms = [
            "XNP",
            "XNotar",
            "XJustiz",
            "UVZ",
            "VVZ",
            "Grundbuch",
            "Handelsregister",
            "Kartenleser",
            "BPMN",
            "localhost",
            "Local Evidence Companion",
            "XNP does not deliver land-register data to NaC",
            "XNP liefert keine Grundbuchdaten an NaC",
            "Datenaustauschverzeichnis",
            "no automated external XNotar import trigger",
            "kein automatisierter externer XNotar-Import-Trigger",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_contract_keeps_forbidden_demo_claims_out(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in CONTRACT_DOCS.values())

        forbidden_claims = [
            "XNP liefert Grundbuchdaten",
            "XNP returns land-register data",
            "Cloud ruft XNP direkt auf",
            "NaC stores XNP API keys",
            "NaC speichert XNP-API-Keys",
            "PIN speichern",
            "store card PIN",
            "localhost tunnel",
            "Mandatsdaten anzeigen",
            "Oracle Cloud Infrastructure",
        ]
        for claim in forbidden_claims:
            self.assertNotIn(claim, combined)

    def test_contract_cites_public_sources(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in CONTRACT_DOCS.values())

        sources = [
            "https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk/integration-xnp-mit-notariatssoftware.html",
            "https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnotar/integration-xnp-xnotar-mit-weiterer-notariatssoftware.html",
            "https://xjustiz.justiz.de/",
        ]
        for source in sources:
            self.assertIn(source, combined)


if __name__ == "__main__":
    unittest.main()
