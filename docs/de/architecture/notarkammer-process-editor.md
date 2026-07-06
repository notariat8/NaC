# Notarkammer Prozess-Editor

Status: Contract-first, kein produktiver Cloud-Apply.

Der Notarkammer Prozess-Editor beschreibt die sichere Grenze zwischen
BPMN-Editor, BPMN-Viewer, Git-Templates und M365/SharePoint-Runtime-
Metadaten. Ziel ist ein vorzeigbarer Immobilienkaufvertrag, der die
XNP/SNP-Grenzen, XNotar/XJustiz, Grundbuch, Kartenleser, Vollzug,
Parallelität, Dauerband und kritischer Pfad sichtbar macht.

## Daten- und Speichergrenze

- Git bleibt Source of Truth für BPMN-Templates, Verträge, Governance und
  Review-Nachweise.
- M365/SharePoint-Listen, Dokumentbibliotheken und ein späteres Event-Journal
  sind die Runtime-Datenebene für Tenant, Vorgang, Prozessinstanz,
  Prozessereignisse, Audit-Metadaten und Graph-Projektion.
- Keine Mandatsdaten werden im Template oder in der öffentlichen Demo
  gespeichert.
- Es erfolgt kein produktiver XNP-Zugriff und kein Live-Registerabruf in
  diesem Vertrag.

## Bearbeitbare Flächen

Der Editor darf nur demo- und review-sichere Struktur bearbeiten:

- BPMN-Editor-Struktur und Schrittbezeichnungen.
- Dauerband pro Schritt, zum Beispiel Minuten, Stunden, Tage, Wochen oder
  Monate.
- Parallelgruppen für Arbeiten, die gleichzeitig vorbereitet werden können.
- Hinweise zum kritischen Pfad, wenn ein externer Rücklauf oder eine Freigabe
  den Vollzug blockiert.
- XNP/SNP-, XNotar/XJustiz-, Grundbuch- und Kartenleser-Gates als
  Modellgrenzen.

Jede Änderung an einem Template läuft über Review und Protected PR, bevor sie
in den Template-Katalog gelangt.

## Viewer und Demo

Der Viewer zeigt die fachliche Prozessstruktur, nicht den Mandatsinhalt. Für
die Notarkammer-Demo ist der wichtigste Punkt: NaC kann zeigen, wo im
Immobilienkaufvertrag XNP/SNP-Kommunikation nötig wäre, welche Schritte
parallel laufen können und welche Gates den kritischen Pfad bestimmen. Die
Graph-Projektion aus Runtime-Ereignissen kann später denselben Ablauf als
Statussicht darstellen.
