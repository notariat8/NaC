# Operations

Dieser Ordner bündelt Betriebsmodell, Upstream-Sync, Version-Binding,
Arbeitsmodell und Repo-Konsolidierung.

Die Command-Ausführung in diesem Ordner folgt
[policies/codex-command-rules-policy.json](../../../policies/codex-command-rules-policy.json)
und [.codex/rules/default.rules](../../../.codex/rules/default.rules):
GREEN ist read-only/lokale Validierung, YELLOW ist Prompt- oder owner-gated
Batch-Arbeit, und RED ist für destruktive, Secret-, Credential-, Deploy- oder
produktive Apply-Kommandos blockiert.

## Dokumente

- [fork-and-release-operating-model.md](fork-and-release-operating-model.md): Unternehmensbetrieb mit zentralem
  Upstream.
- [release-sync-playbook.md](release-sync-playbook.md): verbindlicher Upstream-Sync-Ablauf.
- [release-checklist.md](release-checklist.md): Freigabeformular für Tag, Release, Audit-Artefakte
  und Rollout-Entscheidung versionierter Prozesspakete.
- [parallelbetrieb-version-binding.md](parallelbetrieb-version-binding.md): Mischbetrieb alt/neu mit
  Version-Binding.
- [agile-cadence.md](agile-cadence.md): Arbeitsmethode und Team-Cadence.
- [codex-time-ledger.md](codex-time-ledger.md): lokales Zeitprotokoll für Codex-Arbeitsblöcke,
  Toolzeit, Freigaben und wiederkehrende Wartezeiten.
- [codex-worktree-operating-model.md](codex-worktree-operating-model.md): read-only
  Worktree-Hygiene-Audit, Namensschema und owner-gated Cleanup-Grenzen.
- [codex-memory-hooks-operating-model.md](codex-memory-hooks-operating-model.md): Memory-Quellen,
  Hook-Grenzen und progressive Context-Layer ohne Live-Hook-Aktivierung.
- [codex-command-rules-operating-model.md](codex-command-rules-operating-model.md):
  GREEN/YELLOW/RED-Command-Governance, repo-lokale `.rules` und owner-gated
  Command-Grenzen.
- [m365-mcp-batch-approval.md](m365-mcp-batch-approval.md): Batch-Freigabe für
  vorbereitete M365-MCP-PRs und getrennt freizugebende Live-Smokes.
- [agent-memory-search-qmd.md](agent-memory-search-qmd.md): optionaler lokaler qmd-Suchindex
  für Agent-Regeln, Release-Memory und Runbooks ohne Secrets oder Mandatsdaten.
- [oci-runtime.md](oci-runtime.md): archivierter Legacy-Runtime-Vertrag für
  OCI, ATP und OCI-Release-Pfade; nicht Teil des aktiven M365-MVP.
- [ponytail-skill-only-smoke.md](ponytail-skill-only-smoke.md): Owner-gated
  ausgeführter Ponytail Skill-Only Smoke für `notoclaw01` mit
  Target-Control-Evidence und ohne Installation, Hooks oder Runtime-Aktivierung.
- [nac-runtime-smoke.md](nac-runtime-smoke.md): vorbereiteter Owner-gated
  Runtime-Smoke für `notoclaw01-host` mit read-only NemoClaw-/OpenClaw-Status,
  redigierter Evidence und ohne Installation, Onboarding, Rebuild oder
  Dashboard-Token-Erfassung.
- [repository-consolidation.md](repository-consolidation.md): migrierte, offene und stillzulegende
  Einzelrepos.
- [single-repo-refactor-plan.md](single-repo-refactor-plan.md): Zielstruktur und Migration in einem Repo.
- [../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md](../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md): GitHub-first Arbeitssteuerung für agentische Issues, PRs und Projects.
