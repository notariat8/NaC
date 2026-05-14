# Grundbuchportal Plugin Integration Plan

Stand: 2026-05-11

Dieser Plan beschreibt, wie NoC Prozesse rund um das gemeinsame Grundbuchportal der Laender und die Internet-Grundbucheinsicht als Plugin integrieren kann. Ziel ist nicht, Grundbuchportale zu scrapen oder automatisierte Abrufe ohne Zulassung durchzufuehren. Ziel ist ein sicherer, mandantenfaehiger Workflow- und Evidence-Ansatz, der spaeter nur bei formaler Zulassung und technischer Freigabe zu einem direkten Abruf-Connector ausgebaut wird.

## Zielbild

NoC soll Grundbuch-bezogene Vorgaenge fuer berechtigte SaaS-Kunden nachvollziehbar fuehren:

- Zulassungen pro Bundesland und Nutzergruppe dokumentieren
- berechtigtes Interesse vor jedem Abruf erfassen und pruefbar machen
- Aktenzeichen, Vollmacht, dingliche Berechtigung, Zwangsvollstreckung oder sonstigen Abrufgrund strukturiert erfassen
- Grundbuchauszuege und Nachweise nur kundenseitig oder verschluesselt speichern
- Hashes, Metadaten, Freigaben und Abrufattestationen als Audit Evidence fuehren
- Gebuehren, Abrufgrund und verantwortliche Person nachvollziehbar machen
- spaeter optional autorisierte Portal-/Abrufintegration pro Bundesland anbinden

## Offizielle Faktenbasis

- Das gemeinsame Grundbuchportal der Laender verweist fuer die Internet-Grundbucheinsicht auf die einzelnen Bundeslaender.
- In jedem Bundesland besteht die Moeglichkeit, in das Grundbuch elektronisch Einsicht zu nehmen.
- Die Einsichtnahme ist kostenpflichtig und an Zulassungskriterien geknuepft.
- Das automatisierte Grundbuchabrufverfahren erlaubt bei Vorliegen rechtlicher und technischer Voraussetzungen Online-Einsicht in Grundbuch und Hilfsverzeichnisse.
- Leistungen des Abrufverfahrens sind u.a. Einsicht in ein bestimmtes Grundbuchblatt, Abdruck des Grundbuchinhalts, Suche nach unbekanntem Grundbuchblatt anhand Flurstueck oder Eigentuemer, Feststellung der letzten Eintragung und Hinweis auf noch nicht vollzogene Eintragungsantraege.
- Die Zulassung muss sicherstellen, dass die Einsicht nur im durch die Grundbuchordnung erlaubten Umfang erfolgt und dass die Rechtmaessigkeit der Abrufe auf Grundlage einer Protokollierung kontrolliert werden kann.
- Es gibt ein uneingeschraenktes und ein eingeschraenktes Abrufverfahren. Beim eingeschraenkten Verfahren ist vor jeder Recherche der Grund des berechtigten Interesses darzulegen.
- Gerichte, Behoerden, Notare und oeffentlich bestellte Vermessungsingenieure koennen Zugang zum uneingeschraenkten Verfahren erhalten. Weitere Nutzungsberechtigte, z.B. Banken und Rechtsanwaelte, werden typischerweise zum eingeschraenkten Verfahren zugelassen.
- Die Zulassung erfolgt je Bundesland; auch wenn bestimmte Gebuehren bundesweit geregelt sind, bleibt die landesspezifische Zulassung relevant.
- Fuer Abrufe besteht Vollprotokollierung. Protokolle dienen der Kontrolle der Rechtmaessigkeit, ordnungsgemaessen Datenverarbeitung und Kostenerhebung.
- Beispiel Brandenburg: Fuer SolumWEB ist eine foermliche Zulassung nach § 133 Abs. 2 GBO und Anmeldung am Landes-Grundbuchportal erforderlich; das Portal weist ausdruecklich auf Phishing-Risiken hin.

## Leitentscheidung

NoC sollte in drei Stufen vorgehen:

