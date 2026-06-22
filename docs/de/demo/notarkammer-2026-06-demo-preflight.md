# Notarkammer-Demo 2026-06: XNP-Preflight und Audit-Spur

Status: owner-freier Protected-PR-Track für die 1h-Live-Demo.

Diese Checkliste wird vor der Vorstellung ausgeführt und als Demo-Nachweis
abgelegt. Sie schuetzt die Live-Demo vor Ad-hoc-Debugging, echten Mandatsdaten,
lokaler Karten-/XNP-Improvisation und nicht freigegebenen Betriebsaktionen.
Alle Beispiele bleiben synthetisch; es gilt ausdruecklich: no real mandate
data, no secrets, no release, no apply, no runtime change, no cloud change.

## Zeitplan CET/CEST

Alle Uhrzeiten werden als lokale Kammer-/Berlin-Zeit geführt: CET im Winter
(UTC+1) und CEST im Sommer (UTC+2). Für Juni 2026 ist CEST maßgeblich; keine
Demo-Notiz darf nur UTC nennen.

| CET/CEST-Zeit | Ziel | Ergebnis |
| --- | --- | --- |
| T-03:00 | Frisches Browserprofil öffnen, Cache vermeiden, Demo-Tabs vorbereiten. | Fünf Tabs sind geladen oder als Fallback markiert. |
| T-02:45 | Public-Onboarding, DNS-Readiness und vorhandene Request-Statusseite nur per GET prüfen. | Customer Journey ist vorführbar oder als Fallback markiert. |
| T-02:30 | Lokalen Kartenleser-/SAK-Pfad für XNP als Readiness-Gate prüfen. | Evidence zeigt `ready`, `manual_review` oder Stop-Line. |
| T-02:00 | XNP-Localhost, XNotar-Austauschordner und XJustiz-Paketgrenze prüfen. | Nur nicht-sensitive Status- und Hash-Nachweise liegen vor. |
| T-01:45 | OIDC-Login-Intent, geschützten Startstatus und Workspace-Gate prüfen. | Login endet vor dem Workspace, sofern keine Demo-Freigabe vorliegt. |
| T-01:40 | ATP-Healthcheck-Status als Store-Gate einordnen. | `enabled`, `disabled`, `unavailable` oder `not_checked` ohne Secret-Ausgabe. |
| T-01:30 | 1h-Demo-Skript mit den sichtbaren Browser- und Arbeitsplatzständen abgleichen. | Keine neue Storyline wird begonnen. |
| T-01:00 | Stop-Lines laut lesen und Browser-Tabs final sortieren. | Demo kann ohne Live-Debugging starten. |
| T-00:15 | Nur noch Read-only-Sichtung, keine Änderungen mehr. | Praesentationsfenster bleibt stabil. |

## Befehlssicherheit

Alle Befehle in diesem Preflight dürfen nur vorbereiten oder lesen. Beispiele
mit `curl` sind Sichtprüfungen. Beispiele mit `tenant apply-request` müssen
`--dry-run` enthalten. POST, OCI-CLI, produktive Apply-Schritte, Vault-,
Wallet-, ATP- und Identity-Secret-Zugriffe bleiben Stop-Lines und werden im
Termin nicht ausgeführt.

## Browser-Checks

Alle Checks laufen in einem frischen Browserfenster ohne gespeicherte Sitzung.

1. `https://notariat8.de`
   - Erwartung: Startseite laedt und zeigt keine echten Mandatsdaten.
   - Fallback: Bereits geladene Startseite nutzen; nicht live deployen.
2. `https://notariat8.de/prozessmodell.html`
   - Erwartung: Immobilienkaufvertrag, Dauerlogik und kritischer Pfad sind
     sichtbar.
   - Fallback: Lokalen Screenshot oder bereits geöffneten Tab verwenden.
3. `https://app.notariat8.de/healthz`
   - Erwartung: Status ist kurz und unkritisch, zum Beispiel `ok`.
   - Fallback: Health-Tab schliessen und den Fail-Closed-Workspace zeigen.
4. `https://app.notariat8.de/login`
   - Erwartung: Anmeldung oeffnet, aber es werden keine echten Zugangsdaten
     eingegeben.
   - Fallback: Login nicht debuggen; auf Prozessmodell und Workspace-Grenze
     wechseln.
5. `https://app.notariat8.de/workspace`
   - Erwartung: Ohne gültige Sitzung bleibt der Arbeitsbereich geschlossen.
   - Fallback: Genau diesen Zustand als Sicherheitsnachweis erklären.

## Was Heute Gezeigt Werden Kann

