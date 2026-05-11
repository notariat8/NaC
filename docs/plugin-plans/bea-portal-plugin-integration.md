# beA Portal Plugin Integration Plan

Stand: 2026-05-11

## Ziel

Dieses Dokument plant die Integration des beA-Portals und der beA-nahen Arbeitsablaeufe als lokales bzw. mandantenfaehiges OaC8-Plugin. Ziel ist nicht, das besondere elektronische Anwaltspostfach technisch zu ersetzen oder unkontrolliert zu automatisieren. Ziel ist ein sicherer, auditierbarer Arbeitsrahmen, in dem OaC8:

- beA-Voraussetzungen prueft,
- lokale beA-Client-Security-Ablaeufe kontrolliert begleitet,
- Versand-, Empfangs-, Signatur- und eEB-Vorgaenge als OaC-Prozesse dokumentiert,
- Nachweise minimiert speichert,
- Kanzlei- und Mandanten-Onboarding reproduzierbar macht.

beA bleibt das fuehrende System fuer Postfachzugang, Versand, Empfang, Signatur, Entschluesselung und beA-spezifische Rechte. OaC8 fuehrt Governance, Prozessstatus, Evidence, Freigabe und Audit.

## Quellenlage und Integrationsanker

Aus den offiziellen beA-/BRAK-Unterlagen ergeben sich folgende belastbare Integrationspunkte:

- Das beA-Portal ist die einheitliche Startseite fuer Anwendungen rund um den elektronischen Rechtsverkehr. Es soll perspektivisch mehrere Anwendungen mit einer beA-Authentifizierung erschliessen.
- Jeder in Deutschland zugelassene Rechtsanwalt verfuegt ueber ein beA fuer sichere elektronische Kommunikation im ERV.
- Seit 2018 besteht passive Nutzungspflicht; seit 2022 besteht eine allgemeine aktive Nutzungspflicht fuer elektronische Uebermittlung an Gerichte.
- Die beA Client Security ist lokal auf dem Nutzerrechner oder in einer Terminalserverumgebung installiert.
- Die beA Client Security fuehrt sicherheitsrelevante Funktionen aus, die nicht im Internet stattfinden duerfen, darunter Anmeldung, Signieren, Signaturpruefung, Ver- und Entschluesselung sowie Export.
- Browser und beA Client Security kommunizieren lokal. Dafuer wird ein individuelles Schluessel-/Zertifikatspaar erzeugt; das zugehoerige Zertifikat muss im Browser hinterlegt werden.
- Fuer den Zugriff mit Hardware-Token gilt Zwei-Faktor-Authentifizierung aus Besitz der Karte und Wissen der PIN.
- Hardware-Token werden fuer Registrierung, Anmeldung und Signatur genutzt.
- Fuer qualifizierte elektronische Signaturen werden unterstuetzte Signaturkarten bzw. Fernsignaturverfahren genutzt. Signaturdateien werden typischerweise als `.p7s` neben dem Originaldokument erzeugt.
- Aktuelle beA-/KSW-Stoerungen und Versionshinweise koennen sich auf Kanzleisoftware-Schnittstellen auswirken; das Plugin muss daher versions- und stoerungsbewusst geplant werden.

## Leitentscheidung

Die erste OaC8-Integration erfolgt nicht als verdeckte Browser-Automation und nicht als direkter Zugriff auf beA-interne Schnittstellen. Der sichere Start ist ein lokaler Companion, der beA-Status, Client-Security-Bereitschaft, lokale Preconditions und OaC-Evidence abbildet.

```text
Kanzlei-Arbeitsplatz oder Terminalserver
  Browser
  beA Portal / beA Webanwendung
  beA Client Security
  Karte / Software-Token / Fernsignatur
  oac8-bea-local-plugin
        |
        | signierte Evidence / Workflow-Status
        v
OaC8 SaaS / OCI
  beA workflow service
  tenant evidence store
  audit journal
  OaC process requests
```

## Plugin-Grenzen

### Das Plugin darf

- lokale Voraussetzungen pruefen,
- beA-Portal und Hilfeseiten oeffnen,
- Vorbereitungs-Checklisten fuer Registrierung, Anmeldung, Versand, Signatur und eEB fuehren,
- Dokumentpakete vor dem beA-Upload lokal pruefen,
- Dateinamen, Groessen, Hashes und Strukturmetadaten erfassen,
- OaC-Evidence zu Nutzerbestaetigungen und beA-Aktionen erzeugen,
- Exportpakete aus beA in eine OaC-Akte uebernehmen, wenn der Nutzer den Export bewusst bereitstellt,
- Stoerungs- und Versionshinweise als Risikoindikator in Prozesse einbringen.

### Das Plugin darf nicht

