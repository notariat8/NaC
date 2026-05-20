# ELSTER Developer Plugin Integration Plan

Stand: 2026-05-11

Dieser Plan beschreibt, wie NaC ELSTER-nahe Prozesse als Plugin integrieren kann. Ziel ist nicht, Mein ELSTER heimlich zu automatisieren oder nichtöffentliche Schnittstellen zu nutzen. Ziel ist ein sicherer, auditierbarer SaaS- und Local-Companion-Ansatz, der später zu einer offiziellen ERiC-basierten Herstellerintegration ausgebaut werden kann.

## Zielbild

NaC soll steuer- und verwaltungsnahe Workflows für SaaS-Kunden abbilden:

- Vorbereitung und Nachweis von ELSTER-relevanten Abgaben, Meldungen und Bescheiden
- sichere Verwaltung von Mandanten-, Organisations- und Benutzerkontexten
- Hash- und Evidence-Erfassung statt unnötiger Speicherung steuerlicher Inhalte
- kontrollierte Freigabe durch berechtigte Personen
- optionaler Ausbau zu ERiC, wenn NaC als Hersteller/Entwickler registriert ist
- optionaler Ausbau zu Mein Unternehmenskonto / Organisationszertifikat-Workflows für Verwaltungsleistungen

## Offizielle Faktenbasis

- ELSTER stellt für Entwickler den Weg über Registrierung als Hersteller/Entwickler bereit. Danach prüft der IuK-Bereich des Bayerischen Landesamts für Steuern, ob Softwareherstellung beabsichtigt ist, und richtet Zugang zum Entwicklerbereich ein.
- ERiC, der ELSTER Rich Client, ist eine C-Bibliothek mit Schnittstellenspezifikation. Sie wird kostenlos für Steuer-, Finanz- und Lohnbuchhaltungsprogramme bereitgestellt.
- ERiC plausibilisiert Steuerdaten und übermittelt sie verschlüsselt über eine sichere Verbindung an die Annahmeserver der Finanzverwaltung. Bei erfolgreicher Rückmeldung kann ERiC eine PDF-Datei erstellen.
- Für die Teilnahme als Softwarehersteller ist eine Hersteller-ID zu beantragen; der ELSTER-Newsletter ist für Änderungen und Neuerungen relevant.
- Mein ELSTER nutzt elektronische Zertifikate für Authentifizierung und Verschlüsselung; ElsterSecure ist eine mobile Login-Alternative ohne Zertifikatsdatei.
- Für Mein ELSTER gelten Systemvoraussetzungen für Browser, Zertifikatsdatei, ElsterSecure, Personalausweis, Sicherheitsstick, Signaturkarte und ElsterAuthenticator.
- Der ElsterAuthenticator ist die lokale Schnittstelle für Sicherheitsstick bzw. Signaturkarte und wird u.a. für Login, Registrierung, authentisierte Datenübermittlung, Entschlüsselung von Postfachnachrichten und ELSTER-fit-Prüfung eingesetzt.
- Mein Unternehmenskonto nutzt ELSTER-Technologie als digitale Identität für Organisationen. Für Portalbetreiber verweist ELSTER auf das MUK Self Service Portal; Grundlage sind ELSTER-Organisationszertifikate.

## Leitentscheidung

NaC sollte in drei Stufen vorgehen:

1. **Local/Workflow Companion für ELSTER-Prozesse**
   - kein Scraping
   - keine PIN-, Passwort- oder Zertifikatsdatei-Speicherung
   - kein automatisches Absenden
   - Evidence, Checklisten, Hashes, Benutzerfreigaben und Betriebsnachweise

2. **Offizielle ERiC-Herstellerintegration**
   - nur nach Entwicklerregistrierung, Zugang zum Entwicklerbereich, ERiC-Lizenz-/Nutzungsprüfung und Hersteller-ID
   - technische Integration über die dokumentierte ERiC-C-Bibliothek
   - NaC wird damit zu einer steuerlichen Fachsoftware-Komponente mit hohem Compliance- und Haftungsanspruch

3. **Mein Unternehmenskonto / Organisationsidentität**
   - für SaaS-Kunden, die Verwaltungsleistungen über Organisationszertifikate nutzen
   - getrennte Behandlung von Steuerdatenübermittlung und Verwaltungsportal-Login
   - Mandantenfähigkeit pro Kunde und pro Organisation

## Architektur

