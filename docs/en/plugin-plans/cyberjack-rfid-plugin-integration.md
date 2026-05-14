# Card / cyberJack RFID Plugin Integration Plan

Stand: 2026-05-14

## Ziel

Dieses Dokument plant die Integration des REINER SCT cyberJack RFID standard und vergleichbarer lokaler Kartenpfade als Sicherheits-Plugin fuer NoC. Ziel ist ein belastbarer Einstieg fuer eID-, BNotK-/Notar-Kartenleser-, SAK-lite-, secureFramework- und spaeter Signatur-Workflows, ohne dass PIN, Kartenrohdaten oder lokale Geraetekontrolle in die SaaS wandern.

Fuer notariatsseitige Online-HRA-Workflows ist dieses Plugin dem XNP-Plugin vorgelagert. XNP-Login-Tests sind erst sinnvoll, wenn BNotK Chip-/Signaturkarte, kompatibler Kartenleser der Sicherheitsklasse 3, PC/SC, BNotK SAK lite oder XNP-Kartenpfad, secureFramework und die lokale XNP-Schnittstelle bereit sind.

Der cyberJack wird nicht als Cloud-Geraet behandelt. Er bleibt am Arbeitsplatz des Nutzers. Die NoC SaaS erzeugt nur Challenges, fuehrt Policies, speichert Evidenz und protokolliert auditierbare Entscheidungen.

## Produkt- und Schnittstellenlage

Aus der Hersteller- und AusweisApp-Dokumentation ergeben sich folgende Integrationsanker:

- Der cyberJack RFID standard ist ein USB-Kartenleser fuer kontaktbehaftete und kontaktlose RFID-Chipkarten.
- Er unterstuetzt nPA/eID, Secoder-Funktion, beA/BRAK/BNotK, D-Trust Card 4.x/5.x und elektronischen Aufenthaltstitel.
- Die BNotK nennt `cyberJack RFID komfort (USB)`, `cyberJack RFID standard (USB)` und `cyberJack one (USB)` als kompatibel getestete Kartenleser fuer Kartenverwaltungsprozesse; weitere Geraete muessen mindestens Sicherheitsklasse 3, Display und eigenes PIN-Pad haben.
- Fuer BNotK-Chipkartenprozesse ist RFID nicht der fachliche Zielpfad. Wenn ein Reiner-SCT-Leser eine RFID-Funktion hat, soll sie fuer diese Workflows ausgeschaltet bleiben, sofern kein expliziter kontaktloser Use Case vorliegt.
- Reiner SCT e-com/e-com plus und weitere nicht kompatible oder nicht mehr unterstuetzte Leser sind als Blocker zu behandeln.
- Die BNotK beschreibt fuer Chipkartenanmeldungen den Bedarf an Chipkarte, Kartenlesegeraet der Sicherheitsklasse 3 und BNotK SAK lite oder XNP.
- Fuer die Kommunikation mit dem Kartenleser wird im BNotK-Kartenloginpfad secureFramework verwendet.
- XNP kann sich mit Signaturkarte/Chipkarte und PIN anmelden; die PIN-Eingabe erfolgt am Kartenlesegeraet bzw. in der lokalen zertifizierten Komponente, nicht in NoC.
- XNP stellt fuer Notariatssoftware eine lokale Web-Service-Schnittstelle bereit. Sie ist auf den jeweiligen Rechner beschraenkt, bindet standardmaessig den ersten freien Port im Bereich `12774` bis `12784` und kann einen API-Key fuer Anmeldefunktionen nutzen. NoC darf API-Keys nicht speichern.
- Der Leser nutzt PC/SC 2.0 und CT-API als lokale Schnittstellen.
- On Windows, the REINER SCT stack is checked through `C:\Program Files\REINER SCT\DriverPackage`, PC/SC/CT-API files and the installed SmartCardReader driver provider.
- Der Leser bietet sichere PIN-Eingabe am Geraet; PIN-Eingabe darf nicht in NoC oder ein LLM wandern.
- REINER SCT nennt BSI-/TUEV-IT-Zertifizierung und Sicherheitsklasse 3.
- Unter Linux und macOS ist Nutzung moeglich; Firmwareupdate/-upgrade ist laut Herstellerhinweis dort nicht ueber das cyberJack ControlCenter vorgesehen.
- For Linux, REINER SCT notes that cyberJack drivers are already available through the standard repositories of many distributions; otherwise distribution-specific packages or source code should be used.
- Die AusweisApp Desktop-SDK-Schnittstelle ist per WebSocket erreichbar, typischerweise unter `ws://localhost:24727/eID-Kernel`.
- Der AusweisApp-Status kann ueber `http://localhost:24727/eID-Client?Status=json` gelesen werden.
- Die AusweisApp nutzt PC/SC und gepaarte Smartphones als Kartenleser; fuer den cyberJack ist PC/SC der relevante MVP-Pfad.

