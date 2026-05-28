# DPP Evidence Passport Design

Datum: 2026-05-28

Issue: https://github.com/notariat8/NaC/issues/38

## Entscheidung

NaC führt Digital Product Passports nicht als eigenes notarielles
Hauptprodukt und nicht als generische Pflicht für alle Usecases ein. Der
passende NaC-Zuschnitt ist ein **DPP Evidence Passport**: eine
notarielle Trust-, Evidence- und Audit-Schicht für Vorgänge, in denen
Produkt-, Bauprodukt-, Objekt- oder Lieferkettennachweise für die rechtliche
Prüfung relevant werden.

NaC bleibt damit 100 Prozent Notariat. Das Modul unterstützt notarielle
Vorgänge durch nachweisbare Quellen, Hashes, Zeitpunkte, Rollen, Zugriffsklassen
und Review-Gates. Es ersetzt weder offizielle DPP-Register noch Hersteller-,
Marktaufsichts- oder Produktdatenplattformen.

## Quellenrahmen

Der rechtliche und technische Mindestkontext ist:

- Regulation (EU) 2024/1781, Ecodesign for Sustainable Products Regulation
  (ESPR): Rahmen für Digital Product Passports, produktgruppenspezifische
  Pflichten über delegierte Rechtsakte.
  <https://eur-lex.europa.eu/eli/reg/2024/1781/oj/eng>
- Regulation (EU) 2023/1542, Battery Regulation: erster konkreter
  Batteriepass für LMT-Batterien, Industriebatterien über 2 kWh und
  Elektrofahrzeugbatterien ab 2027-02-18.
  <https://eur-lex.europa.eu/eli/reg/2023/1542/oj>
- Regulation (EU) 2024/3110, Construction Products Regulation: eigenes
  digitales Produktpasssystem für Bauprodukte, kompatibel mit dem ESPR-Rahmen.
  <https://eur-lex.europa.eu/eli/reg/2024/3110/oj>
- CEN/CENELEC JTC 24 und Mandat M/604: technische Standardisierung für
  Identifikatoren, Datenträger, Zugriff, Sicherheit, Interoperabilität,
  Datenformate, APIs, Speicherung, Archivierung und Integrität.
  <https://standards.iteh.ai/catalog/tc/cen/b2e63c3a-8446-4d3f-b148-51c2b3928ecd/jtc-24>
  <https://standards.iteh.ai/catalog/mandate/cen/e7165d1b-1a7a-47ed-b2eb-2b18d664fabe/m-604>

## NaC-Fit

DPP ist für NaC dann relevant, wenn ein notarieller Vorgang eine belastbare
Nachweiskette zu einem Objekt, Bauprodukt, technischen Bestandteil, Register-
oder Lieferkettenstatus braucht. Der Nutzen liegt nicht in der Speicherung
vollständiger Produktdaten, sondern in der prüfbaren Verbindung:

1. Welcher DPP- oder produktnahe Nachweis wurde vorgelegt?
2. Aus welcher Quelle stammt er?
3. Welcher Stand wurde zu welchem Zeitpunkt geprüft?
4. Welche Zugriffsklasse und rechtliche Grundlage gab es?
5. Welche notarielle Entscheidung oder Rueckfrage haengt daran?

Diese Informationen passen in die vorhandene NaC-Architektur aus
Knowledge-Graph, Secure Document Link, Event-/Evidence-Nachweis und
Human-Gates.

## Usecase-Prioritaeten

### P1: Objekt- und Bau-nahe Vorgänge

- `bautraegervertrag`: Bauleistungsbeschreibung, Bauproduktnachweise,
  Fertigstellungs- und Mängelkontext, Verbraucherfreigaben.
- `immobilienkaufvertrag`: Objekt-, Energie-, Sanierungs-, Anlagen- und
  Dokumentationsnachweise, soweit sie für Vertragsprüfung oder Vollzug
  relevant sind.
- `teilungserklaerung-weg`: Einheiten-, Plan-, Bau- und
  Ausstattungsnachweise als objektbezogene Evidence.

### P2: Asset- und Gesellschaftsvorgaenge

- `geschaeftsanteilsuebertragung-gmbh`, `handelsregisteranmeldung` und
  verwandte Usecases, wenn DPP-Daten Teil einer Due Diligence oder
  Gewährleistungs-/Haftungsprüfung sind.

### P3: Nur bei konkreter fachlicher Relevanz