| Spur | Vorführbarer Stand | Read-only-Check | Fallback |
| --- | --- | --- | --- |
| Public Onboarding | `https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example` zeigt Domain, Admin-E-Mail, DNS-Hinweis und Einrichtungsstatus ohne Mandatsdaten. | `curl -fsS "https://app.notariat8.de/onboarding/readiness?audience=customer&domain_hint=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example" >/tmp/nac-onboarding-readiness.html` | Bereits geladenen Tab zeigen; keine Anfrage absenden. |
| DNS-Check | `https://app.notariat8.de/onboarding/dns-check?audience=customer&domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat&admin_email=admin%40kanzlei-notariat.example` zeigt erwarteten TXT-Record und aktuellen Status. | `python scripts/nac.py tenant dns-check --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --format json` | Wenn DNS nicht `verified` ist, `pending`/`mismatch` als normaler Setup-Status erklären. |
| Request-Status | Bestehende Anfrage kann über `/onboarding/requests/<request_id>?audience=customer` nur als Statusseite gezeigt werden. | `curl -fsS "https://app.notariat8.de/onboarding/requests/onr_demo_20260621_100000?audience=customer" >/tmp/nac-request-status.html` | Wenn Store deaktiviert oder ID unbekannt ist, `not found`/`unavailable` als ATP-Gate erklären. |
| OIDC-Login bis Protected Start | `/login?tenant_hint=notariat-musterstadt` und `/api/tenant/login-intent?tenant_hint=notariat-musterstadt` zeigen den Start des Login-Flows ohne Zugangsdaten. | `curl -fsS "https://app.notariat8.de/api/tenant/login-intent?tenant_hint=notariat-musterstadt" >/tmp/nac-login-intent.json` | Login nicht fortsetzen; geschützten Startstatus zeigen. |
| Workspace Metadata-only Gate | `/workspace` bleibt ohne freigegebene Sitzung geschlossen und zeigt nur Metadatenstatus, keine Akte. | `curl -i "https://app.notariat8.de/workspace"` erwartet `401` oder geschlossene HTML-Sicht mit `Keine Mandatsdaten geladen`. | Fail-closed als Sicherheitsnachweis erklären. |
| BPMN-Prozessmodell | Immobilienkaufvertrag ist als BPMN-/Prozessmodell sichtbar und validierbar. | `python scripts/nac.py bpmn validate` und `python scripts/nac.py bpmn show immobilienkaufvertrag --format text` | Öffentliche Prozessmodellseite oder Screenshot verwenden. |
| ATP-Healthcheck-Status | ATP ist nur Store-Gate für Onboarding-Anfragen; Healthcheck darf keine Wallet-, Secret- oder DSN-Werte zeigen. | `python scripts/nac.py tenant customer-plan --domain kanzlei-notariat.example --tenant-slug kanzlei-notariat --admin-email admin@kanzlei-notariat.example --saas-admin-email saas-owner@example.com --format json` zeigt `shared_atp_with_tenant_id`; `/healthz` zeigt nur Runtime-Status. | Bei `onboarding_request_store_disabled` oder `onboarding_request_store_unavailable` keine Live-ATP-Analyse; Status als Demo-Gate markieren. |
| Apply-/Provisioning-Status | Es gibt nur Review-Artefakte, keine OCI-Schreiboperation. | `python scripts/nac.py tenant apply-request --tenant-slug kanzlei-notariat --domain kanzlei-notariat.example --admin-email admin@kanzlei-notariat.example --admin-display-name "Admin Notariat" --identity-domain-url https://idcs.example.invalid --identity-domain-id ocid1.domain.oc1.example --dns-verified --owner-approval-id DEMO-OWNER --audit-event-id DEMO-AUDIT --rollback-plan-id DEMO-ROLLBACK --dry-run --format json` | Wenn Gate fehlt, Blocker erklären; kein Apply ausführen. |

Alle `curl`-Beispiele sind GET/HEAD-artige Sichtprüfungen. Keine Formulare im
Termin absenden, keine POST-Requests ausführen, keine OCI-CLI, keine Vault-,
Wallet-, ATP- oder Identity-Secrets öffnen.

## XNP- und Kartenleser-Gates

Diese Gates dürfen nur lokal am freigegebenen Arbeitsplatz geprüft werden.
NaC steuert XNP, Kartenleser, SAK lite, secureFramework oder PIN-Eingabe nicht
aus der Cloud.

| Gate | Erwartung | Evidence |
| --- | --- | --- |
| BNotK-Karte und Kartenleser | Sicherheitsklasse-3-Leser ist lokal verfügbar; PIN wird nur am Leser oder in der lokalen zertifizierten Komponente eingegeben. | `nac-cyberjack-rfid`-Readiness ohne PIN, Kartendaten oder Rohattribute. |
| RFID für BNotK-Chipkartenpfad | Kontaktloser Pfad ist ausgeschaltet, sofern kein eigener kontaktloser Usecase freigegeben ist. | Manuelle Attestation oder lokaler Readiness-Status. |
| PC/SC, SAK lite oder XNP-Kartenpfad | Treiber, PC/SC und Kartenpfad sind lokal plausibel bereit. | Minimierte Statusliste; keine System-Secrets. |
| XNP-Localhost | XNP ist nur lokal erreichbar; erlaubter Portbereich bleibt `12774` bis `12784`. | Host, Portbereich und Erreichbarkeitsstatus; kein API-Key, kein Login-Token. |
| Lokale XNP-Anmeldung | Nutzerrolle und Amtstaetigkeitskontext werden nur lokal bestätigt. | Ja/Nein-Attestation; keine Session-Werte. |
| XNotar-Modul | Für Registerfaelle ist der Austauschordner bekannt und schreibend nur nach Owner-Freigabe nutzbar. | Pfadstatus als Hash oder Platzhalter; keine Dokumentinhalte. |
| XJustiz-Paketgrenze | Paketstruktur wird nur synthetisch oder mit leerem Testpaket erklärt. | Schema-/Strukturstatus; keine Urkunden-, UVZ-, VVZ- oder Registerinhalte. |

