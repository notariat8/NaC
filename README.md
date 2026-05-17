# NoC: Notariat as Code

NoC ist ein oeffentliches Referenz- und Produktkern-Repository fuer den
AI-first-Betrieb notarieller Vorgangsarten. Ein Notariat soll dieses Repository
klonen, pruefen und als Vorlage fuer einen privaten, eigenen Betriebs-Fork nutzen
koennen.

Der Kern ist einfach: KI hilft beim Strukturieren, Menschen entscheiden, Git
dokumentiert, Python prueft, und echte Mandatsdaten bleiben ausserhalb dieses
oeffentlichen Repositories.

Herausgeber und Maintainer: [ofunk](https://github.com/ofunk). Weitere
Einordnung steht in [HERAUSGEBER.md](HERAUSGEBER.md).

Deutsch ist repo-weit die fuehrende Sprache fuer menschlich lesbare Inhalte.
Englisch ist Pflichtsprache fuer lokalisierte Spiegel, aber nur Uebersetzung
oder Orientierung. Fuer deutsches Recht und notarielle Usecases ist Deutsch
fuehrend und rechtlich bindend. Die verbindliche Sprachregel steht in
[policies/language-policy.yaml](policies/language-policy.yaml) und wird mit
[scripts/validate_language_parity.py](scripts/validate_language_parity.py)
geprueft.

## Fuer Wen

| Zielgruppe | Einstieg | Worum es geht |
| --- | --- | --- |
| Notariat und fachliche Entscheidung | [docs/de/notar-start.md](docs/de/notar-start.md) | Nutzen, Grenzen, Datenschutz, erster Prueflauf und Entscheidung, ob ein privater Fork sinnvoll ist. |
| Office-Admin und IT-Betrieb | [docs/de/betriebsstart.md](docs/de/betriebsstart.md) | Klonen, lokale Checks, private Betriebsumgebung, Rollen, Arbeitsplatz- und Plugin-Voraussetzungen. |
| Fachsystem- und Integrationsseite | [docs/de/integration-start.md](docs/de/integration-start.md) | Wie bestehende Fachsysteme, lokale Middleware, Portale und Connectoren an NoC angebunden werden koennen. |
| Pruefung und Standardisierung | [docs/de/pruefung-standardisierung-start.md](docs/de/pruefung-standardisierung-start.md) | Wie Kontroll-, Nachweis-, Zertifizierungs- und Standardisierungsfragen am Repo nachvollzogen werden. |
| Entwicklung und Maintainer | [docs/de/START_HERE.md](docs/de/START_HERE.md) | Verbindlicher Arbeitsstart fuer Code, Policies, Plugins, Workflows, Usecases und Agenten. |

Schnelle Orientierung fuer Nicht-Technik:
[Reifegrad](docs/de/reifegrad.md), [Glossar](docs/de/glossar.md) und
[Beispiel Immobilienkaufvertrag](docs/de/beispiel-immobilienkaufvertrag.md).

Englische Orientierung: [docs/en/notar-start.md](docs/en/notar-start.md),
[docs/en/betriebsstart.md](docs/en/betriebsstart.md),
[docs/en/integration-start.md](docs/en/integration-start.md),
[docs/en/pruefung-standardisierung-start.md](docs/en/pruefung-standardisierung-start.md).

## Was Dieses Repo Leistet

- Es beschreibt notarielle Vorgangsarten als versionierte, pruefbare Usecases.
- Es trennt oeffentliche Muster, private Kanzlei-/Notariatsdaten und lokale
  Fachsysteme.
- Es stellt Plugins, Workflow-Vertraege und deterministische Python-Pruefungen
  fuer AI-first-Betrieb bereit.
- Es macht Freigaben, offene Fragen, technische Readiness, Datenschutzgrenzen und
  Nachweise nachvollziehbar.
- Es verhindert im Musterrepo echte personenbezogene Daten, Secrets, PINs,
  Registerauszuege oder Mandatsdokumente.

## Was Es Bewusst Nicht Leistet

- NoC ersetzt kein vorgeschriebenes Fachsystem und keine berufsrechtliche
  Verantwortung.
- NoC ist keine automatische Rechtsberatung und keine autonome Beurkundung.
- Oeffentliche Repository-Dateien sind keine Ablage fuer echte Akten,
  Ausweisdaten, Registerauszuege, Zahlungsdaten oder Signaturgeheimnisse.
- Produktive Nutzung braucht einen privaten Fork, lokale Rollen, Freigaben,
  Datenschutzklaerung und einen geprueften Arbeitsplatz.

## Produktstruktur

Dieses Repository trennt drei Produktbereiche:

- [plugins/](plugins): installierbare Plugin-Artefakte fuer GPT-Store-Pruefung,
  Workspace-Installation oder lokale Integration.
- [workflows/](workflows): wiederverwendbare Notariats-Workflows, getrennt nach
  installierbaren Skills, Workflow-Vertraegen und deterministischer
  Python-Ausfuehrung.
- [usecases/](usecases): konkrete notarielle Vorgangsarten wie
  Online-GmbH-Gruendung, AO52-Gemeinnuetzigkeit, Immobilienkaufvertrag oder
  Testament. Jeder Usecase besitzt seine eigene statische KG/DB fuer offene
  Fragen, Dokumente, Entscheidungen, Gates und Nachweisreferenzen.

Weitere Dokumentation:

- Deutsch: [docs/de/](docs/de), [prompts/de/](prompts/de)
- Englisch: [docs/en/](docs/en), [prompts/en/](prompts/en)
- Mindestvoraussetzungen: [docs/de/minimum-requirements.md](docs/de/minimum-requirements.md)
- Reifegrad: [docs/de/reifegrad.md](docs/de/reifegrad.md)
- Glossar: [docs/de/glossar.md](docs/de/glossar.md)
- Beispiel Immobilienkaufvertrag: [docs/de/beispiel-immobilienkaufvertrag.md](docs/de/beispiel-immobilienkaufvertrag.md)
- Datenschutz und AVV/DPA: [docs/de/datenschutz-avv-dpa.md](docs/de/datenschutz-avv-dpa.md)
- AI-SBOM: [docs/de/sbom-for-ai.md](docs/de/sbom-for-ai.md)
- KG-Editor-Workstream: [docs/de/kg-editor-workstream.md](docs/de/kg-editor-workstream.md)
- Globale Roadmap: [roadmap/GANTT.md](roadmap/GANTT.md)

## Erster Prueflauf

Nach dem Klonen:

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
python scripts/quality_gate.py --profile strict
```

Wenn Python noch nicht eingerichtet ist, zuerst
[docs/de/minimum-requirements.md](docs/de/minimum-requirements.md) lesen.

## Aktueller Entwicklungsmodus

NoC wird als ausfuehrbare Software entwickelt, nicht nur als Dokumentation. Die
aktuell implementierte Runtime-Oberflaeche ist die notarielle KG-CLI:

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
```

Das aktive Build-Board wird in [roadmap/BUILD_NOW.md](roadmap/BUILD_NOW.md)
gepflegt.

## Push- Und Qualitaetsregel

Jeder Push muss [roadmap/GANTT.md](roadmap/GANTT.md) aktualisieren. Aenderungen
unter [plugins/](plugins), [workflows/](workflows) oder [usecases/](usecases)
muessen zusaetzlich das jeweilige Themen-Gantt aktualisieren.

Das strikte Quality Gate prueft Prozessdateien, Tests, Datenschutzregeln,
Governance-Sync, Sprachregeln, Cloud-Runbook-Paritaet, Plugin-Manifeste,
AI-SBOM-Stand, Gantt-Pflege, die usecase-lokalen statischen Knowledge Graphs
und den KG-Editor-Vertrag.
