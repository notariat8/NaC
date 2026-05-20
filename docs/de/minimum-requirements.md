# Mindestvoraussetzungen

Status: verbindliche Day-0-Baseline
Letzte inhaltliche Anpassung: 2026-05-15

## Zweck

Dieses Kapitel definiert die Mindestvoraussetzungen für lokale Entwicklung,
Plugin-Tests und den späteren Notariatsarbeitsplatz. Die Liste ist Teil der
SBOM-Pflege: Runtime, lokale Middleware, Hardware und optionale Fachsysteme
werden als Lieferkettenbestandteile behandelt, auch wenn sie nicht als
Repository-Datei eingecheckt werden.

## Profile

| Profil | Zweck | Verbindlichkeit |
| --- | --- | --- |
| `base` | Repo lesen, Policies prüfen, Python-Tests ausführen | Pflicht für jede produktive Änderung |
| `plugin-dev` | Plugins, lokale Actions, Packaging und App-nahe Artefakte entwickeln | Pflicht für Plugin- und Integrationsarbeit |
| `notary-workstation` | XNP-, Kartenleser-, morris- und Notariatsarbeitsplatz-Pfade prüfen | Pflicht vor lokalen Fachsystemtests |

## Base-Workspace

Der Base-Workspace ist die Mindestumgebung für Arbeit am Repository:

| Komponente | Mindeststand | Zweck |
| --- | --- | --- |
| Betriebssystem | Windows 11 oder ein aktuelles, gepflegtes Entwickler-OS | Lokale Entwicklung und GitOps-Arbeit |
| Git | installiert und im `PATH` | Versionierung, Branches, Pull Requests |
| GitHub CLI `gh` | installiert und authentifiziert | PR-, Actions- und Repo-Operationen |
| Python | `>= 3.11` | deterministische Checks, KG-Runtime, Workflow-Runtime |
| VS Code oder Cursor | empfohlen | IDE-gestützte Mitarbeit |
| VS Code Copilot Extensions | erforderlich für VS-Code-Pfad | Agenten- und Copilot-Synchronität |
| `pandoc` | empfohlen | späterer Dokumentexport |

Pflichtcheck:

```bash
python scripts/startup_check.py --profile base --ide auto --run-tests
```

## Plugin-Development-Workspace

Für Plugin- und Integrationsentwicklung kommt zum Base-Workspace hinzu:

| Komponente | Mindeststand | Zweck |
| --- | --- | --- |
| Node.js | `>= 20` empfohlen | Packaging, lokale Web-/Action-Prototypen, Validatoren |
| npm | passend zu Node.js | Paketinstallation und Build-Kommandos |
| Lokaler Loopback-Zugriff | `127.0.0.1` erreichbar | lokale Gateways wie morris, XNP-Testadapter |
| Browser | aktueller Chromium/Edge/Chrome oder Firefox | lokale Middleware- und Admin-Oberflächen |

Pflichtcheck für Plugin-Arbeit:

```bash
python scripts/nac.py plugins validate
python scripts/nac.py plugins install --mode link
python scripts/startup_check.py --profile plugin-dev --ide auto
```

Danach Codex neu starten oder eine neue Session mit Workspace `~/NaC` öffnen,
weil aktive Plugins beim Session-Start geladen werden. Wenn Symlinks auf einem
Arbeitsplatz nicht erlaubt sind, nach Freigabe `--mode copy --force` verwenden.

## Notariatsarbeitsplatz Für Karten- Und XNP-Pfade

Der Notariatsarbeitsplatz ist eine lokale Windows-Umgebung. Er ist nicht durch
Cloud-Ausführung oder Omnistation zu ersetzen, solange lokale Karten-,
Signatur- oder XNP-Komponenten benötigt werden.

