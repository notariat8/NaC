# Plugin Plans

## Zweck

Dieses Verzeichnis beschreibt die lokalen Plugin- und Connector-Plaene fuer OaC.
Die Plaene sind bewusst als Markdown-Quellen gepflegt, damit sie reviewbar, versioniert und ohne proprietaere Laufzeit lesbar bleiben.

## Grundentscheidung

OaC wird lokal betrieben:

- Workspace: `~/OaC` in Ubuntu WSL.
- Git-Quelle: `https://github.com/ofunk/OaC.git`.
- Codex, OCI CLI, GitHub-CLI und Fachintegrationen werden lokal eingerichtet.
- Omnistation ist fuer OaC kein Ausfuehrungsort.
- Remote-Hosts duerfen nur fuer unkritische Recherche genutzt werden.

Diese Entscheidung verhindert Brueche bei GitHub-Authentifizierung, Browser-Callbacks, OCI-Konfiguration und lokalen Fachintegrationen.

## Planfamilien

| Plan | Zweck | Day0 | Day1 | Day2 |
| --- | --- | --- | --- | --- |
| `local-codex-runtime.md` | Lokaler Codex-/LLM-Arbeitsplatz | Workspace und Startcheck | lokale Planerzeugung | regelmaessige Tool-/Policy-Pruefung |
| `github-control-plane.md` | GitHub als GitOps-Steuerung | Auth und Repo-Zugriff | PRs, Checks, Reviews | Branchschutz, Audit, Drift |
| `oci-infrastructure.md` | OCI CLI/MCP und Resource Manager | API-Key und CLI | Stacks, Eventstream, Evidence | Drift, Rotation, Kostenkontrolle |
| `domain-connector-runtime.md` | Fachsystem-Connectoren | Vertragsmodell | Plan/Apply/Reconcile | Monitoring, Replays, Exit |
| `handelsregister-bundesapi.md` | Handelsregister-Recherche ueber technischen Spike | Nutzungs- und Lizenzpruefung | Dry-run Rechercheplan | Rate-Limits, Quellenwechsel, Audit |
| `bnotk-xnp-notariatssoftware.md` | XNP/Notariatssoftware lokaler Companion | Arbeitsplatz- und Schnittstellenpruefung | lokaler Plan/Apply-Companion | lokale Logs, Evidence, Updatepflege |

## Verbindliches Adapter-Muster

Jeder Plugin- oder Connector-Plan folgt diesem Ablauf:

1. Intent aufnehmen.
2. Schema und Policy pruefen.
3. Plan Preview erzeugen.
4. Menschliche Freigabe einholen.
5. Idempotent ausfuehren.
6. Audit Evidence schreiben.
7. Drift sichtbar machen.
8. Exit- und Ersatzpfad dokumentieren.

## Sicherheitsgrenzen

- Keine Secrets, Tokens, Private Keys oder personenbezogenen Echtdaten im Repo.
- Lokale Credentials bleiben in lokalen Stores (`~/.oci`, Git Credential Manager, Browser/OAuth Stores).
- Adapter duerfen nicht direkt an Policies vorbei schreiben.
- Sensible Prozesse brauchen Vier-Augen-Freigabe.
- Jeder dauerhafte manuelle Eingriff muss in Git reconciled werden.

## Statusmodell

Plugin-Plaene nutzen folgende Statuswerte:

- `draft`: fachlich skizziert, nicht zur Umsetzung freigegeben.
- `proposed`: umsetzungsnah, aber noch ohne Review.
- `approved`: fuer Pilotumsetzung freigegeben.
- `active`: in einem Pilot oder produktiven Ablauf verwendet.
- `deprecated`: ersetzt, nur noch fuer Rueckverfolgung.

## Lokaler Regenerationsablauf

```bash
cd ~/OaC
git pull
python3 scripts/startup_check.py --ide auto --run-tests
```

Wenn der Startcheck fehlschlaegt, werden die Fehler dokumentiert und nicht durch Remote-Ausfuehrung umgangen.
Danach werden die Markdown-Plaene lokal angepasst, geprueft, committed und gepusht.

## Offene lokale Voraussetzungen

Der aktuelle lokale Startcheck erwartet noch:

- `python` als Alias oder Command neben `python3`.
- `gh` fuer GitHub-Operationen.
- VS-Code-Extensions `github.copilot` und `github.copilot-chat`, falls VS Code als Ziel-IDE genutzt wird.
- Paketinstallation oder `PYTHONPATH=src`, damit `business_os` in Tests gefunden wird.
- Optional `pandoc` fuer PDF-Exporte.

Diese Punkte sind lokale Tooling-Aufgaben, keine Omnistation-Aufgaben.
