from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class AtpGraphRuntimeModelTests(unittest.TestCase):
    def test_atp_runtime_model_is_hybrid_not_sql_only(self) -> None:
        german = read("docs/de/architecture/atp-graph-runtime-model.md")
        english = read("docs/en/architecture/atp-graph-runtime-model.md")
        combined = "\n".join([german, english])

        required_terms = [
            "Transaktionale Anker",
            "Versionierte JSON-Payloads",
            "Graph- und Ontologie-Projektionen",
            "kein Synonym für ein vollständig relationales",
            "not a synonym for a fully relational",
            "Transactional anchors",
            "Versioned JSON payloads",
            "Graph and ontology projections",
            "Property Graph",
            "RDF/SPARQL/OWL",
            "No OCI apply",
            "Kein OCI-Apply",
            "Keine Speicherung von Rohmandatsdaten",
            "No storage of raw mandate data",
        ]

        for term in required_terms:
            self.assertIn(term, combined)

        forbidden_terms = [
            "SQL-only decision",
            "SQL-only-Entscheidung ohne Graph",
            "PDB pro Mandant ist entschieden",
            "one PDB per tenant is decided",
            "Productive Graph Studio activation is approved",
            "Produktive Graph-Studio-Aktivierung ist freigegeben",
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, combined)

    def test_data_sovereignty_docs_link_to_runtime_model(self) -> None:
        german = read("docs/de/architecture/data-sovereignty-git-vs-atp.md")
        english = read("docs/en/architecture/data-sovereignty-git-vs-atp.md")

        self.assertIn("[atp-graph-runtime-model.md](atp-graph-runtime-model.md)", german)
        self.assertIn("[atp-graph-runtime-model.md](atp-graph-runtime-model.md)", english)
        self.assertIn("keinen rein\nrelationalen Fachentwurf", german)
        self.assertIn("not mean a purely\nrelational subject-matter design", english)


if __name__ == "__main__":
    unittest.main()
