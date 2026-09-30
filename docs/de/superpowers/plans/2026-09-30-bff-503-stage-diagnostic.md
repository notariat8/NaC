# Implementierungsplan: BFF-503-Stufenbeleg

Führendes Issue: [#762](https://github.com/notariat8/NaC/issues/762). Grundlage: [DE-Spezifikation](../specs/2026-09-30-bff-503-stage-diagnostic-design.md).

1. Mit synthetischen Negativtests die unveränderte neutrale Antwort, feste Stufen, Nichtausgabe sensibler Details und die HTTP-Grenze nachweisen (AC-762-01 bis AC-762-03).
2. Im Workbench-Endpunkt die 503-Ursprünge trennen; im HTTP-Adapter Timeout und unerwartete Grenzfehler erfassen. Nur der konfigurierte BFF erhält den festwertigen internen Log-Sink.
3. Datenschutz-, Providergrenzen- und Testreview; Befunde korrigieren. Fokussierte Tests, Graft und Strict-Doctor ausführen. Als geschützten Draft-PR ausliefern; kein Deployment und keine Live-Ursachenbehauptung.

Nachgelagert, separat zu autorisieren: kontrollierter BFF-Release, genau ein Teams-Test und korrelierter Serverbefund; danach nur den belegten Fehler reparieren.
