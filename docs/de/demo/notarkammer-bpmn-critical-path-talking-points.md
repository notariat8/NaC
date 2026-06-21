# Notarkammer-Demo: BPMN Critical Path Talking Points

Diese Notizen ergänzen die öffentliche Notarkammer-Demo. Sie sind für eine
kurze Sprechspur zum Immobilienkaufvertrag und zur Handelsregisteranmeldung
gedacht und bleiben bewusst source-agnostisch: gezeigt wird nur das
freigegebene BPMN-Modell, keine personenbezogenen Vorgangsinhalte, keine
Betreiber- oder Infrastrukturdetails und keine produktive Fachsystemhandlung.
Alle Dauerangaben sind Planwerte für die Demo-Erzählung und keine
Rechtsberatung oder Bearbeitungszusage.

## Sprechspur

- "Der Immobilienkaufvertrag ist ein Notariat-Usecase mit mehreren
  fachlichen Rückläufen. BPMN macht sichtbar, welche Schritte parallel
  vorbereitet werden können und welcher Schritt den kritischen Pfad blockiert."
- "Der kritische Pfad liegt nicht bei der schönsten Benutzeroberfläche,
  sondern bei den fachlichen Gates: Vorprüfung, Beurkundung, Grundbuch,
  Finanzierung, Gemeinde, Steuer und abschließende Eigentumsumschreibung."
- "Für Grundbuch und Register zeigt NaC eine Übergabegrenze. Das Modell
  benennt, wann ein XNotar/XJustiz-Paket, ein Austauschordner, ein Portal oder
  ein lokaler Kartenleser-/Signaturpfad relevant wird."
- "NaC ersetzt diese Fachsysteme nicht. Es hält die Nachweisfrage fest: Wer
  hat welche Übergabe vorbereitet, geprüft, freigegeben oder als Rücklauf
  dokumentiert?"
- "Die Handelsregisteranmeldung zeigt denselben Punkt auf kürzerem Pfad:
  Entwurf, Beschluss- oder Vertretungsgrundlage, Signatur, Einreichung und
  Registerrücklauf sind unterschiedliche Gates. Einige Vorarbeiten dauern
  Minuten oder Stunden, der blockierende Rücklauf kann Tage oder Wochen
  bestimmen."

## Prozess 1: Immobilienkaufvertrag

| Beat | Demo-Punkt | Planwert | Parallel vorbereitbar | Blockierendes Ereignis | Kritischer-Pfad-Hinweis |
| --- | --- | --- | --- | --- | --- |
| Intake und Vorprüfung | Beteiligte, Objektbezug, Entwurfsauftrag und Checkliste strukturieren | 15-30 Minuten | Identitäts-/Rollenprüfung, Unterlagenliste, Finanzierungsabfrage | fehlende Objekt- oder Beteiligtenangaben | Ohne vollständige Vorprüfung kein belastbarer Entwurf. |
| Entwurf und Abstimmung | Vertragsentwurf, Anlagen, Kosten- und Vollzugshinweise vorbereiten | 2-6 Stunden | Entwurfsprüfung, Rückfragen, Terminabstimmung | offener Änderungswunsch oder fehlende Freigabe | Entwurfsfreigabe ist das Gate vor Beurkundung. |
| Beurkundung | Termin, Identität, Signatur- oder Präsenzpfad durchführen | 60-120 Minuten | Vollzugsakte und Versandpakete vorbereiten | Terminverschiebung oder Identitäts-/Vertretungsfrage | Erst nach Beurkundung starten die Vollzugsgates. |
| Vollzug parallelisieren | Vormerkung, Löschungsunterlagen, Finanzierung, Gemeinde und Steuer anstoßen | 1-3 Arbeitstage Vorbereitungszeit | Grundbuchpaket, Finanzierungsunterlagen, Vorkaufsrechtsanfrage, Steueranzeige | fehlende Bank-, Gemeinde-, Steuer- oder Grundbuchrückmeldung | Der längste externe Rücklauf bestimmt die Demo-Erzählung. |
| Eigentumsumschreibung | Zahlungsvoraussetzungen, Unbedenklichkeit, Löschungen und Umschreibung nachhalten | 2-8 Wochen als Modellfenster | Statusnachweise und Erinnerungen vorbereiten | Rücklauf aus Grundbuch, Finanzierer, Gemeinde oder Steuer fehlt | Kritischer Pfad liegt beim letzten erforderlichen Rücklauf. |
| Abschlussnachweis | Abschlussstatus, Nachweise und sichere Ablage erklären | 15-30 Minuten | Abschlusskommunikation, Kontrollvermerk | widersprüchlicher oder fehlender Nachweis | Abschluss erst, wenn alle Gates fachlich grün sind. |

## Prozess 2: Handelsregisteranmeldung

