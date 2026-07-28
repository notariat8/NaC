# Microsoft-first, On-Prem-AI Umsetzungsplan

**Ziel:** Das Zielbild aus Issue #613 schrittweise in prüfbare Produktslices
überführen, ohne SharePoint zur Workflow-Engine oder Microsoft zu einer
Cloud-AI-Voraussetzung zu machen.

**Architektur:** Teams/SPFx/SharePoint/Entra/Graph bilden die Microsoft-Kante.
Python/FastAPI, deterministische Workflows, NeMo, PostgreSQL, Outbox/Broker und
WORM laufen on-prem. Temporal- und Baseline-Modus sind exklusive
Ausführungsmodi mit je einer technischen Wahrheit; WORM bleibt getrennt. Lokale
Sidecars bleiben nichtautoritativ.

**Delivery:** Jeder Slice besitzt ein führendes Issue, Contract/Verification,
Protected PR und bei Live-/Credential-/Deployment-Aktionen ein separates
Owner-Gate.

## Slice 1: S3/S4 Typvalidierung Und Graph-Read-Port

- [ ] S3 BusinessCaseType-Runtime offline abschließen.
- [ ] S4 Graph-v1.0-Adapter mit ETag, Paging, Redaction und fail-closed Read-Port bauen.
- [ ] Kein Graph SDK, SharePoint REST, PnP oder Graph Beta.
- [ ] Registry- und Viewer-Caches getrennt halten.

## Slice 2: Entra-Geschützter BFF

- [ ] FastAPI-BFF-Vertrag für OBO-/Benutzerkontext und App-Rollen spezifizieren.
- [ ] Rollen-, Akten-, Zweck- und Vertretungsbindung vor jeder Fachoperation erzwingen.
- [ ] SPFx/AadHttpClient-Request, DTO-Redaktion und Correlation-ID definieren.
- [ ] Provisioning- und Runtime-App-Identitäten getrennt halten.

## Slice 3: SPFx Read-only Workspace

Status 28. Juli 2026: Der Baseline-Live-One-Shot in `notary_team_01` war
erfolgreich; #632 stellte die begrenzten BFF-Bindungen bereit. Der aktuelle
vollständige 12-Step-Abschlusslauf und Live-Entra-Nachweis bleiben offen.

Nachweisbindung: [Issue #620](https://github.com/notariat8/NaC/issues/620),
[Verification Contract](../../../../workflows/contracts/m365-mvp-test-environment.verification.contract.json)
und [versionierte redigierte Live-Attestation](../../../../workflows/verification-contracts/m365-mvp-test-environment-live.verification.json).

- [x] Aktenstatus, Aufgaben und Fristen read-only anzeigen.
- [ ] Dokumentzeiger read-only anzeigen.
- [x] Vorhandenen `bpmn-js`-Viewer integrieren.
- [x] Teams-Tab und SharePoint-Webpart aus demselben Paket bereitstellen.
- [x] SPFx 1.22+/Heft, App Catalog, `.sppkg`, Teams-Publishing und frühes Admin-Gate festschreiben.
- [x] BPMN-Modellversion je Instanz binden.
- [ ] `bpmn-js` per Lazy Loading/Code Splitting laden.
- [x] Keine Geschäftslogik, Secrets, Workflow-Timer oder Agentic Runtime im Browser.

## Slice 4: Durable-Workflow-Spike

- [ ] Gemeinsames synthetisches Szenario und Messkriterien festschreiben.
- [ ] Temporal/Python-SDK self-hosted gegen Python/PostgreSQL-Baseline testen.
- [ ] Ausfall, Monats-Timer, Human Task, Versionierung, Backup/Restore,
  Idempotenz, HA, Monitoring und Betriebskosten messen.
- [ ] Entscheidung per separater ADR treffen; kein automatisches Temporal-Go.

## Slice 5: Technische Persistenz Und Audit

- [ ] Gemeinsames PostgreSQL-Schema für Domain-Read-Models, Outbox, Task-Metadaten, Projektionen und Synchronisation bauen.
- [ ] Im Temporal-Modus Temporal Service/Event History exklusiv für Ausführungszustand, Timer und Retries verwenden.
- [ ] Im Baseline-Modus PostgreSQL zusätzlich exklusiv für Workflow-Zustand, Timer, Leases und Retries verwenden.
- [ ] WORM-Nachweise in beiden Modi getrennt von der technischen Ausführungswahrheit halten.
- [ ] Broker-/Inbox-/Reconciliation-Vertrag ergänzen.
- [ ] WORM-Journal, Signatur-/Anchor-Evidence und Retention owner-gated auswählen.
- [ ] SharePoint-Projektionen aus zentralem Zustand reproduzierbar erzeugen.

## Slice 6: NeMo-Aktivitäten Und Personal Agent

- [ ] NeMo Agent Toolkit als einzige Agentic Runtime hinter klaren Activities nutzen.
- [ ] Graph-, Audit- und lokale Arbeitsplatz-MCP-Server zweckgebunden anbinden.
- [ ] Agentenantworten als Vorschläge behandeln; deterministische Gates entscheiden.
- [ ] Keine Mandatsdaten in Agent Memory oder GitHub-Evidence speichern.

## Slice 7: Lokale Sidecars Und Pilot

- [ ] Word/Track-Changes-, Scanner-, Kartenarbeitsplatz- und XNP-Adapter pilotieren.
- [ ] Kurzzeitcache verschlüsseln und lokale Outbox signieren.
- [ ] Offline-Konflikte zentral und auditierbar lösen.
- [ ] Vier First-Wave-Vorgänge und den 2+2-Pilot nach Betriebsabnahme starten.

## Validierung Je Slice

- fokussierte Unit-/Contract-/Security-Tests,
- passender Standalone-Validator,
- `python3 scripts/nac.py contracts verify`,
- `python3 scripts/nac.py doctor --profile strict`,
- unabhängiger `base...head`-Review,
- Live- oder Deployment-Evidence nur nach konkretem Owner-Gate.

