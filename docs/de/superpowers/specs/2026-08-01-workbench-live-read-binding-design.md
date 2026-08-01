# Workbench Live-Read-Bindung

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: workbench-live-read-binding
leading_issue: https://github.com/notariat8/NaC/issues/725
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-08-01-workbench-live-read-binding.md
review_gates:
  - Privacy
  - Workflow
  - External Service
acceptance_ids:
  - AC-725-01
  - AC-725-02
  - AC-725-03
  - AC-725-04
  - AC-725-05
  - AC-725-06
  - AC-725-07
  - AC-725-08
validation_commands:
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_workbench_endpoint
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_live_graph_ports tests.test_nac_bff_azure_function_host
  - cd spfx/nac-bpmn-viewer && npm run build
  - cd spfx/nac-bpmn-viewer && npm run workbench:capture
  - python3 scripts/nac.py frontend workbench-verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
```

## Ziel

Die generische Workbench-Foundation wird über einen eigenen, kurzlebigen
Read-Endpunkt des vorhandenen Azure-BFF an den SPFx-/Teams-Host gebunden. Die
Autorisierung, Rollenentscheidung, Projektion und Redaktionsattestierung bleiben
vollständig serverseitig. Der Browser erhält weder Graph- noch MCP-Zugriff.

## Akzeptanzkriterien

- **AC-725-01:** Der BFF erzwingt vor jedem Port-/Graph-Aufruf die exakte Synthetic-Allowlist für Tenant, `notary_team_01`, `NAC-SYN-MATTER-001` und den einzigen Query-Purpose. Tenant und Subject stammen ausschließlich aus validierten Entra-Token-Claims.
- **AC-725-02:** Assigned-/Deputy-Entscheidungen enthalten serverseitig gebundene Rolle, Decision-ID/-Version, Subject und eine maximal fünfminütige Lease. Alle authentisierten Deny- und ungültigen Scope-Varianten liefern exakt denselben identifikatorfreien `403`-Body und keine Actor-/Rollen-/Decision-Header; alle Antworten tragen `Cache-Control: no-store`.
- **AC-725-03:** Die Redaktionsattestation prüft den vollständigen projizierten Inhalt und bindet Policy, Classifier, Zeitpunkt und den normativ kanonisierten SHA-256 gemäß `workbench-live-read-binding.contract.json`; Golden-Wire- und Unicode-Fixtures müssen in Python und TypeScript denselben Digest ergeben.
- **AC-725-04:** Akte, Aufgaben und BPMN-Referenz stammen aus den vorhandenen autoritativen Ports. Nicht belegte Attention-, Decision- und Agent-Zustände bleiben leer und werden nicht aus Fristen oder Aufgaben erfunden.
- **AC-725-05:** Der SPFx-Client verwendet ausschließlich `AadHttpClient`, begrenzt auch chunked Antworten ohne `Content-Length` auf 131.072 Bytes und prüft Vertrag, Inhaltsbindung, das erwartete Subject aus dem authentisierten Seitenkontext, eine feste UI-Rollen-Allowlist sowie Workspace-, Matter- und Purpose-Bindung. Der Seitenkontext ist niemals Autorisierungsinput für den BFF.
- **AC-725-06:** Der React-Host lädt und erneuert den Snapshot vor Ablauf, verwirft alte Daten bei jedem Fehler und verwendet eine monotone Request-Generation, damit verspätete oder Abort-ignorierende Antworten keinen neueren Zustand überschreiben. Loading-, Deny- und Unavailable-Zustände sind deterministisch.
- **AC-725-07:** Die bestehende BPMN-Detailansicht und ihr v0.2-Endpunkt bleiben kompatibel; die Workbench ist die neue primäre read-only Arbeitsansicht.
- **AC-725-08:** Assigned, Deputy, Deny, falscher Tenant/Subject/Purpose/Workspace/Matter, nicht-synthetische Ziele, Redaktionsfehler, 128-KiB-/256-UTF-16-Grenzen, deny-only Capabilities, Ablauf, überlappende Refreshes, Unmount und Abort-ignorierende Transporte sind automatisiert getestet; Desktop-/Mobile-Evidence und Strict Gate bestehen.

## Servergrenze

Der neue Pfad lautet
`GET /v1/workspaces/{workspace_id}/matters/{matter_id}/workbench-snapshot`.
Er verwendet dieselbe validierte Entra-Abhängigkeit, den bestehenden
`Matter.Read`-Scope und den exakt einmal erlaubten `purpose`-Queryparameter. Ein eigener Domänenorchestrator prüft zuerst die feste Synthetic-Allowlist, entscheidet dann Zugriff, liest
danach feste Graph-Projektionen und das paketgebundene BPMN-Modell und baut erst
dann den Snapshot. Die serialisierten UTF-8-Bytes werden unverändert ausgeliefert.

Unauthorized-, falsche Scope- und Deny-Fälle sind nach Body und sichtbaren
Metadaten ununterscheidbar. Erfolgs-, Deny- und Fehlerantworten sind `no-store`.
Die Access-Entscheidung wird um die für die Workbench benötigte
Entscheidungsmetadaten erweitert. Zugeordnete Rollen werden aus der eindeutigen
Aktenzuordnung bestimmt. Eine Vertretungsentscheidung bindet Grant, Audit,
Rolle und den exakt allowlist-beschränkten synthetischen Grund
`Synthetische Urlaubsvertretung`; freie Begründungstexte werden vor jedem
Daten-Port abgewiesen. Ihre Laufzeit begrenzt zusätzlich die Snapshot-Lease.

## Daten- und Redaktionsgrenze

Der MVP zeigt ausschließlich die synthetische Testakte in `notary_team_01`.
Die primäre Datenschutzgrenze ist die feste Synthetic-Allowlist vor jedem
Graph-Read; der Redaktionsscan ist zusätzliche Tiefenverteidigung. Der
Redaktionsprüfer akzeptiert nur die bereits allowlist-projizierte Struktur,
scannt rekursiv nach verbotenen sensitiven Textformen und attestiert exakt den
kanonischen Projektionshash. Evidence enthält zunächst nur die
nicht-autoritative, hashgebundene BPMN-Modellreferenz.

## Browsergrenze

Der SPFx-Host übernimmt die erwartete Subject-ID aus dem authentisierten
SharePoint-Seitenkontext ausschließlich für den Konsistenzcheck. Die
Serverautorisierung verwendet nur validierte Token-Claims. Die Rolle muss in
einer fest kompilierten UI-Allowlist liegen; ihre fachliche Entscheidung bleibt
serverseitig. Jeder Load erhält eine monotone Generation. Nur die jüngste noch
aktive Generation darf nach vollständiger Bindungsprüfung Zustand setzen. Bei
Ablauf, Abbruch, Parse-, Hash-, Scope- oder Netzwerkfehlern wird der vorherige
Snapshot sofort entfernt.

## Normativer Vertrag

[workbench-live-read-binding.contract.json](../../../../workflows/contracts/workbench-live-read-binding.contract.json)
versioniert Route, Ziel-Allowlist, Claims-Autorität, Deny-/Cache-Semantik,
Wire-Limits und kanonische Hashbildung. Der Inhaltsdigest umfasst das gesamte
Top-Level-Objekt ohne `redaction`; Objektschlüssel werden rekursiv nach
Unicode-Codepunkten sortiert, Arrays behalten ihre Reihenfolge, Strings werden
nicht normalisiert und JSON wird ohne Whitespace als UTF-8 serialisiert. Das
Live-DTO enthält keine Zahlen, damit sprachübergreifende Number-Kanonisierung
nicht Teil dieses Vertrags ist.

## Delivery-Grenze

Der Slice endet mit geschütztem PR, Remote-CI und Deployment-Readiness. Ein
Live-Deploy erfolgt erst aus geprüftem `main` und ausschließlich in
`notary_team_01` mit bereits vorhandenen Berechtigungen.
