# Handelsregister / bundesAPI Plugin Integration Plan

Stand: 2026-05-11

Dieser Plan beschreibt, wie NaC Handelsregister-Recherchen und Register-Evidence als Plugin integrieren kann. Ausgangspunkt ist das GitHub-Projekt `bundesAPI/handelsregister`. Das Projekt kann als technischer Spike dienen, sollte aber nicht ungeprüft als produktiver SaaS-Connector übernommen werden. Maßgeblich bleiben die Nutzungsordnung des gemeinsamen Registerportals der Länder, HGB/HRV, Datenschutz, Zweckbindung und die betrieblichen Grenzen des Portals.

## Zielbild

NaC soll Handelsregister-bezogene Workflows für SaaS-Kunden abbilden:

- gezielte Einzelrecherche zu Unternehmen und Rechtsträgern
- strukturierte Erfassung von Registergericht, Registerart, Registernummer, Firma, Status und Sitz
- Nachweis, wann welche Registerinformation für welchen Geschäftsvorgang abgerufen wurde
- Hash- und Evidence-Erfassung für Registerauszüge, Dokumente und SI/XML-Inhalte
- klare Rate Limits und Schutz gegen Massenabrufe
- optionaler technischer Adapter auf Basis von `bundesAPI/handelsregister` oder einer eigenen, freigegebenen Implementierung
- optionaler Whitelist-IP-/Sonderzugang nur nach Antrag und Nachweis eines berechtigten Erfordernisses

## Offizielle Faktenbasis

- Das gemeinsame Registerportal der Länder ist das elektronische Informations- und Kommunikationssystem, über das Daten aus den Rechtsträgerregistern der Justiz abrufbar sind.
- Das Portal umfasst u.a. Handelsregister A und B, Genossenschaftsregister, Partnerschaftsregister, Gesellschaftsregister und Vereinsregister.
- Bereitgestellt werden u.a. Indexdaten, Dokumente, Unternehmensträgerdaten, sonstige Veröffentlichungen, aktueller Abdruck, chronologischer Abdruck, historischer Abdruck und strukturierter Registerinhalt als XML-Datei.
- Nach der Nutzungsordnung ist die Einsichtnahme zu Informationszwecken durch einzelne Abrufe gestattet.
- Systematische Abrufe zum Aufbau, Ausbau oder zur Aktualisierung eigener Voll- oder Teilregister sind unzulässig.
- Normale Nutzung darf nicht mehr als 60 Suchen oder Rechtsträgeraufrufe pro Stunde im Registerportal vornehmen.
- Für höhere Abruffrequenz kann bei der Servicestelle Registerportal beim Amtsgericht Hagen ein Zugang mit registrierter IP-Adresse beantragt werden; Umfang und Zweck der Abrufe müssen angegeben werden.
- Das Registerportal kann IP-Adressen sperren und Sessions beenden, wenn ein Verstoss gegen gesetzliche Vorgaben oder Nutzungsordnung vermutet wird.
- Das Portal weist darauf hin, dass es regelmäßig Ziel automatisierter Massenabfragen ist; bei sehr hoher Frequenz können strafrechtliche Risiken im Raum stehen.
- Statushinweise des Portals zeigen, dass Suche, Dokumentenabruf und strukturierter Registerinhalt phasenweise eingeschraenkt sein können.

## Fakten zum GitHub-Projekt

- Repository: `https://github.com/bundesAPI/handelsregister`
- Public Repository, Python-basiert, keine Releases sichtbar.
- README beschreibt eine "Handelsregister API" und die POST-Parameter der erweiterten Suche.
- Die CLI ist im README als "work in progress" gekennzeichnet.
- `pyproject.toml` nennt Python `>3.6.2,<4` und nutzt u.a. `mechanize` und `mechanicalsoup`.
- `handelsregister.py` steuert das Webportal programmatisch über `mechanize`, setzt Browser-Header und parst HTML mit BeautifulSoup.
- Im Code ist Rate-Limiting als TODO markiert; ein produktionsreifer Token-Bucket ist nicht implementiert.
- Im Repo-Listing ist kein LICENSE-File sichtbar. Vor Codeübernahme ist daher zwingend zu klären, ob und unter welchen Bedingungen der Code genutzt, verändert oder verteilt werden darf.

