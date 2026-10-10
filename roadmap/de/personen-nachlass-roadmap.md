# Roadmap: Personen, Genogramme, Vermögen und zeitliche Nachlassszenarien

Stand: 2026-10-10 · Status: geplantes Backlog, noch nicht implementiert  
Auftrag und Akzeptanzkriterien: [Issue #772](https://github.com/notariat8/NaC/issues/772)  
Einordnung: [Globale Roadmap](../GANTT.md)  
Lizenz: CC-BY-4.0

## Ziel und NaC-Anbindung

NaC soll notarielle Nachlassplanung unterstützen: strukturierte Personen- und Familienbeziehungen, ein daraus abgeleitetes Genogramm, Vermögen mit Eigentumsanteilen sowie nachvollziehbare Szenarien für Schenkungen, Testamente und zeitlich unterschiedliche Erbfälle. Der bestehende MVP wird dadurch nicht als umgesetzt oder umpriorisiert dargestellt.

Anknüpfungspunkte sind das [Notarsoftware-Datenmodell](../../docs/de/notarsoftware-datenmodell.md), der [KG-Editor](../../docs/de/kg-editor-workstream.md), die bestehenden notariellen Nachlass-/Testaments-Usecases und der Legal-Graph-Workstream. Deren statische fachliche Knowledge Graphs bleiben von konkreten Personen- und Vermögensdaten getrennt. Fachliche KG-Artefakte bleiben usecase-lokal; kein zentraler knowledge-graph-Ordner.

## Speicher- und Modellrichtung

SharePoint wird auf Wunsch des Owners als Zielkandidat für den produktiven Personenspeicher im vorhandenen M365-Modell eingeplant. Die konkrete Listentopologie, Payload-Ablage und produktive Freigabe bleiben Teil der ersten Designphase.

| Ebene | Geplanter Inhalt und Verantwortung |
| --- | --- |
| GitHub | Code, versionierte JSON Schemas, Ontologie, Validierungsregeln, freigegebene Fachregeln und synthetische Beispiele. Keine echten Personen- oder Mandatsdaten. |
| SharePoint-Listen | Zweckgebundene Personenstammdaten, Beziehungen, Vermögensobjekte, Eigentumsanteile, Verfügungsmetadaten und Ereignisse in getrennten Entitätstypen; stabile fachliche IDs. Zugriff nach Notar-Team, Rolle und Mandatskontext. |
| Geschützte Payloads und Bibliotheken | Große strukturierte Personen-Payloads und Dokumente mit getrennten Schutzklassen, Versionen und Pointern. Speicherort und Verschlüsselung werden vor produktiver Nutzung geprüft. Kein großes JSON-Schema mit Hunderten frei sichtbaren Listenspalten. |
| Python-Graph-Projektion | Ein fall- und zeitpunktbezogener Graph für Familien- und Eigentumsabfragen; NetworkX als Kandidat für den In-Memory-Prototyp. |
| RDF/Turtle | Kandidat für semantische Ontologie und Graph-Austausch mit RDFLib, SPARQL und SHACL. RDF ist das Datenmodell, Turtle eine Serialisierung. |
| Graphdatenbank | Optionaler späterer Query-/Projektionsspeicher nach Benchmark und Betriebsentscheidung; nicht allein durch die Zahl 10.000 begründet. |

Ein führendes Datenmodell und definierte Mapping-/Versionsregeln vermeiden auseinanderlaufende Wahrheiten zwischen Listen, JSON und RDF. Ein großer Personen-Payload wird in Stammdaten, Beziehungen, Rollen, Nachweise und fachliche Erweiterungen gegliedert. Fehlende Angaben bleiben unbekannt, statt als Nein oder als erfundene Beziehung zu erscheinen.

Für 10.000 Personen werden Indizes, selektive Abfragen und Pagination von Anfang an geplant. SharePoint hat eine List-View-Schwelle von 5.000 Elementen; diese ist keine Obergrenze für den gesamten Personenbestand. Ein vollständiger Export braucht eine eigene getestete Strategie, statt eine ungefilterte Ansicht vorauszusetzen. Technische Quellen: [List-View-Schwelle](https://learn.microsoft.com/en-us/troubleshoot/sharepoint/lists-and-libraries/items-exceeds-list-view-threshold), [Indizes und Filter](https://learn.microsoft.com/en-us/troubleshoot/sharepoint/lists-and-libraries/fails-filtering-sharepoint-column).

## Fachliche Bausteine

- Person: stabile person_id, modularer schema_version, relevante Stammdaten, Nachweisreferenzen und getrennte Aktenrollen.
- Beziehung: eigene relationship_id, Typ, beteiligte person_ids, Gültigkeitszeit, Quelle, Prüfstatus und Unsicherheit. Elternschaft, Adoption, Ehe und Trennung werden fachlich unterschieden; Personen können mehreren Akten zugeordnet sein.
- Vermögen: asset_id, Typ (Haus, Auto, Aktien/Beteiligung, Bargeld/Konto), Bewertungsstichtag, Währung, Eigentumsanteile, Verbindlichkeiten und belastende Rechte. Eigentum, Besitz und Nutzungsrechte sind getrennt.
- Verfügung: Testament, Erbvertrag oder Schenkungsvereinbarung mit Version, zeitlicher Wirkung, begünstigten IDs, Dokumentreferenz und fachlicher Bestätigung.
- Ereignis: beispielsweise Schenkung, Anteilstransfer, Bewertung, Todesfall oder dokumentierte Korrektur. effective_at beschreibt die fachliche Wirkung; recorded_at den Zeitpunkt der Erfassung. Unbekannte oder nur ungefähr bekannte Zeiten bleiben sichtbar.
- Szenario: isolierte Annahmen, Ereignisreihenfolge, Regelversion und Ergebnisse. Hypothetische Todesfälle verändern keine bestätigten Stammdaten.

## Phasen und überprüfbare Ergebnisse

Die Reihenfolge beschreibt Abhängigkeiten, keine zugesagten Kalendertermine. Alle Phasen sind geplant.

| Phase | Umfang | Ergebnis und Abnahmekriterium |
| --- | --- | --- |
| P0: Design und Speichergrenze | SharePoint-Ziel, JSON-/RDF-Rollen, Zugriffe, Schutzklassen und Rechtsraum bestimmen. | Freigegebene zweisprachige Spec mit AC-IDs, Plan und Prüfpfaden; ein führendes Modell, genehmigte Speichergrenzen und klare Nichtziele. |
| P1: Personen und Familie | Modulare JSON Schemas, stabile IDs, Beziehungen und Import-/Änderungsvertrag. | Ein kleiner synthetischer Familienfall validiert; fehlende Referenzen, unzulässige Selbstbeziehungen, widersprüchliche Zeiten und Dubletten werden nachvollziehbar behandelt. |
| P2: Speicheradapter und 10.000er-Prototyp | Synthetische JSON-Dateien als Referenzdataset; SharePoint-Adapter zunächst offline, später in freigegebenem Testtenant. | 10.000 synthetische Personen importierbar; paginierte Lesewege, ID-Erhalt, Schema-Migration, Konflikte, Neustart und Berechtigungsgrenzen geprüft. Laufzeit, Speicherbedarf und Abfragezeiten dokumentiert. |
| P3: Genogramm | Deterministische Familienprojektion, Legende, Export und Codex-Anbindung. | Gleiche Daten ergeben dieselben Knoten und Beziehungen; mehrere Partnerschaften, Adoption, Verstorbene und unbekannte Angaben sichtbar. Keine automatisch erfundenen Verbindungen. |
| P4: Vermögensgraph | Objekte, Anteilshistorie, Bewertungen, Verpflichtungen und Schenkungen. | Eigentum je Stichtag rekonstruierbar; vollständige Anteilsbestände summieren sich korrekt, unvollständige Bestände werden markiert. Werte bleiben an Bewertungsdatum und Quelle gebunden. |
| P5: Zeitliche Nachlassszenarien | Testamentabhängige Simulation, Sterbereihenfolge und Ereignishistorie. | Beide Sterbereihenfolgen und verschiedene Todeszeitpunkte sind reproduzierbar; Ergebnis nennt Annahmen, Daten-/Regelversion, Berechnungsweg, offene Fragen und notarielle Prüfpunkte. |
| P6: Bedienung und Betriebsentscheidung | Zentrale nac-CLI, Bürooberfläche, Review-Flow und Backend-Benchmark. | Freigegebene CLI-/UI-Sichten unterstützen Lesen, Validieren, Visualisieren und Szenarien; Graphdatenbank nur bei belegtem Nutzen für Query, Parallelität oder Betrieb. |

P0 → P1 → P2 → P3 ist der Familienpfad. P4 baut auf P1/P2 auf; P5 braucht P3/P4 und fachlich freigegebene Regeln. P6 integriert die geprüften Bausteine.

## Durchgehender synthetischer Referenzfall

1. Ein Mann überträgt seiner Frau zu Zeitpunkt T1 ein Haus oder einen dokumentierten Anteil.
2. Der Vater schenkt der Tochter zu T2 ein Auto.
3. Der Vater überträgt dem Sohn in mehreren Jahren Aktien; jede tatsächlich erfolgte Übertragung ist ein eigenes Ereignis.
4. Ein dokumentiertes Testament beziehungsweise mehrere Versionen werden mit ihrer zeitlichen Wirkung berücksichtigt.
5. Szenario A: Vater stirbt zuerst, Mutter später. Szenario B: Mutter stirbt zuerst, Vater später.
6. Todeszeitpunkte werden vor und nach einzelnen Übertragungen variiert. Auch unklare Reihenfolge und fehlende Zeitangaben müssen als Unsicherheit behandelbar sein.

Die Ausgabe soll Genogramm, Vermögen unmittelbar vor dem jeweiligen Todesfall, bereits erfolgte Übertragungen und potenzielle Nachlass-/Anspruchsfolgen nebeneinander zeigen. Eigentumsbestand, erbrechtliche Zuordnung, Pflichtteilsfragen und steuerliche Betrachtung sind getrennte Berechnungsebenen. Konkrete Regeln, Fristen und Rechtsfolgen werden erst nach Quellenprüfung und notarieller Freigabe implementiert; insbesondere keine pauschale Zehnjahreslogik für alle Schenkungen.

## Codex und fachliche Wahrheit

Codex strukturiert Eingaben und schlägt nachvollziehbare Patches vor. Schema- und Referenzvalidierung, Diff und menschliche Bestätigung gehen einer Änderung voraus. Genogramme werden aus belegten Beziehungen erzeugt; Berechnungen laufen deterministisch in Python. Jede Ausgabe ist an Datenstand, Stichtag, Regelversion und Quellenreferenzen gebunden. Offene Tatsachen und fehlende Regeln führen zu markierten offenen Ergebnissen.

Geplante Bedienaktionen sind Personen-/Beziehungsvalidierung, Genogramm-Export, Vermögensansicht zu einem Stichtag und Nachlassszenario-Vergleich über die zentrale nac-CLI und Bürooberfläche. Namen und Verträge werden in P0 festgelegt; diese Roadmap behauptet keine bereits verfügbaren Befehle.

## Nächster Umsetzungsschritt

P0 vorbereiten: SharePoint-Datenmodell und Schutzgrenzen konkretisieren, JSON-first mit abgeleiteter RDF-Projektion gegen RDF-first mit JSON-Eingabevertrag vergleichen und den kleinen synthetischen Referenzfall festlegen. Vor Umsetzung gelten die bestehenden NaC-Design-, Spec-, Review-, Datenschutz- und Qualitätsregeln. Diese Roadmap speichert die Ideen und autorisiert keine produktive Tenant-Änderung.
