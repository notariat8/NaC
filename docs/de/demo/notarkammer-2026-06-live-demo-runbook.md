# Notarkammer-Demo 2026-06: Live-Runbook

Status: Protected-PR-fähige Vorführ-Checkliste für die 60-Minuten-Live-Demo.

Dieses Runbook führt die gemergten Demo-Spuren zusammen:

- XNP-Demo-Kontrakt: `notarkammer-xnp-demo-contract.md`
- 60-Minuten-Skript: `notarkammer-2026-06-demo-script.md`
- XNP-Preflight/Audit-Spur: `notarkammer-2026-06-demo-preflight.md`

Scope für diesen PR: nur `docs/de`, `docs/en` und `tests`. Keine Runtime,
No OCI, keine Infrastruktur, no release, no apply, no runtime change, no cloud
change, no secrets und no real mandate data. Alle Beispiele bleiben synthetic.

## Kernlinie

1. XNP lokal: XNP, Kartenleser, SAK lite, secureFramework, Rolle und
   Amtstätigkeitskontext werden nur am freigegebenen Arbeitsplatz geprüft.
2. XNotar/XJustiz-Übergabe: Register- und Grundbuchpfade werden als
   Austauschordner, XJustiz-Paket, lokaler Import und menschliche Rückmeldung
   gezeigt.
3. NaC BPMN/Evidence/Gate: NaC zeigt die Fachsystemgrenze im BPMN, übernimmt
   nur redigierte Evidence und blockiert oder eröffnet den nächsten Schritt
   über ein explizites Gate.
4. Harte Aussage: XNP liefert keine Grundbuchdaten an NaC.
5. Harte Aussage: kein automatisierter externer XNotar-Import-Trigger.
6. Demo-Gate: Login und Workspace werden nur weitergeführt, wenn die
   Freigabe für die Demo-Sitzung vorliegt; sonst wird fail-closed gezeigt.
7. Public-Onboarding ist heute als GET-/Statuspfad vorführbar: Readiness,
   DNS-Check und Request-Status, aber keine neue Anfrage im Termin.
8. ATP-Healthcheck ist ein Store-Gate: `enabled`, `disabled`, `unavailable`
   oder `not_checked`; Secrets, Wallets, DSN und OCI-Schreiboperationen werden
   nicht geöffnet.

## Zeitangabe

Die Vorführung verwendet lokale Kammer-/Berlin-Zeit: CET im Winter (UTC+1) und
CEST im Sommer (UTC+2). Für Juni 2026 ist CEST maßgeblich. Zeitangaben in
Audit-Notizen immer als CET/CEST plus optionaler technischer UTC-Ergänzung
schreiben, nie UTC-only.

## Browser-Tabs vorab öffnen

Keine Live-Suche, keine Browser-Historie und keine spontanen Admin- oder
Cloud-Konsolen im Termin. Vor Beginn nur diese Tabs öffnen:

| Tab | Seite | Zweck | Fallback |
| --- | --- | --- | --- |
| Tab 1 | `https://notariat8.de` | Öffentlicher Einstieg. | Geladenen Tab behalten. |
| Tab 2 | `https://notariat8.de/prozessmodell.html` | BPMN, Dauer, Parallelität und kritischer Pfad. | Freigegebenen Screenshot nutzen. |
| Tab 3 | `https://app.notariat8.de/onboarding/dns-check?audience=customer&domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example` | DNS-/Readiness-Nachweis mit synthetischer Domain. | Setup-Status erklären. |
| Tab 4 | `https://app.notariat8.de/onboarding/requests/<request_id>?audience=customer` | vorhandener Request-Status. | Store-Gate `unavailable` erklären. |
| Tab 5 | `https://app.notariat8.de/login` | geschützter Einstieg. | Login nicht live debuggen. |
| Tab 6 | `https://app.notariat8.de/workspace` | fail-closed oder Metadata-only Workspace. | geschlossene Grenze erklären. |

## Vorführmodus