## Leitentscheidung

NaC sollte in drei Stufen vorgehen:

1. **Register-Evidence-Companion**
   - NaC führt den Businessprozess, die Recherche erfolgt manuell oder kontrolliert.
   - Kein Aufbau eigener Registerdatenbank.
   - Kein Massenabruf.
   - Standardmäßig werden nur Suchauftrag, Treffer-Metadaten, Hashes, Attestationen und Quellenlinks gespeichert.

2. **Kontrollierter Einzelabruf-Adapter**
   - technischer Adapter für gezielte Einzelrecherche
   - harte Rate Limits unterhalb der Portalgrenze
   - Zweckbindung je Request
   - Cache nur fallbezogen und mit Retention
   - keine parallelen Voll-/Teilregister

3. **Registrierte IP / Sondernutzung**
   - nur bei nachgewiesenem Erfordernis
   - Antrag bei der Servicestelle Registerportal
   - dokumentierter Umfang und Zweck
   - widerrufbare Freigabe einkalkulieren
   - eigene Monitoring-, Audit- und Abuse-Detection

## Architektur

```text
NaC SaaS / OCI
  handelsregister workflow service
  purpose and rate-limit engine
  tenant evidence store
  audit journal
  optional retrieval adapter
        |
        | controlled single retrievals
        v
Gemeinsames Registerportal der Laender
  Normal search / Advanced search
  Register announcements
  Documents
  Structured register content (SI/XML)
```

Optional lokal:

```text
Kundenarbeitsplatz
  Browser / Registerportal
  nac-handelsregister-local-plugin
        |
        | hashes, attestations, selected metadata
        v
NaC SaaS
```

## Was das Plugin tun darf

- offizielle Registerportal-Seiten oeffnen
- gezielte Suchaufträge für einzelne Unternehmen anlegen
- Suchparameter dokumentieren: Firma, Registerart, Registernummer, Registergericht, Bundesland, Sitz, PLZ
- Treffer-Metadaten strukturiert speichern
- Registerauszüge, Dokumente oder SI/XML nur fallbezogen hashen und referenzieren
- Benutzerattestationen erfassen, z.B. "Registerauszug wurde im Registerportal geprüft"
- Abrufzeitpunkt, Zweck, Nutzer, Tenant und Case-ID protokollieren
- Statushinweise des Registerportals als Betriebsrisiko berücksichtigen
- Rate Limits hart erzwingen und pro Kunde quotieren
- bei Bedarf Whitelist-IP-Antrag und Sonderfreigaben als NaC-Objekte dokumentieren

## Was das Plugin nicht tun darf

- keine systematischen Voll- oder Teilregister aufbauen
- keine Massenabfragen
- keine Umgehung von Portalgrenzen, IP-Sperren oder Session-Schutz
- keine parallele Hochlast-Suche über mehrere Tenants zur Umgehung der 60/h-Grenze
- keine gezielte Suche nach natuerlichen Personen
- keine ungeprüfte produktive Nutzung von `bundesAPI/handelsregister`
- keine Speicherung personenbezogener Registerdokumente ohne Mandantenpolicy
- keine Weiterverwendung unter der Bezeichnung "Handelsregister", soweit dadurch gesetzliche Vorgaben verletzt werden
- keine LLM-Verarbeitung von Registerdokumenten ohne explizite Freigabe und Datenklassifikation

## Integrationspfade

### Pfad A: Evidence-Companion (MVP)

Dieser Pfad ist sofort planbar.

