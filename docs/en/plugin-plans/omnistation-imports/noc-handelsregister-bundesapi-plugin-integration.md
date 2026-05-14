# Handelsregister / bundesAPI Plugin Integration Plan

Stand: 2026-05-11

Dieser Plan beschreibt, wie NoC Handelsregister-Recherchen und Register-Evidence als Plugin integrieren kann. Ausgangspunkt ist das GitHub-Projekt `bundesAPI/handelsregister`. Das Projekt kann als technischer Spike dienen, sollte aber nicht ungeprueft als produktiver SaaS-Connector uebernommen werden. Massgeblich bleiben die Nutzungsordnung des gemeinsamen Registerportals der Laender, HGB/HRV, Datenschutz, Zweckbindung und die betrieblichen Grenzen des Portals.

## Zielbild

NoC soll Handelsregister-bezogene Workflows fuer SaaS-Kunden abbilden:

- gezielte Einzelrecherche zu Unternehmen und Rechtstraegern
- strukturierte Erfassung von Registergericht, Registerart, Registernummer, Firma, Status und Sitz
- Nachweis, wann welche Registerinformation fuer welchen Geschaeftsvorgang abgerufen wurde
- Hash- und Evidence-Erfassung fuer Registerauszuege, Dokumente und SI/XML-Inhalte
- klare Rate Limits und Schutz gegen Massenabrufe
- optionaler technischer Adapter auf Basis von `bundesAPI/handelsregister` oder einer eigenen, freigegebenen Implementierung
- optionaler Whitelist-IP-/Sonderzugang nur nach Antrag und Nachweis eines berechtigten Erfordernisses

## Offizielle Faktenbasis

- Das gemeinsame Registerportal der Laender ist das elektronische Informations- und Kommunikationssystem, ueber das Daten aus den Rechtstraegerregistern der Justiz abrufbar sind.
- Das Portal umfasst u.a. Handelsregister A und B, Genossenschaftsregister, Partnerschaftsregister, Gesellschaftsregister und Vereinsregister.
- Bereitgestellt werden u.a. Indexdaten, Dokumente, Unternehmenstraegerdaten, sonstige Veroeffentlichungen, aktueller Abdruck, chronologischer Abdruck, historischer Abdruck und strukturierter Registerinhalt als XML-Datei.
- Nach der Nutzungsordnung ist die Einsichtnahme zu Informationszwecken durch einzelne Abrufe gestattet.
- Systematische Abrufe zum Aufbau, Ausbau oder zur Aktualisierung eigener Voll- oder Teilregister sind unzulaessig.
- Normale Nutzung darf nicht mehr als 60 Suchen oder Rechtstraegeraufrufe pro Stunde im Registerportal vornehmen.
- Fuer hoehere Abruffrequenz kann bei der Servicestelle Registerportal beim Amtsgericht Hagen ein Zugang mit registrierter IP-Adresse beantragt werden; Umfang und Zweck der Abrufe muessen angegeben werden.
- Das Registerportal kann IP-Adressen sperren und Sessions beenden, wenn ein Verstoss gegen gesetzliche Vorgaben oder Nutzungsordnung vermutet wird.
- Das Portal weist darauf hin, dass es regelmaessig Ziel automatisierter Massenabfragen ist; bei sehr hoher Frequenz koennen strafrechtliche Risiken im Raum stehen.
- Statushinweise des Portals zeigen, dass Suche, Dokumentenabruf und strukturierter Registerinhalt phasenweise eingeschraenkt sein koennen.

## Fakten zum GitHub-Projekt

