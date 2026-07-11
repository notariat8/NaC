# BusinessCaseType Runtime S3 Implementierungsplan

**Spec:** [BusinessCaseType Runtime S3 Design](../specs/2026-07-11-business-case-type-runtime-s3-design.md)
**Leading Issue:** [GitHub #612](https://github.com/notariat8/NaC/issues/612)
**Delivery Mode:** Protected PR
**Risk Gate:** Privacy

## Ziel

Die viewer-unabhängige `BusinessCaseTypeId`-Gültigkeitsprüfung als
deterministische Python-Runtime mit Fixture-Transport, getrennten Caches,
zentraler CLI und ausführbarem Verification Contract umsetzen. Der Plan endet
vor jeder Graph-, Entra-, Credential- oder Tenant-Kante.

## Acceptance-Mapping zu Issue #612

- **AC-S3-01:** ID-/Aliasauflösung, Varianten- und Lifecycle-Blocker.
- **AC-S3-02:** Registry-Kardinalität, Zeilenform, Version und Status.
- **AC-S3-03:** Registry-TTLs und site-weite Invalidierung.
- **AC-S3-04:** strikte Viewer-Isolation von der Typgültigkeit.
- **AC-S3-05:** ETag/Not-Modified und Datenminimierung.
- **AC-S3-06:** zentrale CLI, Doku, Validator, Strict-Gate und Review.

## Arbeitspakete

- [ ] **WP1 – Governance und Traceability:** Spec, Plan, ADR-Verweise,
  Agent-Context und Roadmap mit `AC-S3-01` bis `AC-S3-06` verbinden.
- [ ] **WP2 – Snapshot und Katalog:** inhaltsbasierte `CatalogVersion`,
  expliziten Runtime-Lifecycle und fail-closed Alias-/ID-Invarianten umsetzen.
- [ ] **WP3 – Read Port und Registry-Prüfung:** read-only Protocol,
  paginierte Fixture-Ergebnisse und vollständige Zeilenvalidierung umsetzen.
- [ ] **WP4 – Cache:** Registry-Cache mit 300/900/30-Sekunden-Grenzen,
  ETag, Generation, Single Flight und monotone Uhr sowie separaten Viewer-Cache
  umsetzen.
- [ ] **WP5 – API und CLI:** `business_case_type_get` und
  `nac kg business-case-type-get` ausschließlich mit Fixture-Transport
  bereitstellen.
- [ ] **WP6 – Contracts und Verification:** Domain Contract, Verification
  Contract, Standalone-Validator, `nac contracts verify` und Strict-Gate
  integrieren.
- [ ] **WP7 – Tests:** positive und negative Grenzfälle für IDs, Aliase,
  Paging, Registry-Shape, TTL-Grenzen, 304, Generationen, Parallelität,
  Datenminimierung und Viewer-Isolation abdecken.
- [ ] **WP8 – Abschluss:** vollständige Diff prüfen, unabhängigen Review
  durchführen, Findings beheben und Protected PR mit grünen Remote-Checks
  bereitstellen.

## Validierungsreihenfolge

1. fokussierte Runtime-, Cache-, Contract-, CLI- und Regressionstests,
2. S3-, Inventar- und Ontologie-Validatoren,
3. CLI-Hilfe und `nac contracts verify`,
4. Spec-Traceability, Sprachparität, Links und Gantt,
5. `python3 scripts/nac.py doctor --profile strict`,
6. `git diff --check`, vollständige `base...head`-Review und Remote-CI.

Die konkreten Befehle sind im Manifest der Spec bindend aufgeführt.

## Abschlussregel

Der Board- und ADR-Status bleibt während der Umsetzung `in progress`. S3 wird
erst nach erfülltem `AC-S3-06`, bestandenem Strict-Gate, unabhängigem Review
und grünen Protected-PR-Checks als implementiert markiert. S4 ist ein eigener
Folgescope für Microsoft Graph REST v1.0 und darf S3 nicht stillschweigend
erweitern.
