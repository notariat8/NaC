# Einmalige BFF-Request-Log-Triage für den Teams-403

Status: Spec und Plan freigegeben; lokale test-first Umsetzung in Arbeit; kein Provider-Read

Datum: 25. September 2026

Führendes Issue: [#748](https://github.com/notariat8/NaC/issues/748)

Ausgangsbasis der bereitgestellten Teams-App: `main`-Commit
`862c87e1e378657f0066faed1bd36b830be2146d`, Tree
`3b1cfe5a4cfd7972912b961bfad46b713469f9fa`. Der Entwurf ist eine
separate Vorwärtsänderung und verändert weder die historische
[#748-Diagnosespezifikation](2026-09-20-m365-current-state-access-diagnostic-design.md)
noch den [Read-Driver-Release-Entwurf](2026-09-23-m365-current-state-read-driver-design.md).

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-request-log-triage
leading_issue: https://github.com/notariat8/NaC/issues/748
plan: docs/de/superpowers/plans/2026-09-25-m365-bff-request-log-triage.md
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - External Service
  - Human Approval
  - Privacy
  - Secrets
  - Policy
acceptance_ids:
  - AC-748-TG-01
  - AC-748-TG-02
  - AC-748-TG-03
  - AC-748-TG-04
  - AC-748-TG-05
  - AC-748-TG-06
validation_commands:
  - python scripts/validate_m365_bff_request_log_triage.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python -m unittest discover -s tests -p test_m365_historical_bff_request_log_triage.py
  - graft check
  - python scripts/nac.py doctor --profile strict
```

## Zweck und belegter Ausgangspunkt

Die beiden lokal vorhandenen Clientbelege mit SHA-256
`ed89c1171a02fc79c80314512375c7db84be2fce1528c7ba6596d7c24d805e40`
und `daf4cc55f0f95f38b118155d8bef33d36a0a68809848ba96b049f1f129b80bda`
gehören zum geschlossenen Fenster `2026-09-25T10:42:03.397Z` bis
`2026-09-25T10:42:10.487Z`. Sie belegen `spfx_subject_available=true` und
eine vom Client empfangene HTTP-403-Antwort auf den fest gebundenen
Workbench-Snapshot-GET. Sie belegen weder Azure-Function-Ingress noch eine
konkrete BFF-Zugriffsregel. Die Beleginhalte, der rohe Korrelationswert und
personenbezogene Daten bleiben repository-extern.

Diese Triage soll mit möglichst wenig zusätzlicher Arbeit feststellen, ob
*ein eindeutig korrelationsgebundener Eintrag* in bereits vorhandener
Function-Request-Telemetrie nachweisbar ist. Sie ist weder die formale
Zwei-Snapshot-Diagnose noch eine neue Teams-Beobachtung oder ein Fix.

## Scope und Designentscheidung

1. Ein eigener, vorwärtsversionierter Triage-Vertrag bleibt vom historischen
   [Verification Contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml)
   und [Ressourcenvertrag](../../../../workflows/contracts/m365-current-state-read-driver-resources.contract.json)
   getrennt. Deren `projection_proven=false`, No-Refresh-Blockade, zwei
   Erhebungen und Freigaben werden nicht stillschweigend geändert.
2. Der einzige spätere Provider-Read wäre ein GET der Application-Insights-v1-
   Query-Familie `/v1/apps/{app_id}/query` für genau die gebundene Test-Function
   `func-nac-bff-test-funktion8` im Workspace `notary_team_01`. Die
   tatsächliche `{app_id}` ist **nicht** aus dem Function-Hostnamen oder einer
   Bicep-Namensschablone abzuleiten. Ein geschützter, repository-externer
   Zielnachweis muss die App-ID, Function, Tenant und Berechtigung eindeutig
   verbinden; fehlt er, gilt `BLOCKED_TARGET_UNBOUND`.
3. Die Query benötigt eine versionierte, bytegenau gehashte und fest
   parametrisierte Vorlage. Sie darf ausschließlich das oben genannte
   Millisekundenfenster, den festen Workbench-Snapshot-Pfad, GET und eine
   nachweislich erfasste Korrelationsspalte verwenden. Frei eingegebene KQL,
   Ziel-IDs, Zeitfenster, Suchbegriffe oder Antwort-URLs sind verboten. Der
   jetzige Ressourcenvertrag nennt nur eine Query-Template-ID und enthält
   **keinen** kompilierten oder schema-geprüften KQL-Text. Bis eine reale
   Telemetrieschema- und Projektionsbindung separat nachgewiesen ist, gilt
   `BLOCKED_QUERY_PROJECTION_UNPROVEN`.
4. Die zufällige Client-Korrelationskennung ist nur als SHA-256 im geschützten
   Beleg vorhanden. Ein späterer Kandidat darf ausschließlich innerhalb des
   geschützten Prozesses gegen diesen Hash geprüft werden. Ein Zeit- oder
   Pfadtreffer allein ist keine Korrelation. Ist der Header in der
   Request-Telemetrie nicht nachweislich erfasst, fehlt der Vergleich oder
   gibt es mehrere Treffer, gilt `BLOCKED_CORRELATION_UNPROVEN` beziehungsweise
   `BLOCKED_AMBIGUOUS_MATCH`.
5. Die feste Ergebnisprojektion enthält nur `request_observed`, `http_class`
   und `request_correlation_binding_sha256`. Rohzeilen, URL, Header,
   Korrelationsklartext, Tokens, Account-/Tenant-IDs und weitere Felder dürfen
   weder ausgegeben noch gespeichert werden. Unbekannte Felder, übergroße
   Antworten, Redirects, Authentifizierungs-Challenges und nicht redigierbare
   Daten blockieren. Es gibt höchstens einen GET, keinen Body, kein Paging,
   keinen automatischen Retry und keinen neuen Teams-Aufruf.
6. Die lokale Vorbereitung darf weder Credentials öffnen noch Netzwerk- oder
   Providerzugriff ausführen. Für einen späteren realen Read wären ein
   überprüfter bestehender Authentifizierungskontext mit **null**
   Token-Refresh, geschützte AVV-/DPA-, Ziel-, Account-/Principal-Bindungen
   sowie eine eigene exakt gebundene Einmal-Freigabe nötig. Ohne konkret
   zitierte anwendbare externe Zwei-Personen-Pflicht ist
   `OWNER_SOLO_APPROVAL` zulässig und keine Vier-Augen-Freigabe; mehrere
   Accounts desselben Principals zählen nie als zwei Personen. Bei einer
   konkret zitierten anwendbaren Pflicht und nur einem Principal gilt
   `BLOCKED_SINGLE_PRINCIPAL`. Jeder spätere stille Refresh wäre eine
   getrennt freizugebende RED-Credential-Operation mit eigenem
   Vorwärtsvertrag, nicht Teil dieser Triage. Ein Login, Token-Refresh,
   Release, Deployment oder Provider-Write wird hier nicht autorisiert.

## Ergebnisgrenze

Ein eindeutiger, geschützter Logtreffer mit HTTP 403 würde nur
`FUNCTION_TELEMETRY_MATCH_403` stützen: Der Function-Monitoringpfad sah
einen passenden Request. Er beweist **nicht**, dass der Python-Endpunkt die
Antwort erzeugte oder welche fachliche Berechtigungsregel griff. Ohne
eindeutig korrelationsgebundene und vollständig redigierbare Telemetrie
lautet das Ergebnis `BLOCKED`; eine fehlende Zeile darf weder als
`BFF_REQUEST_NOT_OBSERVED` noch als Erfolg ausgegeben werden. Erst ein
separat genehmigter Folgeschritt könnte Azure-Edge oder BFF-Access-Decision
gezielt unterscheiden.

## Akzeptanzkriterien und Testplan

- **AC-748-TG-01:** Beide vorliegenden Datei-Hashes, die Companion-Bindung,
  die exakten UTC-Grenzen und der Korrelationshash werden offline geprüft;
  Abweichung oder zusätzliche Receipt-Felder blockieren.
- **AC-748-TG-02:** Nur ein geschützter Zielnachweis mit eindeutigem
  Application-Insights-App-ID-zu-Function-/Tenant-Bezug ist zulässig;
  Namensableitung und freie Zielwahl scheitern.
- **AC-748-TG-03:** Eine feste, gehashte Query-Vorlage und ein bewiesenes
  Telemetrieschema sind Voraussetzung; der heutige reine Template-Identifier
  und `projection_proven=false` bleiben blockiert.
- **AC-748-TG-04:** Null, mehrere, unkorrelierte oder unvollständige Treffer,
  unerwartete HTTP-Klassen und überschüssige Ausgabefelder scheitern
  fail-closed. Synthetische Tests zeigen, dass Uhrzeit allein kein Match ist.
- **AC-748-TG-05:** Synthetische Negativtests beweisen null Netzwerk-,
  Provider-, Credential-, Login- und Refreshzugriff bei lokaler Vorbereitung;
  spätere Transportgrenzen sind ein GET, null Redirects, Retries, Paging,
  Bodies und Writes.
- **AC-748-TG-06:** DE/EN-Spec, späterer Plan, separater Triage-Vertrag,
  Validator, Tests und Traceability stimmen überein. Weder die historische
  #748-Klassifikation noch #739, #632 oder PR #754 erhalten dadurch eine
  Live-Freigabe. Die hier genannten zukünftigen Test- und Strict-Befehle
  sind bis zur Implementierung Prüfziele, keine behaupteten Ergebnisse.

## Risiken und Nicht-Ziele

Das Telemetrieschema, die tatsächliche Application-Insights-App-ID, die
Erfassung des Korrelationsheaders und die Authentifizierungsfähigkeit sind
ohne Providerzugriff derzeit **nicht bewiesen**. Diese Lücken werden als
Blocker dokumentiert, nicht mit Dummywerten geschlossen. Keine reale
Microsoft-Abfrage, kein Tenant- oder Credentialzugriff, keine neue Anmeldung,
kein Token-Refresh, kein BFF-/SPFx-Deployment, keine Rollen- oder
Berechtigungsänderung und keine produktive Fehlerbehebung in dieser Phase.