- Repository: `https://github.com/bundesAPI/handelsregister`
- Public Repository, Python-basiert, keine Releases sichtbar.
- README beschreibt eine "Handelsregister API" und die POST-Parameter der erweiterten Suche.
- Die CLI ist im README als "work in progress" gekennzeichnet.
- `pyproject.toml` nennt Python `>3.6.2,<4` und nutzt u.a. `mechanize` und `mechanicalsoup`.
- `handelsregister.py` steuert das Webportal programmatisch ueber `mechanize`, setzt Browser-Header und parst HTML mit BeautifulSoup.
- Im Code ist Rate-Limiting als TODO markiert; ein produktionsreifer Token-Bucket ist nicht implementiert.
- Im Repo-Listing ist kein LICENSE-File sichtbar. Vor Codeuebernahme ist daher zwingend zu klaeren, ob und unter welchen Bedingungen der Code genutzt, veraendert oder verteilt werden darf.

## Leitentscheidung

NoC sollte in drei Stufen vorgehen:

1. **Register-Evidence-Companion**
   - NoC fuehrt den Businessprozess, die Recherche erfolgt manuell oder kontrolliert.
   - Kein Aufbau eigener Registerdatenbank.
   - Kein Massenabruf.
   - Standardmaessig werden nur Suchauftrag, Treffer-Metadaten, Hashes, Attestationen und Quellenlinks gespeichert.

2. **Kontrollierter Einzelabruf-Adapter**
   - technischer Adapter fuer gezielte Einzelrecherche
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
NoC SaaS / OCI
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
  noc-handelsregister-local-plugin
        |
        | hashes, attestations, selected metadata
        v
