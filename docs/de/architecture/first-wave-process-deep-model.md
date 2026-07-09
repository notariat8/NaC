# First-Wave-Process-Deep-Model

Diese Decision Note beschreibt den ersten tieferen, aber weiterhin
mandatsdatenfreien Prozessmodell-Vertrag für die vier First-Wave-Fälle.

## Zweck

`nac kg first-wave-process-deep-model --format json` verdichtet die bisherigen
Offline-Artefakte zu einem nutzbaren Prozessmodell-Shape:

- acht kanonische Prozessphasen je First-Wave-Fall
- kanonische Rollenbindungen inklusive Vertretungsrollen
- bestehende BPMN-Quellen als nicht-ausführende Prozessmodell-Bindings
- usecase-lokale KG-Knoten für Pflichtangaben, Dokumenttypen, Entscheidungen,
  Gates und Nachweise
- SharePoint-Projektionsplan für die MVP-Listen und -Bibliotheken
- bekannte SharePoint-, BPMN- und Ontologie-Gaps als owner-gated
  Gap-Closure-Plan

Damit ist der nächste fachliche Schritt nicht mehr nur ein Outline, sondern ein
konkreter, prüfbarer Contract für spätere Prozessinstanzen.

## Grenzen

Der Contract bleibt offline-only:

- keine Microsoft-Graph-Requests
- keine SharePoint-Schreiboperation
- keine SharePoint-Schemaänderung
- keine Mutation bestehender BPMN-Dateien
- keine Dokumentinhalte
- keine Mandatswerte
- keine Secrets
- kein zentraler Knowledge-Graph-Ordner

SharePoint bleibt der operative MVP-Store. Die Ontologie bleibt
Produktmodell-, Sizing- und Projektionsvertrag, nicht Runtime-Datenbank und
nicht Reasoning-Pfad für Nutzeraktionen.

## Anschluss

Der sinnvolle Anschluss ist ein `first_wave_process_instance_seed_plan`: aus dem
Deep-Model können synthetische Prozessinstanz-Templates geplant werden. Ein
echter SharePoint-Write oder eine BPMN-Modellmutation braucht danach weiterhin
einen expliziten Owner-Gate.

Der Validator
[scripts/validate_first_wave_process_deep_model.py](../../../scripts/validate_first_wave_process_deep_model.py)
prüft diese Grenzen im strikten Quality Gate.
