# Grundbuchportal Plugin Integration Plan

Stand: 2026-05-11

Dieser Plan beschreibt, wie NaC Prozesse rund um das gemeinsame Grundbuchportal der Länder und die Internet-Grundbucheinsicht als Plugin integrieren kann. Ziel ist nicht, Grundbuchportale zu scrapen oder automatisierte Abrufe ohne Zulassung durchzuführen. Ziel ist ein sicherer, mandantenfähiger Workflow- und Evidence-Ansatz, der später nur bei formaler Zulassung und technischer Freigabe zu einem direkten Abruf-Connector ausgebaut wird.

## Zielbild

NaC soll Grundbuch-bezogene Vorgänge für berechtigte SaaS-Kunden nachvollziehbar führen:

- Zulassungen pro Bundesland und Nutzergruppe dokumentieren
- berechtigtes Interesse vor jedem Abruf erfassen und prüfbar machen
- Aktenzeichen, Vollmacht, dingliche Berechtigung, Zwangsvollstreckung oder sonstigen Abrufgrund strukturiert erfassen
- Grundbuchauszüge und Nachweise nur kundenseitig oder verschlüsselt speichern
- Hashes, Metadaten, Freigaben und Abrufattestationen als Audit Evidence führen
- Gebühren, Abrufgrund und verantwortliche Person nachvollziehbar machen
- später optional autorisierte Portal-/Abrufintegration pro Bundesland anbinden

## Offizielle Faktenbasis

- Das gemeinsame Grundbuchportal der Länder verweist für die Internet-Grundbucheinsicht auf die einzelnen Bundesländer.
- In jedem Bundesland besteht die Möglichkeit, in das Grundbuch elektronisch Einsicht zu nehmen.
- Die Einsichtnahme ist kostenpflichtig und an Zulassungskriterien geknuepft.
- Das automatisierte Grundbuchabrufverfahren erlaubt bei Vorliegen rechtlicher und technischer Voraussetzungen Online-Einsicht in Grundbuch und Hilfsverzeichnisse.
- Leistungen des Abrufverfahrens sind u.a. Einsicht in ein bestimmtes Grundbuchblatt, Abdruck des Grundbuchinhalts, Suche nach unbekanntem Grundbuchblatt anhand Flurstück oder Eigentümer, Feststellung der letzten Eintragung und Hinweis auf noch nicht vollzogene Eintragungsanträge.
- Die Zulassung muss sicherstellen, dass die Einsicht nur im durch die Grundbuchordnung erlaubten Umfang erfolgt und dass die Rechtmäßigkeit der Abrufe auf Grundlage einer Protokollierung kontrolliert werden kann.
- Es gibt ein uneingeschraenktes und ein eingeschraenktes Abrufverfahren. Beim eingeschraenkten Verfahren ist vor jeder Recherche der Grund des berechtigten Interesses darzulegen.
- Gerichte, Behörden, Notare und öffentlich bestellte Vermessungsingenieure können Zugang zum uneingeschraenkten Verfahren erhalten. Weitere Nutzungsberechtigte, z.B. Banken und Rechtsanwaelte, werden typischerweise zum eingeschraenkten Verfahren zugelassen.
- Die Zulassung erfolgt je Bundesland; auch wenn bestimmte Gebühren bundesweit geregelt sind, bleibt die landesspezifische Zulassung relevant.
- Für Abrufe besteht Vollprotokollierung. Protokolle dienen der Kontrolle der Rechtmäßigkeit, ordnungsgemaessen Datenverarbeitung und Kostenerhebung.
- Beispiel Brandenburg: Für SolumWEB ist eine foermliche Zulassung nach § 133 Abs. 2 GBO und Anmeldung am Landes-Grundbuchportal erforderlich; das Portal weist ausdrücklich auf Phishing-Risiken hin.

## Leitentscheidung

NaC sollte in drei Stufen vorgehen:

1. **Zulassungs- und Workflow-Companion**
   - NaC führt Zulassungen, Rollen, berechtigtes Interesse, Aktenbezug, Vollmachten, Gebühren und Evidence.
   - Der Abruf selbst erfolgt weiterhin durch berechtigte Nutzer im offiziellen Länderportal.
   - NaC speichert standardmäßig keine Grundbuchinhalte, sondern Hashes und Nachweise.

2. **Evidence-Import und kontrollierte Ablage**
   - Nutzer können Grundbuchauszüge oder Abrufnachweise explizit bereitstellen.
   - NaC erfasst Hash, Abrufgrund, Aktenzeichen, Portal/Bundesland, Zeitstempel und Verantwortliche.
   - Speicherung von Inhalten nur nach Mandantenpolicy, verschlüsselt und mit strengem Zugriff.

3. **Autorisierter Direktabruf pro Bundesland**
   - nur nach foermlicher Zulassung, Vertrag/Genehmigung, technischer Dokumentation und Sicherheitsfreigabe
   - keine inoffizielle Browserautomation
   - keine Nutzung fremder Zugangsdaten außerhalb genehmigter Rollen
   - pro Land getrennte Adapter, weil Portale und Zulassungsstellen länderspezifisch sind

## Architektur

```text
Kundenorganisation
  berechtigter Nutzer / Notariat / Bank / Kanzlei / Behoerde
  offizielles Landes-Grundbuchportal
  lokale Dokumentablage oder DMS
  nac-grundbuch-local-plugin
        |
        | Evidence, Hashes, Abrufgrund, Freigaben
        v
NaC SaaS / OCI
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
- Vier-Augen-Freigaben für sensible Abrufe erzwingen
- Abrufattestationen erfassen, nachdem der berechtigte Nutzer im offiziellen Portal gearbeitet hat
- importierte Grundbuchauszüge hashen und optional in kundengesteuerter Ablage referenzieren
- Gebühren- und Abrufzählungsnachweise für interne Kontrolle vorbereiten
- Phishing- und Portal-Link-Hygiene unterstützen, z.B. nur bekannte offizielle Domains oeffnen

## Was das Plugin nicht tun darf

- keine Grundbuchportale ohne Zulassung automatisiert abfragen
- keine Portal-Zugangsdaten, Kennwörter, Zertifikate oder Codezeichen in NaC speichern
- keine heimliche Browserautomation oder Scraping
- keine Suche nach Eigentümer oder Grundbuchblatt ohne dokumentiertes berechtigtes Interesse
- keine Grundbuchinhalte an LLMs übergeben
- keine Nutzung eines Zugangs durch nicht zugelassene Personen oder Organisationen
- keine zentrale Mischablage für mehrere Kunden
- keine Direktintegration pro Bundesland ohne Genehmigung, technische Dokumentation und Sicherheitsfreigabe

## Integrationspfade

### Pfad A: Zulassungs- und Evidence-Companion (MVP)

Dieser Pfad ist sofort planbar.

- NaC verwaltet Zulassungen und Rollen.
- NaC erzeugt Abrufvorgänge mit Pflichtfeldern.
- NaC prüft, ob für Land, Nutzergruppe und Abrufgrund eine passende Zulassung dokumentiert ist.
- NaC oeffnet das offizielle Portal, führt aber keinen Abruf aus.
- Der Nutzer bestätigt nach Durchführung den Abruf und importiert optional Nachweise.

Empfehlung: Das ist der erste Schritt.

### Pfad B: Kontrollierter Dokument- und Nachweisimport

- Grundbuchauszüge bleiben primär im Kundensystem.
- NaC speichert nur Hash, Speicherort, Aktenzeichen, Zeitstempel und Freigaben.
- Wenn Inhalte in NaC gespeichert werden, dann nur tenantisoliert, verschlüsselt, mit strenger Retention und Zugriffskontrolle.
- LLM-Verarbeitung bleibt deaktiviert, bis eine ausdrückliche Policy je Mandant und Vorgang existiert.

### Pfad C: Autorisierter Direktadapter

Dieser Pfad ist nur nach Zulassung und technischer Klärung zulässig.

Voraussetzungen:

- formale Zulassung zum automatisierten Abrufverfahren
- geklärte Rolle: Kunde, SaaS-Anbieter, technischer Dienstleister oder zugelassene Stelle
- Dokumentation der erlaubten Abrufarten und Nutzer
- technische Spezifikation des jeweiligen Landesportals oder Abrufverfahrens
- Vereinbarung über Protokollierung, Codezeichen, Geheimnisverwahrung und Missbrauchsschutz
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
- `grundbuch.direct.retrieve_sheet` (später, nur mit Zulassung)
- `grundbuch.direct.search_sheet` (später, nur mit Zulassung)

## Evidence-Modell

```json
{
  "plugin": "nac-grundbuch",
  "tenant_id": "customer-compartment-or-nac-tenant-id",
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
    "approved_by": "nac-user-id"
  },
  "retrieval": {
    "performed_externally": true,
    "performed_by": "nac-user-id",
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

## NaC-Prozesstypen

- `grundbuch_admission_management`
- `grundbuch_access_request`
- `grundbuch_legitimate_interest_review`
- `grundbuch_retrieval_attestation`
- `grundbuch_document_archival`
- `grundbuch_fee_reconciliation`
- `grundbuch_audit_export`
- `grundbuch_direct_retrieval` (später)

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

Für SaaS gilt weiter: ein Compartment pro Kunde.

Empfohlen:

- `nac-platform`
  - zentrale Plugin-Definition, CI, Policy und Observability
- `nac-shared-security`
  - Vault, KMS, Audit, Logging, Security Zones, Budgets
- `customer-<id>`
  - kundenspezifische Workflows
  - Evidence-Buckets
  - tenantisolierte Secrets nur bei späterem Direktadapter
  - kundenspezifische Retention und Zugriffskontrolle

Für Grundbuchdaten besonders wichtig:

- Grundbuchinhalte sind hochsensibel und können Eigentums-, Belastungs- und Personenbezug enthalten.
- Standard ist: keine Inhalte in NaC, nur Hashes und Metadaten.
- Wenn Inhalte gespeichert werden, dann pro Kunde verschlüsselt, mit striktem Need-to-know, Retention, Legal Hold und Exportkontrolle.
- Zugriff auf Grundbuch-Evidence sollte enger sein als normaler Projekt- oder CRM-Zugriff.

## MVP

Umsetzung für die erste Iteration:

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
- Beispielworkflow für einen eingeschraenkten Abruf mit Vollmacht oder Aktenbezug
- Tenant-Onboarding-Runbook ohne Portalzugangsdaten

Nicht im MVP:

- direkte Portalabfrage
- Eigentümersuche durch NaC
- Speicherung von Portalzugangsdaten oder Codezeichen
- browserbasierte Automation
- LLM-Verarbeitung von Grundbuchauszügen
- landesspezifischer Direktadapter

## Sicherheitsanforderungen

- Kein Abruf ohne dokumentierte Zulassung.
- Kein Abruf ohne berechtigtes Interesse oder passende Nutzergruppe.
- Kein Zugriff durch nicht zugelassene Personen.
- Keine Speicherung von Zugangsdaten, Kennwörtern, Zertifikaten oder Codezeichen im MVP.
- Vier-Augen-Prinzip für risikoreiche Abrufe konfigurierbar.
- Evidence append-only und revisionsfest.
- Jede Aktion mit Nutzer, Rolle, Zeitstempel, Kunde, Aktenzeichen und Zweckbindung.
- Hash-first-Design für Dokumente.
- Keine Prompt-/Telemetry-Erfassung von Grundbuchinhalten.
- Phishing-Schutz durch Domain-Allowlist für offizielle Portale.
- CIS-/C5-orientierte OCI-Baseline: IAM least privilege, MFA, Vault, KMS, Logging, Budgets, Security Zones wo sinnvoll.
- Datenschutz-Folgenabschaetzung vor Speicherung oder automatisierter Verarbeitung von Grundbuchinhalten.

## SaaS-Anbieter-Runbook

1. Rolle klären: NaC als Prozessbegleiter, technischer Dienstleister oder selbst zugelassene Stelle.
2. Pro Zielbundesland Zulassungsprozess und Stelle identifizieren.
3. Kundengruppen und Nutzergruppen bestimmen: Notariat, Kanzlei, Bank, Behörde, Versorger, sonstige.
4. Zulassungsnachweise und Genehmigungsumfang als NaC-Objekte modellieren.
5. TOMs für ordnungsgemaesse Datenverarbeitung und Missbrauchsschutz dokumentieren.
6. Portal-Domain-Allowlist und Phishing-Hinweise einrichten.
7. MVP-Plugin ohne Secrets bauen.
8. Evidence-Schema und Retention je Kunde festlegen.
9. Kundenspezifisches OCI-Compartment anlegen.
10. Pilot mit rein manuellem Portalabruf und NaC-Evidence durchführen.
11. Erst danach prüfen, ob ein genehmigter Direktadapter je Bundesland machbar ist.

## Kunden-Onboarding-Runbook

1. Kunde benennt Bundesländer, Organisationseinheiten und berechtigte Nutzer.
2. Kunde liefert vorhandene Zulassungen oder startet den Zulassungsantrag beim jeweiligen Land.
3. NaC erfasst Zulassungsart, Gültigkeit, Nutzerkreis und erlaubte Abrufgründe.
4. Kunde definiert Freigaberegeln und Retention für Grundbuchnachweise.
5. NaC legt Kundentenant und Evidence Store an.
6. NaC aktiviert Grundbuch-Prozessvorlagen.
7. Erster Abruf wird manuell im offiziellen Portal durchgeführt.
8. NaC erfasst berechtigtes Interesse, Attestation, Hash und Gebührenereignis.
9. Review: Welche Daten dürfen später gespeichert oder automatisiert verarbeitet werden?

## Offene Entscheidungen

- Soll NaC selbst jemals als zugelassene abrufende Stelle auftreten oder nur Kundenprozesse begleiten?
- Welche Bundesländer sind für die ersten Kunden relevant?
- Welche Nutzergruppen sind Zielkunden: Kanzleien, Notariate, Banken, Immobilienunternehmen, Versorger, Behörden?
- Welche Abrufgründe sollen im MVP erlaubt sein?
- Sollen Grundbuchauszüge überhaupt in NaC gespeichert werden oder nur im Kundensystem?
- Welche Retention gilt für Evidence und importierte Dokumente?
- Gibt es landesspezifische technische Schnittstellen, die offiziell für Dienstleister freigegeben sind?
- Wie wird Kostenkontrolle pro Kunde und Abruf umgesetzt?

## Akzeptanzkriterien für die erste Umsetzung

- Plugin führt keinen direkten Abruf durch.
- Plugin speichert keine Portal-Zugangsmittel.
- Jeder Vorgang enthält Bundesland, Zulassungsstatus, Abrufgrund, Aktenbezug und verantwortliche Person.
- Jeder importierte Nachweis wird gehasht.
- Grundbuchinhalte werden standardmäßig nicht in NaC gespeichert.
- Freigaben und Attestationen sind zeitgestempelt und rollenbasiert.
- Offizielle Portale und rechtliche Quellen sind dokumentiert.
- Tenant-Isolation ist pro Kunde dokumentiert.

## Quellen

- Gemeinsames Grundbuchportal der Länder: https://www.grundbuchportal.de/
- Allgemeine Hinweise zur Internet-Grundbucheinsicht: https://grundbuchportal.de/allg-infos.htm
- Justizportal des Bundes und der Länder, Internet-Grundbucheinsicht: https://www.justiz.de/onlinedienste/internet_grundbucheinsicht/index.php
- Beispiel Landesportal Brandenburg / SolumWEB: https://grundbuch.brandenburg.de/
- Grundbuchordnung § 133: https://www.gesetze-im-internet.de/gbo/__133.html
- Grundbuchverfügung § 80: https://www.gesetze-im-internet.de/gbvfg/__80.html
- Grundbuchverfügung § 82: https://www.gesetze-im-internet.de/gbvfg/__82.html
- Grundbuchverfügung § 83: https://www.gesetze-im-internet.de/gbvfg/__83.html
