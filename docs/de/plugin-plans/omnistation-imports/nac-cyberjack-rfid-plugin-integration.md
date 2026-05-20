# cyberJack RFID Plugin Integration Plan

Stand: 2026-05-11

## Ziel

Dieses Dokument plant die Integration des REINER SCT cyberJack RFID standard als lokales Sicherheits-Plugin für NaC. Ziel ist ein belastbarer Einstieg für eID-, Kartenleser- und später Signatur-Workflows, ohne dass PIN, Kartenrohdaten oder lokale Gerätekontrolle in die SaaS wandern.

Der cyberJack wird nicht als Cloud-Gerät behandelt. Er bleibt am Arbeitsplatz des Nutzers. Die NaC SaaS erzeugt nur Challenges, führt Policies, speichert Evidenz und protokolliert auditierbare Entscheidungen.

## Produkt- und Schnittstellenlage

Aus der Hersteller- und AusweisApp-Dokumentation ergeben sich folgende Integrationsanker:

- Der cyberJack RFID standard ist ein USB-Kartenleser für kontaktbehaftete und kontaktlose RFID-Chipkarten.
- Er unterstützt nPA/eID, Secoder-Funktion, beA/BRAK/BNotK, D-Trust Card 4.x/5.x und elektronischen Aufenthaltstitel.
- Der Leser nutzt PC/SC 2.0 und CT-API als lokale Schnittstellen.
- Der Leser bietet sichere PIN-Eingabe am Gerät; PIN-Eingabe darf nicht in NaC oder ein LLM wandern.
- REINER SCT nennt BSI-/TUEV-IT-Zertifizierung und Sicherheitsklasse 3.
- Unter Linux und macOS ist Nutzung möglich; Firmwareupdate/-upgrade ist laut Herstellerhinweis dort nicht über das cyberJack ControlCenter vorgesehen.
- Die AusweisApp Desktop-SDK-Schnittstelle ist per WebSocket erreichbar, typischerweise unter `ws://localhost:24727/eID-Kernel`.
- Der AusweisApp-Status kann über `http://localhost:24727/eID-Client?Status=json` gelesen werden.
- Die AusweisApp nutzt PC/SC und gepaarte Smartphones als Kartenleser; für den cyberJack ist PC/SC der relevante MVP-Pfad.

## Leitentscheidung

Die Integration erfolgt über einen lokalen Adapter, nicht über direkte Cloud-Hardwaresteuerung.

```text
User Workstation
  cyberJack RFID standard
  REINER SCT Treiber / PCSC
  AusweisApp
  nac-cyberjack-local-plugin
        |
        | mTLS oder signierte short-lived challenge
        v
NaC SaaS / OCI
  nac-identity-service
  tenant evidence store
  audit log
  NaC process request / pull request
```

## Plugin-Rollen

### Lokales Plugin

Das lokale Plugin läuft auf dem Arbeitsplatz oder einem kontrollierten lokalen Terminal. Es darf:

- Kartenleserstatus prüfen,
- AusweisApp-Status prüfen,
- einen eID-Workflow starten,
- eine SaaS-Challenge binden,
- ein minimiertes Evidenzobjekt zurückgeben.

Es darf nicht:

- PINs lesen oder speichern,
- Kartenrohdaten an NaC oder ein LLM geben,
- personenbezogene Attribute ohne explizite Policy-Freigabe ausgeben,
- globale Adminrechte benötigen,
- automatisch produktive Freigaben ersetzen.

### NaC SaaS

Die SaaS darf:

- Challenges erzeugen,
- Workflow-Intention und Mandantenzuordnung prüfen,
- Evidenzobjekte speichern,
- Audit Events erzeugen,
- Policy Gates für Folgeprozesse auswerten.

Die SaaS darf nicht:

- USB-Hardware direkt steuern,
- PINs entgegennehmen,
- Ausweisdaten im Git-Repository speichern,
- eID-Ergebnisse ohne Zweckbindung für andere Prozesse wiederverwenden.

## Vorgeschlagene Plugin-API

