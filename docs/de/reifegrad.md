# Reifegrad: Was Heute Nutzbar Ist

Diese Seite trennt klar zwischen lauffähigem Kern, Pilotflächen, Planung und
bewusst gesperrter Automatisierung. Sie soll fachlichen Entscheidern helfen,
NaC realistisch einzuordnen.

## Reifegrad-Matrix

| Bereich | Stand | Was das bedeutet |
| --- | --- | --- |
| Repository klonen und lesen | Heute nutzbar | Die Struktur, Policies, Usecases und Startpfade sind öffentlich nachvollziehbar. |
| CLI-/Python-Kern ausführen | Heute nutzbar | Die stabile Logik läuft lokal und kann später von Plugins, CI oder UI-Schichten bedient werden. |
| Quality Gate lokal ausführen | Heute nutzbar | Tests, Sprachregeln, Datenschutzlint, Plugin-Validierung, KG-Validierung und Gantt-Regel laufen lokal. |
| Usecase-KGs prüfen | Heute nutzbar | Jeder Usecase hat eine maschinenlesbare KG und eine menschliche Review-Sicht. |
| KG-Editor-View anzeigen | Heute nutzbar | Fachpersonal kann offene Knoten als sichere Formular-/Checklisten-Sicht ansehen, ohne `value`-Felder zu bearbeiten. |
| BPMN-js Business Layer | Profil vorhanden | BPMN 2.0 ist fachliche Prozessquelle; ein erstes bpmn-js-taugliches Modell und die Python-Prüfung sind vorhanden. |
| Privater Betriebs-Fork | Pilotfähig | Ein Notariat kann das Muster in einen privaten Fork übernehmen und Rollen, Freigaben und lokale Speicherorte definieren. |
| Lokale Karten-/XNP-Readiness | Pilotfähig | Die Plugin-Pfade prüfen zunächst technische Bereitschaft und Metadaten, keine echte Signatur oder produktive Einreichung. |
| Fachsystem-Connectoren | Geplant / Integrationsarbeit | Schreibende Adapter brauchen gesonderte Freigabe, Datenschutzklärung, Testmodus und Verantwortlichkeitsmodell. |
| Automatische Register-, Portal- oder Fachsystemeinreichung | Bewusst gesperrt | Keine produktive Schreibaktion ohne geprüften Connector, menschliche Freigabe und privaten Betriebsrahmen. |
| Echte Mandatsdaten im öffentlichen Repo | Verboten | Personen-, Register-, Finanz-, Gesundheits-, Nachlass- und Familiendaten gehören nicht in dieses Repository. |
| KI als finale Rechtsentscheidung | Verboten | KI strukturiert und vorbereitet; die fachliche Verantwortung bleibt beim Menschen. |

## Kurzform Für Entscheider

NaC ist heute stark als prüfbares Muster, lokaler Kontrollrahmen und
Pilotvorbereitung. Der produktive Kanzlei- oder Notariatsbetrieb entsteht erst
in einem privaten Fork mit lokalen Systemen, Rollen, Datenschutzklärung und
menschlichen Freigaben.

## Nächste Dokumente

- [docs/de/notar-start.md](notar-start.md)
- [ausfuehrungsmodell.md](ausfuehrungsmodell.md)
- [bpmn-js-business-layer.md](bpmn-js-business-layer.md)
- [docs/de/betriebsstart.md](betriebsstart.md)
- [docs/de/integration-start.md](integration-start.md)
- [pruefung-standardisierung-start.md](pruefung-standardisierung-start.md)