## Audit-Spur

Die Demo-Audit-Spur besteht aus einem Protected PR, Testausgaben und
minimierten Evidence-Artefakten. Sie ist kein Betriebsjournal und keine
Mandatsakte.

- Protected PR enthält nur Dokumentation und Tests.
- Evidence-IDs dürfen synthetisch sein, zum Beispiel `DEMO-XNP-2026-06-001`.
- Zeitstempel, Commit-SHA, Branch und Testergebnis werden dokumentiert.
- Pfade, Ports und Reader-Fingerprints werden nur gehasht oder als Status
  beschrieben.
- Keine PIN, kein API-Key, kein Login-Token, keine Kartenrohdaten und keine
  Urkundeninhalte werden in Git, PR-Kommentaren oder LLM-Kontext abgelegt.
- Jede Abweichung wird als `ready`, `manual_review` oder `blocked` markiert.

## Fallback-Entscheidungen

| Lage | Entscheidung |
| --- | --- |
| Public-Seite langsam, Prozessmodell-Tab vorhanden | Auf vorhandenen Tab wechseln und offen sagen: "Wir zeigen die geprüfte Demo-Sicht." |
| Login braucht laenger als zwei Minuten | Nicht warten, Workspace fail-closed zeigen. |
| Kartenleser, PC/SC, SAK lite oder secureFramework unklar | XNP-/Kartenpfad nicht zeigen; nur das Preflight-Gate und die Stop-Line erklären. |
| XNP-Localhost nicht erreichbar | Keine Portsuche im Termin; Status `manual_review` oder `blocked` dokumentieren. |
| XNotar-Austauschordner oder XJustiz-Struktur nicht sicher abgegrenzt | Kein Paket öffnen; nur synthetische Paketgrenze erklären. |
| Lokaler Editor ist nicht verfügbar | Öffentliche Prozessmodellseite verwenden, GitHub-PR nur als Governance-Nachweis nennen. |
| Netzwerk schwankt | Keine neuen Tabs öffnen; nur geladene Demo-Tabs verwenden. |
| Public-Onboarding-Requeststatus ist nicht verfügbar | Nicht in ATP debuggen; Einrichtungsstatus als `unavailable` zeigen und auf Public-Onboarding/DNS ausweichen. |
| ATP-Healthcheck ist `disabled` oder `unavailable` | Keine Secrets oder Wallets öffnen; Status als Store-Gate erklären und beim BPMN-/Workspace-Pfad bleiben. |
| OIDC-Login-Intent liefert nur JSON oder Fehler | Nicht live erklären; `/login?tenant_hint=notariat-musterstadt` oder geschlossenen Workspace zeigen. |
| Workspace zeigt nur Metadatenstatus | Genau das ist erwartbar: protected start ja, voller Workspace nein. |

## Stop-Lines

- Stop-Line: "Wir debuggen jetzt nicht live; die Demo zeigt den geprüften
  Prozesspfad."
- Stop-Line: "Ohne Sitzung bleibt der Arbeitsbereich geschlossen. Das ist hier
  der gewünschte Sicherheitsnachweis."
- Stop-Line: "XNP, XNotar und XJustiz bleiben lokal und werden nur gezeigt,
  wenn Kartenpfad, Rolle und Evidence vorher gruen sind."
- Stop-Line: "Für die Kammer-Vorstellung verwenden wir ausschließlich
  synthetische Demo-Daten."
- Stop-Line: "Diese Demo enthält keine Release-, Apply-, Runtime- oder
  Cloud-Aktion."

## Owner-Gates

Diese Punkte bleiben offene Owner-Gates und werden nicht im owner-freien Track
entschieden:

- Freigabe der finalen 1h-Erzählung durch Demo-Owner.
- Freigabe, ob ein echter Login im Termin gezeigt wird oder nur der
  geschlossene Workspace.
- Freigabe, ob ein lokaler XNP-Arbeitsplatz überhaupt gezeigt wird.
- Freigabe des finalen Browserfensters unmittelbar vor Start.
- Merge-Entscheidung für diesen geschuetzten PR.

## PR-Track

- Branch: `agent/notarkammer-demo-preflight-audit`.
- Scope: nur `docs/de/demo/`, `docs/en/demo/` und `tests/`.
- Checks: Language Parity, Documentation Links und Strict Quality Gate.
- Keine OCI-, Runtime-, Release-, Apply- oder Infrastruktur-Änderungen.
- Keine echten Personen-, Akten-, Urkunden-, Ausweis-, Register- oder
  Grundstücksdaten verwenden.
