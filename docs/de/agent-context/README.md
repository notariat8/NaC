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

NaC nutzt mehrere agentenlesbare Artefaktarten:

- Maps: Systemform, Datenebene, Runtime- und Contract-Karten.
- History: Technologieentscheidungen, Architekturentscheidungen, Operating Models.
- Guardrails: Policies, CODEOWNERS, PR-Template, Quality Gate und Verification Contracts.
- Worktree operating model: Branch-Isolation, read-only Hygiene-Audit und
  owner-gated Cleanup-Grenzen.
- Subagent operating gate: Subagent-Registry, Einsatzschwellen und Runtime-Limits.
- Memory/hooks: lokale Recall- und Hook-Grenzen ohne Live-Hook-Aktivierung.
- Command rules: GREEN/YELLOW/RED-Shell-Command-Profile und repo-lokale
  `.rules`-Guardrails für wiederkehrende Command-Entscheidungen.
- 5h batch run envelope: langer autonomer Offline-Batch mit Worktree-
  Isolation, Subagent-Plan, Runtime-Checkpoints und gebündelten Owner-Gates.

Diese Artefakte sind keine Ersatz-Wahrheit für Mandatsdaten oder notarielle
Entscheidungen. Sie erklären Architektur, Grenzen und Nachweise.

## Verification Contracts

Neue agentische Betriebsflächen sollen einen Verification Contract erhalten,
wenn sie wiederholt als Definition of Done diskutiert werden. Der erste Pilot
ist [codex-agent-context.verification.json](../../../workflows/verification-contracts/codex-agent-context.verification.json).
Der erste fachliche Domain-Pilot ist
[m365-matter-access-delegation.verification.json](../../../workflows/verification-contracts/m365-matter-access-delegation.verification.json).
Command-Permission-Profile werden durch
[codex-command-rules.verification.json](../../../workflows/verification-contracts/codex-command-rules.verification.json)
verifiziert.
Der kompakte Querverweisnachweis für Worktree-, Subagent-, Memory/Hooks-,
Command-Rules- und 5h-Batch-Gates ist
[codex-agent-context-index-audit.verification.json](../../../workflows/verification-contracts/codex-agent-context-index-audit.verification.json).
Lange autonome Batches werden durch
[codex-5h-batch-run-envelope.verification.json](../../../workflows/verification-contracts/codex-5h-batch-run-envelope.verification.json)
verifiziert.

Pflichtfelder:

- `applies_when.paths`
- `required_context`
- `checks`
- `invariants`
- `thresholds`
- `required_evidence`
- `pass_condition`
- `failure_behavior`