- NaC erzeugt einen Registerrecherche-Vorgang.
- Nutzer recherchiert im offiziellen Registerportal.
- NaC speichert Suchparameter, Zweck, Treffer-Metadaten, Hashes und Attestation.
- Keine automatisierten Portalabrufe.
- Keine Inhalte in NaC, solange der Kunde dies nicht explizit erlaubt.

Empfehlung: Dieser Pfad ist der erste Schritt.

### Pfad B: Adapter-Spike mit bundesAPI

Dieser Pfad dient der technischen Bewertung, nicht sofort der Produktion.

Prüfpunkte:

- Lizenzstatus des Repositories klären.
- Abhängigkeiten und Wartungsstand bewerten.
- HTML-/JSF-Abhängigkeit und Bruchrisiko des Parsers testen.
- Rate-Limit-Mechanismus nachruesten.
- Cache-Semantik auf Zweckbindung und Retention umbauen.
- Unit- und Integrationstests gegen kontrollierte Testfälle bauen.
- Robots-/Nutzungsordnungsfragen rechtlich prüfen.

Produktionsentscheidung erst nach Review.

### Pfad C: Eigener kontrollierter Registerportal-Adapter

Falls ein Adapter erlaubt und benötigt ist, sollte NaC eine eigene kleine Komponente bauen:

- Request-Queue statt direkter Abrufe
- Token Bucket pro NaC-Installation, pro IP, pro Tenant und pro User
- harte globale Obergrenze unterhalb 60/h, solange keine Whitelist-IP genehmigt ist
- deduplizierte Suchaufträge
- Backoff bei Portalproblemen
- keine parallelen Abfragen für Bulk-Listen
- beweissicheres Audit Journal

### Pfad D: Registrierte IP / Sonderzugang

Nur bei belastbarem Business Case:

- Umfang und Zweck der Abrufe beschreiben
- Antrag bei Servicestelle Registerportal beim AG Hagen vorbereiten
- technische IP-Architektur in OCI festlegen
- Egress-IP stabilisieren
- Missbrauchsschutz, Monitoring und Limits dokumentieren
- Widerruf und Fallback auf manuelle Recherche einplanen

## Plugin-Schnittstelle

Vorgeschlagene Commands:

- `handelsregister.health`
- `handelsregister.open_portal`
- `handelsregister.open_advanced_search`
- `handelsregister.prepare_search`
- `handelsregister.record_search_attestation`
- `handelsregister.record_result_metadata`
- `handelsregister.record_document_hash`
- `handelsregister.record_si_xml_hash`
- `handelsregister.get_evidence`
- `handelsregister.export_audit_package`
- `handelsregister.adapter.status`
- `handelsregister.adapter.search_single_entity` (später)
- `handelsregister.adapter.fetch_register_printout` (später)
- `handelsregister.adapter.fetch_si_xml` (später)
- `handelsregister.whitelist_ip.prepare_application` (später)

## Evidence-Modell

```json
{
  "plugin": "nac-handelsregister",
  "tenant_id": "customer-compartment-or-nac-tenant-id",
  "organization_id": "customer-organization-id",
  "workflow_id": "handelsregister-workflow-2026-0001",
  "workflow_type": "register_lookup",
  "purpose": {
    "category": "kyb|contracting|vendor_onboarding|compliance|litigation|portfolio_monitoring|other",
    "case_reference": "customer-case-id",
    "description": "short non-sensitive purpose"
  },
  "query": {
    "company_name": "Example GmbH",
    "register_type": "HRB|HRA|GnR|PR|VR|all",
    "register_number": "optional",
    "register_court": "optional",
    "federal_state": "optional",
    "search_mode": "manual|adapter"
  },
  "rate_limit": {
    "adapter_enabled": false,
    "global_limit_per_hour": 60,
    "tenant_limit_per_hour": 10,
    "request_count_at_time": 1
  },
  "result_metadata": [
    {
      "name": "Example GmbH",
      "register_court": "Amtsgericht Example",
      "register_number": "HRB 12345",
      "state": "NW",
      "status": "current",
      "source_url": "https://www.handelsregister.de/"
    }
  ],
  "documents": [
    {
      "label": "current-printout-or-si-xml",
      "sha256": "hex",
      "content_stored_in_oac": false,
      "storage_reference": "customer-controlled-storage"
    }
  ],
  "attestations": [
    {
      "type": "user_confirmed_register_lookup",
      "timestamp": "2026-05-11T00:00:00Z",
      "text": "Recherche wurde als einzelner Abruf zu Informationszwecken im Registerportal durchgefuehrt."
    }
  ]
}
```

