# BusinessCaseType Live-Write-Grenze S4d Plan

**Spec:** [S4d Design](../specs/2026-07-29-business-case-type-live-write-boundary-s4d-design.md)

1. Domain- und Verification-Contract mit `S4D_READY_OFFLINE` sowie
   Standalone-Validator anlegen.
2. Typisierte, hashgebundene Owner-Attestation, zirkelfreie kanonische
   Planbindung, `owner-approval-v1`-Authorization und Neuaufbau/Revalidation
   des finalen Plans implementieren.
3. Getrennte read-only Identity-Inspection- und Business-Write-Token-Factory-
   Ports implementieren.
4. S6-Ereignismodell versioniert um die fünf S4b-Operationen ergänzen.
5. Zusammengesetzten Evidence-Hook implementieren: lokaler Intent vor
   kanonischem Intent, WORM-Finalisierung vor lokaler Closure.
6. S4d-Boundary und synthetische Offline-Factory für alle fünf Operationen
   bauen; keine Live-Factory.
7. Gate-, Crash-, Replay-, Redaction-, Contract- und CLI-Tests ergänzen.
8. Doku-, Context-, Roadmap- und Quality-Gate-Indizes aktualisieren.
9. Unit-/Contract-/Strict-Gates, unabhängigen Review und Remote-CI
   vollständig ausführen.
10. Protected PR mergen und Branch/Worktree aufräumen.
11. Danach genau eine gebündelte Freigabe für produktive Adapterbindung,
    gebundenen synthetischen Write in `notary_team_01`, Readback, WORM-
    Evidence und Idempotenz vorbereiten.

## Review-Hardening

12. Approval-Kandidat und unabhängigen Owner-Verifier-Port trennen.
13. Finale Plan-Revalidation vor alle Owner-, Identity- und Credential-Zugriffe
    ziehen.
14. Identity-Inspection mit Quelle, Beobachtungszeit, Principal- und
    Approval-Bindung attestieren.
15. S6-v0.2-Kette an konkrete Mutation und Provider-Readback-Digest binden.
16. Fremdketten-, S6-Intent-, Plan-, Owner- und Inspection-Negativtests
    ausführen, bevor der PR mergefähig ist.

