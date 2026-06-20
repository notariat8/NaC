# Notarkammer-Demo: Vollzug, Dauerlogik und kritischer Pfad

Diese Notiz dient als fachliche Demo-Stütze für die Notarkammer-Vorstellung.
Sie ist keine amtliche Statistik und enthält keine Mandatsdaten. Dauerangaben
sind bewusst als Planwerte modelliert: hours, days, weeks und months. Es sind
keine amtlichen Durchschnittswerte.

## Quellenstand

- Bundesnotarkammer, Kaufpreisfälligkeit:
  https://www.notar.de/themen/immobilien/kaufpreisfaelligkeit
- Bundesnotarkammer, Eigentumsübergang:
  https://www.notar.de/themen/immobilien/eigentumsuebergang
- Bundesnotarkammer, Notarkosten:
  https://www.notar.de/themen/notarkosten
- Bundesnotarkammer, Gebührenrechner:
  https://www.notar.de/themen/notarkosten/gebuehrenrechner

## Fachliche Ableitung für den Immobilienkaufvertrag

Der Vollzug ist nicht linear. Nach der Beurkundung laufen mehrere Stränge
parallel, aber nicht alle sind gleich wichtig für den nächsten rechtlichen
Schritt. Der kritische Pfad entsteht dort, wo ein Rücklauf Voraussetzung für
eine folgende Handlung ist.

Die Kaufpreisfälligkeit hängt nach der Bundesnotarkammer typischerweise davon
ab, dass erforderliche Genehmigungen vorliegen, die Eigentumsvormerkung im
Grundbuch eingetragen ist, Löschungsunterlagen für nicht übernommene
Belastungen vorliegen und das gemeindliche Vorkaufsrecht geklärt ist. Erst
dann informiert das Notariat die Beteiligten über die Fälligkeit.

Der Eigentumsübergang ist ebenfalls nachgelagert. Der Antrag auf Umschreibung
wird nach der Darstellung der Bundesnotarkammer erst nach vollständiger
Kaufpreiszahlung eingereicht. Zusätzlich kann die
Unbedenklichkeitsbescheinigung des Finanzamts erforderlich sein.

## Demo-Modellierung

| Phase | Planwert | Parallel möglich | Kritischer Pfad |
| --- | --- | --- | --- |
| Aufnahme und Vorprüfung | hours bis days | begrenzt | ja, wenn Unterlagen fehlen |
| Entwurf und Abstimmung | days | teilweise | ja, wenn Freigaben fehlen |
| Beurkundung | hours | nein | ja |
| Vormerkung, Genehmigungen, Löschung, Vorkaufsrecht | days bis weeks | ja | ja, wenn Fälligkeitsvoraussetzung |
| Kaufpreiszahlung und Besitzübergang | days bis weeks | teilweise | ja |
| Steuer-/Grundbuchrückläufe und Eigentumsumschreibung | weeks bis months | ja | ja, wenn Rücklauf fehlt |

## Demo-Aussage

Die Visualisierung sollte nicht behaupten, wie lange ein konkreter Fall dauern
wird. Sie sollte zeigen:

- welche Arbeit sofort beginnen kann,
- welche Schritte auf externe Rückläufe warten,
- welche Rückläufe den kritischen Pfad blockieren,
- wo Dauerklassen als editierbare Planwerte gepflegt werden,
- warum eine lineare Vier-Schritte-Darstellung den Vollzug fachlich zu stark
  vereinfacht.

## Gebührenlogik

Die Notarkosten sind gesetzlich geregelt und nicht frei verhandelbar. Für die
Demo ist relevant, dass eine Gebührenkomponente als wiederverwendbares Modul
gedacht werden kann: Der Gebührenrechner gehört nicht in jeden Usecase neu,
sondern als zentral gepflegtes GNotKG-Modul in die Vorgangsbearbeitung.

Die öffentliche Demo sollte dabei nur zeigen, dass die Gebührenlogik als
Modul vorgesehen ist. Sie sollte keine verbindliche Kostenberechnung und keine
echten Geschäftswerte anzeigen.