## Leitentscheidung

Die Integration erfolgt ueber einen lokalen Adapter, nicht ueber direkte Cloud-Hardwaresteuerung.

```text
User Workstation
  BNotK chip/signature card
  cyberJack RFID standard
  RFID function disabled for BNotK chip-card workflows
  BNotK SAK lite / XNP card path
  secureFramework
  XNP local web-service interface
  REINER SCT Treiber / PCSC
  AusweisApp
  noc-cyberjack-local-plugin
        |
        | mTLS oder signierte short-lived challenge
        v
NoC SaaS / OCI
  noc-identity-service
  tenant evidence store
  audit log
  NoC process request / pull request
```

## Plugin-Rollen

### Lokales Plugin

Das lokale Plugin laeuft auf dem Arbeitsplatz oder einem kontrollierten lokalen Terminal. Es darf:

- Kartenleserstatus pruefen,
- RFID-off-Status fuer BNotK-Chipkartenprozesse pruefen,
- BNotK SAK lite oder XNP-Kartenpfad und secureFramework-Bereitschaft pruefen,
- nicht geheime XNP-Schnittstellenmetadaten wie aktiv/inaktiv und lokalen Portbereich pruefen,
- AusweisApp-Status pruefen,
- einen eID-Workflow starten,
- eine SaaS-Challenge binden,
- ein minimiertes Evidenzobjekt zurueckgeben.

Es darf nicht:

- PINs lesen oder speichern,
- XNP-API-Keys, Login-Informationen oder verschluesselte Schluesselblobs speichern,
- Kartenrohdaten an NoC oder ein LLM geben,
- personenbezogene Attribute ohne explizite Policy-Freigabe ausgeben,
- globale Adminrechte benoetigen,
- automatisch produktive Freigaben ersetzen.

### NoC SaaS

Die SaaS darf:

- Challenges erzeugen,
- Workflow-Intention und Mandantenzuordnung pruefen,
- Evidenzobjekte speichern,
- Audit Events erzeugen,
- Policy Gates fuer Folgeprozesse auswerten.

Die SaaS darf nicht:

- USB-Hardware direkt steuern,
- PINs entgegennehmen,
- Ausweisdaten im Git-Repository speichern,
- eID-Ergebnisse ohne Zweckbindung fuer andere Prozesse wiederverwenden.

## Vorgeschlagene Plugin-API

Das Plugin sollte als lokaler MCP- oder HTTP-Adapter startbar sein. MCP ist fuer NoC/Codex ergonomisch; HTTP ist fuer Desktop- und Browser-Integrationen einfacher testbar. Beide Varianten koennen denselben Kern nutzen.

### Minimale Tools

- `cyberjack.health`
  - prueft Plugin-Version, Betriebssystem, PC/SC-Verfuegbarkeit, RFID-off-Status, SAK-lite/XNP-Kartenpfad, XNP-Lokalschnittstelle und AusweisApp-Erreichbarkeit.
- `cyberjack.list_readers`
  - listet erkannte PC/SC-Reader mit anonymisiertem Reader-Fingerprint.
- `cyberjack.check_bnotk_card_path`
  - prueft ohne Kartendaten, ob BNotK Chip-/Signaturkarte, kompatibler Sicherheitsklasse-3-Leser, RFID-off-Status, SAK lite/XNP-Kartenpfad, secureFramework und lokale XNP-Schnittstelle einsatzbereit erscheinen.
- `cyberjack.check_ausweisapp`
  - ruft den AusweisApp-Status ab und prueft WebSocket-Faehigkeit.
- `cyberjack.start_eid_auth`
  - startet einen eID-Workflow gegen eine SaaS-Challenge.
- `cyberjack.cancel_session`
  - beendet eine laufende lokale Session.
- `cyberjack.get_evidence`
  - gibt nur minimierte Evidenz und technische Statusdaten zurueck.

### Spaeter moegliche Tools

- `cyberjack.sign_challenge`
  - fuer Karten-/Signaturfaelle ausserhalb des eID-MVP.
- `cyberjack.check_certificate`
  - prueft Zertifikatsmetadaten, ohne private Schluessel oder PINs offenzulegen.
- `cyberjack.bea_precheck`
  - spaeterer Preflight fuer beA/BNotK-Szenarien, nicht im MVP.

## Datenmodell fuer Evidenz

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

Personenbezogene Attribute duerfen nicht Teil des Default-Evidenzobjekts sein. Wenn ein Prozess Attribute braucht, muss das ueber eine eigene Policy mit Zweck, Retention, Empfaenger und Review-Pfad beschrieben werden.

## MVP-Scope

Der MVP umfasst zuerst den sicheren Nachweis, dass der lokale Kartenpfad fuer XNP-Login-Tests bereit ist. Der eID-Workflow bleibt ein weiterer lokaler Kartenfall.

