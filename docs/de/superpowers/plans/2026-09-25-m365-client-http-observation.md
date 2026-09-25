# Implementierungsplan: HTTP-Zusatzbeleg der Teams-Registerkarte

Datum: 25. September 2026. Führendes [Issue #748](https://github.com/notariat8/NaC/issues/748). Grundlage ist die [Spezifikation](../specs/2026-09-25-m365-client-http-observation-design.md).

Ziel ist eine eng begrenzte Clientbeobachtung, nicht die Behauptung einer behobenen Berechtigung oder eines empfangenen BFF-Requests. Der bestehende sechs Felder umfassende Beleg und sein historischer [Vertrag](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml) bleiben unverändert.

1. **Test zuerst:** Synthetische 401-/403-Antworten, fehlende SPFx-Kennung, unbekannter Fehler, parallele Ladevorgänge und explizite Download-Auslösung prüfen. Kein zusätzlicher Request und keine Inhalts- oder Identitätsfelder im Beleg. AC-748-HTTP-01/02/04.
2. **Client:** Nur der echte `/workbench-snapshot`-HTTP-Response erzeugt eine typisierte 401-/403-Klasse. Ein separates Modul bildet daraus und aus dem abgeschlossenen Basisbeleg einen maximal 1024 Byte großen, hashgebundenen Zusatzbeleg. Die UI bleibt neutral und bietet den zweiten Download nur bei zulässiger Beobachtung an. AC-748-HTTP-01/02/03.
3. **Vertrag und Prüfung:** Ein neuer Verification Contract und ein lokaler Validator akzeptieren ausschließlich die geschlossenen Felder, prüfen beide Hashes sowie den unveränderten Basisbeleg und lehnen Ersatz, Zusatzfelder und Klassenwechsel ab. Es erfolgt keine automatische Materialisierung für den produktiven #748-Preflight. AC-748-HTTP-03/04.
4. **Review und Gates:** Daten-/Logik-/UI-Grenzen, Datenschutz, DE/EN-Parität, Spec-Traceability und AI-SBOM-Entscheidung prüfen. Danach SPFx-Tests, visueller Nachweis, Graft Build/Check und Strict-Doctor. Erst nach gesondertem Release-Gate darf eine neue App-Version im Test-App-Catalog landen. Ein realer Teams-Test und Provider-Read bleiben getrennte Folgeschritte. AC-748-HTTP-05.

Abbruchkriterien: jede neue Login-/Token-/Providerhandlung, personenbezogene Ausgabe, nicht zuordenbarer HTTP-Status oder Änderung des historischen Belegs. Der Plan autorisiert keine Bereitstellung und keinen realen Diagnoselauf.
