from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    file_path = REPO_ROOT / path
    if not file_path.exists():
        raise AssertionError(f"{path} is missing")
    return file_path.read_text(encoding="utf-8")


class Office365AgentRegistryArchitectureTests(unittest.TestCase):
    def test_client_target_architecture_requires_office365_and_agent_registry_governance(self) -> None:
        german_auth = read("docs/de/authenticated-webapp-operating-model.md")
        english_auth = read("docs/en/authenticated-webapp-operating-model.md")
        german_arch = read("docs/de/architecture.md")
        english_arch = read("docs/en/architecture.md")
        combined = "\n".join([german_auth, english_auth, german_arch, english_arch])

        required_terms = [
            "Office 365",
            "Microsoft 365",
            "Entra ID",
            "Microsoft Graph REST/MCP",
            "Microsoft Agent 365 Agent Registry",
            "Agent Registry Sync",
            "Vorschau",
            "Preview",
            "Microsoft 365 Admin Center",
            "zentrale Sichtbarkeit und Governance",
            "central visibility and governance",
            "Amazon Bedrock",
            "Google Vertex AI",
            "Salesforce Agentforce",
            "Databricks Genie",
            "OCI Identity Domains",
            "App Release Overlay",
            "Legacy-Referenzen",
            "legacy references",
            "kein aktueller Deploy-Schritt",
            "not a current deploy step",
        ]

        for term in required_terms:
            self.assertIn(term, combined)

        self.assertIn("Microsoft 365 ist im MVP nicht nur Client-Schicht", german_auth)
        self.assertIn("Microsoft 365 is not only the client layer in the MVP", english_auth)
        self.assertIn("Entra ID ist für den M365-MVP die aktive Identitäts-", german_auth)
        self.assertIn("Entra ID is the active identity and group-anchor layer", english_auth)
        self.assertIn("Microsoft Agent 365 Agent Registry", german_arch)
        self.assertIn("Microsoft Agent 365 Agent Registry", english_arch)

        forbidden_terms = [
            "Office 365 ersetzt OCI Identity Domains",
            "Office 365 replaces OCI Identity Domains",
            "OCI Identity Domains bleibt die aktuelle SaaS-IdP-Schicht",
            "OCI Identity Domains remains the current SaaS IdP layer",
            "Agent Registry ist produktiv verpflichtend",
            "Agent Registry is production mandatory",
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, combined)


if __name__ == "__main__":
    unittest.main()
