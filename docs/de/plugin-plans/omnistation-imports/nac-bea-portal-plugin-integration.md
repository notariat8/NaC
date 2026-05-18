# beA Portal Plugin Integration Plan

Stand: 2026-05-11

## Ziel

Dieses Dokument plant die Integration des beA-Portals und der beA-nahen Arbeitsabläufe als lokales bzw. mandantenfähiges NaC-Plugin. Ziel ist nicht, das besondere elektronische Anwaltspostfach technisch zu ersetzen oder unkontrolliert zu automatisieren. Ziel ist ein sicherer, auditierbarer Arbeitsrahmen, in dem NaC:

- beA-Voraussetzungen prüft,
- lokale beA-Client-Security-Abläufe kontrolliert begleitet,
- Versand-, Empfangs-, Signatur- und eEB-Vorgänge als NaC-Prozesse dokumentiert,
- Nachweise minimiert speichert,
- Kanzlei- und Mandanten-Onboarding reproduzierbar macht.

beA bleibt das führende System für Postfachzugang, Versand, Empfang, Signatur, Entschlüsselung und beA-spezifische Rechte. NaC führt Governance, Prozessstatus, Evidence, Freigabe und Audit.

## Quellenlage und Integrationsanker

Aus den offiziellen beA-/BRAK-Unterlagen ergeben sich folgende belastbare Integrationspunkte:

- Das beA-Portal ist die einheitliche Startseite für Anwendungen rund um den elektronischen Rechtsverkehr. Es soll perspektivisch mehrere Anwendungen mit einer beA-Authentifizierung erschließen.
- Jeder in Deutschland zugelassene Rechtsanwalt verfügt über ein beA für sichere elektronische Kommunikation im ERV.
- Seit 2018 besteht passive Nutzungspflicht; seit 2022 besteht eine allgemeine aktive Nutzungspflicht für elektronische Übermittlung an Gerichte.
- Die beA Client Security ist lokal auf dem Nutzerrechner oder in einer Terminalserverumgebung installiert.
- Die beA Client Security führt sicherheitsrelevante Funktionen aus, die nicht im Internet stattfinden dürfen, darunter Anmeldung, Signieren, Signaturprüfung, Ver- und Entschlüsselung sowie Export.
- Browser und beA Client Security kommunizieren lokal. Dafür wird ein individuelles Schlüssel-/Zertifikatspaar erzeugt; das zugehörige Zertifikat muss im Browser hinterlegt werden.
- Für den Zugriff mit Hardware-Token gilt Zwei-Faktor-Authentifizierung aus Besitz der Karte und Wissen der PIN.
- Hardware-Token werden für Registrierung, Anmeldung und Signatur genutzt.
- Für qualifizierte elektronische Signaturen werden unterstützte Signaturkarten bzw. Fernsignaturverfahren genutzt. Signaturdateien werden typischerweise als `.p7s` neben dem Originaldokument erzeugt.
- Aktuelle beA-/KSW-Störungen und Versionshinweise können sich auf Kanzleisoftware-Schnittstellen auswirken; das Plugin muss daher versions- und störungsbewusst geplant werden.

## Leitentscheidung

Die erste NaC-Integration erfolgt nicht als verdeckte Browser-Automation und nicht als direkter Zugriff auf beA-interne Schnittstellen. Der sichere Start ist ein lokaler Companion, der beA-Status, Client-Security-Bereitschaft, lokale Preconditions und NaC-Evidence abbildet.

```text
Kanzlei-Arbeitsplatz oder Terminalserver
  Browser
  beA Portal / beA Webanwendung
  beA Client Security
  Karte / Software-Token / Fernsignatur
  nac-bea-local-plugin
        |
        | signierte Evidence / Workflow-Status
        v
NaC SaaS / OCI
  beA workflow service
  tenant evidence store
  audit journal
  NaC process requests
```

## Plugin-Grenzen

