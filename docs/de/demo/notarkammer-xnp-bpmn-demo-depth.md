# Notarkammer-Demo: XNP/BPMN-Demo-Tiefe

Stand: 2026-06-21

Dieses Artefakt ergänzt den 1h-Demo-Track für die Notarkammer. Es erklärt,
wie NaC XNP, XNotar/XJustiz, Grundbuch, Register, Kartenleser/Signatur und
externe Nachweise im BPMN-Modell sichtbar macht. Notariat-only: Die Sprache
bleibt bei notariellen Vorgängen wie Immobilienkaufvertrag,
Grundbuchvollzug, Handelsregisteranmeldung, Beglaubigung und
Nachweisführung. Es gibt keine Rohdaten, keine Mandatsdaten und nur
redigierte Evidence.

## Demo-Kernaussage

NaC ist in dieser Demo der BPMN-, Gate- und Audit-Rahmen. XNP bleibt eine
externe notarielle Arbeitsumgebung. XNotar/XJustiz, Grundbuch, Register,
Kartenleser und Signaturpfad bleiben externe Systemgrenze oder lokaler
Arbeitsplatzpfad. NaC behauptet keine Live-XNP-API-Zugriffe, keine produktive
XNP-Handlung und keine direkte XNP-zu-NaC-Grundbuchdatenlieferung.

Die Demo zeigt deshalb nicht, dass NaC Fachsysteme ersetzt. Sie zeigt, dass
NaC die fachliche Verantwortung, die Systemgrenze, den Nachweisstatus, das
Dauerband, die Parallelität und den Kritischer Pfad explizit modelliert. Der
primäre Fluss ist `Immobilienkaufvertrag`; SNP- und XNP-API-Zugänge werden nur
als ISV-Test- und Freigabefragen an BNotK/Notarkammer benannt.

## BPMN-Tasktypen für die 1h-Demo

| BPMN-Tasktyp | Wann zeigen | Notarielle Bedeutung | Erlaubter Nachweis |
| --- | --- | --- | --- |
| Service Task | Automatisierbarer NaC-Prüfpunkt ohne Fachsystemeingriff | NaC prüft, ob ein Gate formal weitergeführt werden darf, zum Beispiel Evidence vorhanden, Hash plausibel, Friststatus gesetzt | Status, Hash, Zeitstempel, Rolle, Prüfergebnis |
| User Task | Entscheidung oder Bestätigung durch Notariatsperson | Notariat prüft Entwurf, Vertretung, Freigabe, Rücklauf oder Versandstatus | redigierte Evidence, Freigabevermerk, `manual_review` oder `blocked` |
| Manual Task | Tätigkeit außerhalb von NaC | Lokaler Arbeitsplatz, XNP, XNotar/XJustiz, Grundbuch-/Registerportal, Kartenleser oder Signaturvorgang wird außerhalb der SaaS ausgeführt | Attestation ohne Dokumentinhalt, ohne PIN, ohne Loginwert |

Der wichtigste Satz für die Demo: Service Task erklärt NaC-Logik, User Task
erklärt notarielle Verantwortung, Manual Task erklärt externe oder lokale
Fachsystemarbeit.

## Modellierung der Fachsystemgrenzen

| Grenze | BPMN-Modellierung | Demo-Satz | Nicht behaupten |
| --- | --- | --- | --- |
| XNP lokal | Manual Task oder User Task mit lokalem Gate | "XNP bleibt lokal; NaC zeigt nur, dass dieser Schritt den nächsten BPMN-Status blockiert oder freigibt." | Live-Aufruf, Remote-Steuerung oder produktiver XNP-Vollzug durch NaC. |
| XNotar/XJustiz | Manual Task für Paket-, Austausch- oder Versandpfad plus User Task für Bestätigung | "Grundbuch- und Registerkommunikation bleibt ein externer Handoff mit Evidence-Frage." | NaC führt den Grundbuch- oder Registervollzug automatisch aus. |
| Grundbuch | External Gate mit Dauerband und Rücklaufstatus | "Der Grundbuchrücklauf kann den Kritischer Pfad bestimmen." | XNP oder NaC liefert Grundstücks- oder Grundbuchrohwerte in die Demo. |
| Register | External Gate mit Rücklaufstatus | "Registerrücklauf, Zwischenverfügung oder Eintragung sind externe Ereignisse." | NaC erzeugt produktiven Registerversand. |
| Kartenleser/Signatur | Manual Task am lokalen Arbeitsplatz | "Karte, Leser und PIN-Eingabe bleiben lokal; NaC sieht nur redigierte Evidence." | Kartenleser oder Signaturkarte sind Teil einer entfernten Automation. |
| externe Nachweise | User Task für fachliche Prüfung, Service Task für formale Vollständigkeit | "Nachweise sind Gate-Fragen, keine Rohdatenablage." | NaC speichert Ausweis-, Urkunden-, Register- oder Grundstücksrohwerte. |