Die Demo läuft in genau einem Browserfenster mit vorbereiteten Tabs. Die
Adresszeile wird nicht vorgelesen und nicht als Belegfläche verwendet. Gezeigt
werden nur die Nutzerflächen `notariat8.de/prozessmodell.html`,
`app.notariat8.de/login` und `app.notariat8.de/workspace` sowie die
vorbereiteten Readiness-/Statusseiten mit synthetischen Daten.

Kein JSON-Endpunkt als Benutzeroberfläche zeigen. Wenn ein JSON-, Callback-
oder Fehler-Tab sichtbar wird, Tab schließen und auf das Prozessmodell, die
Login-Seite oder den geschlossenen Workspace wechseln. Wenn eine Live-Fläche
langsam ist oder technisch nicht verfügbar wirkt, nicht debuggen, sondern die
Fallback-Evidence nutzen und die fachliche Grenze benennen.

## T-03:00 Preflight-Reihenfolge

| Reihenfolge | Live-Test | Erwartung | Fallback |
| --- | --- | --- | --- |
| 1 | `https://notariat8.de` | Startseite lädt ohne Mandatsdaten. | Bereits geladenen Tab verwenden. |
| 2 | `https://notariat8.de/prozessmodell.html` | Immobilienkaufvertrag, Dauerlogik und kritischer Pfad sind sichtbar. | Screenshot oder geöffneten Tab nutzen. |
| 3 | `https://app.notariat8.de/healthz` | Kurzer, nicht-sensitiver Status. | Tab schließen, Workspace-Grenze zeigen. |
| 4 | `https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example` | Public-Onboarding zeigt Einrichtungsstatus ohne Mandatsdaten. | Geladenen Tab zeigen, keine Anfrage absenden. |
| 5 | `https://app.notariat8.de/onboarding/dns-check?audience=customer&domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example` und CLI-DNS-Check | Erwarteter TXT-Record und Status sind sichtbar. | `pending`/`mismatch` als Setup-Status erklären. |
| 6 | `/onboarding/requests/<request_id>?audience=customer` | Statusseite für vorhandene Anfrage oder `unavailable` als Store-Gate. | Nicht in ATP debuggen. |
| 7 | `https://app.notariat8.de/login` | Login-Seite öffnet; keine echten Zugangsdaten eingeben; Login-Flow nur mit Freigabe fortsetzen. | Nicht debuggen, zum Prozessmodell wechseln. |
| 8 | `https://app.notariat8.de/api/tenant/login-intent?tenant_hint=notariat-musterstadt` | Read-only Login-Intent ohne Credentials. | Falls JSON/Fehler sichtbar ist, Login-Seite oder Workspace-Grenze zeigen. |
| 9 | `https://app.notariat8.de/workspace` | Ohne freigegebene Sitzung bleibt der Arbeitsbereich geschlossen; nur Metadatenstatus, keine Akte. | Fail-closed als Sicherheitsnachweis erklären. |
| 10 | BPMN-Validierung | `python scripts/nac.py bpmn validate` bleibt grün; `bpmn show immobilienkaufvertrag` ist lesbar. | Öffentliche Prozessmodellseite nutzen. |
| 11 | ATP-Healthcheck-Status | `/healthz` zeigt Runtime-Status; ATP-Store-Gate wird nur als `enabled`, `disabled`, `unavailable` oder `not_checked` eingeordnet. | Keine Secrets, Wallets, DSN oder OCI-CLI öffnen. |
| 12 | XNP lokal | Kartenpfad, XNP-Localhost `12774` bis `12784` und Rolle sind nur lokal plausibel. | Keine Live-XNP-Aktion; Gate als `manual_review` oder `blocked` markieren. |
| 13 | XNotar/XJustiz-Übergabe | Austauschordner und Paketgrenze sind synthetisch oder leer prüfbar. | Kein Paket öffnen; nur die Übergabegrenze erklären. |

## Exakte Read-only Checks