| Komponente | Mindeststand | Zweck |
| --- | --- | --- |
| Betriebssystem | Windows 11 oder aktueller unterstützter Windows-Client | Treiber-, Karten- und XNP-Kompatibilität |
| Benutzerkontext | derselbe Windows-Benutzer für Codex, morris, Treiber und XNP | konsistente lokale Rechte und Laufzeitpfade |
| Lokale Adminrechte | für Installation/Wartung verfügbar | Treiber, morris, XNP, PC/SC |
| Kartenleser | REINER SCT cyberJack oder aequivalenter Sicherheitsklasse-3-Leser | BNotK-Kartenpfad und sichere PIN-Eingabe |
| BNotK Chip-/Signaturkarte | vorhanden für Fachtests | Authentisierung und Signaturpfade |
| PC/SC-Dienst | installiert und gestartet | Smartcard-Zugriff für lokale Software |
| REINER SCT DriverPackage | installiert, typischer Pfad `C:\Program Files\REINER SCT\DriverPackage` | Kartenleser-Treiber |
| REINER SCT morris | installiert, typischer Pfad `C:\Program Files (x86)\REINER SCT\morris` | lokales Browser-/Middleware-Gateway |
| morris Loopback | lokale Antwort auf `127.0.0.1`, Standardprobe `8800` | Plugin kann Middleware-Erreichbarkeit testen |
| XNP | lokal installiert | BNotK-/Registerkommunikation |
| SAK lite oder XNP-Kartenpfad | installiert/konfiguriert | Kartenbasierter XNP-Zugang |
| secureFramework | installiert/konfiguriert, falls vom Kartenpfad verlangt | lokale Sicherheitskomponente |
| XNotar/Exchange-Pfad | vorhanden, wenn Registervorgänge getestet werden | HRA/HRB- und Austauschpakete |
| AusweisApp | optional für IDaaS/eID-Pfade | eID-Funktionsprüfung |

Ein morris-Test ist erfolgreich, wenn die Middleware erreichbar antwortet. Ohne
angeschlossene oder eingelegte Karte ist eine Antwort wie `kein Kartenleser
angeschlossen`, `NoReader` oder `NaCard` für die technische
Anbindungsprüfung ausreichend. Wenn echte Hardware, Karte, morris und XNP lokal
installiert sind, sind echte lokale Hardware-Readiness-Tests vorgesehen.

Notariatsarbeitsplatz-Check:

```bash
python scripts/startup_check.py --profile notary-workstation --ide auto
python scripts/nac.py plugins card-readiness --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
python scripts/nac.py plugins xnp-reader-prompt --manual-card-present yes --manual-rfid-off yes --probe-morris-api --json
```

## Datenschutz Und Betriebsgrenzen

- Keine PINs, Kartenseriennummern, Zertifikatsinhalte, Mandatsdaten oder echten
  personenbezogenen Daten im Repository speichern.
- Karten- und XNP-Tests dürfen bei installierter echter Hardware lokale
  Hardware-, Middleware- und XNP-Erreichbarkeit prüfen. Gesperrt bleiben PIN-,
  Kartenrohdaten-, Secret-, Mandatsdaten-, Signatur- und Produktivaktionen.
- Externe Verarbeitung mit personenbezogenen Daten braucht vor einem Pilot einen
  dokumentierten AVV/DPA-Status.
- Lokale Fachsysteme bleiben lokale Abhängigkeiten und müssen in SBOM und
  AI-SBOM als Infrastruktur-/Runtime-Komponenten auftauchen.

## SBOM-Pflicht

Jede Komponente aus diesem Kapitel muss in einem der folgenden Artefakte
abgebildet oder begründet als `pending` geführt werden:

- `policies/sbom-policy.yaml`
- `sbom/ai/nac-ai-sbom-draft.json`
- spätere CycloneDX-/SPDX-Exports unter `out/sbom/`

Bei jeder neuen Plugin-, Workflow- oder Usecase-Abhängigkeit gilt:

1. Mindestvoraussetzung dokumentieren.
2. SBOM-/AI-SBOM-Eintrag ergänzen.
3. lokalen Check oder manuelle Prüfnotiz angeben.
4. `roadmap/GANTT.md` aktualisieren.
