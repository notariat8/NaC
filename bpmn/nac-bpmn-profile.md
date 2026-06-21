# NaC BPMN-Profil

Dieses Profil beschreibt die kleine, fachlich geführte BPMN-Schicht, die
später in einem bpmn-js-Editor bearbeitet werden soll.

## Produktentscheidung

- `*.bpmn` ist die fachliche Prozessquelle.
- `bpmn-js` ist die visuelle Bearbeitungsschicht.
- `bpmn/nac-moddle.json` ergänzt BPMN um NaC-Metadaten für Rollen,
  Ausführungskanal, Datenklasse, Freigabe, Nachweis, Plugin-Bindung und
  KG-Referenz sowie Demo-Planungsmetadaten für Dauer, Parallelität und
  kritischen Pfad.
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
| `nac:channel` | Flow Node | Ausführungsform, Semikolon-getrennt, zum Beispiel `personal`, `email`, `fax`, `video`, `qualified_e_signature`, `xnp_local`, `xnotar_xjustiz`, `register_portal` oder `land_register_portal`. |
| `nac:dataClass` | Flow Node | Datenklasse: `metadata`, `public_reference`, `confidential_placeholder`, `no_mandate_data`. |
| `nac:approval` | Flow Node | Freigabe: `none`, `human`, `four_eyes`. |
| `nac:evidence` | Flow Node | Nachweis: `none`, `optional`, `required`. |
| `nac:plugin` | Flow Node | Optional gebundenes lokales Plugin, etwa `nac-cyberjack-rfid`. |
| `nac:localExecution` | Flow Node | `true`, wenn der Schritt lokal am Arbeitsplatz laufen muss. |
| `nac:kgRef` | Flow Node | Zugehöriger usecase-lokaler Knowledge Graph. |
| `nac:durationBand` | Flow Node | Planungs-Dauerklasse: `same_day_or_internal`, `short_party_turnaround`, `standard_external`, `extended_external`, `statutory_or_exceptional`. Das sind editierbare Planwerte, keine amtlichen Durchschnittswerte. |
| `nac:parallelGroup` | Flow Node | Fachliche Gruppe für Schritte, die parallel vorbereitet oder nachgehalten werden können, z.B. `post_notarization`. |
| `nac:criticalPath` | Flow Node | `true`, wenn der Schritt den kritischen Pfad des Vollzugs blockieren kann; `false` oder fehlend bedeutet keine kritische-Pfad-Markierung. |

## Demo-Planungsmetadaten

Für die Notarkammer-Demo werden Dauerklasse, Parallelgruppe und kritischer Pfad
als fachliche Sicht auf das BPMN-Modell gepflegt. Sie dienen dazu, den
Vollzugspfad im Editor zu erklären, nicht dazu, Fristen oder produktive
Automatisierung auszulösen.

- `same_day_or_internal` beschreibt Notariats- oder Arbeitsplatzschritte, die
  in der Demo als intern beherrschbar gezeigt werden.
- `short_party_turnaround` beschreibt kurze Rückläufe mit Beteiligten oder
  üblichen Versand-/Abstimmungsschritten.
- `standard_external`, `extended_external` und `statutory_or_exceptional`
  markieren externe Abhängigkeiten, insbesondere Behörden-, Steuer-,
  Register- oder Grundbuchgrenzen.
- `parallelGroup` darf vorbereitbare oder nachzuhaltende Vollzugsgates
  bündeln. Beim Immobilienkaufvertrag ist `post_notarization` die parallele
  Phase nach der Beurkundung; `ownership_transfer` markiert den späteren
  Umschreibungsabschnitt.
- `criticalPath=true` markiert Demo-Blocker, die den weiteren Vollzug
  fachlich sperren können. Die Markierung ist keine Runtime-Anweisung.

XNP- und XNotar-Bezüge werden als Boundary-Gates modelliert:
`xnp_local` steht für lokale Arbeitsplatzbereitschaft und darf nur zusammen mit
lokaler Ausführung oder einem rein internen Prüfpunkt erscheinen. Der
bestehende BPMN-Kanal `xnotar_xjustiz` steht im Demo-Profil für die
öffentlich beschriebenen XNotar-Schritte innerhalb XNP, insbesondere
Grundbuch, Handelsregister, Signatur und Versand via beN. Konkrete
XJustiz-/Import-/Export-Artefakte sind zu klären im XNP-Testzugang. Beide
Kanäle beschreiben keinen produktiven Fachsystemzugriff und keine behauptete
direkte XNP-zu-NaC-Grundbuchdatenlieferung.

