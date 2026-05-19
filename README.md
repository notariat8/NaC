# NaC: Notariat as Code

NaC ist ein öffentliches Referenz- und Produktkern-Repository für den
AI-first-Betrieb notarieller Vorgangsarten. Ein Notariat soll dieses Repository
klonen, prüfen und als Vorlage für einen privaten, eigenen Betriebs-Fork nutzen
können.

Der Kern ist einfach: KI hilft beim Strukturieren, Menschen entscheiden, Git
dokumentiert, Python prüft, und echte Mandatsdaten bleiben außerhalb dieses
öffentlichen Repositories.

Herausgeber und Maintainer: [ofunk](https://github.com/ofunk). Weitere
Einordnung steht in [HERAUSGEBER.md](HERAUSGEBER.md).

Deutsch ist repo-weit die führende Sprache für menschlich lesbare Inhalte.
Englisch ist Pflichtsprache für lokalisierte Spiegel, aber nur Übersetzung
oder Orientierung. Für deutsches Recht und notarielle Usecases ist Deutsch
führend und rechtlich bindend. Die verbindliche Sprachregel steht in
[policies/language-policy.yaml](policies/language-policy.yaml) und wird mit
[scripts/validate_language_parity.py](scripts/validate_language_parity.py)
geprüft.

## Für Wen

| Zielgruppe | Einstieg | Worum es geht |
| --- | --- | --- |
| Notariat und fachliche Entscheidung | [docs/de/notar-start.md](docs/de/notar-start.md) | Nutzen, Grenzen, Datenschutz, erster Prüflauf und Entscheidung, ob ein privater Fork sinnvoll ist. |
| Office-Admin und IT-Betrieb | [docs/de/betriebsstart.md](docs/de/betriebsstart.md) | Klonen, lokale Checks, private Betriebsumgebung, Rollen, Arbeitsplatz- und Plugin-Voraussetzungen. |
| Fachsystem- und Integrationsseite | [docs/de/integration-start.md](docs/de/integration-start.md) | Wie bestehende Fachsysteme, lokale Middleware, Portale und Connectoren an NaC angebunden werden können. |
| Prüfung und Standardisierung | [docs/de/pruefung-standardisierung-start.md](docs/de/pruefung-standardisierung-start.md) | Wie Kontroll-, Nachweis-, Zertifizierungs- und Standardisierungsfragen am Repo nachvollzogen werden. |
| Entwicklung und Maintainer | [docs/de/START_HERE.md](docs/de/START_HERE.md) | Verbindlicher Arbeitsstart für Code, Policies, Plugins, Workflows, Usecases und Agenten. |

Schnelle Orientierung für Nicht-Technik:
[Ausführungsmodell](docs/de/ausfuehrungsmodell.md),
[Reifegrad](docs/de/reifegrad.md), [Glossar](docs/de/glossar.md) und
[Beispiel Immobilienkaufvertrag](docs/de/beispiel-immobilienkaufvertrag.md).

Englische Orientierung: [docs/en/notar-start.md](docs/en/notar-start.md),
[docs/en/betriebsstart.md](docs/en/betriebsstart.md),
[docs/en/integration-start.md](docs/en/integration-start.md),
[docs/en/pruefung-standardisierung-start.md](docs/en/pruefung-standardisierung-start.md).

## Was Dieses Repo Leistet

- Es beschreibt notarielle Vorgangsarten als versionierte, prüfbare Usecases.
- Es trennt öffentliche Muster, private Kanzlei-/Notariatsdaten und lokale
  Fachsysteme.
- Es stellt Plugins, Workflow-Verträge und deterministische Python-Prüfungen
  für AI-first-Betrieb bereit.
- Es macht Freigaben, offene Fragen, technische Readiness, Datenschutzgrenzen und
  Nachweise nachvollziehbar.
- Es verhindert im Musterrepo echte personenbezogene Daten, Secrets, PINs,
  Registerauszüge oder Mandatsdokumente.

## Was Es Bewusst Nicht Leistet

- NaC ersetzt kein vorgeschriebenes Fachsystem und keine berufsrechtliche
  Verantwortung.
- NaC ist keine automatische Rechtsberatung und keine autonome Beurkundung.
- Öffentliche Repository-Dateien sind keine Ablage für echte Akten,
  Ausweisdaten, Registerauszüge, Zahlungsdaten oder Signaturgeheimnisse.
- Produktive Nutzung braucht einen privaten Fork, lokale Rollen, Freigaben,
  Datenschutzklärung und einen geprüften Arbeitsplatz.

## Produktstruktur

Dieses Repository trennt drei Produktbereiche:

- [plugins/](plugins): installierbare Plugin-Artefakte für GPT-Store-Prüfung,
  Workspace-Installation oder lokale Integration.
- [workflows/](workflows): wiederverwendbare Notariats-Workflows, getrennt nach
  installierbaren Skills, Workflow-Verträgen und deterministischer
  Python-Ausführung.
- [usecases/](usecases): konkrete notarielle Vorgangsarten wie
  Online-GmbH-Gründung, Immobilienkaufvertrag, Handelsregisteranmeldung oder
  Testament. Jeder Usecase besitzt seine eigene statische KG/DB für offene
  Fragen, Dokumente, Entscheidungen, Gates und Nachweisreferenzen.

Weitere Dokumentation:

- Deutsch: [docs/de/](docs/de), [prompts/de/](prompts/de)
- Englisch: [docs/en/](docs/en), [prompts/en/](prompts/en)
- Mindestvoraussetzungen: [docs/de/minimum-requirements.md](docs/de/minimum-requirements.md)
- Ausführungsmodell: [docs/de/ausfuehrungsmodell.md](docs/de/ausfuehrungsmodell.md)
- BPMN-js Business Layer: [docs/de/bpmn-js-business-layer.md](docs/de/bpmn-js-business-layer.md)
- Reifegrad: [docs/de/reifegrad.md](docs/de/reifegrad.md)
- Glossar: [docs/de/glossar.md](docs/de/glossar.md)
- Beispiel Immobilienkaufvertrag: [docs/de/beispiel-immobilienkaufvertrag.md](docs/de/beispiel-immobilienkaufvertrag.md)
- Datenschutz und AVV/DPA: [docs/de/datenschutz-avv-dpa.md](docs/de/datenschutz-avv-dpa.md)
- AI-SBOM: [docs/de/sbom-for-ai.md](docs/de/sbom-for-ai.md)
- KG-Editor-Workstream: [docs/de/kg-editor-workstream.md](docs/de/kg-editor-workstream.md)
- Globale Roadmap: [roadmap/GANTT.md](roadmap/GANTT.md)

## Erster Prüflauf

Nach dem Klonen:

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
python scripts/quality_gate.py --profile strict
```

Wenn Python noch nicht eingerichtet ist, zuerst
[docs/de/minimum-requirements.md](docs/de/minimum-requirements.md) lesen.

## Aktueller Entwicklungsmodus

NaC wird als ausführbare Software entwickelt, nicht nur als Dokumentation. Die
aktuell implementierte Runtime-Oberfläche ist die notarielle KG-CLI:

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
```

Das aktive Build-Board wird in [roadmap/BUILD_NOW.md](roadmap/BUILD_NOW.md)
gepflegt.

## Lizenz Und Attribution

NaC ist maximal offen und zugleich schützend lizenziert:

- Code, Plugins, Workflows, Validatoren, Schemas und ausführbare Beispiele:
  `AGPL-3.0-or-later`
- Dokumentation, Diagramme, Policies, Roadmap, Prompts und fachliche Usecases:
  `CC-BY-4.0`

Die verbindliche Zuordnung steht in [LICENSES/README.md](LICENSES/README.md).
Bitte bei Forks, öffentlichen Deployments, Präsentationen und abgeleiteten
Unterlagen sichtbar nennen:

> Based on NaC: Notariat as Code by funktion8 / ofunk (https://github.com/ofunk/NaC).

Weitere Hinweise: [NOTICE](NOTICE), [AUTHORS.md](AUTHORS.md),
[CITATION.cff](CITATION.cff) und [TRADEMARK.md](TRADEMARK.md).

## Push- Und Qualitätsregel

Jeder Push muss [roadmap/GANTT.md](roadmap/GANTT.md) aktualisieren. Änderungen
unter [plugins/](plugins), [workflows/](workflows) oder [usecases/](usecases)
müssen zusätzlich das jeweilige Themen-Gantt aktualisieren.

Das strikte Quality Gate prüft Prozessdateien, Tests, Datenschutzregeln,
Governance-Sync, Sprachregeln, Cloud-Runbook-Parität, Plugin-Manifeste,
AI-SBOM-Stand, Gantt-Pflege, die usecase-lokalen statischen Knowledge Graphs
und den KG-Editor-Vertrag.
