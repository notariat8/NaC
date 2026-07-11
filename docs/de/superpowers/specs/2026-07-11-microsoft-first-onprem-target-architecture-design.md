# Microsoft-first, On-Prem-AI Zielarchitektur

Status: Planungsentscheidung, Umsetzung in Folgeslices per Protected PR.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: microsoft-first-onprem-target-architecture
leading_issue: https://github.com/notariat8/NaC/issues/613
risk_gate: Architecture and Privacy
delivery_mode: Protected PR
acceptance_ids:
  - AC-613-01
  - AC-613-02
  - AC-613-03
  - AC-613-04
  - AC-613-05
  - AC-613-06
validation_commands:
  - python3 scripts/validate_microsoft_first_onprem_target_architecture.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/validate_gantt_progress.py
  - python3 scripts/nac.py doctor --profile strict
```

Plan:
[2026-07-11-microsoft-first-onprem-target-architecture.md](../plans/2026-07-11-microsoft-first-onprem-target-architecture.md)

## Problem

Die M365-MVP-Entscheidung ist final, aber UI, Agentic Runtime, langlebige
Workflow-Ausführung, M365-Adapter, Persistenz, lokaler Arbeitsplatz und Audit
dürfen nicht zu einer SharePoint-zentrierten Monolitharchitektur verschmelzen.
Das bereitgestellte PDF bietet eine geeignete Basis, setzt aber einzelne
Technologieoptionen breiter, als die NaC-Guardrails erlauben.

## Ziel

Die verbindliche Grenze lautet:

- Microsoft-first für Teams, SPFx, SharePoint, Entra und Graph REST v1.0/MCP.
- On-prem-first für Python/FastAPI, AI/Modelle, deterministische
  Workflow-Control-Plane, PostgreSQL, Outbox/Broker und WORM. Temporal- und
  Baseline-Modus sind exklusive Ausführungsmodi: Temporal History führt im
  Temporal-Modus Zustand/Timer/Retries, PostgreSQL im Baseline-Modus zusätzlich
  Zustand/Timer/Leases/Retries; WORM bleibt in beiden getrennt.
- NVIDIA NeMo Agent Toolkit als einziges Agentic Toolkit.
- SharePoint als Dokument-/Projektionsspeicher, nicht als technische
  Langzeit-Workflow-Wahrheit.
- WSL-Sidecars als nichtautoritative Arbeitsplatzadapter.
- Temporal nur als zeitbegrenzter, ergebnisoffener Durable-Workflow-Kandidat.

## Abnahme

- **AC-613-01:** Jede relevante PDF-Empfehlung ist als Übernehmen, Anpassen
  oder Verwerfen bewertet.
- **AC-613-02:** UI, BFF/Access, Workflow, Personal Agent, M365-Adapter,
  Persistenz und Audit sind getrennt.
- **AC-613-03:** Graph-v1.0-/MCP-only, NeMo-only-agentic und On-Prem-AI sind
  maschinenlesbare Guardrails.
- **AC-613-04:** SharePoint, PostgreSQL, Workflow-History, WORM, lokaler Cache
  und Agent Memory besitzen eindeutige Rollen; die autoritative technische
  Ausführungswahrheit ist pro gewähltem Modus exakt einmal festgelegt.
- **AC-613-05:** 90-/180-/365-Tage-Roadmap, kritischer Pfad, Repo-Ownership,
  Kosten und offene Owner-Entscheidungen sind dokumentiert.
- **AC-613-06:** DE/EN-Spiegel, Vertrag, Validator, Spec-Traceability,
  Dokumentlinks und Gantt-Prüfung bestehen.

## Grenzen

Dieser Slice ändert keine Runtime, keine Tenant-Konfiguration, keine Entra-App,
keine Credentials, kein Deployment und keine Live-Daten. Er entscheidet weder
Temporal noch einen WORM-Anbieter oder ein M365-Lizenzpaket endgültig.