1. **Zulassungs- und Workflow-Companion**
   - NoC fuehrt Zulassungen, Rollen, berechtigtes Interesse, Aktenbezug, Vollmachten, Gebuehren und Evidence.
   - Der Abruf selbst erfolgt weiterhin durch berechtigte Nutzer im offiziellen Laenderportal.
   - NoC speichert standardmaessig keine Grundbuchinhalte, sondern Hashes und Nachweise.

2. **Evidence-Import und kontrollierte Ablage**
   - Nutzer koennen Grundbuchauszuege oder Abrufnachweise explizit bereitstellen.
   - NoC erfasst Hash, Abrufgrund, Aktenzeichen, Portal/Bundesland, Zeitstempel und Verantwortliche.
   - Speicherung von Inhalten nur nach Mandantenpolicy, verschluesselt und mit strengem Zugriff.

3. **Autorisierter Direktabruf pro Bundesland**
   - nur nach foermlicher Zulassung, Vertrag/Genehmigung, technischer Dokumentation und Sicherheitsfreigabe
   - keine inoffizielle Browserautomation
   - keine Nutzung fremder Zugangsdaten ausserhalb genehmigter Rollen
   - pro Land getrennte Adapter, weil Portale und Zulassungsstellen laenderspezifisch sind

## Architektur

```text
Kundenorganisation
  berechtigter Nutzer / Notariat / Bank / Kanzlei / Behoerde
  offizielles Landes-Grundbuchportal
  lokale Dokumentablage oder DMS
  noc-grundbuch-local-plugin
        |
        | Evidence, Hashes, Abrufgrund, Freigaben
        v
NoC SaaS / OCI
  grundbuch workflow service
  admission registry
  tenant evidence store
  audit journal
  policy engine
  billing / fee evidence
```

## Was das Plugin tun darf

- offizielle Grundbuchportal- und Landesportal-Links oeffnen
- Bundesland, Grundbuchamt, Aktenzeichen und Vorgangsart erfassen
- Zulassungsstatus je Kunde, Organisation, Bundesland und Nutzergruppe dokumentieren
- berechtigtes Interesse strukturiert vor dem Abruf erfassen
- Vollmachten, dingliche Berechtigungen oder Zwangsvollstreckungsbezug als Nachweis-Hash referenzieren
- Vier-Augen-Freigaben fuer sensible Abrufe erzwingen
- Abrufattestationen erfassen, nachdem der berechtigte Nutzer im offiziellen Portal gearbeitet hat
- importierte Grundbuchauszuege hashen und optional in kundengesteuerter Ablage referenzieren
- Gebuehren- und Abrufzaehlungsnachweise fuer interne Kontrolle vorbereiten
- Phishing- und Portal-Link-Hygiene unterstuetzen, z.B. nur bekannte offizielle Domains oeffnen

## Was das Plugin nicht tun darf

- keine Grundbuchportale ohne Zulassung automatisiert abfragen
- keine Portal-Zugangsdaten, Kennwoerter, Zertifikate oder Codezeichen in NoC speichern
- keine heimliche Browserautomation oder Scraping
- keine Suche nach Eigentuemer oder Grundbuchblatt ohne dokumentiertes berechtigtes Interesse
- keine Grundbuchinhalte an LLMs uebergeben
- keine Nutzung eines Zugangs durch nicht zugelassene Personen oder Organisationen
- keine zentrale Mischablage fuer mehrere Kunden
- keine Direktintegration pro Bundesland ohne Genehmigung, technische Dokumentation und Sicherheitsfreigabe

## Integrationspfade

### Pfad A: Zulassungs- und Evidence-Companion (MVP)

Dieser Pfad ist sofort planbar.

- NoC verwaltet Zulassungen und Rollen.
- NoC erzeugt Abrufvorgaenge mit Pflichtfeldern.
- NoC prueft, ob fuer Land, Nutzergruppe und Abrufgrund eine passende Zulassung dokumentiert ist.
- NoC oeffnet das offizielle Portal, fuehrt aber keinen Abruf aus.
- Der Nutzer bestaetigt nach Durchfuehrung den Abruf und importiert optional Nachweise.

Empfehlung: Das ist der erste Schritt.

### Pfad B: Kontrollierter Dokument- und Nachweisimport