| Beat | Demo-Punkt | Planwert | Parallel vorbereitbar | Blockierendes Ereignis | Kritischer-Pfad-Hinweis |
| --- | --- | --- | --- | --- | --- |
| Anlass und Registerbezug klären | Anmeldungstyp, Rechtsträger, Vertretung und Beschlusslage modellieren | 10-25 Minuten | Registerauszug prüfen, Beteiligtenrollen, Unterlagenliste | unklare Vertretung oder fehlender Beschluss | Ohne tragfähige Grundlage keine Einreichung. |
| Entwurf der Anmeldung | Anmeldetext, Anlagen und Vollmachten vorbereiten | 45-120 Minuten | Anlagenprüfung, Registerdatenabgleich, Terminfenster | fehlende Anlage oder widersprüchliche Registerlage | Entwurf muss vor Signatur fachlich stimmig sein. |
| Beglaubigung oder Beurkundungsbezug | Identität, Vertretung und Signaturpfad abschließen | 30-60 Minuten | Versandpaket und interne Prüfliste | Identitäts-, Signatur- oder Vertretungsproblem | Dieses Gate blockiert jede Registerkommunikation. |
| XNotar/XJustiz-Paket vorbereiten | Austauschpaket und Registerportal-Handoff erklären | 15-45 Minuten | technische Readiness, Anlagenbenennung, Freigabevermerk | fehlende Datei, falsche Zuordnung oder fehlende Freigabe | NaC zeigt Vorbereitung und Freigabe; die Übergabe bleibt außerhalb der Demo. |
| Registerrücklauf beobachten | Eingangsbestätigung, Zwischenverfügung oder Eintragung als Rücklauf modellieren | 2 Tage bis 3 Wochen als Modellfenster | Wiedervorlage, Statusnotiz, Rückfragenentwurf | Zwischenverfügung oder fehlender Registerrücklauf | Registerrücklauf ist der kritische Pfad nach der Einreichung. |
| Abschluss und Nachweis | Eintragungsnachweis, Beteiligteninformation und Ablage erklären | 15-30 Minuten | Abschlusskommunikation und Kontrollvermerk | Eintragungsnachweis fehlt | Abschluss erst nach fachlichem Rücklauf. |

## Parallele Vorarbeiten

- Bei beiden Prozessen können Unterlagenlisten, Rollenprüfung,
  Terminabstimmung, Entwurfsprüfung und Paketvorbereitung parallel laufen,
  solange kein Gate eine fachliche Freigabe voraussetzt.
- Im Immobilienkaufvertrag laufen nach Beurkundung mehrere Stränge nebeneinander:
  Grundbuch, Finanzierung, Gemeinde, Steuer und Löschungsunterlagen.
- In der Handelsregisteranmeldung laufen Anlagenprüfung, Vertretungsprüfung,
  Signaturpfad und Paketvorbereitung nebeneinander, bis die notarielle
  Freigabe den Registerhandoff erlaubt.
- Die Demo sollte Dauer nicht als SLA erklären, sondern als Planwert:
  Minuten für Erfassung und Abschluss, Stunden für Entwurf und Prüfung, Tage
  für Paket- und Rückfragefenster, Wochen für externe Rückläufe.

## Blockierende Ereignisse

- fehlende oder widersprüchliche Unterlagen
- ungeklärte Vertretungs-, Identitäts- oder Signaturfrage
- nicht freigegebener Entwurf
- fehlender Grundbuch-, Register-, Gemeinde-, Steuer- oder Finanzierungsrücklauf
- Zwischenverfügung, Rückfrage oder Korrekturbedarf
- fehlender Abschlussnachweis

## Kritischer Pfad und Nachweisfrage

| Beat | Demo-Punkt | Nachweisfrage |
| --- | --- | --- |
| Entwurf und Vorprüfung | fachliche Eingaben, Beteiligte, Objekt- und Registerbezug prüfen | Ist der nächste notarielle Schritt fachlich freigegeben? |
| Beurkundung | Termin, Identität, Signatur- oder Präsenzpfad | Ist der Beurkundungsschritt abgeschlossen oder blockiert? |
| Grundbuch | Vormerkung, Löschungsunterlagen, Eigentumsumschreibung | Welche Rückmeldung wird vor dem nächsten Vollzugsschritt benötigt? |
| Register | Handelsregisteranmeldung als gesondertes Gate zeigen | Ist die Registerkommunikation nur vorbereitet oder bereits zurückgemeldet? |
| Abschluss | Zahlungsvoraussetzungen, Steuer, Nachweise, Umschreibung | Welche externe Rückmeldung blockiert den Abschluss? |

## Sichere Grenze

- Notariat only: Die Sprechspur bleibt bei notariellen Vorgängen,
  insbesondere Immobilienkaufvertrag, Handelsregisteranmeldung und
  Grundbuch-/Registerhandoff.
- Keine personenbezogenen Vorgangsinhalte: Die Demo nutzt nur öffentliche
  Prozessreferenzen und Modellbegriffe.
- Source-agnostisch: Keine internen Betreiber-, Tenant- oder
  Infrastrukturdetails nennen.
- Kein Produktionsversprechen: XNP, Kartenleser, XNotar/XJustiz, Grundbuch
  und Register werden als Grenzen, Pakete, Portale, lokale Readiness und
  menschlich freigegebene Gates erklärt.

## Nicht sagen

- "NaC führt den Grundbuch- oder Registervollzug automatisch aus."
- "XNP liefert die Grundbuchdaten in NaC."
- "Der Kartenleser ist Teil einer entfernten Automation."
- "Das ist bereits ein vollständiges Notariatsprodukt."
- "Wir zeigen echte Urkunden, echte Registerinhalte oder echte
  Grundstücksdaten."

## Übergabe

Der stärkste Abschluss für diesen Abschnitt ist:

"BPMN macht nicht nur den Ablauf sichtbar, sondern die kritische
Verantwortung: Was kann im Notariat vorbereitet werden, welcher externe
Rücklauf blockiert den nächsten Schritt, und welche Übergabe bleibt bewusst
außerhalb der Demo?"