### Das Plugin darf

- lokale Voraussetzungen prüfen,
- beA-Portal und Hilfeseiten oeffnen,
- Vorbereitungs-Checklisten für Registrierung, Anmeldung, Versand, Signatur und eEB führen,
- Dokumentpakete vor dem beA-Upload lokal prüfen,
- Dateinamen, Groessen, Hashes und Strukturmetadaten erfassen,
- NaC-Evidence zu Nutzerbestätigungen und beA-Aktionen erzeugen,
- Exportpakete aus beA in eine NaC-Akte übernehmen, wenn der Nutzer den Export bewusst bereitstellt,
- Störungs- und Versionshinweise als Risikoindikator in Prozesse einbringen.

### Das Plugin darf nicht

- PINs abfragen, speichern oder an NaC senden,
- beA-Zugangsmittel in der SaaS speichern,
- beA-Sessions heimlich fernsteuern,
- Nachrichten ohne lokale Nutzerbestätigung versenden,
- qualifizierte elektronische Signaturen automatisiert anbringen,
- beA-interne oder nicht freigegebene Schnittstellen reverse engineeren,
- Anwaltsgeheimnisse oder Mandatsdaten ungefiltert in LLM-Kontexte geben,
- die Berufsträgerverantwortung ersetzen.

## Integrationspfade

### Pfad A: Lokaler Companion für beA-Webanwendung

Dieser Pfad ist für den MVP empfohlen.

- Nutzer arbeitet weiterhin in der beA-Webanwendung.
- Plugin prüft lokale Readiness und führt NaC-Checklisten.
- Plugin erzeugt Evidence aus expliziten Nutzerbestätigungen, Dateihashes, Exportnachweisen und Audit-Zeitpunkten.
- Kein direkter Versand über NaC.

Vorteile:

- geringes rechtliches und technisches Risiko,
- kompatibel mit aktueller beA-Webanwendung,
- keine Abhängigkeit von nicht öffentlich dokumentierten beA-Schnittstellen,
- gut für Kanzlei-Onboarding und Compliance.

### Pfad B: Kanzleisoftware-Schnittstelle / KSW-Toolkit

Dieser Pfad ist später zu prüfen.

- BRAK/beA stellt bzw. stellte Kanzleisoftware-Schnittstellen bereit, die von Kanzleisoftwareherstellern genutzt werden.
- Zugang, Lizenz, Supportmodell und aktuelle technische Version müssen separat mit BRAK/beA-Support geklärt werden.
- NaC darf diesen Pfad erst nach expliziter Freigabe und Vertrag/Schnittstellendokumentation produktiv nutzen.

Vorteile:

- tiefer integrierter Empfang/Versand möglich,
- bessere Workflow-Automation,
- potenziell weniger manuelle Schritte.

Risiken:

- Versions- und Störungsabhängigkeit,
- Haftungs- und Supportfragen,
- höhere Geheimnis- und Compliance-Anforderungen,
- nicht als erster NaC-MVP geeignet.

### Pfad C: Export-/Import-Bridge

Dieser Pfad kann als Zwischenstufe dienen.

- NaC erzeugt lokale Entwurfs- und Prüfpakete.
- Der Nutzer übernimmt sie bewusst in beA oder eine autorisierte Kanzleisoftware.
- beA-Exportpakete werden lokal gehasht und als Evidence referenziert.

Vorteile:

- keine beA-Sitzungsautomatisierung,
- klare Trennung von Vorbereitung und rechtswirksamer Handlung,
- auditierbar.

## Vorgeschlagene Plugin-API

Das Plugin kann als lokaler MCP-Server oder lokaler HTTP-Service umgesetzt werden. MCP ist für Codex/NaC-Prozesse naheliegend; HTTP erleichtert Desktop- und Browser-Integrationen.

### Readiness und Diagnose

- `bea.health`
  - prüft Plugin-Version, Betriebssystem, User-Kontext, Terminalserver-Hinweise.