- PINs abfragen, speichern oder an OaC8 senden,
- beA-Zugangsmittel in der SaaS speichern,
- beA-Sessions heimlich fernsteuern,
- Nachrichten ohne lokale Nutzerbestaetigung versenden,
- qualifizierte elektronische Signaturen automatisiert anbringen,
- beA-interne oder nicht freigegebene Schnittstellen reverse engineeren,
- Anwaltsgeheimnisse oder Mandatsdaten ungefiltert in LLM-Kontexte geben,
- die Berufstraegerverantwortung ersetzen.

## Integrationspfade

### Pfad A: Lokaler Companion fuer beA-Webanwendung

Dieser Pfad ist fuer den MVP empfohlen.

- Nutzer arbeitet weiterhin in der beA-Webanwendung.
- Plugin prueft lokale Readiness und fuehrt OaC-Checklisten.
- Plugin erzeugt Evidence aus expliziten Nutzerbestaetigungen, Dateihashes, Exportnachweisen und Audit-Zeitpunkten.
- Kein direkter Versand ueber OaC8.

Vorteile:

- geringes rechtliches und technisches Risiko,
- kompatibel mit aktueller beA-Webanwendung,
- keine Abhaengigkeit von nicht oeffentlich dokumentierten beA-Schnittstellen,
- gut fuer Kanzlei-Onboarding und Compliance.

### Pfad B: Kanzleisoftware-Schnittstelle / KSW-Toolkit

Dieser Pfad ist spaeter zu pruefen.

- BRAK/beA stellt bzw. stellte Kanzleisoftware-Schnittstellen bereit, die von Kanzleisoftwareherstellern genutzt werden.
- Zugang, Lizenz, Supportmodell und aktuelle technische Version muessen separat mit BRAK/beA-Support geklaert werden.
- OaC8 darf diesen Pfad erst nach expliziter Freigabe und Vertrag/Schnittstellendokumentation produktiv nutzen.

Vorteile:

- tiefer integrierter Empfang/Versand moeglich,
- bessere Workflow-Automation,
- potenziell weniger manuelle Schritte.

Risiken:

- Versions- und Stoerungsabhaengigkeit,
- Haftungs- und Supportfragen,
- hoehere Geheimnis- und Compliance-Anforderungen,
- nicht als erster OaC8-MVP geeignet.

### Pfad C: Export-/Import-Bridge

Dieser Pfad kann als Zwischenstufe dienen.

- OaC8 erzeugt lokale Entwurfs- und Pruefpakete.
- Der Nutzer uebernimmt sie bewusst in beA oder eine autorisierte Kanzleisoftware.
- beA-Exportpakete werden lokal gehasht und als Evidence referenziert.

Vorteile:

- keine beA-Sitzungsautomatisierung,
- klare Trennung von Vorbereitung und rechtswirksamer Handlung,
- auditierbar.

## Vorgeschlagene Plugin-API

Das Plugin kann als lokaler MCP-Server oder lokaler HTTP-Service umgesetzt werden. MCP ist fuer Codex/OaC-Prozesse naheliegend; HTTP erleichtert Desktop- und Browser-Integrationen.

### Readiness und Diagnose

- `bea.health`
  - prueft Plugin-Version, Betriebssystem, User-Kontext, Terminalserver-Hinweise.
- `bea.open_portal`
  - oeffnet das beA-Portal bzw. gibt eine oeffentliche Start-URL aus.
- `bea.check_client_security`
  - prueft, ob beA Client Security laeuft oder vom Nutzer gestartet werden muss.
- `bea.check_browser_certificate`
  - dokumentiert, ob die lokale Browser-Kommunikation eingerichtet ist; keine Zertifikatsextraktion in OaC8.
- `bea.check_token_readiness`
  - fuehrt eine Checkliste fuer Karte, Software-Token oder Fernsignatur.

### Prozessvorbereitung

- `bea.prepare_outgoing_message`
  - erstellt eine lokale Versand-Checkliste mit Empfaenger, Aktenzeichen, Anlagenliste, Hashes, Suchbarkeit, Signaturbedarf.
- `bea.prepare_eeb`
  - fuehrt Pruefung fuer elektronisches Empfangsbekenntnis.
- `bea.prepare_signature`
  - prueft, ob Signaturpflicht, Signaturkarte/Fernsignatur und Verantwortlicher dokumentiert sind.
- `bea.record_user_attestation`
  - speichert eine ausdrueckliche Nutzerbestaetigung als Evidence.

### Evidence und Audit

- `bea.record_export`
  - nimmt ein vom Nutzer bereitgestelltes beA-Exportpaket lokal entgegen, hasht es und erzeugt Evidence.
