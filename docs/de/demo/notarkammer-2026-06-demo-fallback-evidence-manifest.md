# Notarkammer-Demo 2026-06: Fallback-Evidence-Manifest

Status: geschützter Demo-Nachweis für vorbereitete Screenshots und
Ersatzansichten. Keine produktive Einreichung, keine echten Mandatsdaten, keine
Secrets.

Dieses Manifest beschreibt, welche vorbereiteten Ansichten in der
Notarkammer-Demo verwendet werden dürfen, wenn Live-Seiten langsam sind oder
ein lokaler Arbeitsplatz nicht bereit ist. Es ersetzt keine Live-Prüfung,
sondern verhindert Ad-hoc-Debugging im Termin.

## Erlaubte vorbereitete Evidence

| Evidence | Erlaubter Inhalt | Zweck |
| --- | --- | --- |
| `notariat8.de` Startseite | Öffentliche Startseite ohne Akten- oder Mandatsbezug. | Einstieg stabil zeigen, wenn die Seite nicht lädt. |
| `notariat8.de/prozessmodell.html` | Prozessmodell Immobilienkaufvertrag mit Dauerlogik, Parallelität und kritischem Pfad. | BPMN-Logik erklären, wenn der Viewer nicht lädt. |
| `app.notariat8.de/workspace` | Geschlossene oder metadata-only Ansicht mit fail-closed Status. | Sicherheitsgrenze zeigen, wenn Login nicht fortgesetzt wird. |
| XNP und card reader Readiness | Nur lokaler Status `ready`, `manual_review` oder `blocked`; keine Rohdaten. | XNP als lokale Arbeitsplatzgrenze erklären. |
| Protected PR | Pull Request, Checks und redigierte Testausgabe. | Änderungs- und Freigabespur zeigen. |

## Nicht erlaubte Evidence

- keine echten Mandatsdaten
- keine Ausweise
- keine Urkunden
- keine Registerauszüge
- keine Grundbuchdaten
- keine Zugangsdaten
- keine PINs
- keine Tokens
- keine Schlüssel
- keine produktive Einreichung
- keine produktive XNP-, Register- oder Grundbuchaktion

## Redaktionsregel

Screenshots und Nachweise dürfen nur sichtbare Produkt- oder
Prozessoberflächen zeigen. Fenster mit Logins, Tokens, Cookies, Session-Werten,
interner Infrastruktur, Secret-Referenzen, Wallets oder echten Namen werden
nicht verwendet. Wenn ein Screenshot unsicher ist, wird er nicht gezeigt.

## Stop-Line

"Wir zeigen jetzt die vorbereitete, redigierte Evidence. Sie belegt den
geprüften Demo-Stand und enthält keine Mandatsdaten."
