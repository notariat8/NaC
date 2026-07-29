# Umsetzungsplan S4g Produktionskanten-Komposition

1. Issue #708, DE/EN-Specs, DE/EN-Pläne und AC-S4G-01 bis AC-S4G-08
   miteinander binden.
2. Tatsächliche S4d-, S4f- und S6b-Vertragsdateien sowie die Repository-
   Implementierungen für Identity-Inspector-Implementierung und Snapshot-Attestation getrennt, Owner-Verifier, Writer-Token-
   Factory, Graph- und Azure-WORM-REST-Transport domänensepariert hashen; das
   WORM-Ziel explizit als offline-unconfigured binden.
3. Provisioner, Writer und BFF über getrennte, jeweils paarweise eindeutige und
   über beide vollständigen Namensräume disjunkte Entra-`app_id`- und
   `service_principal_object_id`-Werte prüfen; Writer auf
   `Sites.Selected/write` und BFF auf `Sites.Selected/read` begrenzen.
4. Mutation-State und Evidence-Staging auf getrennte lokale SQLite-Pfade
   binden und gleiche, gesyncte, remote, unbekannte, symlinkbasierte oder
   schwach geschützte oder mehrfach verlinkte Dateien geschlossen abweisen.
5. Den Azure-Blob-WORM-REST-Transport mit injizierten Token-/HTTP-Ports,
   festen Hosts und API-Versionen, `GET`/`PUT`, begrenzten Größen,
   create-only-Idempotenz und exaktem Versions-Readback offline prüfen; Lock-
   und Delete-Operationen ausschließen.
6. PostgreSQL-Promotion/Ack/Retention/Cleanup, Brokerentscheidung,
   Signaturankerentscheidung, durable Reconciliation, irreversiblen WORM-Lock
   und owner-gated Live-Aktivierung als zwingende Blocker verifizieren.
7. Statusausgabe und redigierte Evidence auf
   `S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE` und
   `BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION` begrenzen;
   Runtime-Konstruktion und Credential-Lesen vor den zentralen Gates
   verhindern.
8. Domain-/Verification-Contract, Validator und negative Contract-Tests
   ergänzen und fokussierte Tests, Traceability-, Sprach-, Link-, Contract-
   und Strict-Gates ausführen.
9. Die vollständige `base...head`-Diff unabhängig prüfen, P1/P2-Befunde
   beheben und ausschließlich über den geschützten PR-Pfad liefern.
10. Keine Tenant-, Entra-, Graph-, Azure-, Credential-, Permission-,
    Infrastruktur- oder WORM-Lock-Aktion ausführen.