```bash
curl -fsS https://app.notariat8.de/healthz
curl -fsS "https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example" >/tmp/nac-onboarding-readiness.html
curl -fsS "https://app.notariat8.de/api/tenant/login-intent?tenant_hint=notariat-musterstadt" >/tmp/nac-login-intent.json
curl -i "https://app.notariat8.de/workspace"
python scripts/nac.py tenant customer-plan --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --saas-admin-email saas-owner@example.com --format json
python scripts/nac.py tenant dns-check --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --format json
python scripts/nac.py tenant apply-request --tenant-slug kanzlei-notariat --domain kanzlei-notariat.example --admin-email admin@kanzlei-notariat.example --admin-display-name "Admin Notariat" --identity-domain-url https://idcs.example.invalid --identity-domain-id ocid1.domain.oc1.example --dns-verified --owner-approval-id DEMO-OWNER --audit-event-id DEMO-AUDIT --rollback-plan-id DEMO-ROLLBACK --dry-run --format json
python scripts/nac.py bpmn validate
python scripts/nac.py bpmn show immobilienkaufvertrag --format text
```

Nicht ausführen: `POST /onboarding/requests`, `POST /admin/onboarding/review`,
OCI-CLI, Vault-/Wallet-Lesen, ATP-Schemaänderungen oder echte
Identity-Provisionierung.

## Login-Triage

Wenn der Login in der Demo nicht bis zum geschützten Startstatus führt, wird
nicht live geraten. Die sichtbare Diagnose bleibt redigiert und
kundenverständlich:

- `Token-Austausch: Anmeldung technisch nicht verfügbar`: die Anmeldung wurde
  angenommen, aber der serverseitige Austausch konnte nicht belastbar
  abgeschlossen werden.
- `Token-Austausch: ungültig`: der serverseitige Austausch lieferte kein
  verwendbares Ergebnis.
- `Token-Prüfung: nicht gestartet`: ohne belastbares Ergebnis startet keine
  nachgelagerte Prüfung.
- `Rollenprüfung: geschlossen`: ohne geprüfte Anmeldung und Rolle bleibt der
  Arbeitsbereich geschlossen.

Erlaubte interne Diagnoseklassen für die Nachbereitung sind nur
`missing_id_token`, `token_response_not_json` und
`id_token_verification_failed`. In Demo, Logs und Issues werden keine Tokens,
keine Claims, keine Provider-Details, keine Callback-Werte, keine Zugangsdaten
und keine Mandatsdaten ausgegeben. Stop-Line: "Der Login ist fail-closed; wir
zeigen jetzt den Prozesspfad und prüfen die technische Ursache nach dem Termin."

## 60-Minuten Live-Folge

1. 0-5 Minuten: `https://notariat8.de` zeigen und klar sagen, dass die
   öffentliche Sicht keine Mandatsdaten enthält.
2. 5-20 Minuten: `https://notariat8.de/prozessmodell.html` öffnen,
   Immobilienkaufvertrag, Dauerlogik, Parallelität und kritischer Pfad
   erklären.
3. 20-28 Minuten: Public-Onboarding, DNS-Readiness und vorhandenen
   Request-Status als kundenverständliche Setup-Spur zeigen. Keine neue
   Anfrage im Termin absenden.
4. 28-35 Minuten: Fachsystemgrenzen zeigen: XNP lokal für Readiness,
   Kartenleser und Signaturpfad; XNotar/XJustiz-Übergabe für Register- und
   Grundbuchkommunikation.
5. 35-43 Minuten: Falls lokal verfügbar, BPMN-Editor zeigen; sonst beim
   öffentlichen Prozessmodell bleiben. NaC BPMN/Evidence/Gate ist die
   Aussage, nicht Live-Automatisierung.
6. 43-52 Minuten: `https://app.notariat8.de/login`,
   `https://app.notariat8.de/api/tenant/login-intent?...` und
   `https://app.notariat8.de/workspace` als geschützten Einstieg zeigen.
   Login nur fortsetzen, wenn es vorab für diese Demo freigegeben ist;
   ansonsten den geschlossenen Workspace mit Metadata-only-Gate als erwartetes
   Ergebnis zeigen.
7. 52-55 Minuten: Unterschriftsbeglaubigung als kurzen Vergleichsprozess
   nennen.
