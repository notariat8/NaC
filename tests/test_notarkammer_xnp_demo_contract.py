from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-xnp-demo-contract.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-xnp-demo-contract.md",
}


def normalized_contract_text() -> str:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in CONTRACT_DOCS.values())
    return " ".join(combined.split())


class NotarkammerXnpDemoContractTests(unittest.TestCase):
    def test_contract_exists_in_german_and_english(self) -> None:
        for path in CONTRACT_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_contract_maps_public_xnp_facts_to_bpmn_boundaries(self) -> None:
        combined = normalized_contract_text()

        required_terms = [
            "100% notariat",
            "XNP",
            "Basisanwendung der Bundesnotarkammer",
            "BNotK base application",
            "external notarial environment",
            "externe notarielle Arbeitsumgebung",
            "XNotar",
            "UVZ",
            "VVZ",
            "beN",
            "Grundbuch",
            "Handelsregister",
            "notarielle Onlineverfahren",
            "notarial online procedures",
            "Dokumente",
            "PDF viewer",
            "Signaturmappe",
            "signature folder",
            "Benutzerverwaltung",
            "Kartenverwaltung",
            "Kartenleser",
            "BPMN",
            "Local Evidence Companion",
            "NaC does not claim direct XNP-to-NaC land-register data delivery",
            "NaC behauptet im Demo-Modell keine direkte XNP-zu-NaC-Grundbuchdatenlieferung",
            "zu klären im XNP-Testzugang",
            "to be clarified in XNP test access",
            "fail-closed",
            "durationBand",
            "parallelGroup",
            "criticalPath",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_contract_keeps_customer_ui_provider_neutral(self) -> None:
        combined = normalized_contract_text()

        required_terms = [
            "Kunden-UI",
            "customer UI",
            "Externe notarielle Arbeitsumgebung erforderlich",
            "External notarial environment required",
            "keine Providerdetails",
            "no provider details",
            "local-notary-workstation",
            "card-reader",
            "register",
            "land-register",
            "REINER SCT",
            "class 3",
            "Sicherheitsklasse 3",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_contract_keeps_forbidden_demo_claims_out(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in CONTRACT_DOCS.values())

        forbidden_claims = [
            "XNP liefert Grundbuchdaten",
            "XNP returns land-register data",
            "XNP liefert keine Grundbuchdaten an NaC",
            "XNP does not deliver land-register data to NaC",
            "Cloud ruft XNP direkt auf",
            "NaC stores XNP API keys",
            "NaC speichert XNP-API-Keys",
            "PIN speichern",
            "store card PIN",
            "localhost tunnel",
            "Mandatsdaten anzeigen",
            "Oracle Cloud Infrastructure",
            "keine softwareseitige Schnittstelle",
            "does not describe a software interface",
            "kein automatisierter externer XNotar-Import-Trigger",
            "no automated external XNotar import trigger",
        ]
        for claim in forbidden_claims:
            self.assertNotIn(claim, combined)

    def test_contract_cites_public_sources(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in CONTRACT_DOCS.values())

        sources = [
            "https://notarnet.de/produkte/xnp",
            "https://notarnet.de/produkte/xnotar",
            "https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk.html",
            "https://onlinehilfe.bnotk.de/einrichtungen/notarnet/xnotar/einstiegshilfen/alle-schritte-eines-grundbuchantrags-auf-einen-blick.html",
            "https://onlinehilfe.bnotk.de/einrichtungen/notarnet/xnotar/einstiegshilfen/alle-schritte-einer-registeranmeldung-auf-einen-blick.html",
            "https://onlinehilfe.bnotk.de/einrichtungen/zertifizierungsstelle/hinweis-zu-kartenlesegeraeten.html",
        ]
        for source in sources:
            self.assertIn(source, combined)


if __name__ == "__main__":
    unittest.main()
