# Notarkammer-Demo: Live-Checkkarte

Status: 2026-06-24

Diese Checkkarte ist die kurze Entscheidungshilfe direkt vor und während der
Vorführung. Sie fasst zusammen, wann der aktuelle Live-Stand gut genug ist und
wann ohne Debugging auf BPMN, Skript und Fallback-Evidence gewechselt wird.

Scope: Demo-Orientierung, öffentliche Prozesssicht und geschützter
Portal-Start. Keine Runtime-Änderung, keine Cloud-Änderung, keine Secrets,
no mandate data, keine Mandatsdaten, keine produktive XNP-Handlung, keine
produktive Einreichung.

## Live-Pfad

| Schritt | Route oder Sicht | Go | Fallback |
| --- | --- | --- | --- |
| L1 | `https://notariat8.de/prozessmodell.html` | Immobilienkaufvertrag, XNP/SNP, Dauerband, Parallelität und kritischer Pfad sind sichtbar. | Vorab geladene Sicht oder freigegebenen Screenshot zeigen. |
| L2 | `https://app.notariat8.de/login` | Der Nutzer startet auf notariat8 und löst die Anmeldung aus. | Nicht auf technische Endpunkte wechseln; vorbereitete Sprecherlinie nutzen. |
| L3 | `https://app.notariat8.de/workspace` nach Anmeldung | Portal-Start bereit: Sitzung ist aufgebaut, Rollengate bestätigt, role gate fachlich erfüllt. | Wenn die Sicht geschlossen bleibt: geschlossene Grenze erklären und zum Prozessmodell wechseln. |
| L4 | Erster Vorgang im Portal-Start | Immobilienkaufvertrag wird nur als metadata-only Einstieg gezeigt. | Auf `notarkammer-first-matter-metadata.md` und BPMN-Evidence wechseln. |

## Gut Genug Für Die Demo

Der Live-Stand ist ausreichend, wenn diese Bedingungen erfüllt sind:

1. `Portal-Start bereit` oder fail-closed ist klar sichtbar.
2. Sitzung und Berechtigung werden ohne interne Details beschrieben.
3. Der erste Vorgang bleibt metadata-only.
4. Kein vollständiger Arbeitsbereich wird geöffnet; no full workspace.
5. Keine Mandatsdaten werden geladen; no mandate data.
6. XNP/SNP wird als modellierte Fachsystemgrenze und Zielpfad erläutert.
7. Keine produktive XNP-Handlung und keine produktive Einreichung werden
   behauptet.

## Stop-Sätze

Diese Sätze begrenzen die Vorführung sauber:

- notariat8 zeigt hier den geschützten Startstatus, nicht die Akte.
- Der Immobilienkaufvertrag ist in BPMN modelliert; der vollständige
  Arbeitsbereich bleibt geschlossen.
- XNP/SNP ist als Zielpfad und Nachweisgrenze vorbereitet, produktive
  Schnittstellenfreigaben sind Teil der nächsten Abstimmung.
- Der kritische Pfad liegt im Vollzug vor allem bei externen Rückläufen.
- Wenn ein Live-Schritt geschlossen bleibt, ist das ein Sicherheitsverhalten,
  kein Anlass für Debugging im Termin.

## Nicht Sagen

- Es gibt keine produktive XNP- oder Grundbuchkopplung in dieser Demo.
- Es werden keine echten Urkunden, Registerwerte, Ausweise oder
  Kaufpreisdaten gezeigt.
- Es werden keine technischen Anbieter-, Schlüssel-, Sitzungs- oder
  Infrastrukturdetails gezeigt.
- Es werden keine produktiven Vorgänge eingereicht.