- Erb-, Familien-, Vollmachts- und Beglaubigungsvorgaenge bekommen kein
  DPP-Gate als Standard. Ein DPP-Nachweis kann dort nur als normales Dokument
  oder Evidence-Objekt auftauchen, wenn der Einzelfall es erfordert.

## Architektur

1. `nac-dpp-evidence` wird als fachliches Modul oder als Capability von
   `nac-regulated-core` geplant.
2. Das Modul erzeugt keine offiziellen DPPs. Es erfasst und prüft
   DPP-nahe Nachweise als Evidence-Referenzen.
3. Der Knowledge Graph bekommt optionale Knoten für:
   - `asset.product_passport_subject`
   - `evidence.dpp_snapshot`
   - `decision.dpp_relevance`
   - `gate.dpp_evidence_review`
4. Secure Document Link bleibt die Grenze für Dokumente und Dateien. Das
   DPP-Modul speichert keine geheimen Links, Access Tokens oder Rohdaten im
   Produktrepo.
5. Event-/Evidence-Komponenten speichern nur mandatsdatenfreie Referenzen,
   Hashes, Zeitstempel, Quellenkennung, Zugriffsklasse und Reviewstatus.
6. Eine spätere `xyflow`-Ansicht rendert nur den geprüften Graph-Vertrag:
   Objekt, DPP-Nachweis, Quelle, Prüfstatus, offene Entscheidung, Gate.

## Minimales Datenmodell

Ein DPP-Evidence-Eintrag benötigt mindestens:

- `evidence_id`: stabile NaC-interne Evidence-ID ohne Geheimnisanteil.
- `subject_type`: `building_product`, `building_unit`, `technical_asset`,
  `company_asset` oder `other_notarial_asset`.
- `subject_reference`: mandatsdatenfreie Referenz auf den KG-Knoten.
- `source_type`: `official_registry`, `manufacturer_dpp`, `third_party_dpp`,
  `document_snapshot` oder `manual_evidence`.
- `source_uri_hash`: Hash der Quelle oder des DPP-Identifiers, keine geheimen
  Zugriffsdaten.
- `content_hash`: Hash des geprüften Snapshots, falls ein Snapshot vorliegt.
- `checked_at`: UTC-Zeitpunkt der Prüfung.
- `access_class`: `public`, `restricted`, `confidential` oder `unknown`.
- `legal_basis_note`: kurze fachliche Begründung für die Verwendung im
  konkreten notariellen Vorgang.
- `review_status`: `not_relevant`, `needed`, `received`, `checked`,
  `question_open`, `approved` oder `rejected`.
- `reviewed_by_role`: NaC-Rolle, nicht Personen- oder Secret-Daten.

## Workflow

1. Usecase Intake erkennt, ob ein DPP-naher Nachweis potentiell relevant ist.
2. Fachpersonal markiert `decision.dpp_relevance` als nicht relevant,
   benötigt oder offen.
3. Bei Relevanz wird ein DPP-/Evidence-Nachweis über Secure Document Link
   oder einen späteren Connector referenziert.
4. NaC erzeugt `evidence.dpp_snapshot` mit Hash, Quelle, Zeitpunkt und
   Zugriffsklasse.
5. `gate.dpp_evidence_review` bleibt offen, bis fachlich entschieden ist,
   ob der Nachweis ausreicht, Rueckfragen ausloest oder nicht verwendet werden
   darf.
6. GNotKG bleibt getrennt. Ein DPP-Nachweis kann gebuehren- oder
   abrechnungsrelevant sein, ist aber kein Bestandteil der Kostenberechnung
   selbst.

## Grenzen

- Kein offizieller DPP-Registry-Betrieb durch NaC.
- Keine Behauptung vollständiger EU-DPP-Konformität vor finaler
  produktgruppenspezifischer Konkretisierung.
- Keine echten Mandatsdaten, Produktrohdaten, Access Tokens, API Keys oder
  geheimen Links im Produktrepo.
- Kein Standardgate für jeden notariellen Usecase.
- Keine automatische notarielle Bewertung ohne Human-Gate.
- NaC bleibt auf notarielle Usecases begrenzt.

## Akzeptanz

- Die DPP-Relevanz ist als optionaler Evidence-Track beschrieben, nicht als
  universelle Pflicht.
- P1-Usecases sind auf Bautraegervertrag, Immobilienkaufvertrag und
  Teilungserklärung WEG begrenzt.
- Das Design referenziert bestehende KG-, Secure-Document-Link- und
  Evidence-Mechanismen statt neue Datensilos zu erzeugen.
- Risiken und Nicht-Ziele sind explizit dokumentiert.
- Strict Quality Gate bleibt gruen.
