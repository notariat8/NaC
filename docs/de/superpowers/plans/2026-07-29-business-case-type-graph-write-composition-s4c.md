# BusinessCaseType Graph Write Composition S4c Implementierungsplan

**Issue:** [#698](https://github.com/notariat8/NaC/issues/698)
**Spec:** [S4c Design](../specs/2026-07-29-business-case-type-graph-write-composition-s4c-design.md)
**Status:** Offline implementiert; Live-Write owner-gated

## Arbeitspakete

- [x] **WP1 – Verträge:** S4c-Domain- und Verification-Contract, Validator und
  Spec-Traceability für `AC-S4C-01` bis `AC-S4C-08`.
- [x] **WP2 – State:** SQLite-Adapter mit atomarem State-/Event-Commit,
  vollständiger Übergangsmatrix, Zwei-Verbindungs-CAS,
  Authorization-Run-Bindung und lokalem POSIX-Prozess-Restart-Envelop.
- [x] **WP3 – Transport:** Graph-v1.0-Adapter mit injiziertem Token- und
  HTTP-Port, Redirect-/Host-/Methoden-/Body-Grenzen und ohne Auto-Retry.
- [x] **WP4 – Komposition:** reine DI-Wurzel ohne Env-/Credential-/Live-Factory.
- [x] **WP5 – Offline-Smoke:** temporärer State und Fake-HTTP für alle fünf
  Operationen; Socket/DNS, externe Credential-Reads, Live-Graph und
  Tenant-Writes bleiben null, synthetische Token-Provider-Aufrufe werden
  separat ausgewiesen.
- [x] **WP6 – Crash-/Negativtests:** Restart-Fenster, Korruption, CAS-Konflikte,
  Busy/Timeout, Blockaden vor Transport ohne Token-Provider-Aufruf und
  Providerfehler ohne Rohdaten.
- [x] **WP7 – Doku/Context:** DE/EN-CLI, Architektur, Contract-Indizes,
  Agent-Context und Roadmap synchronisieren.
- [x] **WP8 – Abschluss:** Fokustests, Validator, Contracts, Compileall,
  Spec-Traceability, Sprachparität, Links, Strict-Gate und unabhängiger Review.

## Reihenfolge

1. Plan unabhängig prüfen und Findings schließen.
2. State und Transport in getrennten Write-Sets parallel implementieren.
3. Komposition, Smoke und CLI im Hauptlauf integrieren.
4. Vollständige `base...head`-Review durchführen.
5. Erst nach grüner lokaler und Remote-CI mergen.

Live-Factory, echte Credentials und Tenant-Write bleiben nach S4c separat
owner-gated.