## Dauer, Parallelität und kritischer Pfad

In der 1h-Demo werden Dauerwerte als Modellfenster erklärt, nicht als Zusage.
Das Dauerband beschreibt, wie lange ein Gate typischerweise die Erzählung
prägen kann. Parallelität beschreibt, welche Vorarbeiten im Notariat
gleichzeitig laufen können. Der Kritischer Pfad beschreibt, welcher externe
Rücklauf den nächsten Schritt blockiert.

Beispiel Immobilienkaufvertrag:

- Vorprüfung und Entwurf können mit Unterlagenliste, Rollenprüfung und
  Terminabstimmung parallel laufen.
- Nach der Beurkundung laufen Grundbuch, Finanzierung, Gemeinde, Steuer und
  Löschungsunterlagen parallel.
- Das Modellfenster für externe Vollzugsrückläufe kann 2-8 Wochen betragen.
- Der kritische Pfad ist der letzte fachlich notwendige Rücklauf, nicht die
  Bedienzeit in NaC.

Beispiel Handelsregisteranmeldung:

- Anlagenprüfung, Vertretungsprüfung, Signaturpfad und Paketvorbereitung
  können parallel vorbereitet werden.
- XNotar/XJustiz und Register bleiben als Handoff und Rücklauf modelliert.
- Ohne signierte, fachlich freigegebene Anmeldung bleibt der Registerpfad
  fail-closed.

## Guardrails für die Vorführung

- Notariat-only Sprache: nur notarielle Vorgänge, Rollen, Gates, Rückläufe
  und Nachweise nennen.
- Keine Rohdaten: keine Personen-, Register-, Grundstücks-, Ausweis-,
  Urkunden-, Karten- oder PIN-Inhalte zeigen.
- Keine Mandatsdaten: die Demo nutzt synthetische Begriffe, Statuswerte und
  Prozessmodelle.
- Nur redigierte Evidence: Status, Hash, Zeitpunkt, Rolle, Prüfergebnis und
  Blocker reichen aus.
- Keine Live-XNP-API-Zugriffe: offene technische Details bleiben "zu klären
  im XNP-Testzugang".
- Keine produktiven SNP- oder XNP-API-Claims: offizielle Testzugänge,
  Schnittstellenverträge, Zertifizierung und Pilotfreigabe sind
  Gesprächsfragen, keine Demo-Behauptung.
- Kein Produktionsversprechen: alle externen Fachsysteme bleiben Grenzen,
  Handoffs oder manuell bestätigte Gates.

## 1h-Sprechspur

1. "Wir zeigen zuerst den notariellen Prozess, nicht ein Fachsystem-Login."
2. "BPMN unterscheidet Service Task, User Task und Manual Task: NaC-Gate,
   notarielle Entscheidung und externe Fachsystemarbeit."
3. "XNP, XNotar/XJustiz, Grundbuch, Register, Kartenleser und Signatur sind
   bewusst modellierte Grenzen."
4. "Dauerband, Parallelität und Kritischer Pfad zeigen, warum externe
   Rückläufe fachlich wichtiger sind als eine lineare Klickstrecke."
5. "Ohne lokale Readiness oder redigierte Evidence bleibt der nächste Schritt
   fail-closed."
