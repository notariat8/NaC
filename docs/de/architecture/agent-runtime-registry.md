# Agent-Runtime-Registry Und Sandbox-Leases

Status: Vertrags- und Schemaartefakt, kein produktiver Apply
Letzte inhaltliche Anpassung: 2026-07-02

## Zweck

Diese Seite konkretisiert die Variante-C-Architektur für
`agent.notariat8.de`. OCI bleibt die öffentliche Identitäts-, Policy- und
Routing-Schicht. `notoclaw01` bleibt Zielruntime und verbindet sich ausgehend
über mTLS oder WebSocket/HTTPS. Die rohe NemoClaw-/OpenClaw-Oberfläche wird
nicht direkt veröffentlicht.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/agent-runtime-registry.contract.json](../../../workflows/contracts/agent-runtime-registry.contract.json).
Das dazugehörige DDL-Artefakt steht in
[deploy/database/atp-agent-runtime-registry-schema.sql](../../../deploy/database/atp-agent-runtime-registry-schema.sql).
Beides ist contract-first und darf ohne eigenes Owner-Apply-Gate nicht auf ATP
angewendet werden.

## Laufzeitfluss

1. Der Browser erreicht `agent.notariat8.de`.
2. OCI Identity Domain authentifiziert den Benutzer.
3. API Gateway oder BFF prüft Session, Tenant, Rolle und Zweck.
4. ATP löst Agent, Endpoint, Sandbox-Bindung und aktive Lease auf.
5. `notoclaw01` nimmt nur geprüfte Aufträge über den outbound Connector an.
6. NemoClaw/OpenClaw hält die lokale Sandbox; produktive Mandatsdaten bleiben
   bis zu einem privaten Betriebsrahmen gesperrt.

SSH bleibt Betriebs- und Diagnoseweg. Produktiver User-Traffic läuft nicht über
SSH und nicht direkt zu Brev oder zur rohen OpenClaw-UI.

## ATP-Metadaten

Das Schemaartefakt definiert nur sichere Metadatenanker:

| Tabelle | Zweck |
| --- | --- |
| `nac_agent_registry` | freigegebene Agent-Typen, Runtime-Klasse und Git-Vertragsreferenz |
| `nac_agent_endpoints` | outbound Connector-Endpunkte und redigierter Health-Status |
| `nac_sandbox_bindings` | Tenant-, Benutzer-, Rollen-, optionaler Vorgangs- und Sandbox-Bezug |
| `nac_sandbox_leases` | aktive, abgelaufene oder widerrufene Sandbox-Lease |
| `nac_agent_session_bindings` | serverseitige Bindung zwischen Sitzung und Sandbox-Lease |

Die Tabellen dürfen keine Tokens, Claims-Rohdaten, Secrets, Private Keys,
Dashboard-Tokens, Umgebungsdumps oder unredigierten Mandatsinhalte enthalten.

## Isolierung

Die Mindestisolierung ist `tenant + user`. Sobald Vorgangs- oder
Rollen-Kontext geladen wird, ist `tenant + user + vorgang + rolle` die
bevorzugte Isolierung. Eine Sandbox darf nicht von mehreren unabhängigen
Benutzern geteilt werden. Wiederverwendung ist nur zulässig, wenn ATP eine
aktive, nicht widerrufene und nicht abgelaufene Lease bestätigt.

## Owner-Gates

Separat freizugeben sind:

- produktiver ATP-Schema-Apply,
- Connector-Credentials und mTLS-Material,
- produktiver Connector-Start,
- Sandbox-Auto-Start-Policy,
- privater Payload-Zugriff.

Diese Entscheidung startet keinen Connector, verändert kein OCI Gateway und
wendet kein Schema an.
