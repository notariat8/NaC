# Technologieentscheidung fuer das Musterrepo

## Ergebnis in einem Satz

Verbindlicher Standard ist:

- Dokumentation in Markdown (Quelle), PDF-Export automatisiert,
- Prozessausfuehrung in Python, aber fachlicher Ablauf BPMN-2.0-first,
- BPMN-2.0 als kanonisches Fachmodell, Mermaid nur fuer Uebersicht.

## Bewertung der aktuellen Fassung

Die aktuelle Fassung ist gut als Start, aber noch nicht die beste Endform fuer skalierbare Unternehmensdokumentation. Grund:

- Stark in kollaborativer Markdown-Dokumentation,
- stark in Python-Referenzlogik,
- aber BPMN-2.0 war bisher nicht als verbindliche Quellnorm definiert.

Mit der vorliegenden Policy wird das geschlossen.

## a) Dokumentation: Markdown vs AsciiDoc vs Superdoc

### Bewertung

- `Markdown`: beste Lesbarkeit, breiteste Toolunterstuetzung, ideal fuer LLM/Copilot/Cursor-Kollaboration.
- `AsciiDoc`: staerker fuer komplexe Publikations-Layouts und klassische Handbuchstrukturen.
- `Superdoc`: kein belastbarer De-facto-Standard fuer langfristige, revisionsfeste Unternehmensdokumentation.

### Entscheidung

- Quelle bleibt `Markdown`.
- PDF wird aus Markdown automatisiert exportiert (Pandoc-Pipeline).
- AsciiDoc wird nicht als zweite manuelle Quelle gepflegt, um Doppelpflege zu vermeiden.

Damit werden Kollaboration und PDF-Faehigkeit kombiniert.

## b) Python code-first fuer Geschaeftsprozesse unter BPMN-2.0-Vorgabe

### Bewertung

Reines code-first ist fuer Fachbereiche langfristig nicht optimal, weil:

- Fachlogik in Code fuer Nicht-IT schwer pruefbar wird,
- Abweichungen zwischen Sollprozess und Implementierung spaet sichtbar werden.

### Entscheidung

- `BPMN-2.0-first` fuer fachliche Prozessmodelle.
- `Python` als Ausfuehrungs- und Integrationsschicht.
- Python muss sich am BPMN-Modell orientieren, nicht umgekehrt.

Das verbessert Lesbarkeit, Auditierbarkeit und Wartbarkeit fuer IT und Fachbereich.

## c) BPMN-2.0-Visualisierung: Mermaid oder Alternativen

### Bewertung

- `Mermaid`: sehr gut fuer einfache Uebersichtsbilder, aber kein vollwertiges BPMN-2.0-Quellformat.
- `PlantUML`: gut fuer Technikdiagramme, jedoch ebenfalls kein vollwertiger BPMN-2.0-Ersatz.
- `BPMN-2.0 XML` mit geeigneten BPMN-Werkzeugen: beste Wahl fuer fachlich verbindliche Prozessmodelle und Exporte.

### Entscheidung

- Verbindliche Fachquelle: BPMN-2.0 XML.
- Mermaid nur als Zusatzsicht fuer Management- und Schnelluebersichten.
- PlantUML optional fuer technische Architektur, nicht fuer die fachliche BPMN-Quelle.

## Was Fachbereiche davon haben

- Das Unternehmen kann Prozesse primaer ueber visuelle BPMN-Modelle verstehen.
- IT und Fachbereich arbeiten auf derselben Prozesswahrheit.
- Dokumentation ist versioniert, exportierbar und revisionsfaehig.
