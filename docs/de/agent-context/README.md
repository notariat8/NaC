# Agent-Readable Context

## Zweck

NaC trennt Agentenkontext in Schichten, damit Codex nicht mehr Kontext lädt,
sondern den richtigen Kontext zur richtigen Zeit.

Der maschinenlesbare Index steht in
[agent-context/index.json](../../../agent-context/index.json).
Akzeptierte fachliche Entscheidungen stehen in
[agent-context/decision-index.json](../../../agent-context/decision-index.json).
Kritische Invarianten stehen in
[agent-context/invariant-index.json](../../../agent-context/invariant-index.json).

## Schichten

| Schicht | Inhalt | Quelle |
| --- | --- | --- |
| Always-on | stabile Invarianten und Navigation | [AGENTS.md](../../../AGENTS.md), Policies, START_HERE |
| Scoped | verzeichnis- oder domänenspezifische Regeln | [docs/AGENTS.md](../../AGENTS.md), [workflows/contracts/AGENTS.md](../../../workflows/contracts/AGENTS.md), [.codex/agents/](../../../.codex/agents) |
| On-demand | Architektur, Entscheidungen, Guardrails, Runbooks | Architekturdocs, Technology Decision, Contracts, Verification Contracts |
| Runtime | aktueller Prompt, Toolausgaben, Logs, Diffs, Evidence | frische Befehlsausgaben und redigierte Laufartefakte |

## Agent-Readable Artifacts

NaC nutzt drei Artefaktarten:

- Maps: Systemform, Datenebene, Runtime- und Contract-Karten.
- History: Technologieentscheidungen, Architekturentscheidungen, Operating Models.
- Guardrails: Policies, CODEOWNERS, PR-Template, Quality Gate und Verification Contracts.

Diese Artefakte sind keine Ersatz-Wahrheit für Mandatsdaten oder notarielle
Entscheidungen. Sie erklären Architektur, Grenzen und Nachweise.

## Verification Contracts

Neue agentische Betriebsflächen sollen einen Verification Contract erhalten,
wenn sie wiederholt als Definition of Done diskutiert werden. Der erste Pilot
ist [codex-agent-context.verification.json](../../../workflows/verification-contracts/codex-agent-context.verification.json).
Der erste fachliche Domain-Pilot ist
[m365-matter-access-delegation.verification.json](../../../workflows/verification-contracts/m365-matter-access-delegation.verification.json).

Pflichtfelder:

- `applies_when.paths`
- `required_context`
- `checks`
- `invariants`
- `thresholds`
- `required_evidence`
- `pass_condition`
- `failure_behavior`