NoC SaaS
```

## Was das Plugin tun darf

- offizielle Registerportal-Seiten oeffnen
- gezielte Suchauftraege fuer einzelne Unternehmen anlegen
- Suchparameter dokumentieren: Firma, Registerart, Registernummer, Registergericht, Bundesland, Sitz, PLZ
- Treffer-Metadaten strukturiert speichern
- Registerauszuege, Dokumente oder SI/XML nur fallbezogen hashen und referenzieren
- Benutzerattestationen erfassen, z.B. "Registerauszug wurde im Registerportal geprueft"
- Abrufzeitpunkt, Zweck, Nutzer, Tenant und Case-ID protokollieren
- Statushinweise des Registerportals als Betriebsrisiko beruecksichtigen
- Rate Limits hart erzwingen und pro Kunde quotieren
- bei Bedarf Whitelist-IP-Antrag und Sonderfreigaben als NoC-Objekte dokumentieren

## Was das Plugin nicht tun darf

- keine systematischen Voll- oder Teilregister aufbauen
- keine Massenabfragen
- keine Umgehung von Portalgrenzen, IP-Sperren oder Session-Schutz
- keine parallele Hochlast-Suche ueber mehrere Tenants zur Umgehung der 60/h-Grenze
- keine gezielte Suche nach natuerlichen Personen
- keine ungepruefte produktive Nutzung von `bundesAPI/handelsregister`
- keine Speicherung personenbezogener Registerdokumente ohne Mandantenpolicy
- keine Weiterverwendung unter der Bezeichnung "Handelsregister", soweit dadurch gesetzliche Vorgaben verletzt werden
- keine LLM-Verarbeitung von Registerdokumenten ohne explizite Freigabe und Datenklassifikation

## Integrationspfade

### Pfad A: Evidence-Companion (MVP)

Dieser Pfad ist sofort planbar.

- NoC erzeugt einen Registerrecherche-Vorgang.
- Nutzer recherchiert im offiziellen Registerportal.
- NoC speichert Suchparameter, Zweck, Treffer-Metadaten, Hashes und Attestation.
- Keine automatisierten Portalabrufe.
- Keine Inhalte in NoC, solange der Kunde dies nicht explizit erlaubt.

Empfehlung: Dieser Pfad ist der erste Schritt.

### Pfad B: Adapter-Spike mit bundesAPI

Dieser Pfad dient der technischen Bewertung, nicht sofort der Produktion.

Pruefpunkte:

- Lizenzstatus des Repositories klaeren.
- Abhaengigkeiten und Wartungsstand bewerten.
- HTML-/JSF-Abhaengigkeit und Bruchrisiko des Parsers testen.
- Rate-Limit-Mechanismus nachruesten.
- Cache-Semantik auf Zweckbindung und Retention umbauen.
- Unit- und Integrationstests gegen kontrollierte Testfaelle bauen.
- Robots-/Nutzungsordnungsfragen rechtlich pruefen.

Produktionsentscheidung erst nach Review.

### Pfad C: Eigener kontrollierter Registerportal-Adapter

Falls ein Adapter erlaubt und benoetigt ist, sollte NoC eine eigene kleine Komponente bauen:

- Request-Queue statt direkter Abrufe
- Token Bucket pro NoC-Installation, pro IP, pro Tenant und pro User
- harte globale Obergrenze unterhalb 60/h, solange keine Whitelist-IP genehmigt ist
- deduplizierte Suchauftraege
- Backoff bei Portalproblemen
- keine parallelen Abfragen fuer Bulk-Listen
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
- `handelsregister.adapter.search_single_entity` (spaeter)
- `handelsregister.adapter.fetch_register_printout` (spaeter)
- `handelsregister.adapter.fetch_si_xml` (spaeter)
- `handelsregister.whitelist_ip.prepare_application` (spaeter)

## Evidence-Modell

```json
{
  "plugin": "noc-handelsregister",
  "tenant_id": "customer-compartment-or-noc-tenant-id",
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

## NoC-Prozesstypen

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

Fuer SaaS gilt weiter: ein Compartment pro Kunde.

Empfohlen:

- `noc-platform`
  - Plugin-Definition, CI, Adapter-Code, Observability
- `noc-shared-security`
  - Vault, KMS, Audit, Logging, Budgets, Egress-Kontrolle
- `customer-<id>`
  - kundenspezifische Workflows
  - Evidence-Buckets
  - tenantisolierte Retention
  - kundenspezifische Quoten

Fuer Handelsregister besonders wichtig:

- Eine globale Rate-Limit-Instanz verhindert, dass mehrere Kunden gemeinsam Portalgrenzen ueberschreiten.
- OCI-Egress muss kontrollierbar sein, falls spaeter eine registrierte IP beantragt wird.
- Caches duerfen nicht zu einem parallelen Register anwachsen.
- Retention fuer Registerdokumente muss je Zweck und Kunde festgelegt werden.

## MVP

Umsetzung fuer die erste Iteration:

- Markdown-Dokumentation und Plugin-Spezifikation
- `handelsregister.health`
- `handelsregister.open_portal`
- `handelsregister.open_advanced_search`
- `handelsregister.prepare_search`
- `handelsregister.record_search_attestation`
- `handelsregister.record_result_metadata`
- `handelsregister.record_document_hash`
- Evidence-JSON-Schema
- Rate-Limit-Policy als NoC-Konfiguration
- Beispielworkflow fuer KYB/Vendor-Onboarding
- technische Spike-Notiz zu `bundesAPI/handelsregister`

Nicht im MVP:

- automatisierter Portalabruf
- Massensuche
- kontinuierliches Monitoring ganzer Firmenlisten
- Dokumentdownload per Adapter
- SI/XML-Abruf per Adapter
- Whitelist-IP-Sonderzugang
- produktive Nutzung des GitHub-Codes ohne Lizenz- und Rechtspruefung

## Sicherheitsanforderungen

- Einzelabruf-Prinzip.
- Zweckbindung je Request.
- Kein Aufbau eigener Voll- oder Teilregister.
- Harte globale und tenantbezogene Rate Limits.
- Keine Umgehung von Portal-Sperren.
- Keine gezielte Personensuche.
- Keine Speicherung von Registerdokumenten ohne Mandantenpolicy.
- Evidence append-only und revisionsfest.
- Hash-first-Design fuer Dokumente.
- Keine Prompt-/Telemetry-Erfassung von Registerdokumenten.
- Datenschutzpruefung fuer Unternehmenstraegerdaten und Dokumente mit Personenbezug.
- CIS-/C5-orientierte OCI-Baseline: IAM least privilege, MFA, Vault, KMS, Logging, Budgets, Security Zones wo sinnvoll.

## SaaS-Anbieter-Runbook

1. Rolle klaeren: NoC als Prozessbegleiter, technischer Rechercheadapter oder registrierter IP-Nutzer.
2. Nutzungsordnung und HGB/HRV-Anforderungen in Policies uebersetzen.
3. Code-Lizenz von `bundesAPI/handelsregister` pruefen.
4. MVP ohne automatisierte Abrufe bauen.
5. Evidence-Schema und Retention je Kunde festlegen.
6. Globale und tenantbezogene Rate-Limits definieren.
7. Kundenspezifisches OCI-Compartment anlegen.
8. Pilot mit manueller Recherche und Evidence-Erfassung durchfuehren.
9. Adapter-Spike isoliert testen.
10. Erst nach Rechts-, Lizenz- und Lastpruefung automatisierte Einzelabrufe freischalten.
11. Bei hoeherem Bedarf Whitelist-IP-Antrag vorbereiten.

## Kunden-Onboarding-Runbook

1. Kunde benennt Use Cases: KYB, Lieferanten-Onboarding, Vertragspruefung, Compliance, Litigation.
2. Kunde bestaetigt, dass keine systematische Registerkopie aufgebaut werden soll.
3. NoC legt Tenant, Quoten und Evidence Store an.
4. NoC aktiviert Prozessvorlagen fuer Registerrecherche.
5. Erste Recherche erfolgt manuell im offiziellen Registerportal.
6. NoC erfasst Suchzweck, Treffer-Metadaten, Attestation und Dokument-Hash.
7. Review: Sollen Inhalte gespeichert werden oder nur Hashes?
8. Review: Ist ein Adapter wirklich notwendig oder reicht der Companion?

## Offene Entscheidungen

- Darf der Code von `bundesAPI/handelsregister` aufgrund fehlender sichtbarer Lizenz ueberhaupt uebernommen werden?
- Soll NoC nur Recherche-Evidence dokumentieren oder selbst Abrufe ausloesen?
- Welche Use Cases brauchen automatisierte Einzelabrufe?
- Welche Rate Limits gelten pro Kunde und global?
- Ist eine registrierte IP notwendig?
- Wie wird verhindert, dass Kunden zusammen faktisch ein Teilregister aufbauen?
- Welche Registerdokumente duerfen gespeichert werden?
- Wie lange werden Treffer-Metadaten und Dokument-Hashes aufbewahrt?

## Akzeptanzkriterien fuer die erste Umsetzung

- Plugin fuehrt im MVP keine automatisierten Abrufe durch.
- Jeder Vorgang enthaelt Zweck, Case-ID, Suchparameter, Nutzer und Zeitstempel.
- Kein Massenabruf und kein Voll-/Teilregister.
- Dokumente werden standardmaessig nicht in NoC gespeichert.
- Jeder importierte Nachweis wird gehasht.
- Rate-Limit-Policy ist dokumentiert.
- `bundesAPI/handelsregister` wird nur als Spike referenziert, nicht produktiv eingebunden.
- Offizielle Quellen und Nutzungsgrenzen sind dokumentiert.

## Quellen

- GitHub `bundesAPI/handelsregister`: https://github.com/bundesAPI/handelsregister
- Raw README `bundesAPI/handelsregister`: https://raw.githubusercontent.com/bundesAPI/handelsregister/main/README.md
- Raw `handelsregister.py`: https://raw.githubusercontent.com/bundesAPI/handelsregister/main/handelsregister.py
- Registerportal der Laender, Informationen und Nutzungsordnung: https://www.handelsregister.de/rp_web/information/welcome.xhtml
- Registerportal Statushinweise: https://www.handelsregister.de/rp_web/aktuelleStatusHinweise/welcome.xhtml
- HGB § 9: https://www.gesetze-im-internet.de/hgb/__9.html
- HRV § 52: https://www.gesetze-im-internet.de/hdlregvfg/__52.html
- HRV § 53: https://www.gesetze-im-internet.de/hdlregvfg/__53.html
