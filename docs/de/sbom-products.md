# SBOM Produkte und Lizenzmodell

## Ziel

Diese Seite legt fest, welche Produkte fuer SBOM verwendet werden und welche davon Open Source oder kostenpflichtig sind.

## Kurzantwort zu deinem Beispiel

- `Python`: Open Source, keine Subscription noetig.
- `GitHub Lizenz`: Es gibt kostenlose und kostenpflichtige Stufen; fuer reine SBOM-Erzeugung ist keine zwingende Zusatzsubscription noetig.

## Verbindlicher SBOM-Stack im Musterrepo

| Bereich | Produkt | Standard/Format | Open Source | Subscription noetig |
| --- | --- | --- | --- | --- |
| Python-Komponenten-SBOM | `cyclonedx-python` | CycloneDX JSON | Ja | Nein |
| Dateisystem-/Artefakt-SBOM | `syft` | SPDX JSON | Ja | Nein |
| CI-Ausfuehrung | GitHub Actions | Artefakt-Export | Nein (Plattformdienst) | Nein (Basisnutzung) |
| Erweiterte Security-Auswertung | GitHub Advanced Security | Security-Features | Nein | Ja (optional) |

## SBOM for AI

Klassische SBOMs reichen fuer KI-Systeme nicht aus. NaC fuehrt deshalb einen
zusaetzlichen `SBOM for AI`-Track nach `docs/de/sbom-for-ai.md` und
`policies/sbom-policy.yaml`.

Erste Artefakte:

- `sbom/ai/nac-ai-sbom-draft.json`
- `scripts/validate_ai_sbom.py`

Dieser Track gilt repo-weit fuer AI-faehige Plugins, Workflows, Usecases,
Prompts und externe Modellaufrufe.

Lokale Mindestvoraussetzungen wie Python, Node.js/npm, GitHub CLI, morris,
REINER-SCT-Treiber, Kartenleser, PC/SC und XNP gelten ebenfalls als
SBOM-relevante Runtime-/Infrastruktur-Komponenten. Die verbindliche Liste steht
in `docs/de/minimum-requirements.md` und wird in
`sbom/ai/nac-ai-sbom-draft.json` gespiegelt.

## Empfehlung fuer dieses Repository

1. Erzeuge mindestens zwei SBOM-Artefakte:
   - CycloneDX JSON (Python-Sicht)
   - SPDX JSON (Gesamtsicht)
2. Speichere die Artefakte als CI-Artefakte unter `out/sbom/`.
3. Verknuepfe Release-Tags mit den passenden SBOM-Artefakten.
4. Fuehre lokale Arbeitsplatz-, Hardware- und Middleware-Abhaengigkeiten in der
   AI-SBOM, solange sie noch nicht vollstaendig in CycloneDX/SPDX exportiert
   werden.

## Was ist zwingend vs. optional

- Zwingend:
  - SBOM-Erzeugung in offenen Standardformaten
  - versionierte Ablage je Release
- Optional:
  - GitHub Advanced Security
  - zusaetzliche proprietaere Compliance-Produkte

## Hinweise fuer Unternehmen

- Wer nur mit Open-Source-Stack starten will, kann das vollstaendig tun.
- Wer spaeter zusaetzliche Security-Features braucht, kann optional kostenpflichtige GitHub-Funktionen aktivieren, ohne den SBOM-Kernprozess zu aendern.
