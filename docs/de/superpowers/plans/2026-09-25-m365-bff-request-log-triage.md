# Einmalige BFF-Request-Log-Triage – Implementierungsplan

Status: Plan freigegeben; lokale test-first Umsetzung in Arbeit; keine Real-Read-Freigabe

Datum: 25. September 2026

Führendes Issue: [#748](https://github.com/notariat8/NaC/issues/748)

Freigegebene Spec: [BFF-Request-Log-Triage](../specs/2026-09-25-m365-bff-request-log-triage-design.md)

Ausgangsbasis der in Teams bereitgestellten App: `main`-Commit
`862c87e1e378657f0066faed1bd36b830be2146d`, Tree
`3b1cfe5a4cfd7972912b961bfad46b713469f9fa`. Die lokale
Umsetzung liegt isoliert auf `codex/748-bff-request-log-triage` gegen diesen
`main`-Stand. Vor einem späteren Push ist die vollständige Diff zu prüfen.
Nichts wird stillschweigend in PR #754 übernommen.

Delivery Mode: Protected PR. Risk Gate: Human Approval. Der Plan ist
kein Nachweis für einen realen Microsoft-Zugriff.

## Ziel und harte Grenze

Mit den beiden geschützten Clientbelegen und dem geschlossenen UTC-Fenster
`2026-09-25T10:42:03.397Z` bis `2026-09-25T10:42:10.487Z` wird ein
*möglicher* einzelner Application-Insights-Request-Log-Treffer vorbereitet.
Der bereits belegte Client-403 und das vorhandene SPFx-Subject beweisen
weder Function-Ingress noch die Ursache der Zugriffsentscheidung. Ein späterer
korrelationsgebundener 403-Logtreffer darf ausschließlich
`FUNCTION_TELEMETRY_MATCH_403` ergeben. Ohne belegte App-ID, Queryprojektion,
Korrelationsspalte und No-Refresh-Fähigkeit bleibt der Real-Read gesperrt.
Eine fehlende Logzeile darf nie zu `BFF_REQUEST_NOT_OBSERVED` umgedeutet
werden.

Die gesonderte Freigabe für die test-first Umsetzung wurde erteilt; die
Implementierung bleibt lokal und inaktiv. Login, Token-Refresh,
Credentialzugriff, Provider-Read, Deployment,
#739-Quarantänefreigabe und #632-Live-Lauf sind ausgeschlossen.

## Genehmigte lokale Umsetzung

1. **Test-first und getrennte Vertragsfläche.** In
   `tests/test_m365_historical_bff_request_log_triage.py` zuerst synthetische
   Positiv- und Negativfälle für alle sechs ACs anlegen. Ein eigener
   vorwärtsversionierter Vertrag unter
   `workflows/verification-contracts/m365-bff-request-log-triage.verification.json`
   hält die geschlossene Ressource, erlaubten Felder, Null-Effekt-Zähler und
   terminalen Blocker fest. Der historische
   [#748-Verification-Contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml)
   und der [Read-Driver-Ressourcenvertrag](../../../../workflows/contracts/m365-current-state-read-driver-resources.contract.json)
   bleiben unverändert und werden nur per Dateihash referenziert. Die
   formale Zwei-Snapshot-Diagnose wird nicht ersetzt.
2. **Offline-Belege und Zielbindung.** Der neue Validator
   `scripts/validate_m365_bff_request_log_triage.py` verifiziert die
   SHA-256-Werte `ed89c1171a02fc79c80314512375c7db84be2fce1528c7ba6596d7c24d805e40`
   und `daf4cc55f0f95f38b118155d8bef33d36a0a68809848ba96b049f1f129b80bda`,
   Companion-Beziehung, festes Millisekundenfenster und den vorhandenen
   Korrelationshash ohne Rohwertausgabe. Eingaben kommen ausschließlich aus
   geschützten, repository-externen Dateien. Ein Zielnachweis muss die
   tatsächliche Application-Insights-App-ID eindeutig mit
   `func-nac-bff-test-funktion8`, `notary_team_01`, Tenant und Leseberechtigung
   verbinden; Hostnamen- oder Bicep-Namensableitung bleibt blockiert.
3. **Query- und Korrelationsgate.** Erst ein getrennt belegtes Telemetrieschema
   mit nachweislich erfasster Korrelationsspalte erlaubt, eine bytegenau
   gehashte, feste KQL-Vorlage zu spezifizieren. Bis dahin liefert das Gate
   `BLOCKED_QUERY_PROJECTION_UNPROVEN`; fehlende Zielbindung liefert
   `BLOCKED_TARGET_UNBOUND`. Zeit, Pfad oder HTTP-Klasse allein genügen nie
   als Match. Null, mehrere oder nicht eindeutig korrelierte Treffer liefern
   `BLOCKED_CORRELATION_UNPROVEN` beziehungsweise
   `BLOCKED_AMBIGUOUS_MATCH`. Eine synthetische Positiv-Fixture schaltet
   keinen Produktionsport frei.
4. **Transport und Ausgabe begrenzen.** Ein späterer, separat freizugebender
   Port dürfte nur einen GET auf `/v1/apps/{app_id}/query` ausführen, mit
   fester Query, ohne Body, Redirect, Retry, Pagination oder weitere
   Providerabfrage. Vor jedem Portzugriff werden Commit, Tree, Contract,
   Resolver, Principal, Ziel, AVV-/DPA-Nachweis, Toolchain, Account und
   No-Refresh-Eigenschaft gebunden. Ohne konkret zitierte anwendbare externe
   Zwei-Personen-Pflicht gilt `OWNER_SOLO_APPROVAL` mit
   `four_eyes_satisfied=false`. Bei anwendbarer zitierter Pflicht sind
   qualifizierte Freigaben zweier verschiedener natürlicher `principal_id`-Werte
   nötig; bei nur einem gilt `BLOCKED_SINGLE_PRINCIPAL`. Die Ausgabe enthält ausschließlich
   `request_observed`, `http_class` und
   `request_correlation_binding_sha256`; Rohzeilen, URL, Header, IDs, Tokens
   und zusätzliche Felder blockieren vor Speicherung oder Ausgabe.
   Authentifizierungs-Challenges, übergroße Antworten und nicht vollständig
   redigierbare Daten blockieren ebenfalls. Die
   lokale Implementierung bleibt ohne separat geprüfte Authentisierung und
   Real-Read-Freigabe inaktiv. Eine spätere Bedienkante wird ausschließlich
   als feste Unterfunktion der zentralen `nac`-CLI ergänzt; freie URL-, KQL-,
   Ziel- oder Token-Parameter bleiben verboten. Bis zur getrennten
   Real-Read-Freigabe darf diese Bedienkante nur den Offline-Preflight und
   dessen Blocker ausgeben.
5. **Traceability und Review.** DE/EN-Spec und -Plan, neuer Vertrag,
   Validator und Tests erhalten dieselben AC-IDs. Die
   Spec-Traceability-Prüfung wird test-first so ergänzt, dass sie für dieses
   `spec_id` Planpfad und AC-Gleichheit tatsächlich erzwingt. DE/EN-Indizes
   und die Diagnoseanleitung verweisen erst bei Auslieferung auf den neuen
   Pfad; AI-SBOM/SBOM werden nur bei tatsächlicher neuer AI- oder
   Laufzeitkomponente geändert. Unabhängige Policy-, Dokumentations- und
   Validierungsreviews prüfen Datenschutz, Null-Effekte und DE/EN-Parität;
   danach `implement -> review -> fix`.

## Nachweismatrix

| AC | Geplanter lokaler Nachweis | Fail-closed-Gegenbeispiel |
| --- | --- | --- |
| AC-748-TG-01 | Hash-, Companion-, UTC- und Korrelationshash-Fixtures | Veränderte oder zusätzliche Receipt-Felder |
| AC-748-TG-02 | Zielbeleg bindet App-ID, Function, Tenant und Berechtigung | Nur Hostname, Template-Name oder frei gewählte App-ID |
| AC-748-TG-03 | Feste Query-Bytes, Digest und Schema-/Projektionsbeleg | Nur Template-ID oder `projection_proven=false` |
| AC-748-TG-04 | Genau ein vollständiger korrelierter 403-Synthetiktreffer | Null-/Mehrfachtreffer, Zeit-only-Match, andere Klasse, Zusatzfeld, übergroße oder nicht redigierbare Antwort |
| AC-748-TG-05 | Fakes erlauben geschützte lokale Belegreads, zählen aber null Netzwerk-/Provider-/Credential-/Login-/Refresh-Wirkung in der Vorbereitung und höchstens einen späteren GET | Credentialöffnung, Refresh, POST, Redirect, Retry, Paging, Body, Authentifizierungs-Challenge |
| AC-748-TG-06 | DE/EN-Plan-/Spec-Parität und AC-Traceability | Historischer #748-, #739-, #632- oder PR-#754-Pfad als Autorisierung |

Die Negativtests müssen außerdem zeigen, dass `OWNER_SOLO_APPROVAL` keine
Vier-Augen-Freigabe ist, Accounts desselben Principals nicht zwei Personen
sind und eine konkret zitierte anwendbare Zwei-Personen-Pflicht bei nur einem
Principal zu `BLOCKED_SINGLE_PRINCIPAL` führt.

## Prüfungen und Stopppunkte

Für diesen Plan: DE/EN-Links, Sprachparität, Spec-Traceability und Graft
prüfen; dokumentarische Review-Befunde korrigieren. Die geplanten
Implementierungstests sind heute noch keine bestandene Evidence.

Für die genehmigte lokale Umsetzung: fokussierte synthetische Tests,
`python -m unittest discover -s tests`, `graft build`, `graft check` und
`python scripts/nac.py doctor --profile strict`; danach vollständige
`main...HEAD`-Datei- und Commit-Diff, getrennte Review und verpflichtende
Remote-CI im Protected-PR-Modus. Ein grüner lokaler oder Remote-Test gibt
keinen Provider-Read frei. Vor einem tatsächlichen GET sind ein nachweislich
geschlossener Ziel-/Query-/Korrelations-/Auth-Kanal und eine neue exakt
gebundene Einmal-Freigabe erforderlich; jede Lücke stoppt ohne Retry.