8. 55-60 Minuten: Zusammenfassen: sichtbare Fachsystemgrenzen, Protected PRs,
   redigierte Evidence, keine produktiven Register- oder Grundbuchhandlungen.

## 5-Minuten Kurzfolge

1. `https://notariat8.de` öffnen.
2. `https://notariat8.de/prozessmodell.html` zeigen.
3. Immobilienkaufvertrag, Dauer, Parallelität und kritischer Pfad benennen.
4. Public-Onboarding/DNS-Status als GET-only Setup-Spur zeigen.
5. XNP lokal als Readiness-Gate erklären.
6. XNotar/XJustiz-Übergabe als Paket-/Austauschordnergrenze erklären.
7. `https://app.notariat8.de/login`, Login-Intent und den geschlossenen
   Metadata-only-Workspace zeigen.
8. Abschluss: NaC BPMN/Evidence/Gate macht Arbeit sichtbar und prüfbar.

## 20-Minuten Fallback

1. 0-3 Minuten: `https://notariat8.de` öffnen und sagen, dass nur öffentliche
   Prozessreferenzen ohne Mandatsdaten gezeigt werden.
2. 3-9 Minuten: `https://notariat8.de/prozessmodell.html` zeigen:
   Immobilienkaufvertrag, Dauerlogik, Parallelität und kritischen Pfad
   benennen.
3. 9-12 Minuten: Public-Onboarding-Readiness und DNS-Status zeigen. Wenn
   Request-Status oder ATP nicht verfügbar sind, `unavailable` als Store-Gate
   erklären.
4. 12-15 Minuten: XNP lokal, Kartenleser, SAK lite, secureFramework, Rolle und
   Amtstätigkeitskontext als Arbeitsplatzgrenze und Demo-Gate erklären. Keine
   produktive XNP-Aktion starten.
5. 15-17 Minuten: XNotar/XJustiz als Paket-/Austauschordnergrenze für
   Register- und Grundbuchkommunikation erklären. Keine echten Pakete, keine
   Registerdaten und keine Grundstücksdaten öffnen.
6. 17-19 Minuten: `https://app.notariat8.de/login` zeigen. Login-Flow nur bei
   ausdrücklicher Freigabe fortsetzen; sonst direkt
   `https://app.notariat8.de/workspace` fail-closed zeigen.
7. 19-20 Minuten: Stop-Lines zusammenfassen: NaC modelliert BPMN, Evidence und
   Gate; externe Fachsysteme bleiben Grenzen; keine echten Daten, keine
   produktive Behauptung.

## Stop-Lines

- Stop-Line: "Wir debuggen jetzt nicht live; die Demo zeigt den geprüften
  Prozesspfad."
- Stop-Line: "Ohne Freigabe führen wir den Login-Flow nicht weiter; der
  geschlossene Workspace ist dann das erwartete Demo-Ergebnis."
- Stop-Line: "Callback-URL nicht vorlesen und keine Werte aus `code` oder
  `state` zeigen; Tab schließen oder auf `/workspace` wechseln."
- Stop-Line: "XNP bleibt lokal. XNP liefert keine Grundbuchdaten an NaC."
- Stop-Line: "XNotar/XJustiz ist hier eine Übergabegrenze, keine versteckte
  Cloud-Automation."
- Stop-Line: "Ohne Evidence bleibt das NaC-Gate blockiert."
- Stop-Line: "Diese Demo enthält keine Release-, Apply-, Runtime-, OCI- oder
  Cloud-Aktion."

## Protected-PR Nachweis

- Branch: `agent/notarkammer-live-demo-runbook-2`.
- Geänderte Flächen: `docs/de/demo/`, `docs/en/demo/`, `tests/`.
- Erwartete Checks: fokussierte Demo-Runbook-Tests, bestehende Demo-Kontrakt-,
  Demo-Skript- und Preflight-Tests.
- Audit-Spur: Commit-SHA, Testausgabe, Branch und PR-Link; keine Personen-,
  Akten-, Urkunden-, Ausweis-, Register- oder Grundstücksdaten.