- Grundbuchauszuege bleiben primaer im Kundensystem.
- NoC speichert nur Hash, Speicherort, Aktenzeichen, Zeitstempel und Freigaben.
- Wenn Inhalte in NoC gespeichert werden, dann nur tenantisoliert, verschluesselt, mit strenger Retention und Zugriffskontrolle.
- LLM-Verarbeitung bleibt deaktiviert, bis eine ausdrueckliche Policy je Mandant und Vorgang existiert.

### Pfad C: Autorisierter Direktadapter

Dieser Pfad ist nur nach Zulassung und technischer Klaerung zulaessig.

Voraussetzungen:

- formale Zulassung zum automatisierten Abrufverfahren
- geklaerte Rolle: Kunde, SaaS-Anbieter, technischer Dienstleister oder zugelassene Stelle
- Dokumentation der erlaubten Abrufarten und Nutzer
- technische Spezifikation des jeweiligen Landesportals oder Abrufverfahrens
- Vereinbarung ueber Protokollierung, Codezeichen, Geheimnisverwahrung und Missbrauchsschutz
- Penetration Test und Datenschutz-Folgenabschaetzung

Technische Konsequenz:

- Adapter pro Bundesland, kein generischer Scraper
- Secrets nur in tenantisoliertem Vault
- Abrufe nur mit Case-ID, berechtigtem Interesse und Nutzerbindung
- append-only Audit Journal
- Kosten- und Abruflimit je Kunde

## Plugin-Schnittstelle

Vorgeschlagene Commands:

- `grundbuch.health`
- `grundbuch.open_portal`
- `grundbuch.resolve_state_portal`
- `grundbuch.register_admission`
- `grundbuch.check_admission`
- `grundbuch.prepare_inquiry`
- `grundbuch.record_legitimate_interest`
- `grundbuch.request_approval`
- `grundbuch.record_user_attestation`
- `grundbuch.record_retrieval_confirmation`
- `grundbuch.record_document_hash`
- `grundbuch.record_fee_event`
- `grundbuch.get_evidence`
- `grundbuch.export_audit_package`
- `grundbuch.direct.retrieve_sheet` (spaeter, nur mit Zulassung)
- `grundbuch.direct.search_sheet` (spaeter, nur mit Zulassung)

## Evidence-Modell

```json
{
  "plugin": "noc-grundbuch",
  "tenant_id": "customer-compartment-or-noc-tenant-id",
  "organization_id": "customer-organization-id",
  "workflow_id": "grundbuch-workflow-2026-0001",
  "workflow_type": "grundbuch_access_request",
  "jurisdiction": {
    "country": "DE",
    "federal_state": "BB|BW|BY|BE|HB|HH|HE|MV|NI|NW|RP|SL|SN|ST|SH|TH",
    "portal": "official-state-portal-url"
  },
  "admission": {
    "admission_type": "restricted|unrestricted|unknown",
    "admission_reference": "customer-controlled-reference",
    "admitted_user_or_unit": "user-or-unit-id",
    "valid_from": "2026-05-11",
    "valid_until": null
  },
  "matter": {
    "case_reference": "customer-case-id",
    "land_register_office": "optional",
    "sheet_reference": "redacted-or-known-reference",
    "parcel_reference": "redacted-or-known-reference"
  },
  "legitimate_interest": {
    "category": "notary|authority|enforcement|secured_right|owner_authorization|bank|lawyer|utility|other",
    "description": "short non-sensitive reason",
    "supporting_document_sha256": "hex",
    "review_required": true,
    "approved_by": "noc-user-id"
  },
  "retrieval": {
    "performed_externally": true,
    "performed_by": "noc-user-id",
    "performed_at": "2026-05-11T00:00:00Z",
    "direct_adapter_used": false,
    "fee_event_recorded": true
  },
  "documents": [
    {
      "label": "grundbuchauszug-or-retrieval-proof",
      "sha256": "hex",
      "content_stored_in_oac": false,
      "storage_reference": "customer-controlled-storage"
    }
  ],
  "attestations": [
    {
      "type": "user_confirmed_authorized_retrieval",
      "timestamp": "2026-05-11T00:00:00Z",
      "text": "Abruf wurde durch eine zugelassene Person im offiziellen Grundbuchportal durchgefuehrt."
    }
  ]
}
```

