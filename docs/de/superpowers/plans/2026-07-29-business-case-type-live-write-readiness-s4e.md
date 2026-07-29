# BusinessCaseType Live-Write-Readiness S4e Plan

**Spec:** [S4e Design](../specs/2026-07-29-business-case-type-live-write-readiness-s4e-design.md)

1. Domain- und Verification-Contract für Issue #702 anlegen.
2. Typisiertes, rein lokales Readiness-Modell mit redigierten Hashbindungen
   implementieren.
3. Provisioning-, Write- und BFF-Principal sowie Permission-/Site-Rollen
   fail-closed prüfen.
4. Owner-, Graph-, Zertifikats- und Azure-Blob-WORM-Adapterbindungen prüfen.
5. Aktuellen Zustand ohne dedizierte Write-Identität als `BLOCKED` ausgeben.
6. Synthetische vollständige Bindung ausschließlich offline als
   `S4E_READY_OFFLINE` prüfen.
7. Zentrale `nac`-CLI, Validator, Negativtests und DE/EN-Dokumentation
   ergänzen.
8. Strict-Gate, unabhängigen Review, Protected PR, Remote-CI und Cleanup
   abschließen.
9. Erst danach eine gebündelte Owner-Freigabe für die fehlende
   Identity-/Adapter-Bindung und genau einen synthetischen Write vorbereiten.
