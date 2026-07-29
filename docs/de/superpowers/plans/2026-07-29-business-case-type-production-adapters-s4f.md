# Umsetzungsplan S4f Produktionsadapter

1. Issue #704, Spec, Plan und AC-S4F-01 bis AC-S4F-07 binden.
2. GitHub-Owner-Verifier, Zertifikatsfactory und Graph-HTTP-Port implementieren.
3. Restartfeste lokale SQLite-Evidence-Staging-Outbox ohne Abschlussrecht
   implementieren.
4. S4f-Kompositionsstatus und CLI ergänzen; folgende Grenzen einzeln als Blocker
   verifizieren: zentrale PostgreSQL-Outbox mit Promotion, Ack, Retention und lokalem Cleanup,
   Brokerprodukt,
   Signatur-/Anchor-Verfahren, provider-seitiger Identity- und Site-Grant-Readback,
   Azure-WORM-REST-Transport, irreversibler WORM-Policy-Lock, dedizierte
   Entra-Writer-Identität mit Site-Grant und owner-gated Live-Aktivierung.
5. Domain-/Verification-Contract, Validator, Tests und Agent-Context ergänzen.
6. Fokussierte Tests, Contract-Gates und Strict-Gate ausführen.
7. Unabhängigen base...head Review durchführen und P1/P2-Befunde beheben.
8. Protected PR erstellen, Remote-CI prüfen, mergen und Branch aufräumen.
