# Notarkammer-Demo 2026-06: Login-/Portal-Diagnose

Status: interner Protected-PR-Track für Demo-Entscheidungen, keine
Runtime-Änderung. Scope: `docs/de/demo`, `docs/en/demo` und
`tests/test_notarkammer_`. Keine Secrets, keine Tokens, keine Claims, keine
Provider-Details, keine Callback-Werte und keine Mandatsdaten.

Dieses Runbook beantwortet im Termin nur drei Fragen: Was ist vorführbar, was
ist Stopper, was ist Fallback. Es ersetzt keine technische Nachanalyse und
enthält keine Anbieter- oder Sitzungsdetails.

## Ampelklassen

| Klasse | Bedeutung | Demo-Entscheidung |
| --- | --- | --- |
| Grün / Green | Token-Austausch, Token-Prüfung, Rollenprüfung und Sitzung sind grün. | Live-Login darf weitergeführt werden, wenn die Demo-Freigabe vorliegt. |
| Gelb / Yellow | Anmeldung empfangen, aber mindestens ein Gate ist offen, langsam oder technisch nicht belastbar. | In Fallback wechseln: Prozessmodell-Fallback, Readiness-Fallback oder Workspace-Grenzen-Fallback. |
| Rot / Red | Token-Austausch ist ungültig, technisch nicht verfügbar oder Sitzung/Rolle bleibt ohne belastbaren Nachweis geschlossen. | Live-Login-Pfad stoppen; nicht live debuggen. |

Nur fortsetzen, wenn Token-Austausch, Token-Prüfung, Rollenprüfung und Sitzung
grün sind. Bei Gelb oder Rot wird nicht geraten, nicht neu konfiguriert und
nichts produktiv geöffnet.

## Aktuelle Live-Diagnose

Bekannter Browserstand bei `/auth/callback`:

| Sichtbares Signal | Einordnung | Ansage im Termin | Fallback |
| --- | --- | --- | --- |
| `Anmeldung empfangen` | Gelb, solange Folgeschritte offen sind. | "Die Anmeldung wurde angenommen; die App bleibt bis zur abgeschlossenen Prüfung geschlossen." | Readiness-Fallback oder Prozessmodell-Fallback. |
| `Token-Austausch: ungültig` | Rot. | "Der Login ist fail-closed; wir zeigen den geprüften Prozesspfad." | Live-Login-Pfad stoppen. |
| `Token-Austausch: technisch nicht verfügbar` | Rot. | "Die technische Anmeldung ist nicht vorführstabil; wir debuggen nicht live." | Prozessmodell-Fallback. |
| `Token-Prüfung: offen` | Gelb. | "Ohne geprüfte Anmeldung öffnen wir keinen Arbeitsbereich." | Workspace-Grenzen-Fallback. |
| `Rollenprüfung offen` | Gelb. | "Die Rolle ist noch nicht vorführbar bestätigt." | /workspace nur als fail-closed- oder metadata-only-Grenze zeigen. |
| `Sitzung offen` | Gelb. | "Die Sitzung ist nicht belastbar abgeschlossen." | Workspace-Grenzen-Fallback. |

## Gate-Kriterien

| Gate | Grün | Gelb | Rot |
| --- | --- | --- | --- |
| Token-Austausch | Bestätigt ohne sichtbare technische Details. | Anmeldung empfangen, aber Ergebnis offen. | `Token-Austausch: ungültig` oder `Token-Austausch: technisch nicht verfügbar`. |
| Token-Prüfung | Prüfung abgeschlossen. | Prüfung offen oder nicht gestartet. | Prüfung scheitert oder bleibt ohne belastbaren Nachweis. |
| Rollenprüfung | Demo-Rolle bestätigt. | Rollenprüfung offen. | Keine Demo-Rolle nachweisbar. |
| Sitzung | Sitzung abgeschlossen und demo-freigegeben. | Sitzung offen. | Keine belastbare Sitzung. |

## Fallback-Kriterien

In Fallback wechseln, sobald ein Gate gelb oder rot ist und nicht innerhalb der
vorab freigegebenen Demo-Zeit grün wird.

- Prozessmodell-Fallback: `https://notariat8.de/prozessmodell.html` zeigen,
  Immobilienkaufvertrag, Dauer, Parallelität und kritischen Pfad erklären.
- Readiness-Fallback: vorbereitete Readiness-/DNS-/Request-Statusflächen mit
  synthetischen Daten zeigen; keine neue Anfrage absenden.
- Workspace-Grenzen-Fallback: /workspace nur als fail-closed- oder
  metadata-only-Grenze zeigen; keine Akteninhalte, keine Mandatsdaten.
- Live-Login-Pfad stoppen, wenn Token-Austausch ungültig oder technisch nicht
  verfügbar ist.
- Nicht live debuggen, keine Cloud-Konsole, keine Anbieterwerte, keine
  Callback-Werte und keine Tokens öffnen.

## Zeigbar, Stopper, Fallback

| Zustand | Zeigbar | Stopper | Fallback |
| --- | --- | --- | --- |
| Grün | Login-Seite, geschützter Einstieg, freigegebene Startansicht ohne echte Daten. | Keine. | Bei Verzögerung auf Prozessmodell wechseln. |
| Gelb | Anmeldung empfangen, geschlossene Workspace-Grenze, Readiness-Status. | Kein geschützter Workspace als Erfolg behaupten. | Prozessmodell-Fallback oder Workspace-Grenzen-Fallback. |
| Rot | Fail-closed-Status als Sicherheitsnachweis. | Live-Login-Pfad stoppen. | Prozessmodell-Fallback und Nachanalyse nach dem Termin. |

## Redaktionsregeln

Öffentlicher Output bleibt kurz und nicht-technisch:

- keine Secrets
- keine Tokens
- keine Claims
- keine Provider-Details
- keine Callback-Werte
- keine Mandatsdaten
- keine echten IDs, Akten, Urkunden, Ausweise, Register- oder Grundstücksdaten
- keine Runtime-Änderung, keine OCI-/IaC-Änderung, keine produktive Handlung

Zulässige interne Ticket-Sprache: Ampelklasse, Gate-Name, kurzer Fehlertext und
Fallback-Entscheidung. Nicht zulässig: Rohwerte aus Browseradresse, Antwort,
Sitzung, Token, Claim, Anbieter-Konfiguration oder Mandatskontext.

## Stop-Lines

- "Der Login ist fail-closed; wir zeigen jetzt den geprüften Prozesspfad."
- "Ohne grüne Token-, Rollen- und Sitzungsprüfung öffnen wir keinen
  Arbeitsbereich."
- "Die Demo bleibt bei redigierter Diagnose; technische Details prüfen wir nach
  dem Termin."
- "Das ist kein produktiver Login-Nachweis, sondern eine sichere
  Demo-Entscheidung."