- `bea.open_portal`
  - oeffnet das beA-Portal bzw. gibt eine öffentliche Start-URL aus.
- `bea.check_client_security`
  - prüft, ob beA Client Security läuft oder vom Nutzer gestartet werden muss.
- `bea.check_browser_certificate`
  - dokumentiert, ob die lokale Browser-Kommunikation eingerichtet ist; keine Zertifikatsextraktion in NaC.
- `bea.check_token_readiness`
  - führt eine Checkliste für Karte, Software-Token oder Fernsignatur.

### Prozessvorbereitung

- `bea.prepare_outgoing_message`
  - erstellt eine lokale Versand-Checkliste mit Empfaenger, Aktenzeichen, Anlagenliste, Hashes, Suchbarkeit, Signaturbedarf.
- `bea.prepare_eeb`
  - führt Prüfung für elektronisches Empfangsbekenntnis.
- `bea.prepare_signature`
  - prüft, ob Signaturpflicht, Signaturkarte/Fernsignatur und Verantwortlicher dokumentiert sind.
- `bea.record_user_attestation`
  - speichert eine ausdrückliche Nutzerbestätigung als Evidence.

### Evidence und Audit

- `bea.record_export`
  - nimmt ein vom Nutzer bereitgestelltes beA-Exportpaket lokal entgegen, hasht es und erzeugt Evidence.
- `bea.record_send_confirmation`
  - speichert Versandnachweis-Metadaten, wenn der Nutzer diese aus beA bereitstellt.
- `bea.record_inbox_check`
  - protokolliert, dass ein Posteingangscheck durchgeführt wurde, ohne Inhalte an NaC zu übertragen.
- `bea.get_evidence`
  - gibt minimierte Evidence zurück.

### Später optional

- `bea.ksw.connect`
  - nur nach vertraglich und technisch freigegebenem KSW-Pfad.
- `bea.ksw.fetch_messages`
  - nur mit dedizierter Policy, Protokollierung und Geheimnisschutz.
- `bea.ksw.send_message`
  - nur nach expliziter menschlicher Freigabe und Supportklärung.

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

Grundsatz: Evidence enthält bevorzugt Hashes, Referenzen und Status, nicht Mandatsinhalte. Inhaltsübernahme ist nur nach expliziter Tenant-Policy erlaubt.

## NaC-Prozessmodell

Für beA sollte ein eigener Prozess-Typ vorbereitet werden:

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

Wichtig: `executed_in_bea` bedeutet nicht, dass NaC die Aktion selbst ausgeführt hat. Es bedeutet, dass der Nutzer die Aktion in beA bestätigt und ein minimierter Nachweis in NaC abgelegt wurde.

## MVP-Scope

Der erste MVP sollte Pfad A abdecken:

1. `bea.health`
2. `bea.open_portal`
3. `bea.check_client_security`
4. `bea.prepare_outgoing_message`
5. `bea.prepare_signature`
6. `bea.record_user_attestation`
7. `bea.record_export`
8. Evidence-Schema für beA
9. Beispielprozess für Versandvorbereitung
10. Tenant-Onboarding-Runbook für Kanzlei

## Nicht im MVP

- Direktes Abrufen von beA-Nachrichten.
- Direktes Senden von beA-Nachrichten.
- Direkte Nutzung der KSW-Schnittstelle.
- Browser-Scraping oder RPA gegen die beA-Webanwendung.
- Automatische PIN-Eingabe.
- Automatische qualifizierte elektronische Signatur.
- Mandatsinhaltsanalyse durch LLM ohne ausdrückliche Tenant-Policy.

## Sicherheitsanforderungen