## NoC-Prozesstypen

- `grundbuch_admission_management`
- `grundbuch_access_request`
- `grundbuch_legitimate_interest_review`
- `grundbuch_retrieval_attestation`
- `grundbuch_document_archival`
- `grundbuch_fee_reconciliation`
- `grundbuch_audit_export`
- `grundbuch_direct_retrieval` (spaeter)

Statusmodell:

- `draft`
- `admission_missing`
- `interest_required`
- `needs_review`
- `approved`
- `retrieval_pending`
- `retrieved_externally`
- `evidence_recorded`
- `archived`
- `cancelled`
- `blocked`

## Mandanten- und Compartment-Konzept

Fuer SaaS gilt weiter: ein Compartment pro Kunde.

Empfohlen:

- `noc-platform`
  - zentrale Plugin-Definition, CI, Policy und Observability
- `noc-shared-security`
  - Vault, KMS, Audit, Logging, Security Zones, Budgets
- `customer-<id>`
  - kundenspezifische Workflows
  - Evidence-Buckets
  - tenantisolierte Secrets nur bei spaeterem Direktadapter
  - kundenspezifische Retention und Zugriffskontrolle

Fuer Grundbuchdaten besonders wichtig:

- Grundbuchinhalte sind hochsensibel und koennen Eigentums-, Belastungs- und Personenbezug enthalten.
- Standard ist: keine Inhalte in NoC, nur Hashes und Metadaten.
- Wenn Inhalte gespeichert werden, dann pro Kunde verschluesselt, mit striktem Need-to-know, Retention, Legal Hold und Exportkontrolle.
- Zugriff auf Grundbuch-Evidence sollte enger sein als normaler Projekt- oder CRM-Zugriff.

## MVP

Umsetzung fuer die erste Iteration:

- Markdown-Dokumentation und Plugin-Spezifikation
- offizielles Portal- und Landesportal-Verzeichnis
- `grundbuch.health`
- `grundbuch.open_portal`
- `grundbuch.resolve_state_portal`
- `grundbuch.register_admission`
- `grundbuch.prepare_inquiry`
- `grundbuch.record_legitimate_interest`
- `grundbuch.request_approval`
- `grundbuch.record_user_attestation`
- `grundbuch.record_document_hash`
- Evidence-JSON-Schema
- Beispielworkflow fuer einen eingeschraenkten Abruf mit Vollmacht oder Aktenbezug
- Tenant-Onboarding-Runbook ohne Portalzugangsdaten

Nicht im MVP:

- direkte Portalabfrage
- Eigentuemersuche durch NoC
- Speicherung von Portalzugangsdaten oder Codezeichen
- browserbasierte Automation
- LLM-Verarbeitung von Grundbuchauszuegen
- landesspezifischer Direktadapter

## Sicherheitsanforderungen

- Kein Abruf ohne dokumentierte Zulassung.
- Kein Abruf ohne berechtigtes Interesse oder passende Nutzergruppe.
- Kein Zugriff durch nicht zugelassene Personen.
- Keine Speicherung von Zugangsdaten, Kennwoertern, Zertifikaten oder Codezeichen im MVP.
- Vier-Augen-Prinzip fuer risikoreiche Abrufe konfigurierbar.
- Evidence append-only und revisionsfest.
- Jede Aktion mit Nutzer, Rolle, Zeitstempel, Kunde, Aktenzeichen und Zweckbindung.
- Hash-first-Design fuer Dokumente.
- Keine Prompt-/Telemetry-Erfassung von Grundbuchinhalten.
- Phishing-Schutz durch Domain-Allowlist fuer offizielle Portale.
- CIS-/C5-orientierte OCI-Baseline: IAM least privilege, MFA, Vault, KMS, Logging, Budgets, Security Zones wo sinnvoll.
- Datenschutz-Folgenabschaetzung vor Speicherung oder automatisierter Verarbeitung von Grundbuchinhalten.

## SaaS-Anbieter-Runbook