```text
Kundenumgebung / Arbeitsplatz / Terminalserver
  Browser: Mein ELSTER oder angeschlossenes Fachportal
  ElsterSecure / Zertifikatsdatei / ElsterAuthenticator
  optional später: ERiC Runtime
  nac-elster-local-plugin
        |
        | Evidence, Hashes, Status, Freigaben
        v
NaC SaaS / OCI
  elster workflow service
  tenant evidence store
  audit journal
  policy engine
  onboarding registry
```

## Was das Plugin tun darf

- ELSTER- und ERiC-relevante Workflows in NaC modellieren.
- Prüfen, ob lokale Voraussetzungen dokumentiert sind: Browser, JavaScript/Cookies, ElsterSecure, ElsterAuthenticator, Sicherheitsstick/Signaturkarte oder Zertifikatsdatei.
- Mein ELSTER oder offizielle Informationsseiten im Browser oeffnen.
- Aufgabenpakete vorbereiten: Steuerart, Zeitraum, verantwortliche Person, Frist, Anlagenliste, Freigabeweg.
- Dateien lokal hashen und Metadaten erfassen, ohne Inhalte in die SaaS zu übertragen.
- Benutzerattestationen erfassen, z.B. "Übermittlung in ELSTER durchgeführt", "Rückmeldung geprüft", "PDF-Nachweis abgelegt".
- ELSTER-Rückmelde-, Transfer- oder PDF-Nachweise importieren, wenn der Nutzer sie explizit bereitstellt.
- Versions- und Betriebsnachweise für ERiC vorbereiten, sobald die offizielle Herstellerintegration beginnt.

## Was das Plugin nicht tun darf

- keine ELSTER-Passwörter, PINs, Zertifikatsdateien oder privaten Schlüssel in NaC speichern
- keine heimliche Browsersteuerung oder Portal-Scraping
- keine nichtöffentlichen ELSTER-Endpunkte nachbauen
- keine automatische Abgabe ohne explizite Benutzerfreigabe
- keine Steuerberatung simulieren
- keine steuerlichen Inhalte an LLMs geben, solange keine explizite Mandantenfreigabe und Inhaltsklassifikation vorliegt
- keine ERiC-Integration vor Abschluss der Hersteller-/Entwicklerregistrierung und Prüfung der Nutzungsbedingungen

## Integrationspfade

### Pfad A: Local/Workflow Companion (MVP)

Dieser Pfad ist sofort planbar und sicherheitsseitig beherrschbar.

- NaC führt den Prozess.
- Der Nutzer arbeitet weiterhin in Mein ELSTER oder einem zugelassenen Fachprogramm.
- NaC dokumentiert Nachweise, Fristen, Freigaben und Hashes.
- SaaS speichert keine geheimen ELSTER-Zugangsmittel.

Empfehlung: Dieser Pfad ist der erste Schritt.

### Pfad B: ERiC-Herstellerintegration

Dieser Pfad ist die fachlich saubere Variante für echte Softwareübermittlung.

Voraussetzungen:

- Registrierung als Hersteller/Entwickler
- Zugang zum ELSTER-Entwicklerbereich
- Download von ERiC und Schnittstellenspezifikation
- Beantragung und Verwaltung der Hersteller-ID
- Aufbau einer Test-, Release- und Update-Strategie für ERiC-Versionen
- rechtliche Prüfung, wer Hersteller, Betreiber und Verantwortlicher ist

Technische Konsequenz:

- NaC braucht eine native Runtime-Komponente oder einen isolierten Sidecar, der die ERiC-C-Bibliothek nutzt.
- OCI Functions sind für ERiC nur bedingt geeignet, weil Native Libraries, Zertifikate, Testbarkeit und Versionsfreigaben kontrolliert werden müssen.
- Besser: containerisierte Workload in OCI Container Instances oder OKE, mit tenantisolierter Konfiguration und strengem Secret Handling.

### Pfad C: Mein Unternehmenskonto / Portalbetreiber

Dieser Pfad betrifft digitale Verwaltungsleistungen und Unternehmensidentität, nicht automatisch steuerliche Datenübermittlung.

- Organisationen nutzen ELSTER-Organisationszertifikate.
- Portalbetreiber sollen sich über das MUK Self Service Portal informieren.
- NaC kann Mandanten-Onboarding, Organisationszertifikat-Status, Rollen und Evidence modellieren.
- Direkte Authentifizierungsintegration ist erst nach offizieller MUK-Portalbetreiberklärung zu planen.

## Plugin-Schnittstelle

Vorgeschlagene Commands:

- `elster.health`
- `elster.open_portal`
- `elster.open_developer_info`
- `elster.check_local_requirements`
- `elster.check_auth_method`
- `elster.prepare_submission`
- `elster.prepare_attachment_package`
- `elster.record_user_attestation`
- `elster.record_submission_confirmation`
- `elster.record_response_pdf`
- `elster.record_inbox_check`
- `elster.get_evidence`
- `elster.eric.runtime_status` (später)
- `elster.eric.validate_payload` (später)
- `elster.eric.submit_payload` (später, nur nach Herstellerfreigabe)
- `elster.muk.organization_certificate_status` (später)

## Evidence-Modell

```json
{
  "plugin": "nac-elster",
  "tenant_id": "customer-compartment-or-nac-tenant-id",
  "organization_id": "customer-organization-id",
  "workflow_id": "elster-workflow-2026-0001",
  "workflow_type": "elster_submission_preparation",
  "tax_context": {
    "procedure": "ustva|est|kst|lst|other",
    "period": "2026-04",
    "jurisdiction": "DE"
  },
  "actor": {
    "user_id": "nac-user-id",
    "role": "preparer|approver|submitter|auditor"
  },
  "local_checks": {
    "auth_method": "certificate_file|elstersecure|security_stick|signature_card|unknown",
    "elster_authenticator": "present|not_required|unknown",
    "browser_requirements_checked": true
  },
  "documents": [
    {
      "label": "prepared-payload-or-export",
      "sha256": "hex",
      "content_stored_in_oac": false
    }
  ],
  "attestations": [
    {
      "type": "user_confirmed_submission",
      "timestamp": "2026-05-11T00:00:00Z",
      "text": "Übermittlung wurde im offiziellen ELSTER-Kontext durchgeführt."
    }
  ],
  "external_references": [
    {
      "type": "elster_confirmation_pdf",
      "sha256": "hex",
      "stored_location": "customer-controlled-storage"
    }
  ]
}
```

## NaC-Prozesstypen

- `elster_submission_preparation`
- `elster_submission_approval`
- `elster_submission_evidence`
- `elster_inbox_check`
- `elster_response_archival`
- `elster_eric_validation`
- `elster_eric_submission`
- `muk_organization_identity_onboarding`

Statusmodell:

- `draft`
- `prepared`
- `needs_review`
- `approved`
- `submitted_externally`
- `response_recorded`
- `archived`
- `cancelled`
- `blocked_missing_authorization`

## Mandanten- und Compartment-Konzept

Für SaaS gilt weiter: ein Compartment pro Kunde.

Empfohlen:

- `nac-platform`
  - zentrale Build-, Policy- und Observability-Ressourcen
- `nac-shared-security`
  - Vault, KMS, Audit, Logging, Security Zones, Budgets
- `customer-<id>`
  - kundenspezifische Workloads
  - Evidence-Buckets
  - tenantisolierte Secrets
  - optional ERiC Sidecar/Runtime pro Kunde oder pro streng isolierter Kundengruppe

Für ELSTER besonders wichtig:

- Zertifikatsdateien und private Zugangsmittel bleiben primär beim Kunden.
- Falls später ein serverseitiger ERiC-Betrieb rechtlich und technisch freigegeben wird, müssen Secrets pro Kunde im Vault liegen, mit Rotation, Zugriffsnachweis und Break-Glass-Prozess.
- NaC speichert standardmäßig nur Hashes, Metadaten und explizit freigegebene Nachweise.

## MVP

Umsetzung für die erste Iteration:

- Markdown-Dokumentation und Plugin-Spezifikation
- lokaler `elster.health`-Check als Platzhalter
- `elster.open_portal` für offizielle ELSTER-Seiten
- `elster.check_local_requirements` als Checkliste
- `elster.prepare_submission` für NaC-Prozessanlage
- `elster.record_user_attestation`
- `elster.record_submission_confirmation`
- Evidence-JSON-Schema
- Beispielworkflow für Umsatzsteuer-Voranmeldung oder allgemeine ELSTER-Abgabe
- Tenant-Onboarding-Runbook ohne Speicherung von ELSTER-Geheimnissen

Nicht im MVP:

- direkte ERiC-Datenübermittlung
- automatische Portalbedienung
- Login-Automation
- Zertifikatsdatei-Upload in NaC
- steuerliche Inhaltsanalyse durch LLM
- MUK-Portalbetreiberintegration

## Sicherheitsanforderungen