Das Plugin sollte als lokaler MCP- oder HTTP-Adapter startbar sein. MCP ist für NaC/Codex ergonomisch; HTTP ist für Desktop- und Browser-Integrationen einfacher testbar. Beide Varianten können denselben Kern nutzen.

### Minimale Tools

- `cyberjack.health`
  - prüft Plugin-Version, Betriebssystem, PC/SC-Verfügbarkeit und AusweisApp-Erreichbarkeit.
- `cyberjack.list_readers`
  - listet erkannte PC/SC-Reader mit anonymisiertem Reader-Fingerprint.
- `cyberjack.check_ausweisapp`
  - ruft den AusweisApp-Status ab und prüft WebSocket-Fähigkeit.
- `cyberjack.start_eid_auth`
  - startet einen eID-Workflow gegen eine SaaS-Challenge.
- `cyberjack.cancel_session`
  - beendet eine laufende lokale Session.
- `cyberjack.get_evidence`
  - gibt nur minimierte Evidenz und technische Statusdaten zurück.

### Später mögliche Tools

- `cyberjack.sign_challenge`
  - für Karten-/Signaturfälle außerhalb des eID-MVP.
- `cyberjack.check_certificate`
  - prüft Zertifikatsmetadaten, ohne private Schlüssel oder PINs offenzulegen.
- `cyberjack.bea_precheck`
  - späterer Preflight für beA/BNotK-Szenarien, nicht im MVP.

## Datenmodell für Evidenz

Ein Evidenzobjekt soll bewusst knapp bleiben.

```json
{
  "evidence_id": "EID-2026-000001",
  "tenant_id": "tenant-example",
  "process_ref": "REQ-2026-0001",
  "purpose": "identity_verification",
  "reader_kind": "pcsc",
  "reader_fingerprint_hash": "sha256:...",
  "ausweisapp_version": "2.x",
  "assurance_level": "eid_local_reader",
  "result": "succeeded",
  "created_at": "2026-05-11T00:00:00Z",
  "expires_at": "2026-05-11T01:00:00Z",
  "attribute_release_policy": "none_or_explicit",
  "audit_event_ref": "audit://..."
}
```

Personenbezogene Attribute dürfen nicht Teil des Default-Evidenzobjekts sein. Wenn ein Prozess Attribute braucht, muss das über eine eigene Policy mit Zweck, Retention, Empfaenger und Review-Pfad beschrieben werden.

## MVP-Scope

Der MVP umfasst nur den sicheren Nachweis, dass ein lokaler eID-Workflow mit einem unterstützten Leser gestartet und gegen eine SaaS-Challenge abgeschlossen wurde.

1. Lokales Plugin installieren und starten.
2. Reader über PC/SC erkennen.
3. AusweisApp-Status über lokalen HTTP-Status prüfen.
4. WebSocket-Verbindung zur AusweisApp aufbauen.
5. Challenge vom NaC Identity Service beziehen.
6. eID-Workflow starten.
7. Ergebnis minimiert als Evidence speichern.
8. Evidence in einem NaC-Prozess referenzieren.
9. Audit Event erzeugen.

## Nicht im MVP

- Direkte APDU-Kommunikation mit dem nPA.
- Eigene eID-Implementierung außerhalb der AusweisApp.
- beA/BNotK produktiv.
- D-Trust/QES produktiv.
- Gesundheitskartenproduktivbetrieb.
- Cloud-Zugriff auf USB-Geräte.
- Speicherung vollständiger Ausweisdaten in Git.

## Sicherheitsanforderungen

- PIN-Eingabe ausschließlich am Kartenleser oder in der zertifizierten lokalen Komponente.
- Keine PIN-, Token- oder Kartendaten im LLM-Kontext.
- Lokales Plugin nutzt kurzlebige Challenges.
- SaaS akzeptiert nur frische, signierte oder mTLS-gebundene Ergebnisse.
- Evidence ist mandantengebunden und zweckgebunden.
- Tenant-Daten liegen in tenant-spezifischen Compartments oder Stores.
- Audit Events sind revisionssicher abzulegen.
- Debug-Logs müssen redaction-by-default nutzen.
- Der Nutzer muss jede Attributfreigabe bewusst bestätigen.

## SaaS-Provider-Runbook

