# Teams-MVP-Ziel und gestufter Diagnosepfad

Status: Design freigegeben; Spezifikation zur Review; keine Implementierung oder Live-Freigabe

Datum: 26. September 2026

Führendes Issue: [#620](https://github.com/notariat8/NaC/issues/620). Verwandte, eigenständig begrenzte Arbeiten: [#739](https://github.com/notariat8/NaC/issues/739), [#746](https://github.com/notariat8/NaC/issues/746), [#748](https://github.com/notariat8/NaC/issues/748) und [#756](https://github.com/notariat8/NaC/issues/756).

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-teams-mvp-simplification
leading_issue: https://github.com/notariat8/NaC/issues/620
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Privacy
  - Policy
  - Human Approval
acceptance_ids:
  - AC-620-SIM-01
  - AC-620-SIM-02
  - AC-620-SIM-03
  - AC-620-SIM-04
  - AC-620-SIM-05
  - AC-620-SIM-06
validation_commands:
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/nac.py doctor --profile strict
```

## Zweck und überprüfbares Ziel

Der kurzfristige NaC-MVP soll genau einen synthetischen notariellen Vorgang im Testarbeitsraum `notary_team_01` über die Teams-App „NaC Vorgangsansicht“ anzeigen, einschließlich BPMN-Bezug, Status, Aufgaben und UTC-Frist. Eine zugeordnete Identität oder eine gültig vertretene Identität erhält nur die redigierte, zweckgebundene BFF-Projektion; eine unberechtigte Identität oder manipulierte Workspace-, Vorgangs-, Zweck- oder Filterwerte erhalten keine Vorgangsdaten. Der Nachweis umfasst die tatsächlich angezeigte Teams-Oberfläche, die BFF-Zugriffsentscheidung und redigierte Evidence. Das ist Testumgebung-Akzeptanz, keine Freigabe für echte Mandate oder produktiven Notariatsbetrieb. Die bestehenden [MVP-Akzeptanzkriterien](2026-07-13-m365-mvp-test-environment-design.md) bleiben maßgeblich; die sechs folgenden Vereinfachungskriterien ergänzen sie nur.

Die lokal geprüften Clientbelege vom 25. September 2026 haben SHA-256 `ed89c1171a02fc79c80314512375c7db84be2fce1528c7ba6596d7c24d805e40` und `daf4cc55f0f95f38b118155d8bef33d36a0a68809848ba96b049f1f129b80bda`. Sie belegen `spfx_subject_available=true`, `ui_state=no_access` und eine beim Client eingetroffene HTTP-403-Antwort für den gebundenen Workbench-GET. Sie belegen **nicht**, ob die Azure Function den Request annahm, ob der Python-BFF den 403 erzeugte oder welche Zugriffsregel griff. Die Belegdateien und reale Identitäts- und Tenantwerte bleiben repository-extern.

## Scope und Grenzen

Eine ausschließlich lesende repo-weite Bestandsaufnahme ordnet Produktziel, Architektur, aktive und historische Diagnosewege, Statusangaben und gemeinsame Prüfungen ein. Für die erste Änderungsrunde sind nur diese Teams-MVP-Flächen vorgesehen: diese DE/EN-Spezifikation und ihr späterer DE/EN-Plan, [DE/EN-Current-State-Status](../../m365-current-state-access-diagnostic.md) und [BUILD_NOW](../../../../roadmap/BUILD_NOW.md). Wenn ein gemeinsamer Validator, Verification Contract oder ein anderes Dokument tatsächlich geändert werden muss, wird dessen exakter Dateiscope zuerst separat geprüft und freigegeben. Andere NaC-Subsysteme bleiben unverändert. Veröffentlichten Code, Commits, Belege oder Issues löscht oder schreibt dieser Entwurf nicht um.

Die [#739-Provenienzgrenze](2026-09-15-m365-bff-failed-partial-safe-completion-design.md) bleibt terminal; aus verlorenen Artefakten entsteht keine Freigabe. Die #632-Live-Aktivierung bleibt eine getrennte Entscheidung. Ein grüner lokaler Test, ein Client-403 oder eine Owner-Designfreigabe ist keine Provider-, Deployment- oder Credentialfreigabe.

## Bewertete Ansätze

1. **Vollständigen #748-Read-Driver zuerst ausliefern:** breite Current-State-Prüfung und starke Paketbindung, aber zusätzlicher Binary-, SBOM-, Lizenz-, Authentifizierungs- und Freigabeaufwand vor dem ersten 403-Ursachenhinweis. Für diesen Vorfall nicht als Standardvoraussetzung gewählt.
2. **Vorhandene Telemetrie zuerst, #756 nur als begründeter Folgeweg — gewählt:** Die bestehenden Clientbelege legen das Fenster fest. Zuerst wird rein lokal geprüft, ob ein bereits vorhandenes, exakt gebundenes Request-Log-Ziel und eine nachweisbar korrelierbare Abfrage überhaupt verfügbar sind. Ein späterer einzelner Provider-Read bleibt separat freigabepflichtig. Nur wenn historische Telemetrie die notwendige Unterscheidung nicht liefern kann, wird der inaktive interne #756-Eintrag als Grundlage einer separat freigegebenen neuen Reproduktion betrachtet. Das vermeidet einen neuen Releasepfad ohne nachgewiesenen Erkenntnisgewinn.
3. **#756 sofort aktivieren und den Fehler neu erzeugen:** kann den internen 403-Zweig sichtbar machen, benötigt aber BFF-Deployment und eine neue Teams-Reproduktion; die historische Beobachtung wird dadurch nicht rückwirkend erklärt. Nicht als erster Schritt gewählt.

## Eine Entscheidungsfolge statt paralleler Gate-Ketten

1. **Bekannte Client-Evidence:** Beleg-Hashes, Bindung, geschlossenes Fenster und neutrale Felder lokal prüfen. `spfx_subject_available=true` schließt für diese Beobachtung nur den fehlenden SPFx-Subject-Zweig aus. HTTP 403 bleibt `CLIENT_403_ORIGIN_UNKNOWN`; keine BFF-Ursache wird geraten.
2. **Telemetrie-Eignung:** Der [Request-Log-Ressourcenvertrag](../../../../workflows/contracts/m365-current-state-read-driver-resources.contract.json) und geschützte, repository-externe Nachweise müssen Function-Ziel, Application-Insights-App-ID, Query-Projektion und die tatsächliche Erfassung der Korrelationsbindung belegen. Der [historische Triage-Entwurf](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/docs/de/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md) ist Referenz, kein bereits freigegebener Providerlauf. Im Ausgangsstand `862c87e1` steht die Projektion noch auf `projection_proven=false`; der #748-Produktionsport blockiert ohne No-Refresh-Fähigkeit und der Lizenzkatalog ist nicht freigegeben. Deshalb beginnt dieser Pfad nur mit einer Offline-Eignungsprüfung, nicht mit einem ausführbaren Microsoft-Read. Ohne Ziel-, Query- oder Korrelationsbeleg folgt ein präziser `BLOCKED`-Grund; ein fehlender Logtreffer gilt nicht als „kein BFF-Request“.
3. **Späterer Read-only-Abgleich:** Erst nach eigenem, genau begrenztem Vertrag und exakt gebundener Freigabe dürfte eine einzelne geschlossene, redigierte Telemetrieabfrage mit einem zulässigen Authentifizierungskanal laufen. Ein eindeutiger Treffer könnte Function-Telemetrie-Ingress belegen, nicht automatisch den Python-Zweig oder den fachlichen Ablehnungsgrund. Diese einmalige Triage ersetzt niemals die formale #748-Diagnose mit zwei unabhängigen, identischen Snapshots. Kein Login, Token-Refresh, Redirect, Retry oder Write wird aus diesem Design autorisiert.
4. **BFF-interne Unterscheidung bei Bedarf:** Ist Telemetrie nicht eindeutig oder reicht sie nicht zur Ursache, wird die Notwendigkeit des [inaktiven #756-Eintrags auf einem getrennten, noch nicht gemergten Branch](https://github.com/notariat8/NaC/blob/e80c1a6385ecfaddb9d09dfd4e6bf427b184737c/docs/de/superpowers/specs/2026-09-26-m365-bff-403-diagnostic-event-design.md) begründet. Deployment, neue Reproduktion und Auslesen geschützter Diagnose-Evidence benötigen jeweils ihre eigene Scope- und Freigabeprüfung. Der alte Clientbeleg wird nicht als neuer BFF-Beleg umgedeutet.
5. **Fix erst nach Ursache:** Ein späterer Fix richtet sich nur gegen den nachgewiesenen Fehlerpfad und erhält Entra-, Rollen-, Akten-, Zweck-, Datenschutz- und Providergrenzen. Danach werden der berechtigte Positivfall und die unberechtigten Negativfälle in Teams erneut geprüft.

## Vereinfachung der Repository-Arbeit

Die bestehende [Current-State-Diagnosedokumentation](../../m365-current-state-access-diagnostic.md) soll die datierte operative Statusübersicht führen; historische Specs bleiben historische Verträge. Der [Build-Now-Überblick](../../../../roadmap/BUILD_NOW.md) verweist knapp auf diesen Status, statt widersprüchliche Live-Readiness zu behaupten. Jede aktive oder zurückgestellte Diagnosekante wird mit Erkenntnisziel, vorhandener Evidence, konkretem Blocker und nächstem erlaubtem Schritt gekennzeichnet.

Für Änderungen gelten zuerst fokussierte synthetische Tests und der betroffene Validator als Vorprüfung. Der vollständige Strict-Doctor läuft einmal auf dem finalen lokalen Stand; bereits enthaltene Validatoren werden für den Abschluss nicht nochmals separat gezählt. Teilprüfungen werden nur zur Fehleranalyse wiederholt. Ein Validator, dessen Ergebnis als Pflichtgate behauptet wird, muss tatsächlich in diesem Gate registriert sein. Skip-Zahlen und nicht getestete Live-Grenzen werden ausgewiesen. Das spart redundante Läufe, schwächt aber keinen verpflichtenden Check ab.

## Risiken und Akzeptanzkriterien

- **AC-620-SIM-01:** Eine DE/EN-Bestandskarte ordnet die NaC-Hauptbereiche mit Zielbeitrag, Abhängigkeit und Entscheidung `beibehalten`, `vereinfachen` oder `zurückstellen` ein. Ziel und Testakzeptanz unterscheiden sichtbar zwischen Teams-MVP, öffentlichem Referenzrepo und produktivem Notariatsbetrieb.
- **AC-620-SIM-02:** Die beiden Clientbelege werden nur mit den genannten Hashes und neutralen Feldern referenziert; 403-Ursprung und konkrete Berechtigung bleiben bis zum Beweis `UNKNOWN`.
- **AC-620-SIM-03:** #748-Read-Driver, historische Request-Log-Triage und #756-Eintrag sind in einer Entscheidungsfolge als aktiv, bedingt oder zurückgestellt eingeordnet; keine veröffentlichte Historie wird umgeschrieben.
- **AC-620-SIM-04:** Ein realer Read oder eine neue Reproduktion blockiert bei fehlender Ziel-, Query-, Korrelations-, Datenschutz-, Authentifizierungs- oder Owner-Bindung vor dem nächsten Zugriff; dieses Design selbst führt beides nicht aus.
- **AC-620-SIM-05:** Operative Statusangaben in den benannten DE/EN-Current-State-Dokumenten und `BUILD_NOW` widersprechen dem belegten Clientstand nicht. Gemeinsam genutzte Prüfungen werden einmal auf dem finalen Stand ausgeführt; eine nicht integrierte Validatorprüfung wird nicht als bestanden behauptet. Vertrags- oder Gate-Änderungen bedürfen einer gesonderten Scope-Entscheidung.
- **AC-620-SIM-06:** Diese SIM-Kriterien ersetzen weder AC-620-01 bis AC-620-07 noch den gebundenen zwölfstufigen Live-Abschluss. Ein späterer Teams-Abschluss benötigt weiterhin den berechtigten Positiv- und Vertretungsfall, BPMN-/Aufgaben-/Fristdarstellung, die vollständige Manipulations- und Denial-Matrix, site-gebundene Auslieferung, Graph-Write/Readback/Cleanup, exakte #632-Bindungen und redigierte UI-/BFF-Evidence. Ein inaktiver Diagnoseeintrag oder grüne CI allein zählt nicht als Abschluss.

Nichtziel dieser Spezifikation sind Login, Token-Refresh, Providerzugriff, Deployment, BFF- oder SPFx-Änderung, Berechtigungsänderung, #739-Quarantänefreigabe, #632-Live-Lauf, Merge oder eine Behauptung globaler Optimalität des gesamten NaC-Repositories. Eine spätere Umsetzung braucht nach Spec-Review einen DE/EN-Plan und ihre eigenen technischen und operativen Gates.
