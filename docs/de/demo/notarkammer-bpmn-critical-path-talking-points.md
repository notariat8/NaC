# Notarkammer-Demo: BPMN Critical Path Talking Points

Diese Notizen ergänzen die öffentliche Notarkammer-Demo. Sie sind für eine
kurze Sprechspur zum Immobilienkaufvertrag gedacht und bleiben bewusst
source-agnostisch: gezeigt wird nur das freigegebene BPMN-Modell, keine
personenbezogenen Vorgangsinhalte, keine Betreiber- oder
Infrastrukturdetails und keine produktive Fachsystemhandlung.

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

## Kritischer Pfad

| Beat | Demo-Punkt | Nachweisfrage |
| --- | --- | --- |
| Entwurf und Vorprüfung | fachliche Eingaben, Beteiligte, Objekt- und Registerbezug prüfen | Ist der nächste notarielle Schritt fachlich freigegeben? |
| Beurkundung | Termin, Identität, Signatur- oder Präsenzpfad | Ist der Beurkundungsschritt abgeschlossen oder blockiert? |
| Grundbuch | Vormerkung, Löschungsunterlagen, Eigentumsumschreibung | Welche Rückmeldung wird vor dem nächsten Vollzugsschritt benötigt? |
| Register | falls Registerbezug entsteht, Übergabe als gesondertes Gate zeigen | Ist die Registerkommunikation nur vorbereitet oder bereits zurückgemeldet? |
| Abschluss | Zahlungsvoraussetzungen, Steuer, Nachweise, Umschreibung | Welche externe Rückmeldung blockiert den Abschluss? |

## Sichere Grenze

- Notariat only: Die Sprechspur bleibt bei notariellen Vorgängen,
  insbesondere Immobilienkaufvertrag und Grundbuch-/Registerhandoff.
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
