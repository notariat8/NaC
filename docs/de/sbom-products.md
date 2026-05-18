# SBOM Produkte und Lizenzmodell

## Ziel

Diese Seite legt fest, welche Produkte für SBOM verwendet werden und welche davon Open Source oder kostenpflichtig sind.

## Kurzantwort zu deinem Beispiel

- `Python`: Open Source, keine Subscription nötig.
- `GitHub Lizenz`: Es gibt kostenlose und kostenpflichtige Stufen; für reine SBOM-Erzeugung ist keine zwingende Zusatzsubscription nötig.

## Verbindlicher SBOM-Stack im Musterrepo

| Bereich | Produkt | Standard/Format | Open Source | Subscription nötig |
| --- | --- | --- | --- | --- |
| Python-Komponenten-SBOM | `cyclonedx-python` | CycloneDX JSON | Ja | Nein |
| Dateisystem-/Artefakt-SBOM | `syft` | SPDX JSON | Ja | Nein |
| CI-Ausführung | GitHub Actions | Artefakt-Export | Nein (Plattformdienst) | Nein (Basisnutzung) |
| Erweiterte Security-Auswertung | GitHub Advanced Security | Security-Features | Nein | Ja (optional) |

## SBOM for AI

Klassische SBOMs reichen für KI-Systeme nicht aus. NaC führt deshalb einen
zusätzlichen `SBOM for AI`-Track nach `docs/de/sbom-for-ai.md` und
`policies/sbom-policy.yaml`.

Erste Artefakte:

- `sbom/ai/nac-ai-sbom-draft.json`
- `scripts/validate_ai_sbom.py`

Dieser Track gilt repo-weit für AI-fähige Plugins, Workflows, Usecases,
Prompts und externe Modellaufrufe.

Lokale Mindestvoraussetzungen wie Python, Node.js/npm, GitHub CLI, morris,
REINER-SCT-Treiber, Kartenleser, PC/SC und XNP gelten ebenfalls als
SBOM-relevante Runtime-/Infrastruktur-Komponenten. Die verbindliche Liste steht
in `docs/de/minimum-requirements.md` und wird in
`sbom/ai/nac-ai-sbom-draft.json` gespiegelt.

## Empfehlung für dieses Repository

1. Erzeuge mindestens zwei SBOM-Artefakte:
   - CycloneDX JSON (Python-Sicht)
   - SPDX JSON (Gesamtsicht)
2. Speichere die Artefakte als CI-Artefakte unter `out/sbom/`.
3. Verknüpfe Release-Tags mit den passenden SBOM-Artefakten.
4. Führe lokale Arbeitsplatz-, Hardware- und Middleware-Abhängigkeiten in der
   AI-SBOM, solange sie noch nicht vollständig in CycloneDX/SPDX exportiert
   werden.

## Was ist zwingend vs. optional

- Zwingend:
  - SBOM-Erzeugung in offenen Standardformaten
  - versionierte Ablage je Release
- Optional:
  - GitHub Advanced Security
  - zusätzliche proprietäre Compliance-Produkte

## Hinweise für Unternehmen

- Wer nur mit Open-Source-Stack starten will, kann das vollständig tun.
- Wer später zusätzliche Security-Features braucht, kann optional kostenpflichtige GitHub-Funktionen aktivieren, ohne den SBOM-Kernprozess zu ändern.