1. Lokales Plugin installieren und starten.
2. Reader ueber PC/SC erkennen.
3. Sicherheitsklasse-3- und Treiberpfad dokumentieren.
4. RFID-Funktion, sofern vorhanden, fuer BNotK-Chipkartenprozesse als ausgeschaltet pruefen.
5. BNotK SAK lite oder XNP-Kartenpfad pruefen.
6. secureFramework-Bereitschaft pruefen.
7. Lokale XNP-Schnittstelle nur ueber nicht geheime Metadaten pruefen.
8. Keine PIN, keine API-Keys und keine Kartenrohdaten erfassen.
9. Ergebnis minimiert als Evidence speichern.
10. `noc-bnotk-xnp` erst nach erfolgreichem Card/SAK-Gate testen.
11. Evidence in einem NoC-Prozess referenzieren.
12. Audit Event erzeugen.

The first runnable MVP now lives at `plugins/noc-cyberjack-rfid/scripts/check_readiness.py`. It produces evidence JSON according to `plugins/noc-cyberjack-rfid/contracts/readiness-evidence.schema.json`, probes local components only, uses localhost-only checks for XNP/AusweisApp reachability and stores no PINs, card data or XNP API keys. RFID-off and card availability are captured as manual attestations until a reviewed local interface can report these states deterministically.

On Linux, the MVP now also probes cyberJack/PCSC package status, `pcscd`, USB visibility through `lsusb` and PC/SC reader signals through `pcsc_scan -n` where these tools are available.

On Windows, the MVP now also probes the installed REINER SCT DriverPackage path, central driver files, CT-API/PCSC files and the installed REINER SCT SmartCardReader provider through `pnputil`. Connected reader hardware is checked separately; an installed driver stack does not prove that a cyberJack reader is currently attached.

Under the current repository rule, Omnistation is not a general NoC execution workspace. For an isolated hardware lab, Omnistation is only useful if the cyberJack USB reader is visible there through USB passthrough and a documented policy exception or policy update exists. Without USB passthrough, an Omnistation cloud desktop cannot test the physical RFID/card reader.

## Nicht im MVP

- Direkte APDU-Kommunikation mit dem nPA.
- Eigene eID-Implementierung ausserhalb der AusweisApp.
- beA/BNotK produktive Anmeldung oder XNP-Login-Automation.
- Speicherung oder Synchronisation von XNP-API-Keys.
- D-Trust/QES produktiv.
- Gesundheitskartenproduktivbetrieb.
- Cloud-Zugriff auf USB-Geraete.
- Speicherung vollstaendiger Ausweisdaten in Git.

## Sicherheitsanforderungen

- PIN-Eingabe ausschliesslich am Kartenleser oder in der zertifizierten lokalen Komponente.
- Keine PIN-, API-Key-, Token- oder Kartendaten im LLM-Kontext.
- RFID-Funktion bei Reiner-SCT-Lesern fuer BNotK-Chipkartenprozesse ausgeschaltet halten, sofern kein expliziter kontaktloser Use Case freigegeben ist.
- Lokales Plugin nutzt kurzlebige Challenges.
- SaaS akzeptiert nur frische, signierte oder mTLS-gebundene Ergebnisse.
- Evidence ist mandantengebunden und zweckgebunden.
- Tenant-Daten liegen in tenant-spezifischen Compartments oder Stores.
- Audit Events sind revisionssicher abzulegen.
- Debug-Logs muessen redaction-by-default nutzen.
- Der Nutzer muss jede Attributfreigabe bewusst bestaetigen.

## SaaS-Provider-Runbook

1. Produkt-Use-Case auswaehlen:
   - eID-Identitaetsnachweis,
   - beA/BNotK Precheck,
   - D-Trust-Signatur,
   - anderer Kartenprozess.
2. Mandantenfaehige Evidence-Policy definieren.
3. Datenschutz- und AVV-Bezug pruefen.
4. Tenant-spezifischen Evidence Store anlegen.
5. Identity Service mit Challenge-Endpoint bereitstellen.
6. Lokales Plugin signieren und versionieren.
7. Installationspaket pro Zielplattform definieren.
8. Support-Runbook fuer Reader/Treiber/AusweisApp-Probleme anlegen.
9. Pilot mit Testmandant und Testkarte/Simulator ausfuehren.
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
6. Reader-Treiber und AusweisApp pruefen.
7. `cyberjack.health` ausfuehren.
8. Test-Challenge erzeugen.
9. Test-Evidence erzeugen und Audit Event pruefen.
10. Produktive Freigabe im NoC-Prozess dokumentieren.

## Implementierungsphasen

### Phase 0: Recherche und Spike

