# Notarkammer-Demo 2026-06: Live-Runbook

Status: Protected-PR-fähige Vorführ-Checkliste für die 1h-Live-Demo.

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

## T-03:00 Preflight-Reihenfolge

| Reihenfolge | Live-Test | Erwartung | Fallback |
| --- | --- | --- | --- |
| 1 | `https://notariat8.de` | Startseite lädt ohne Mandatsdaten. | Bereits geladenen Tab verwenden. |
| 2 | `https://notariat8.de/prozessmodell.html` | Immobilienkaufvertrag, Dauerlogik und kritischer Pfad sind sichtbar. | Screenshot oder geöffneten Tab nutzen. |
| 3 | `https://app.notariat8.de/healthz` | Kurzer, nicht-sensitiver Status. | Tab schließen, Workspace-Grenze zeigen. |
| 4 | `https://app.notariat8.de/login` | Login-Seite öffnet; keine echten Zugangsdaten eingeben. | Nicht debuggen, zum Prozessmodell wechseln. |
| 5 | `https://app.notariat8.de/workspace` | Ohne Sitzung bleibt der Arbeitsbereich geschlossen. | Fail-closed als Sicherheitsnachweis erklären. |
| 6 | XNP lokal | Kartenpfad, XNP-Localhost `12774` bis `12784` und Rolle sind nur lokal plausibel. | Keine Live-XNP-Aktion; Gate als `manual_review` oder `blocked` markieren. |
| 7 | XNotar/XJustiz-Übergabe | Austauschordner und Paketgrenze sind synthetisch oder leer prüfbar. | Kein Paket öffnen; nur die Übergabegrenze erklären. |

## 60-Minuten Live-Folge

1. 0-5 Minuten: `https://notariat8.de` zeigen und klar sagen, dass die
   öffentliche Sicht keine Mandatsdaten enthält.
2. 5-20 Minuten: `https://notariat8.de/prozessmodell.html` öffnen,
   Immobilienkaufvertrag, Dauerlogik, Parallelität und kritischer Pfad
   erklären.
3. 20-30 Minuten: Fachsystemgrenzen zeigen: XNP lokal für Readiness,
   Kartenleser und Signaturpfad; XNotar/XJustiz-Übergabe für Register- und
   Grundbuchkommunikation.
4. 30-40 Minuten: Falls lokal verfügbar, BPMN-Editor zeigen; sonst beim
   öffentlichen Prozessmodell bleiben. NaC BPMN/Evidence/Gate ist die
   Aussage, nicht Live-Automatisierung.
5. 40-50 Minuten: `https://app.notariat8.de/login` und
   `https://app.notariat8.de/workspace` als geschützten Einstieg zeigen.
6. 50-55 Minuten: Unterschriftsbeglaubigung als kurzen Vergleichsprozess
   nennen.
7. 55-60 Minuten: Zusammenfassen: sichtbare Fachsystemgrenzen, Protected PRs,
   redigierte Evidence, keine produktiven Register- oder Grundbuchhandlungen.

## 5-Minuten Kurzfolge

1. `https://notariat8.de` öffnen.
2. `https://notariat8.de/prozessmodell.html` zeigen.
3. Immobilienkaufvertrag, Dauer, Parallelität und kritischer Pfad benennen.
4. XNP lokal als Readiness-Gate erklären.
5. XNotar/XJustiz-Übergabe als Paket-/Austauschordnergrenze erklären.
6. `https://app.notariat8.de/login` und den geschlossenen Workspace zeigen.
7. Abschluss: NaC BPMN/Evidence/Gate macht Arbeit sichtbar und prüfbar.

## Stop-Lines

- Stop-Line: "Wir debuggen jetzt nicht live; die Demo zeigt den geprüften
  Prozesspfad."
- Stop-Line: "XNP bleibt lokal. XNP liefert keine Grundbuchdaten an NaC."
- Stop-Line: "XNotar/XJustiz ist hier eine Übergabegrenze, keine versteckte
  Cloud-Automation."
- Stop-Line: "Ohne Evidence bleibt das NaC-Gate blockiert."
- Stop-Line: "Diese Demo enthält keine Release-, Apply-, Runtime-, OCI- oder
  Cloud-Aktion."

## Protected-PR Nachweis

- Branch: `agent/notarkammer-live-demo-runbook-c`.
- Geänderte Flächen: `docs/de/demo/`, `docs/en/demo/`, `tests/`.
- Erwartete Checks: fokussierte Demo-Runbook-Tests, bestehende Demo-Kontrakt-,
  Demo-Skript- und Preflight-Tests.
- Audit-Spur: Commit-SHA, Testausgabe, Branch und PR-Link; keine Personen-,
  Akten-, Urkunden-, Ausweis-, Register- oder Grundstücksdaten.