1. Rolle klaeren: NoC als Prozessbegleiter, technischer Dienstleister oder selbst zugelassene Stelle.
2. Pro Zielbundesland Zulassungsprozess und Stelle identifizieren.
3. Kundengruppen und Nutzergruppen bestimmen: Notariat, Kanzlei, Bank, Behoerde, Versorger, sonstige.
4. Zulassungsnachweise und Genehmigungsumfang als NoC-Objekte modellieren.
5. TOMs fuer ordnungsgemaesse Datenverarbeitung und Missbrauchsschutz dokumentieren.
6. Portal-Domain-Allowlist und Phishing-Hinweise einrichten.
7. MVP-Plugin ohne Secrets bauen.
8. Evidence-Schema und Retention je Kunde festlegen.
9. Kundenspezifisches OCI-Compartment anlegen.
10. Pilot mit rein manuellem Portalabruf und NoC-Evidence durchfuehren.
11. Erst danach pruefen, ob ein genehmigter Direktadapter je Bundesland machbar ist.

## Kunden-Onboarding-Runbook

1. Kunde benennt Bundeslaender, Organisationseinheiten und berechtigte Nutzer.
2. Kunde liefert vorhandene Zulassungen oder startet den Zulassungsantrag beim jeweiligen Land.
3. NoC erfasst Zulassungsart, Gueltigkeit, Nutzerkreis und erlaubte Abrufgruende.
4. Kunde definiert Freigaberegeln und Retention fuer Grundbuchnachweise.
5. NoC legt Kundentenant und Evidence Store an.
6. NoC aktiviert Grundbuch-Prozessvorlagen.
7. Erster Abruf wird manuell im offiziellen Portal durchgefuehrt.
8. NoC erfasst berechtigtes Interesse, Attestation, Hash und Gebuehrenereignis.
9. Review: Welche Daten duerfen spaeter gespeichert oder automatisiert verarbeitet werden?

## Offene Entscheidungen

- Soll NoC selbst jemals als zugelassene abrufende Stelle auftreten oder nur Kundenprozesse begleiten?
- Welche Bundeslaender sind fuer die ersten Kunden relevant?
- Welche Nutzergruppen sind Zielkunden: Kanzleien, Notariate, Banken, Immobilienunternehmen, Versorger, Behoerden?
- Welche Abrufgruende sollen im MVP erlaubt sein?
- Sollen Grundbuchauszuege ueberhaupt in NoC gespeichert werden oder nur im Kundensystem?
- Welche Retention gilt fuer Evidence und importierte Dokumente?
- Gibt es landesspezifische technische Schnittstellen, die offiziell fuer Dienstleister freigegeben sind?
- Wie wird Kostenkontrolle pro Kunde und Abruf umgesetzt?

## Akzeptanzkriterien fuer die erste Umsetzung

- Plugin fuehrt keinen direkten Abruf durch.
- Plugin speichert keine Portal-Zugangsmittel.
- Jeder Vorgang enthaelt Bundesland, Zulassungsstatus, Abrufgrund, Aktenbezug und verantwortliche Person.
- Jeder importierte Nachweis wird gehasht.
- Grundbuchinhalte werden standardmaessig nicht in NoC gespeichert.
- Freigaben und Attestationen sind zeitgestempelt und rollenbasiert.
- Offizielle Portale und rechtliche Quellen sind dokumentiert.
- Tenant-Isolation ist pro Kunde dokumentiert.

## Quellen

- Gemeinsames Grundbuchportal der Laender: https://www.grundbuchportal.de/
- Allgemeine Hinweise zur Internet-Grundbucheinsicht: https://grundbuchportal.de/allg-infos.htm
- Justizportal des Bundes und der Laender, Internet-Grundbucheinsicht: https://www.justiz.de/onlinedienste/internet_grundbucheinsicht/index.php
- Beispiel Landesportal Brandenburg / SolumWEB: https://grundbuch.brandenburg.de/
- Grundbuchordnung § 133: https://www.gesetze-im-internet.de/gbo/__133.html
- Grundbuchverfuegung § 80: https://www.gesetze-im-internet.de/gbvfg/__80.html
- Grundbuchverfuegung § 82: https://www.gesetze-im-internet.de/gbvfg/__82.html
- Grundbuchverfuegung § 83: https://www.gesetze-im-internet.de/gbvfg/__83.html