1. Produkt-Use-Case auswählen:
   - eID-Identitätsnachweis,
   - beA/BNotK Precheck,
   - D-Trust-Signatur,
   - anderer Kartenprozess.
2. Mandantenfähige Evidence-Policy definieren.
3. Datenschutz- und AVV-Bezug prüfen.
4. Tenant-spezifischen Evidence Store anlegen.
5. Identity Service mit Challenge-Endpoint bereitstellen.
6. Lokales Plugin signieren und versionieren.
7. Installationspaket pro Zielplattform definieren.
8. Support-Runbook für Reader/Treiber/AusweisApp-Probleme anlegen.
9. Pilot mit Testmandant und Testkarte/Simulator ausführen.
10. Produktive Nutzung erst nach Freigabe der Policy Gates.

## Tenant-Onboarding-Runbook

1. Tenant-Compartment oder Tenant-Datenscope anlegen.
2. Tenant Evidence Policy konfigurieren.
3. Rollen festlegen:
   - `tenant_security_admin`,
   - `tenant_identity_operator`,
   - `tenant_auditor`,
   - `tenant_process_owner`.
4. Zweckbindung und Retention dokumentieren.
5. Lokales Plugin beim Tenant installieren.
6. Reader-Treiber und AusweisApp prüfen.
7. `cyberjack.health` ausführen.
8. Test-Challenge erzeugen.
9. Test-Evidence erzeugen und Audit Event prüfen.
10. Produktive Freigabe im NaC-Prozess dokumentieren.

## Implementierungsphasen

### Phase 0: Recherche und Spike

- PC/SC-Erkennung unter Windows testen.
- AusweisApp-Status und WebSocket-Handshake testen.
- Lokalen MCP-Prototyp ohne echte Attributweitergabe bauen.

### Phase 1: MVP

- `cyberjack.health`, `cyberjack.list_readers`, `cyberjack.check_ausweisapp` implementieren.
- Challenge-Flow stubben.
- Evidence-Schema in `schemas/` definieren.
- Beispielprozess unter `processes/` anlegen.

### Phase 2: eID-Workflow

- AusweisApp WebSocket-Kommandos integrieren.
- Workflow-Status sauber modellieren.
- Abbruch, Timeout und Nutzerfehler auditierbar machen.

### Phase 3: SaaS-Bindung

- Identity Service anbinden.
- Evidence Store tenant-fähig machen.
- mTLS oder signierte Plugin-Identität einführen.

### Phase 4: Erweiterte Kartenfälle

- D-Trust- und Signaturpfade prüfen.
- beA/BNotK-Fälle separat rechtlich und technisch bewerten.
- Gesundheitskarten nur nach eigener Compliance-Prüfung.

## Offene Entscheidungen

- Erster produktiver Use Case: eID, beA/BNotK, D-Trust oder interner Karten-Precheck?
- Erstplattform: Windows nativ oder zusätzlich Linux/macOS?
- Plugin-Form: MCP-only, lokaler HTTP-Service oder beides?
- Evidence-Retention je Tenant?
- Attributfreigabe komplett außerhalb NaC oder mit minimiertem Attributsatz?
- Signierung/Update-Kanal für das lokale Plugin?

## Akzeptanzkriterien für den ersten PR

- Neues Dokument beschreibt Architektur, Scope und Sicherheitsgrenzen.
- Kein Secret, keine echte personenbezogene Information und keine Kartenrohdaten im Repo.
- MVP ist als lokaler Flow beschrieben.
- Tenant-Onboarding ist als eigener Ablauf beschrieben.
- Quellen sind dokumentiert.

## Quellen

- REINER SCT cyberJack RFID standard: https://www.reiner-sct.com/produkt/cyberjack-rfid-standard/
- AusweisApp SDK Desktop/WebSocket: https://www.ausweisapp.bund.de/sdk/desktop.html
- AusweisApp SDK Einführung: https://www.ausweisapp.bund.de/sdk/intro.html
- AusweisApp Entwickler-FAQ: https://www.ausweisapp.bund.de/en/faq-for-developers
- Governikus identglue: https://github.com/Governikus/identglue