- Keine Speicherung von ELSTER-Zugangsmitteln im MVP.
- Strikte Trennung zwischen Kunde, Organisation, Benutzer und Prozess.
- Evidence als append-only Journal.
- Hash-first-Design für Dokumente.
- Kundenseitige Entscheidung, welche Inhalte in NaC gespeichert werden.
- Audit-Logs für jede Attestation und jeden Nachweisimport.
- Kein Screenshot-Logging von Steuerdaten.
- Keine Prompt- oder Telemetrieaufnahme steuerlicher Inhalte.
- CIS-/C5-orientierte OCI-Baseline: IAM least privilege, MFA, Vault, Logging, Budgets, Security Zones wo sinnvoll.
- Datenschutz-Folgenabschaetzung prüfen, sobald personenbezogene Steuerdaten verarbeitet werden.

## SaaS-Anbieter-Runbook

1. Offizielle ELSTER-Entwicklerregistrierung klären.
2. Rollen festlegen: NaC als reiner Prozessbegleiter oder als Hersteller/Entwickler mit ERiC.
3. Datenschutz- und Haftungsgrenzen dokumentieren.
4. MVP-Plugin ohne Secrets bauen.
5. Evidence-Schema und Retention je Kunde festlegen.
6. Kundenspezifisches OCI-Compartment anlegen.
7. Policies, Vault, Logging, Budgets und Object Storage einrichten.
8. ELSTER-Prozessvorlagen in NaC hinterlegen.
9. Kundentest mit manuell bereitgestellten ELSTER-Nachweisen durchführen.
10. Erst danach ERiC-Zugang, Hersteller-ID und technische Spezifikation für Pfad B verwenden.

## Kunden-Onboarding-Runbook

1. Kunde benennt Organisation, Steuernummer-/ELSTER-Kontext und verantwortliche Rollen.
2. Kunde bestätigt, welche ELSTER-Login-Variante genutzt wird.
3. NaC prüft nur Voraussetzungen, keine Geheimnisse.
4. NaC legt Kundentenant und Evidence Store an.
5. NaC aktiviert Prozessvorlagen für relevante ELSTER-Verfahren.
6. Kunde führt erste Abgabe weiter im offiziellen ELSTER-Kontext durch.
7. Kunde importiert oder bestätigt Nachweise.
8. NaC schreibt Audit- und Evidence-Records.
9. Review: Welche Daten dürfen künftig automatisiert verarbeitet werden?

## Offene Entscheidungen

- Soll NaC selbst als ELSTER-Hersteller/Entwickler registriert werden?
- Welche Steuerverfahren sind zuerst relevant: UStVA, Lohnsteuer, E-Bilanz, Bescheiddaten, allgemeine Anlagen?
- Soll die erste ERiC-Runtime lokal beim Kunden oder serverseitig in OCI laufen?
- Welche Kundendaten dürfen in NaC gespeichert werden, welche nur gehasht?
- Ist Mein Unternehmenskonto für NaC als Portalbetreiber relevant oder nur als Kundenidentitätsprozess?
- Welche Haftungs- und Freigabegrenzen gelten zwischen SaaS-Anbieter, Kunde und steuerlichem Berater?

## Akzeptanzkriterien für die erste Umsetzung

- Plugin speichert keine ELSTER-Zugangsmittel.
- Jeder ELSTER-Prozess erzeugt einen nachvollziehbaren Evidence Record.
- Dokumentinhalte werden standardmäßig nicht in NaC übertragen.
- Benutzerfreigaben sind explizit, zeitgestempelt und rollenbasiert.
- Offizielle ELSTER-Seiten und Quellen sind in der Dokumentation referenziert.
- ERiC-Funktionen bleiben deaktiviert, bis Entwicklerzugang, Hersteller-ID und technische Spezifikation vorliegen.
- Tenant-Isolation ist pro Kunde dokumentiert.

## Quellen

- ELSTER Entwickler: https://www.elster.de/eportal/infoseite/entwickler
- ELSTER Erfolgsgeschichte / ERiC und Sicherheitskontext: https://www.elster.de/eportal/infoseite/elster_eine_erfolgsstory
- ELSTER Systemanforderungen: https://www.elster.de/elsterweb/infoseite/systemanforderungen
- ElsterSecure: https://www.elster.de/elsterweb/infoseite/app/elstersecure
- ElsterAuthenticator: https://www.elster.de/eportal/infoseite/elsterauthenticator
- Mein Unternehmenskonto: https://www.elster.de/eportal/infoseite/nezo
- Mein Unternehmenskonto Informationsseite: https://mein-unternehmenskonto.de/