- `bea.record_send_confirmation`
  - speichert Versandnachweis-Metadaten, wenn der Nutzer diese aus beA bereitstellt.
- `bea.record_inbox_check`
  - protokolliert, dass ein Posteingangscheck durchgefuehrt wurde, ohne Inhalte an OaC8 zu uebertragen.
- `bea.get_evidence`
  - gibt minimierte Evidence zurueck.

### Spaeter optional

- `bea.ksw.connect`
  - nur nach vertraglich und technisch freigegebenem KSW-Pfad.
- `bea.ksw.fetch_messages`
  - nur mit dedizierter Policy, Protokollierung und Geheimnisschutz.
- `bea.ksw.send_message`
  - nur nach expliziter menschlicher Freigabe und Supportklaerung.

## Evidence-Datenmodell

```json
{
  "evidence_id": "BEA-2026-000001",
  "tenant_id": "tenant-law-example",
  "process_ref": "REQ-2026-0001",
  "matter_ref": "AKTE-2026-001",
  "workflow_kind": "outgoing_message_preparation",
  "bea_channel": "web_companion",
  "local_actor_role": "rechtsanwalt",
  "requires_signature": true,
  "signature_kind": "qes_or_remote_signature",
  "documents": [
    {
      "name": "schriftsatz.pdf",
      "sha256": "sha256:...",
      "classification": "mandate_confidential"
    }
  ],
  "user_attestation": {
    "confirmed_at": "2026-05-11T00:00:00Z",
    "statement_id": "bea-send-prepared-local-user-confirmation"
  },
  "bea_artifact_ref": "local-export-or-user-provided-reference",
  "audit_event_ref": "audit://...",
  "retention_policy": "tenant-legal-default"
}
```

Grundsatz: Evidence enthaelt bevorzugt Hashes, Referenzen und Status, nicht Mandatsinhalte. Inhaltsuebernahme ist nur nach expliziter Tenant-Policy erlaubt.

## OaC-Prozessmodell

Fuer beA sollte ein eigener Prozess-Typ vorbereitet werden:

- `bea_message_preparation`
- `bea_inbox_check`
- `bea_eeb_response`
- `bea_signature_preparation`
- `bea_export_archival`

Gemeinsame Statuswerte:

- `draft`
- `prepared`
- `needs_review`
- `approved`
- `executed_in_bea`
- `evidence_recorded`
- `archived`
- `cancelled`

Wichtig: `executed_in_bea` bedeutet nicht, dass OaC8 die Aktion selbst ausgefuehrt hat. Es bedeutet, dass der Nutzer die Aktion in beA bestaetigt und ein minimierter Nachweis in OaC8 abgelegt wurde.

## MVP-Scope

Der erste MVP sollte Pfad A abdecken:

1. `bea.health`
2. `bea.open_portal`
3. `bea.check_client_security`
4. `bea.prepare_outgoing_message`
5. `bea.prepare_signature`
6. `bea.record_user_attestation`
7. `bea.record_export`
8. Evidence-Schema fuer beA
9. Beispielprozess fuer Versandvorbereitung
10. Tenant-Onboarding-Runbook fuer Kanzlei

## Nicht im MVP

- Direktes Abrufen von beA-Nachrichten.
- Direktes Senden von beA-Nachrichten.
- Direkte Nutzung der KSW-Schnittstelle.
- Browser-Scraping oder RPA gegen die beA-Webanwendung.
- Automatische PIN-Eingabe.
- Automatische qualifizierte elektronische Signatur.
- Mandatsinhaltsanalyse durch LLM ohne ausdrueckliche Tenant-Policy.

## Sicherheitsanforderungen

- PIN, Karten- und Token-Geheimnisse bleiben lokal und ausserhalb von OaC8.
- beA Client Security bleibt fuehrend fuer lokale Sicherheitsfunktionen.
- OaC8 speichert standardmaessig nur Hashes, Prozessstatus, Attestierungen und Audit-Referenzen.
- Jede rechtswirksame Handlung braucht menschliche Bestaetigung durch berechtigte Rolle.
- Berufsgeheimnis und Mandatsvertraulichkeit werden als Default-Classification behandelt.
- Plugin-Logs sind redaction-by-default.
- Kein Screenshot- oder DOM-Scraping von Mandatsinhalten im MVP.
- Evidence ist tenantgebunden und darf nicht zwischen Mandanten wiederverwendet werden.
- KSW-Pfad braucht separate Zulassung, Vertragsanbindung und Supportmodell.

## SaaS-Provider-Runbook

1. beA-Use-Case festlegen:
   - Versandvorbereitung,
   - Posteingangscheck-Nachweis,
   - eEB-Prozess,
   - Signaturvorbereitung,
   - Exportarchivierung.
