# Agent-Control-API Für agent.notariat8.de

Status: metadata-only Routenimplementierung, kein Gateway- oder Runtime-Apply
Letzte inhaltliche Anpassung: 2026-07-02

## Zweck

Diese Seite beschreibt die zulässige API-Grenze zwischen OCI/BFF,
`agent.notariat8.de`, ATP und dem outbound Connector auf `notoclaw01`. Sie baut
auf der [Agent-Runtime-Registry](agent-runtime-registry.md) auf und definiert
lokale metadata-only Handler ohne produktive Gateway-Route, ohne
API-Gateway-Apply und ohne Connector-Start.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/agent-control-api.contract.json](../../../workflows/contracts/agent-control-api.contract.json)
und wird durch
[scripts/validate_agent_control_api.py](../../../scripts/validate_agent_control_api.py)
geprüft.

## Route-Gruppen

Browser erreichen nur die OCI-Schicht. Die rohe NemoClaw-/OpenClaw-Oberfläche
wird nicht veröffentlicht.

| Gruppe | Route | Zweck |
| --- | --- | --- |
| Browser-Session | `GET /agent/status` | redigierter Agent- und Lease-Status für die geprüfte Sitzung |
| Browser-Session | `POST /agent/leases/prepare` | serverseitige Lease-Vorbereitung nach Tenant-, Rollen-, Zweck- und optionalem Vorgangsgate |
| Connector-Control | `POST /api/agent/connect` | outbound Connector-Endpunkt registrieren oder auffrischen |
| Connector-Control | `POST /api/agent/heartbeat` | redigierten Connector- und Sandbox-Health melden |
| Connector-Control | `GET /api/agent/work/next` | nächsten metadata-only Arbeitsumschlag für eine aktive Lease abrufen |
| Connector-Control | `POST /api/agent/work/result` | redigiertes Ergebnis oder Fehlerklasse zurückmelden |

## Payload-Grenze

Erlaubt sind nur Metadaten wie Request-ID, Tenant-ID, User-Binding-ID,
Agent-ID, Endpoint-ID, Sandbox-Binding-ID, Sandbox-Lease-ID, Lease-Status,
redigierter Health-Status, Work-Envelope-ID, Status, Reason-Class und
Ablaufzeit.

Nicht erlaubt sind IdP-Tokens, Session-Cookies, Provider-Claims, Dashboard-
Tokens, Private Keys, Client-Secrets, Umgebungsdumps, Rohmandatsdaten,
Dokumentvolltexte, Karten-PINs oder XNP-Payloads.

## Lease-Regel

`/api/agent/work/next` darf nur für eine aktive, nicht abgelaufene und nicht
widerrufene Lease antworten. Abgelaufene oder widerrufene Leases schlagen
fail-closed fehl. Die Mindestisolierung bleibt `tenant + user`; bevorzugt ist
`tenant + user + vorgang + rolle`.

## Implementierungsgrenze

`src/nac_web/server.py` implementiert die Routen als lokale BFF-Handler. Diese
Handler liefern nur Metadaten, schlagen ohne geprüfte Sitzung oder aktive Lease
fail-closed fehl und markieren explizit, dass keine Rohmandatsdaten, keine
Secrets, keine Dashboard-Tokens, kein ATP-Schema-Apply, kein OCI-Gateway-Apply
und kein `notoclaw01` Connector-Start erfolgt sind.

Connector-Control-Routen akzeptieren in diesem Slice keinen Header allein. Der
lokale metadata-only Testpfad benötigt zusätzlich
`NAC_AGENT_CONTROL_ALLOW_METADATA_CONNECTOR_HEADER=true`; produktive
mTLS- oder Signed-Connector-Authentifizierung bleibt separat owner-gated.

## Nicht-Ziele

- keine produktive API-Gateway-Route,
- kein OCI API-Gateway-Apply,
- kein ATP-Schema-Apply,
- kein Start oder Neustart des `notoclaw01` Connectors,
- kein Zugriff auf Secrets oder Mandatsdaten.
