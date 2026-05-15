# Mindestvoraussetzungen

Status: verbindliche Day-0-Baseline
Letzte inhaltliche Anpassung: 2026-05-15

## Zweck

Dieses Kapitel definiert die Mindestvoraussetzungen fuer lokale Entwicklung,
Plugin-Tests und den spaeteren Notariatsarbeitsplatz. Die Liste ist Teil der
SBOM-Pflege: Runtime, lokale Middleware, Hardware und optionale Fachsysteme
werden als Lieferkettenbestandteile behandelt, auch wenn sie nicht als
Repository-Datei eingecheckt werden.

## Profile

| Profil | Zweck | Verbindlichkeit |
| --- | --- | --- |
| `base` | Repo lesen, Policies pruefen, Python-Tests ausfuehren | Pflicht fuer jede produktive Aenderung |
| `plugin-dev` | Plugins, lokale Actions, Packaging und App-nahe Artefakte entwickeln | Pflicht fuer Plugin- und Integrationsarbeit |
| `notary-workstation` | XNP-, Kartenleser-, morris- und Notariatsarbeitsplatz-Pfade pruefen | Pflicht vor lokalen Fachsystemtests |

## Base-Workspace

Der Base-Workspace ist die Mindestumgebung fuer Arbeit am Repository:

| Komponente | Mindeststand | Zweck |
| --- | --- | --- |
| Betriebssystem | Windows 11 oder ein aktuelles, gepflegtes Entwickler-OS | Lokale Entwicklung und GitOps-Arbeit |
| Git | installiert und im `PATH` | Versionierung, Branches, Pull Requests |
| GitHub CLI `gh` | installiert und authentifiziert | PR-, Actions- und Repo-Operationen |
| Python | `>= 3.11` | deterministische Checks, KG-Runtime, Workflow-Runtime |
| VS Code oder Cursor | empfohlen | IDE-gestuetzte Mitarbeit |
| VS Code Copilot Extensions | erforderlich fuer VS-Code-Pfad | Agenten- und Copilot-Synchronitaet |
| `pandoc` | empfohlen | spaeterer Dokumentexport |

Pflichtcheck:

```bash
python scripts/startup_check.py --profile base --ide auto --run-tests
```

## Plugin-Development-Workspace

Fuer Plugin- und Integrationsentwicklung kommt zum Base-Workspace hinzu:

| Komponente | Mindeststand | Zweck |
| --- | --- | --- |
| Node.js | `>= 20` empfohlen | Packaging, lokale Web-/Action-Prototypen, Validatoren |
| npm | passend zu Node.js | Paketinstallation und Build-Kommandos |
| Lokaler Loopback-Zugriff | `127.0.0.1` erreichbar | lokale Gateways wie morris, XNP-Testadapter |
| Browser | aktueller Chromium/Edge/Chrome oder Firefox | lokale Middleware- und Admin-Oberflaechen |

Pflichtcheck fuer Plugin-Arbeit:

```bash
python scripts/startup_check.py --profile plugin-dev --ide auto
```

## Notariatsarbeitsplatz Fuer Karten- Und XNP-Pfade

Der Notariatsarbeitsplatz ist eine lokale Windows-Umgebung. Er ist nicht durch
Cloud-Ausfuehrung oder Omnistation zu ersetzen, solange lokale Karten-,
Signatur- oder XNP-Komponenten benoetigt werden.

| Komponente | Mindeststand | Zweck |
| --- | --- | --- |
| Betriebssystem | Windows 11 oder aktueller unterstuetzter Windows-Client | Treiber-, Karten- und XNP-Kompatibilitaet |
| Benutzerkontext | derselbe Windows-Benutzer fuer Codex, morris, Treiber und XNP | konsistente lokale Rechte und Laufzeitpfade |
| Lokale Adminrechte | fuer Installation/Wartung verfuegbar | Treiber, morris, XNP, PC/SC |
| Kartenleser | REINER SCT cyberJack oder aequivalenter Sicherheitsklasse-3-Leser | BNotK-Kartenpfad und sichere PIN-Eingabe |
| BNotK Chip-/Signaturkarte | vorhanden fuer Fachtests | Authentisierung und Signaturpfade |
| PC/SC-Dienst | installiert und gestartet | Smartcard-Zugriff fuer lokale Software |
| REINER SCT DriverPackage | installiert, typischer Pfad `C:\Program Files\REINER SCT\DriverPackage` | Kartenleser-Treiber |
| REINER SCT morris | installiert, typischer Pfad `C:\Program Files (x86)\REINER SCT\morris` | lokales Browser-/Middleware-Gateway |
| morris Loopback | lokale Antwort auf `127.0.0.1`, Standardprobe `8800` | Plugin kann Middleware-Erreichbarkeit testen |
| XNP | lokal installiert | BNotK-/Registerkommunikation |
| SAK lite oder XNP-Kartenpfad | installiert/konfiguriert | Kartenbasierter XNP-Zugang |
| secureFramework | installiert/konfiguriert, falls vom Kartenpfad verlangt | lokale Sicherheitskomponente |
| XNotar/Exchange-Pfad | vorhanden, wenn Registervorgaenge getestet werden | HRA/HRB- und Austauschpakete |
| AusweisApp | optional fuer IDaaS/eID-Pfade | eID-Funktionspruefung |

Ein morris-Test ist erfolgreich, wenn die Middleware erreichbar antwortet. Eine
Antwort wie `kein Kartenleser angeschlossen`, `NoReader` oder `NoCard` ist fuer
die technische Anbindungspruefung ausreichend, solange keine echte Kartenaktion
ausgefuehrt werden soll.

Notariatsarbeitsplatz-Check:

```bash
python scripts/startup_check.py --profile notary-workstation --ide auto
python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --json --probe-morris-api
python plugins\noc-bnotk-xnp\scripts\reader_prompt.py --json --probe-morris-api
```

## Datenschutz Und Betriebsgrenzen

- Keine PINs, Kartenseriennummern, Zertifikatsinhalte, Mandatsdaten oder echten
  personenbezogenen Daten im Repository speichern.
- Karten- und XNP-Tests arbeiten zuerst mit Readiness-Status und technischen
  Negativantworten wie `NoReader` oder `NoCard`.
- Externe Verarbeitung mit personenbezogenen Daten braucht vor einem Pilot einen
  dokumentierten AVV/DPA-Status.
- Lokale Fachsysteme bleiben lokale Abhaengigkeiten und muessen in SBOM und
  AI-SBOM als Infrastruktur-/Runtime-Komponenten auftauchen.

## SBOM-Pflicht

Jede Komponente aus diesem Kapitel muss in einem der folgenden Artefakte
abgebildet oder begruendet als `pending` gefuehrt werden:

- `policies/sbom-policy.yaml`
- `sbom/ai/nac-ai-sbom-draft.json`
- spaetere CycloneDX-/SPDX-Exports unter `out/sbom/`

Bei jeder neuen Plugin-, Workflow- oder Usecase-Abhaengigkeit gilt:

1. Mindestvoraussetzung dokumentieren.
2. SBOM-/AI-SBOM-Eintrag ergaenzen.
3. lokalen Check oder manuelle Pruefnotiz angeben.
4. `roadmap/GANTT.md` aktualisieren.
