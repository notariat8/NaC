# Technologieentscheidung für das Musterrepo

## Ergebnis in einem Satz

Verbindlicher Standard ist:

- Dokumentation in Markdown (Quelle), PDF-Export automatisiert,
- Prozessausführung in Python, aber fachlicher Ablauf BPMN-2.0-first,
- BPMN-2.0 als kanonisches Fachmodell, `bpmn-js` als geplante visuelle
  Bearbeitungsschicht, Mermaid nur für Übersicht.

## Bewertung der aktuellen Fassung

Die aktuelle Fassung ist gut als Start, aber noch nicht die beste Endform für skalierbare Unternehmensdokumentation. Grund:

- Stark in kollaborativer Markdown-Dokumentation,
- stark in Python-Referenzlogik,
- aber BPMN-2.0 war bisher nicht als verbindliche Quellnorm definiert.

Mit der vorliegenden Policy wird das geschlossen.

## a) Dokumentation: Markdown vs AsciiDoc vs Superdoc

### Bewertung

- `Markdown`: beste Lesbarkeit, breiteste Toolunterstützung, ideal für LLM/Copilot/Cursor-Kollaboration.
- `AsciiDoc`: staerker für komplexe Publikations-Layouts und klassische Handbuchstrukturen.
- `Superdoc`: kein belastbarer De-facto-Standard für langfristige, revisionsfeste Unternehmensdokumentation.

### Entscheidung

- Quelle bleibt `Markdown`.
- PDF wird aus Markdown automatisiert exportiert (Pandoc-Pipeline).
- AsciiDoc wird nicht als zweite manuelle Quelle gepflegt, um Doppelpflege zu vermeiden.

Damit werden Kollaboration und PDF-Fähigkeit kombiniert.

## b) Python code-first für Geschäftsprozesse unter BPMN-2.0-Vorgabe

### Bewertung

Reines code-first ist für Fachbereiche langfristig nicht optimal, weil:

- Fachlogik in Code für Nicht-IT schwer prüfbar wird,
- Abweichungen zwischen Sollprozess und Implementierung spät sichtbar werden.

### Entscheidung

- `BPMN-2.0-first` für fachliche Prozessmodelle.
- `Python` als Ausführungs- und Integrationsschicht.
- Python muss sich am BPMN-Modell orientieren, nicht umgekehrt.

Das verbessert Lesbarkeit, Auditierbarkeit und Wartbarkeit für IT und Fachbereich.

## c) BPMN-2.0-Visualisierung: bpmn-js, Mermaid oder Alternativen

### Bewertung

- `bpmn-js`: passend als einbettbarer Web-Modeler für BPMN 2.0, weil
  Fachnutzer Prozesse visuell bearbeiten können.
- `Mermaid`: sehr gut für einfache Übersichtsbilder, aber kein vollwertiges BPMN-2.0-Quellformat.
- `PlantUML`: gut für Technikdiagramme, jedoch ebenfalls kein vollwertiger BPMN-2.0-Ersatz.
- `BPMN-2.0 XML` mit geeigneten BPMN-Werkzeugen: beste Wahl für fachlich verbindliche Prozessmodelle und Exporte.

### Entscheidung

- Verbindliche Fachquelle: BPMN-2.0 XML.
- Geplante Bearbeitungsschicht: `bpmn-js` mit eingeschränkter Palette,
  [bpmn/nac-moddle.json](../../bpmn/nac-moddle.json) und Python-Validator.
- Mermaid nur als Zusatzsicht für Management- und Schnellübersichten.
- PlantUML optional für technische Architektur, nicht für die fachliche BPMN-Quelle.

## Was Fachbereiche davon haben

- Das Unternehmen kann Prozesse primär über visuelle BPMN-Modelle verstehen.
- IT und Fachbereich arbeiten auf derselben Prozesswahrheit.
- Dokumentation ist versioniert, exportierbar und revisionsfähig.
- [docs/de/bpmn-js-business-layer.md](bpmn-js-business-layer.md) beschreibt den
  NaC-Pfad vom visuellen Editor zum geprüften Pull Request.