- PC/SC-Erkennung unter Windows testen.
- AusweisApp-Status und WebSocket-Handshake testen.
- Lokalen MCP-Prototyp ohne echte Attributweitergabe bauen.

### Phase 1: MVP

- Local readiness script `plugins/noc-cyberjack-rfid/scripts/check_readiness.py` implemented.
- Windows DriverPackage/SmartCardReader provider detection implemented.
- Linux driver/PCSC/USB preflight implemented in the readiness script.
- Evidence schema `plugins/noc-cyberjack-rfid/contracts/readiness-evidence.schema.json` implemented.
- `cyberjack.health`, `cyberjack.list_readers`, `cyberjack.check_bnotk_card_path` will be derived from the script core for the later MCP/HTTP adapter.
- `cyberjack.check_ausweisapp` bleibt fuer eID-Folgefaelle vorgesehen.
- Challenge-Flow stubben.
- Beispielprozess unter `processes/` anlegen.

### Phase 2: eID-Workflow

- AusweisApp WebSocket-Kommandos integrieren.
- Workflow-Status sauber modellieren.
- Abbruch, Timeout und Nutzerfehler auditierbar machen.

### Phase 3: SaaS-Bindung

- Identity Service anbinden.
- Evidence Store tenant-faehig machen.
- mTLS oder signierte Plugin-Identitaet einfuehren.

### Phase 4: Erweiterte Kartenfaelle

- D-Trust- und Signaturpfade pruefen.
- beA/BNotK-Faelle separat rechtlich und technisch bewerten.
- Gesundheitskarten nur nach eigener Compliance-Pruefung.

## Offene Entscheidungen

- Erster produktiver Use Case: eID, beA/BNotK, D-Trust oder interner Karten-Precheck?
- Erstplattform: Windows nativ oder zusaetzlich Linux/macOS?
- Plugin-Form: MCP-only, lokaler HTTP-Service oder beides?
- Evidence-Retention je Tenant?
- Attributfreigabe komplett ausserhalb NoC oder mit minimiertem Attributsatz?
- Signierung/Update-Kanal fuer das lokale Plugin?

## Akzeptanzkriterien fuer den ersten PR

- Neues Dokument beschreibt Architektur, Scope und Sicherheitsgrenzen.
- Local readiness script produces JSON evidence without PIN, card-data or API-key capture.
- Evidence schema is versioned inside the plugin.
- Kein Secret, keine echte personenbezogene Information und keine Kartenrohdaten im Repo.
- MVP ist als lokaler Flow beschrieben.
- Tenant-Onboarding ist als eigener Ablauf beschrieben.
- Quellen sind dokumentiert.

## Quellen

- REINER SCT cyberJack RFID standard: https://www.reiner-sct.com/produkt/cyberjack-rfid-standard/
- REINER SCT Linux driver for cyberJack smart card reader: https://help.reiner-sct.com/en/support/solutions/articles/101000480008-linux-driver-for-cyberjack-smart-card-reader
- BNotK Hinweis zu Kartenlesegeraeten: https://onlinehilfe.bnotk.de/einrichtungen/zertifizierungsstelle/hinweis-zu-kartenlesegeraeten.html
- BNotK Kompatible Kartenlesegeraete: https://onlinehilfe.bnotk.de/einrichtungen/elektronisches-urkundenarchiv/kartenverwaltung/kartenmanagement/kompatible-kartenlesegeraete.html
- BNotK XNP Integration mit weiteren Notariatsanwendungen: https://onlinehilfe.bnotk.de/einrichtungen/bundesnotarkammer/xnp/notarsoftwarehersteller-systembetreuer/integration-mit-weiteren-notariatsanwendungen.html
- BNotK FAQ Kartenverwaltung und Schluesseluebergabe: https://onlinehilfe.bnotk.de/einrichtungen/elektronisches-urkundenarchiv/kartenverwaltung/faq-kartenverwaltung-und-schluesseluebergabe.html
- BNotK SAK lite: https://onlinehilfe.bnotk.de/einrichtungen/zertifizierungsstelle/bnotk-sak-lite.html
- BNotK Einstieg ins Bestellsystem / Chipkartenanmeldung: https://onlinehilfe.bnotk.de/einrichtungen/zertifizierungsstelle/einstieg-ins-bestellsystem.html
- BNotK XNP Anmeldung: https://onlinehilfe.bnotk.de/einrichtungen/bundesnotarkammer/xnp/nutzung-von-xnp/anmelden-in-xnp.html
- AusweisApp SDK Desktop/WebSocket: https://www.ausweisapp.bund.de/sdk/desktop.html
- AusweisApp SDK Einfuehrung: https://www.ausweisapp.bund.de/sdk/intro.html
- AusweisApp Entwickler-FAQ: https://www.ausweisapp.bund.de/en/faq-for-developers
- Governikus identglue: https://github.com/Governikus/identglue