## NaC-Prozesstypen

- `handelsregister_lookup`
- `handelsregister_kyb_check`
- `handelsregister_vendor_onboarding`
- `handelsregister_document_archival`
- `handelsregister_si_xml_archival`
- `handelsregister_rate_limit_review`
- `handelsregister_whitelist_ip_application`
- `handelsregister_adapter_spike`

Statusmodell:

- `draft`
- `purpose_required`
- `approved`
- `manual_lookup_pending`
- `lookup_recorded`
- `documents_recorded`
- `archived`
- `blocked_rate_limit`
- `blocked_policy`
- `cancelled`

## Mandanten- und Compartment-Konzept

Für SaaS gilt weiter: ein Compartment pro Kunde.

Empfohlen:

- `nac-platform`
  - Plugin-Definition, CI, Adapter-Code, Observability
- `nac-shared-security`
  - Vault, KMS, Audit, Logging, Budgets, Egress-Kontrolle
- `customer-<id>`
  - kundenspezifische Workflows
  - Evidence-Buckets
  - tenantisolierte Retention
  - kundenspezifische Quoten

Für Handelsregister besonders wichtig:

- Eine globale Rate-Limit-Instanz verhindert, dass mehrere Kunden gemeinsam Portalgrenzen überschreiten.
- OCI-Egress muss kontrollierbar sein, falls später eine registrierte IP beantragt wird.
- Caches dürfen nicht zu einem parallelen Register anwachsen.
- Retention für Registerdokumente muss je Zweck und Kunde festgelegt werden.

## MVP

Umsetzung für die erste Iteration:

- Markdown-Dokumentation und Plugin-Spezifikation
- `handelsregister.health`
- `handelsregister.open_portal`
- `handelsregister.open_advanced_search`
- `handelsregister.prepare_search`
- `handelsregister.record_search_attestation`
- `handelsregister.record_result_metadata`
- `handelsregister.record_document_hash`
- Evidence-JSON-Schema
- Rate-Limit-Policy als NaC-Konfiguration
- Beispielworkflow für KYB/Vendor-Onboarding
- technische Spike-Notiz zu `bundesAPI/handelsregister`

Nicht im MVP:

- automatisierter Portalabruf
- Massensuche
- kontinuierliches Monitoring ganzer Firmenlisten
- Dokumentdownload per Adapter
- SI/XML-Abruf per Adapter
- Whitelist-IP-Sonderzugang
- produktive Nutzung des GitHub-Codes ohne Lizenz- und Rechtsprüfung

## Sicherheitsanforderungen

- Einzelabruf-Prinzip.
- Zweckbindung je Request.
- Kein Aufbau eigener Voll- oder Teilregister.
- Harte globale und tenantbezogene Rate Limits.
- Keine Umgehung von Portal-Sperren.
- Keine gezielte Personensuche.
- Keine Speicherung von Registerdokumenten ohne Mandantenpolicy.
- Evidence append-only und revisionsfest.
- Hash-first-Design für Dokumente.
- Keine Prompt-/Telemetry-Erfassung von Registerdokumenten.
- Datenschutzprüfung für Unternehmensträgerdaten und Dokumente mit Personenbezug.
- CIS-/C5-orientierte OCI-Baseline: IAM least privilege, MFA, Vault, KMS, Logging, Budgets, Security Zones wo sinnvoll.