- PIN, Karten- und Token-Geheimnisse bleiben lokal und außerhalb von NaC.
- beA Client Security bleibt führend für lokale Sicherheitsfunktionen.
- NaC speichert standardmäßig nur Hashes, Prozessstatus, Attestierungen und Audit-Referenzen.
- Jede rechtswirksame Handlung braucht menschliche Bestätigung durch berechtigte Rolle.
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
8. Testfall mit Musterakte und Dummy-Dokumenten durchführen.
9. Audit- und Exportpfad prüfen.
10. Produktivfreigabe nur über NaC-Review.

## Tenant-Onboarding-Runbook

1. Kanzlei-Tenant anlegen.
2. beA-Nutzungspflichten und Rollenverantwortung dokumentieren.
3. Lokale beA Client Security Installation prüfen.
4. Browser-Zertifikat für Client-Security-Kommunikation prüfen.
5. Karten/Token/Fernsignatur je Nutzer dokumentieren, ohne Geheimnisse zu speichern.
6. Rechte- und Rollenmodell im Tenant einrichten.
7. Pilotprozess `bea_message_preparation` starten.
8. Testdokument hashen und Versand-Checkliste erzeugen.
9. Nutzer führt beA-Aktion lokal aus.
10. Export- oder Versandnachweis als Evidence aufnehmen.
11. Review und Go/No-Go für Produktivbetrieb dokumentieren.

## Implementierungsphasen

### Phase 0: Legal/Technical Discovery

- Klären, ob NaC nur Companion oder auch KSW-Integrationspartner werden soll.
- beA-Support-/BRAK-Anforderungen für KSW prüfen.
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

### Phase 3: Kanzleisoftware-/KSW-Prüfung

- Offizielle Schnittstellenunterlagen beschaffen.
- Support- und Haftungsmodell klären.
- Proof of Concept mit Testpostfach, nicht produktiv.

### Phase 4: Produktiver Integrationspfad

- Nur nach Freigabe von Security, Legal, Support und Tenant-Policies.
- Rollout je Kanzlei/Tenant.

## Offene Entscheidungen

- Soll NaC beA nur begleiten oder perspektivisch KSW-Integrationspartner werden?
- Erstes Produktversprechen: Versandvorbereitung, eEB, Posteingangscheck oder Archivnachweis?
- Zielplattform zuerst: Windows-Einzelplatz, Windows-Terminalserver oder macOS/Linux?
- Wie lange werden beA-Evidence-Objekte je Tenant aufbewahrt?
- Dürfen Dokumentinhalte in NaC gespeichert werden oder nur Hashes/Referenzen?
- Wie wird mit beA-Störungen und KSW-Versionen im Prozessstatus umgegangen?

## Akzeptanzkriterien für den ersten PR

- Architektur- und Scope-Dokument vorhanden.
- Offizielle Quellen sind verlinkt.
- MVP ist Companion-only und respektiert beA Client Security.
- Keine Geheimnisse, PINs, Token oder Mandatsinhalte im Repo.
- Tenant-Onboarding ist beschrieben.
- KSW-Pfad ist als spätere, separate Freigabe markiert.

## Quellen

- beA-Portal: https://www.bea-brak.de/beaportal/
- beA Anwenderhandbuch: https://handbuch.bea-brak.de/
- beA Client Security: https://handbuch.bea-brak.de/einrichtung-von-bea/bea-client-security
- Kommunikation Browser und Client Security: https://handbuch.bea-brak.de/einrichtung-von-bea/organisatorische-und-technische-voraussetzungen/einstellungen-fuer-die-kommunikation-der-bea-client-security-mit-dem-browser/
- Unterstützte Signaturkarten und Chipkartenleser: https://handbuch.bea-brak.de/einrichtung-von-bea/organisatorische-und-technische-voraussetzungen/unterstuetzte-signaturkarten-und-chipkartenleser-1
- Signaturverfahren: https://handbuch.bea-brak.de/arbeiten-mit-ihrem-bea/signaturverfahren
- BRAK beA und ERV: https://www.brak.de/anwaltschaft/bea-erv/
