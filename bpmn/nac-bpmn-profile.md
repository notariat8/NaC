# NaC BPMN-Profil

Dieses Profil beschreibt die kleine, fachlich geführte BPMN-Schicht, die
später in einem bpmn-js-Editor bearbeitet werden soll.

## Produktentscheidung

- `*.bpmn` ist die fachliche Prozessquelle.
- `bpmn-js` ist die visuelle Bearbeitungsschicht.
- `bpmn/nac-moddle.json` ergänzt BPMN um NaC-Metadaten für Rollen,
  Ausführungskanal, Datenklasse, Freigabe, Nachweis, Plugin-Bindung und
  KG-Referenz.
- `scripts/validate_bpmn_models.py` prüft BPMN-Dateien deterministisch.
- Python bleibt Ausführungs-, Prüf- und Exportlogik.
- Mermaid bleibt eine Zusatzsicht, nicht die Prozessquelle.

## NaC-Attribute

| Attribut | Ebene | Bedeutung |
| --- | --- | --- |
| `nac:profile` | Prozess | Aktiviert das NaC-Profil. Aktuell: `nac-bpmn/v0.1`. |
| `nac:owner` | Prozess | Herausgeber oder fachlich verantwortliche Stelle. |
| `nac:binding` | Prozess | Bindungsmodell, zum Beispiel `Git Pull Request`. |
| `nac:role` | Flow Node | Fachliche Rolle, die den Schritt verantwortet. |
| `nac:channel` | Flow Node | Ausführungsform, Semikolon-getrennt, zum Beispiel `personal`, `email`, `fax`, `video`, `qualified_e_signature`, `xnp_local`, `register_portal` oder `land_register_portal`. |
| `nac:dataClass` | Flow Node | Datenklasse: `metadata`, `public_reference`, `confidential_placeholder`, `no_mandate_data`. |
| `nac:approval` | Flow Node | Freigabe: `none`, `human`, `four_eyes`. |
| `nac:evidence` | Flow Node | Nachweis: `none`, `optional`, `required`. |
| `nac:plugin` | Flow Node | Optional gebundenes lokales Plugin, etwa `nac-cyberjack-rfid`. |
| `nac:localExecution` | Flow Node | `true`, wenn der Schritt lokal am Arbeitsplatz laufen muss. |
| `nac:kgRef` | Flow Node | Zugehöriger usecase-lokaler Knowledge Graph. |

## bpmn-js-Regeln

Der spätere Editor soll nicht den vollen BPMN-Baukasten freigeben. Für
Fachpersonal reichen zunächst:

- Start- und Endereignis
- Aufgabe, User Task und Service Task
- exklusives Gateway
- Sequenzfluss mit sichtbarer Beschriftung bei Entscheidungen
- NaC-Properties-Panel für Rolle, Ausführungskanal, Datenklasse, Freigabe,
  Nachweis, Plugin und KG-Referenz

## Grenzen

- Keine echten Mandatsdaten in BPMN.
- Keine PINs, Passwörter, Tokens oder API-Keys in Namen oder Metadaten.
- Keine direkte technische Automatisierung aus einem BPMN-Diagramm ohne
  Python-Validator und Pull-Request-Freigabe.
- Ein BPMN-Diagramm darf eine UI anleiten, ersetzt aber nicht notarielle
  Prüfung oder menschliche Freigabe.