## SaaS-Anbieter-Runbook

1. Rolle klären: NaC als Prozessbegleiter, technischer Rechercheadapter oder registrierter IP-Nutzer.
2. Nutzungsordnung und HGB/HRV-Anforderungen in Policies übersetzen.
3. Code-Lizenz von `bundesAPI/handelsregister` prüfen.
4. MVP ohne automatisierte Abrufe bauen.
5. Evidence-Schema und Retention je Kunde festlegen.
6. Globale und tenantbezogene Rate-Limits definieren.
7. Kundenspezifisches OCI-Compartment anlegen.
8. Pilot mit manueller Recherche und Evidence-Erfassung durchführen.
9. Adapter-Spike isoliert testen.
10. Erst nach Rechts-, Lizenz- und Lastprüfung automatisierte Einzelabrufe freischalten.
11. Bei höherem Bedarf Whitelist-IP-Antrag vorbereiten.

## Kunden-Onboarding-Runbook

1. Kunde benennt Use Cases: KYB, Lieferanten-Onboarding, Vertragsprüfung, Compliance, Litigation.
2. Kunde bestätigt, dass keine systematische Registerkopie aufgebaut werden soll.
3. NaC legt Tenant, Quoten und Evidence Store an.
4. NaC aktiviert Prozessvorlagen für Registerrecherche.
5. Erste Recherche erfolgt manuell im offiziellen Registerportal.
6. NaC erfasst Suchzweck, Treffer-Metadaten, Attestation und Dokument-Hash.
7. Review: Sollen Inhalte gespeichert werden oder nur Hashes?
8. Review: Ist ein Adapter wirklich notwendig oder reicht der Companion?

## Offene Entscheidungen

- Darf der Code von `bundesAPI/handelsregister` aufgrund fehlender sichtbarer Lizenz überhaupt übernommen werden?
- Soll NaC nur Recherche-Evidence dokumentieren oder selbst Abrufe ausloesen?
- Welche Use Cases brauchen automatisierte Einzelabrufe?
- Welche Rate Limits gelten pro Kunde und global?
- Ist eine registrierte IP notwendig?
- Wie wird verhindert, dass Kunden zusammen faktisch ein Teilregister aufbauen?
- Welche Registerdokumente dürfen gespeichert werden?
- Wie lange werden Treffer-Metadaten und Dokument-Hashes aufbewahrt?

## Akzeptanzkriterien für die erste Umsetzung

- Plugin führt im MVP keine automatisierten Abrufe durch.
- Jeder Vorgang enthält Zweck, Case-ID, Suchparameter, Nutzer und Zeitstempel.
- Kein Massenabruf und kein Voll-/Teilregister.
- Dokumente werden standardmäßig nicht in NaC gespeichert.
- Jeder importierte Nachweis wird gehasht.
- Rate-Limit-Policy ist dokumentiert.
- `bundesAPI/handelsregister` wird nur als Spike referenziert, nicht produktiv eingebunden.
- Offizielle Quellen und Nutzungsgrenzen sind dokumentiert.

## Quellen

- GitHub `bundesAPI/handelsregister`: https://github.com/bundesAPI/handelsregister
- Raw README `bundesAPI/handelsregister`: https://raw.githubusercontent.com/bundesAPI/handelsregister/main/README.md
- Raw `handelsregister.py`: https://raw.githubusercontent.com/bundesAPI/handelsregister/main/handelsregister.py
- Registerportal der Länder, Informationen und Nutzungsordnung: https://www.handelsregister.de/rp_web/information/welcome.xhtml
- Registerportal Statushinweise: https://www.handelsregister.de/rp_web/aktuelleStatusHinweise/welcome.xhtml
- HGB § 9: https://www.gesetze-im-internet.de/hgb/__9.html
- HRV § 52: https://www.gesetze-im-internet.de/hdlregvfg/__52.html
- HRV § 53: https://www.gesetze-im-internet.de/hdlregvfg/__53.html