## XNP/BPMN-Integrationsvertrag

NaC ist 100% notariat. XNP ist die externe notarielle Arbeitsumgebung des
lokalen Notariatsarbeitsplatzes, nicht ein NaC-Backend und nicht ein
Kunden-UI-Provider. BPMN muss deshalb sichtbar modellieren, wann ein Schritt
eine externe XNP-, local-notary-workstation-, card-reader-, Register- oder
Grundbuch-Abhängigkeit hat.

- `xnp_local` modelliert nur lokale Bereitschaft, Amtstätigkeit,
  Kartenleser-/Signaturpfad oder UVZ-/VVZ-nahe Arbeit am Arbeitsplatz.
- `xnotar_xjustiz` modelliert XNotar-Grundbuch-/Register-, Signatur-,
  Versand- oder Nachweisgrenzen innerhalb XNP; XJustiz-/Import-/Export-Details
  sind zu klären im XNP-Testzugang.
- `register_portal` und `land_register_portal` bleiben externe Register- oder
  Grundbuchpfade; direkte Datenuebergaben an NaC sind zu klären im
  XNP-Testzugang und werden im Demo-Modell nicht behauptet.
- Externe Gates sind fail-closed: ohne `nac:evidence="required"` und
  zuständige menschliche Freigabe darf der Folgepfad nicht als frei gelten.
- Lokale XNP-/Kartenleser-/Arbeitsplatz-Gates brauchen
  `nac:localExecution="true"` oder werden als rein manuelle Notariatsprüfung
  modelliert.
- `nac:durationBand`, `nac:parallelGroup` und `nac:criticalPath` sind bei
  externen Gates Demo-Readiness-Metadaten: Dauerband für erwartete
  Abhängigkeit, Parallelgruppe für gleichzeitig nachzuhaltende Vollzugsgates,
  kritischer Pfad für externe Blocker.
- Kartenleser-Readiness darf intern auf REINER SCT, Sicherheitsklasse 3,
  Display und eigene PIN-Tastatur verweisen; die Kunden-UI zeigt diese
  Details nicht.
- Kundensichten zeigen nur provider-neutrale Status wie "Externe notarielle
  Arbeitsumgebung erforderlich"; XNP-Ports, lokale Pfade,
  Kartenleserdiagnosen, Registersystemdetails und Providerdetails bleiben aus
  Kunden-UI, Reports und normaler Auditansicht heraus.

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
- Externe Gates werden nur als fachliche Übergabe- und Nachweispunkte
  modelliert. Typische Beispiele im Immobilienkaufvertrag sind
  Eigentumsvormerkung, Löschungsunterlagen, gemeindliches Vorkaufsrecht,
  Unbedenklichkeitsbescheinigung und Eigentumsumschreibung.
- Keine PINs, Passwörter, Tokens oder API-Keys in Namen oder Metadaten.
- `xnp_local` beschreibt nur den lokalen XNP-/Karten-/Amtstätigkeitskontext am
  Notariatsarbeitsplatz. Eine direkte XNP-zu-NaC-Grundbuchdatenlieferung wird
  im Demo-Modell nicht behauptet.
- `xnotar_xjustiz` beschreibt XNotar-Grundbuch-/Register-, Signatur-,
  Versand- oder Nachweisgrenzen innerhalb XNP. Der Kanal ist ein Nachweis- und
  Übergabepunkt, keine automatisierte produktive Einreichung aus dem
  BPMN-Diagramm. XJustiz-/Import-/Export-Details sind zu klären im
  XNP-Testzugang.
- Lokale XNP/XNotar-Gates dürfen Metadaten, Bereitschaft und Übergabegrenzen
  prüfen, aber keine Mandatsdaten, Grundbuchinhalte oder produktive
  Fachsystemantworten im Repository abbilden.
- Keine direkte technische Automatisierung aus einem BPMN-Diagramm ohne
  Python-Validator und Pull-Request-Freigabe.
- Ein BPMN-Diagramm darf eine UI anleiten, ersetzt aber nicht notarielle
  Prüfung oder menschliche Freigabe.
- Dauerklassen sind Demonstrations- und Planungswerte. Sie dürfen nicht als
  verbindliche Fristen, SLA oder amtliche Durchschnittsdauer dargestellt werden.
- Kritischer-Pfad-Markierungen zeigen Demo-Blocker im Modell. Sie lösen keine
  Runtime-, OCI-, Release-, Apply- oder Cloud-Aktion aus.