2. Tenant-Datenschutz- und Geheimnisschutzpolicy definieren.
3. Evidence-Retention je Kanzlei festlegen.
4. Rollenmodell definieren:
   - `lawyer_owner`,
   - `legal_staff`,
   - `bea_operator`,
   - `tenant_auditor`,
   - `compliance_reviewer`.
5. Lokales Plugin bereitstellen und signieren.
6. Installations- und Updatepfad dokumentieren.
7. beA Client Security als externe Pflichtkomponente dokumentieren.
8. Testfall mit Musterakte und Dummy-Dokumenten durchfuehren.
9. Audit- und Exportpfad pruefen.
10. Produktivfreigabe nur ueber OaC-Review.

## Tenant-Onboarding-Runbook

1. Kanzlei-Tenant anlegen.
2. beA-Nutzungspflichten und Rollenverantwortung dokumentieren.
3. Lokale beA Client Security Installation pruefen.
4. Browser-Zertifikat fuer Client-Security-Kommunikation pruefen.
5. Karten/Token/Fernsignatur je Nutzer dokumentieren, ohne Geheimnisse zu speichern.
6. Rechte- und Rollenmodell im Tenant einrichten.
7. Pilotprozess `bea_message_preparation` starten.
8. Testdokument hashen und Versand-Checkliste erzeugen.
9. Nutzer fuehrt beA-Aktion lokal aus.
10. Export- oder Versandnachweis als Evidence aufnehmen.
11. Review und Go/No-Go fuer Produktivbetrieb dokumentieren.

## Implementierungsphasen

### Phase 0: Legal/Technical Discovery

- Klaeren, ob OaC8 nur Companion oder auch KSW-Integrationspartner werden soll.
- beA-Support-/BRAK-Anforderungen fuer KSW pruefen.
- Datenschutz- und Berufsgeheimnisschutzmodell dokumentieren.

### Phase 1: Companion MVP

- Lokales Plugin mit Readiness-Checks.
- Evidence-Schema.
- Beispielprozess.
- Kein Versand und kein Abruf.

### Phase 2: Evidence und Archiv

- Hashing und lokale Exportaufnahme.
- Tenant Evidence Store.
- Audit-Events und Retention.

### Phase 3: Kanzleisoftware-/KSW-Pruefung

- Offizielle Schnittstellenunterlagen beschaffen.
- Support- und Haftungsmodell klaeren.
- Proof of Concept mit Testpostfach, nicht produktiv.

### Phase 4: Produktiver Integrationspfad

- Nur nach Freigabe von Security, Legal, Support und Tenant-Policies.
- Rollout je Kanzlei/Tenant.

## Offene Entscheidungen

- Soll OaC8 beA nur begleiten oder perspektivisch KSW-Integrationspartner werden?
- Erstes Produktversprechen: Versandvorbereitung, eEB, Posteingangscheck oder Archivnachweis?
- Zielplattform zuerst: Windows-Einzelplatz, Windows-Terminalserver oder macOS/Linux?
- Wie lange werden beA-Evidence-Objekte je Tenant aufbewahrt?
- Duerfen Dokumentinhalte in OaC8 gespeichert werden oder nur Hashes/Referenzen?
- Wie wird mit beA-Stoerungen und KSW-Versionen im Prozessstatus umgegangen?

## Akzeptanzkriterien fuer den ersten PR

- Architektur- und Scope-Dokument vorhanden.
- Offizielle Quellen sind verlinkt.
- MVP ist Companion-only und respektiert beA Client Security.
- Keine Geheimnisse, PINs, Token oder Mandatsinhalte im Repo.
- Tenant-Onboarding ist beschrieben.
- KSW-Pfad ist als spaetere, separate Freigabe markiert.

## Quellen

- beA-Portal: https://www.bea-brak.de/beaportal/
- beA Anwenderhandbuch: https://handbuch.bea-brak.de/
- beA Client Security: https://handbuch.bea-brak.de/einrichtung-von-bea/bea-client-security
- Kommunikation Browser und Client Security: https://handbuch.bea-brak.de/einrichtung-von-bea/organisatorische-und-technische-voraussetzungen/einstellungen-fuer-die-kommunikation-der-bea-client-security-mit-dem-browser/
- Unterstuetzte Signaturkarten und Chipkartenleser: https://handbuch.bea-brak.de/einrichtung-von-bea/organisatorische-und-technische-voraussetzungen/unterstuetzte-signaturkarten-und-chipkartenleser-1
- Signaturverfahren: https://handbuch.bea-brak.de/arbeiten-mit-ihrem-bea/signaturverfahren
- BRAK beA und ERV: https://www.brak.de/anwaltschaft/bea-erv/
