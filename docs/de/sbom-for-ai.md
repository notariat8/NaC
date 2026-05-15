# SBOM for AI

## Zweck

`SBOM for AI` ist ein eigener, repo-weiter Governance-Track fuer NaC. Er
erweitert klassische Software-SBOMs um KI-spezifische Transparenz zu Modellen,
Daten, Infrastruktur, Sicherheitskontrollen und Leistungsindikatoren.

Diese Seite ist der Startpunkt fuer die Ausarbeitung. Sie gilt fuer alle
Plugins, Workflows, Usecases, Prompts und externen Modellaufrufe in NaC.

## Quellenstand

Geprueft am 2026-05-15:

- BSI-Pressemitteilung zur G7-Richtlinie `SBOM for AI`, 2026-05-12:
  `https://www.bsi.bund.de/DE/Service-Navi/Presse/Pressemitteilungen/Presse2026/260512_G7_Richtlinie_SBOM_for_AI.html`
- BSI-Themenseite KI, Abschnitt `SBOM for AI`:
  `https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Informationen-und-Empfehlungen/Kuenstliche-Intelligenz/KI.html`
- CISA/G7-Ressource `Software Bill of Materials for AI - Minimum Elements`:
  `https://www.cisa.gov/resources-tools/resources/software-bill-materials-ai-minimum-elements`

Die BSI/G7-Linie zielt auf Transparenz entlang der KI-Lieferkette. AI-SBOM
ergaenzt klassische SBOMs, weil KI-Systeme neben Softwarekomponenten auch
Modelle, Datensaetze, Infrastruktur, Sicherheits- und Betriebsparameter
enthalten.

## NoC Mindestcluster

NaC fuehrt die folgenden Mindestcluster als Arbeitsstand ein:

| Cluster | NoC-Inhalt |
| --- | --- |
| `metadata` | Name, Version, Owner, Lebenszyklus, Release-Bindung |
| `system_level_properties` | Systemgrenzen, Zweck, Autonomiegrad, menschliche Freigabe |
| `models` | Modellname, Anbieter, Version, Zweck, lokale/externe Verarbeitung |
| `datasets` | Trainings-, Test-, Validierungs- und Prompt-Datenquellen als Metadaten |
| `infrastructure` | Runtime, Hosting, Tenant, Region, lokale Gateways, Mindestvoraussetzungen fuer Arbeitsplatz, Hardware und Middleware |
| `security_properties` | Schutz gegen Datenabfluss, Prompt Injection, Supply-Chain-Risiken |
| `key_performance_indicators` | Abdeckung, Drift, Fehlerraten, Review- und Incident-Metriken |

NoC ergaenzt zusaetzlich Datenschutz-/AVV-DPA-Status, Berufsgeheimnisgrenzen,
Human-Review-Owner, lokale Runtime-/Hardware-Mindestvoraussetzungen und
Release-/Evidence-Bindung.

## Erste Artefakte

- Policy: `policies/sbom-policy.yaml`
- Draft AI-SBOM: `sbom/ai/nac-ai-sbom-draft.json`
- Validator: `scripts/validate_ai_sbom.py`
- Mindestvoraussetzungen: `docs/de/minimum-requirements.md`
- Klassische SBOM-Produkte: `docs/de/sbom-products.md`
- AVV/DPA-Gate: `docs/de/datenschutz-avv-dpa.md`

## Sofortige Tasks

| Prioritaet | Task | Ergebnis |
| --- | --- | --- |
| P0 | Alle AI-Touchpoints in `plugins/`, `workflows/`, `usecases/` und `prompts/` inventarisieren. | Liste der AI-faehigen Artefakte. |
| P0 | `sbom/ai/nac-ai-sbom-draft.json` je neuem AI-faehigen Artefakt fortschreiben. | Repo-weite AI-SBOM-Baseline. |
| P0 | Lokale Mindestvoraussetzungen fuer Runtime, Hardware, morris und XNP in AI-SBOM fuehren. | Arbeitsplatz- und Middleware-Abhaengigkeiten sind pruefbar inventarisiert. |
| P0 | Externe KI-Verarbeitung gegen `docs/de/datenschutz-avv-dpa.md` pruefen. | AVV/DPA-Status je Kanal. |
| P1 | Mapping auf CycloneDX, SPDX oder ein genehmigtes AI-SBOM-Profil festlegen. | Maschinenlesbares Zielprofil. |
| P1 | Release-Bindung in `.github/workflows/sbom-export.yml` ausbauen. | AI-SBOM als Release-Artefakt. |
| P2 | Modellrisiko-, Vulnerability- und Drift-Review automatisieren. | Day2-Betrieb fuer AI-Lieferkette. |

## Regeln

- Keine echten personenbezogenen Daten, Mandatsinhalte, Secrets, privaten
  Schluessel oder Zertifikatsmaterialien in AI-SBOM-Artefakten speichern.
- AI-SBOM beschreibt Metadaten, Verantwortlichkeiten und Grenzen, nicht die
  vertraulichen Inhalte selbst.
- Jeder AI-faehige Release braucht eine AI-SBOM-Entscheidung.
- Jede lokale Plugin- oder Workflow-Abhaengigkeit aus
  `docs/de/minimum-requirements.md` braucht einen SBOM-/AI-SBOM-Eintrag oder
  eine begruendete `pending`-Markierung.
- Externe KI-Verarbeitung braucht vor Pilot mit personenbezogenen Daten eine
  dokumentierte AVV/DPA-Entscheidung.
- Lokale Plugin-Gates bleiben Standard, solange externe Verarbeitung nicht
  freigegeben ist.

## Definition of Done

Ein AI-faehiges Plugin, ein AI-faehiger Workflow oder ein AI-faehiger Usecase
ist erst releasefaehig, wenn:

1. das Artefakt in der AI-SBOM-Baseline enthalten ist,
2. alle Mindestcluster befuellt oder begruendet als `pending` markiert sind,
3. Runtime-, Middleware- und Hardware-Mindestvoraussetzungen dokumentiert sind,
4. Datenschutz-/AVV-DPA-Status dokumentiert ist,
5. Human-Review-Owner benannt ist,
6. `python scripts/quality_gate.py --profile strict` erfolgreich laeuft.
