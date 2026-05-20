# BNotK XNP / Notariatssoftware Plugin Integration Plan

Stand: 2026-05-11

Dieser Plan beschreibt, wie NaC die XNP-Integration mit Notariatssoftware als Plugin abbilden kann. Die Integration ist besonders sensibel, weil XNP lokale notarielle Fachfunktionen, Amtstätigkeitskontext, Login-Token, Kartenlogin, UVZ, VVZ, eUSL und ggf. XNotar-Prozesse beruehrt. Ziel ist nicht, XNP remote aus der Cloud zu steuern. Ziel ist ein lokaler, kontrollierter Companion auf demselben Arbeitsplatz wie XNP, während NaC SaaS nur Workflow, Policy, Evidence und Audit führt.

## Zielbild

NaC soll Notariatssoftware- und XNP-nahe Workflows sicher orchestrieren:

- lokale XNP-REST-Schnittstelle erkennen und nur von `localhost` ansprechen
- XNP-Konfiguration, Port, Aktivierungsstatus und API-Key-Status dokumentieren
- UVZ- und VVZ-Workflows als fachliche NaC-Prozesse modellieren
- Dokumente und Vorgangsdaten hashen, nicht unnötig in die SaaS übertragen
- Benutzer, Rolle, Amtstätigkeit und Login-Kontext nachvollziehbar machen
- XNotar-Importordner und XJustiz-Pakete validieren, ohne den XNotar-Import von aussen zu erzwingen
- später nur nach BNotK-Schnittstellendefinition direkte lokale API-Aufrufe ausführen

## Offizielle Faktenbasis

- XNP ist die Basisanwendung der Bundesnotarkammer und wird Notarinnen und Notaren kostenfrei bereitgestellt.
- Innerhalb von XNP werden Module für Anwendungen der Bundesnotarkammer und den elektronischen Rechtsverkehr bereitgestellt, u.a. beN, UVZ, VVZ und eUSL.
- Die BNotK beschreibt für XNP eine Integration mit Notariatssoftware, bei der bestimmte Funktionen automatisiert aus anderen Anwendungen direkt und ohne weitere Nutzerinteraktion aufgerufen werden können.
- Stand Oktober 2025 unterstützt die XNP-Notariatssoftware-Schnittstelle:
  - Login mit Karte oder Nutzername in XNP ausloesen
  - UVZ-Einträge suchen
  - UVZ-Eintrag abfragen
  - nächste freie UVZ-Nummer ermitteln
  - UVZ-Einträge erstellen
  - Dokumente zu bestehenden UVZ-Einträgen hinzufuegen
  - Verwahrungsmassen suchen
  - Verwahrungsmasse abfragen
  - Verwahrungsmassen erstellen
- XNP stellt dazu lokal einen REST-Endpunkt bereit. XNP startet einen lokalen Webserver nur auf dem lokalen Pseudointerface `localhost`, so dass nur vom lokalen Rechner kommuniziert werden kann.
- Seit dem Wartungsupdate vom 29.10.2025 wird diese Funktion standardmäßig aktiviert; eine individuelle Deaktivierung und Anpassung ist möglich.
- Ohne individuelle Konfiguration versucht XNP, den ersten freien Port beginnend bei 12774 bis 12784 auf `localhost` zu binden.
- Der gefundene Port wird in die lokale XNP-Konfigurationsdatei geschrieben. Diese liegt im XNP-Anwendungsverzeichnis, ehemals LSP-Home, jetzt `XNP_HOME_CONFIG`, ueblicherweise in `%APPDATA%\XNP`, unter `Configuration\@xna/main.yml`.
- Die Schnittstellenkonfiguration steht im Abschnitt `xjab`, u.a. mit `port`, `encryptedApiKeys` und `disabledByUser`.
- Eine Notariatssoftware muss Login-Informationen, ein Login-Token, sowie die aktuelle Amtstätigkeit übergeben. XNP prüft, ob diese Informationen zur aktuellen Anmeldung in XNP und zum Nutzenden passen.
- Für die spezielle Login-Funktion müssen XNP und Notariatssoftware einander vertrauen. Das erfolgt über einen API-Key, der vom Nutzer in der XNP-Konfiguration hinterlegt wird.
- Dieser API-Key wird verschlüsselt in der Konfigurationsdatei gespeichert und ist in verschlüsselter Form nicht zwischen unterschiedlichen XNP-Installationen übertragbar.
- Für XNotar beschreibt die BNotK dagegen keine softwareseitige Schnittstelle, an die Vorgangsdaten übergeben werden können. Ein Import von aussen soll nicht automatisiert angestossen werden; Vorgangsdaten werden über ein Datenaustausch-Verzeichnis importiert.
- XNotar-Importe müssen als strukturierter Vorgangsordner mit XJustiz-XML und referenzierten Dokumenten im `attachments`-Verzeichnis aufgebaut sein.
- Der XJustiz-Standard ist der Standard für den elektronischen Rechtsverkehr. Stand 30.04.2026 ist XJustiz Version 3.6.2 gültig; BNotK-XNotar-Hilfeseiten enthalten zugleich historische Versionshinweise für konkrete Module und Stichtage. NaC muss Versionen daher pro Modul und Zielsystem explizit pinnen.

## Leitentscheidung

NaC sollte in drei Stufen vorgehen:

1. **Local Evidence Companion**
   - läuft auf demselben Windows-User/Arbeitsplatz wie XNP
   - liest keine PINs und keine Karten-Geheimnisse
   - exponiert XNP-`localhost` niemals ins Netz
   - prüft XNP-Konfiguration, Port, Aktivierung und Modulvoraussetzungen
   - schreibt Evidence in NaC

2. **Lokaler XNP-API-Adapter**
   - nur nach Beschaffung und Prüfung der BNotK-Schnittstellendefinition
   - spricht ausschließlich `localhost`
   - übergibt Login-Token und Amtstätigkeitskontext nur lokal
   - nutzt API-Key nur lokal und installtionsgebunden

3. **XNotar-/XJustiz-Paketvalidierung**
   - NaC erzeugt oder validiert Vorgangsordner
   - Import bleibt Nutzeraktion in XNotar
   - kein externer Import-Trigger, weil BNotK dies für XNotar nicht vorsieht

## Architektur

```text
Notariatsarbeitsplatz / Terminalserver
  XNP
    localhost REST endpoint 12774-12784
    XNP_HOME_CONFIG / Configuration/@xna/main.yml
    UVZ / VVZ / eUSL / beN / XNotar Module
  Notariatssoftware
  nac-xnp-local-plugin
        |
        | Evidence, hashes, workflow status, policy results
        v
NaC SaaS / OCI
  xnp workflow service
  tenant evidence store
  audit journal
  policy engine
  onboarding registry
```

Wichtig: Die Cloud spricht XNP nie direkt an. Die einzige Komponente mit XNP-Zugriff ist der lokale Companion auf demselben Rechner und Benutzerkontext.

## Was das Plugin tun darf

- lokale XNP-Konfiguration finden und den `xjab`-Abschnitt auswerten
- prüfen, ob die Schnittstelle aktiviert ist
- Port im Bereich 12774 bis 12784 validieren oder individuell konfigurierte Ports dokumentieren
- lokalen Health-Check gegen `localhost` ausführen, wenn Schnittstellendefinition und Sicherheitsfreigabe vorliegen
- XNP-API-Keys nur lokal prüfen, nie in die SaaS übertragen
- UVZ-/VVZ-Aufgaben in NaC vorbereiten und Status dokumentieren
- Dokumente lokal hashen und nur Hashes/Metadaten in NaC speichern
- XNotar-Vorgangsordner validieren: `attachments`, `xjustiz_nachricht.xml`, referenzierte Dokumente, Pfadlosigkeit der Dateireferenzen, PDF/TIF-Anforderungen
- XJustiz-Version pro Zielmodul prüfen
- Benutzerattestationen erfassen, z.B. "UVZ-Eintrag wurde in XNP angelegt" oder "XNotar-Import wurde manuell durchgeführt"

## Was das Plugin nicht tun darf

- XNP-`localhost` per Tunnel oder Reverse Proxy für NaC SaaS freigeben
- XNP-API-Key, Karten-PIN, Passwörter, Zertifikate oder Login-Token in NaC SaaS speichern
- Login mit Karte ohne erkennbare lokale Nutzerhandlung erzwingen
- Amtstätigkeitskontext erraten oder ersetzen
- XNotar-Import von aussen automatisiert anstossen
- Notariatsakten, Urkunden, eUSL-Dokumente oder Verwahrungsdaten ungefragt in die SaaS übertragen
- BNotK-Schnittstellendefinitionen nachbauen, falls diese nur für Softwarehersteller oder angemeldete Nutzer bereitgestellt werden
- beN, eBeurkundung oder Online-Verfahren steuern, wenn die XNP-Schnittstelle diese Funktionen nicht ausdrücklich unterstützt

## Integrationspfade

### Pfad A: Local Evidence Companion (MVP)

Dieser Pfad ist sofort planbar.

- NaC führt Prozess und Evidence.
- Der lokale Companion prüft XNP-Installations- und Schnittstellenstatus.
- Nutzer arbeitet weiterhin in XNP und Notariatssoftware.
- NaC speichert nur Hashes, Status, Rollen und Attestationen.
- Keine direkten XNP-API-Aufrufe im MVP, solange die Schnittstellendefinition nicht vorliegt.

Empfehlung: Dieser Pfad ist der erste Schritt.

### Pfad B: XNP-REST-Adapter

Dieser Pfad nutzt die BNotK-XNP-Schnittstelle lokal.

Voraussetzungen:

- Zugriff auf die von der BNotK veröffentlichte Schnittstellendefinition
- klares Softwarehersteller-/Integrationsmodell
- lokaler Secret-Speicher für API-Key-Referenzen
- Nutzer- und Amtstätigkeitskontext aus XNP oder Notariatssoftware
- lokaler Audit-Log und NaC-Evidence-Abgleich
- Tests für aktivierte, deaktivierte und individuell konfigurierte Ports

Technische Konsequenz:

- Companion muss pro Windows-User installiert sein.
- Terminalserver-Szenarien brauchen strikte Session- und Benutzertrennung.
- API-Key ist installationsgebunden und darf nicht migriert oder zentral verteilt werden.
- Alle Calls sind synchron lokal; SaaS sieht nur Ergebnisse/Evidence.

### Pfad C: XNotar-/XJustiz-Dateibrücke

Dieser Pfad betrifft Grundbuch, Handelsregister und sonstige Anträge über XNotar.

- NaC erzeugt oder validiert Vorgangsordner.
- NaC validiert `attachments/xjustiz_nachricht.xml`.
- NaC validiert, dass referenzierte Dokumente im selben `attachments`-Verzeichnis liegen und ohne Pfadangaben referenziert sind.
- NaC prüft PDF/TIF-Anforderungen und Hashes.
- Import wird durch Nutzer in XNotar gestartet.

## Plugin-Schnittstelle

Vorgeschlagene Commands:

- `xnp.health`
- `xnp.discover_config`
- `xnp.read_xjab_config`
- `xnp.validate_local_port`
- `xnp.check_interface_enabled`
- `xnp.record_api_key_presence`
- `xnp.prepare_uvz_entry`
- `xnp.record_uvz_attestation`
- `xnp.prepare_vvz_mass`
- `xnp.record_vvz_attestation`
- `xnp.record_document_hash`
- `xnp.get_evidence`
- `xnp.api.login` (später, nur lokal)
- `xnp.api.uvz.search` (später)
- `xnp.api.uvz.get` (später)
- `xnp.api.uvz.next_number` (später)
- `xnp.api.uvz.create` (später)
- `xnp.api.uvz.add_document` (später)
- `xnp.api.vvz.search` (später)
- `xnp.api.vvz.get` (später)
- `xnp.api.vvz.create` (später)
- `xnotar.validate_exchange_folder`
- `xnotar.prepare_import_package`
- `xjustiz.validate_message`

## Evidence-Modell

```json
{
  "plugin": "nac-bnotk-xnp",
  "tenant_id": "customer-compartment-or-nac-tenant-id",
  "notary_office_id": "customer-notary-office-id",
  "workflow_id": "xnp-workflow-2026-0001",
  "workflow_type": "uvz_entry_preparation",
  "local_environment": {
    "xnp_home_config_present": true,
    "xjab_config_present": true,
    "interface_enabled": true,
    "localhost_only": true,
    "port": 12774,
    "api_key_present_locally": true,
    "api_key_exported_to_oac": false
  },
  "actor": {
    "user_id": "nac-user-id",
    "role": "notary|notary_staff|notary_admin|auditor",
    "xnp_login_confirmed": true,
    "official_activity_context": "redacted-or-local-reference"
  },
  "xnp_action": {
    "module": "UVZ|VVZ|XNotar|eUSL",
    "operation": "prepare|search|create|add_document|manual_import|attestation",
    "performed_locally": true,
    "direct_api_used": false
  },
  "documents": [
    {
      "label": "document-or-xjustiz-package",
      "sha256": "hex",
      "content_stored_in_oac": false,
      "storage_reference": "local-or-customer-controlled-storage"
    }
  ],
  "attestations": [
    {
      "type": "user_confirmed_xnp_action",
      "timestamp": "2026-05-11T00:00:00Z",
      "text": "Die Aktion wurde lokal in XNP im passenden Amtstaetigkeitskontext durchgefuehrt."
    }
  ]
}
```

## NaC-Prozesstypen

- `xnp_local_setup_check`
- `xnp_api_key_local_configuration`
- `uvz_entry_preparation`
- `uvz_document_attachment`
- `vvz_mass_preparation`
- `xnotar_exchange_folder_validation`
- `xjustiz_message_validation`
- `xnp_user_attestation`
- `xnp_audit_export`

Statusmodell:

- `draft`
- `local_prerequisites_missing`
- `xnp_interface_disabled`
- `api_key_missing_for_login`
- `prepared`
- `needs_review`
- `ready_for_local_xnp_action`
- `performed_locally`
- `evidence_recorded`
- `archived`
- `blocked`
- `cancelled`

## Mandanten- und Compartment-Konzept

Für SaaS gilt weiter: ein Compartment pro Kunde bzw. Notarbürokunde.

Empfohlen:

- `nac-platform`
  - Plugin-Definition, Policy, CI, Observability
- `nac-shared-security`
  - Vault, KMS, Audit, Logging, Budgets
- `customer-<notary-office-id>`
  - kundenspezifische Workflows
  - Evidence-Buckets
  - tenantisolierte Retention
  - keine XNP-API-Keys im SaaS-Vault im MVP

Für XNP besonders wichtig:

- Der API-Key ist lokal und installationsgebunden.
- Login-Token bleiben lokal.
- Amtstätigkeitskontext wird nur als notwendige Metadaten oder lokale Referenz dokumentiert.
- Urkunden- und Verwahrungsdaten sind hochsensibel; Standard ist Hash-first, nicht Content-first.

## MVP

Umsetzung für die erste Iteration:

- Markdown-Dokumentation und Plugin-Spezifikation
- `xnp.discover_config`
- `xnp.read_xjab_config`
- `xnp.check_interface_enabled`
- `xnp.validate_local_port`
- `xnp.record_api_key_presence`
- `xnp.prepare_uvz_entry`
- `xnp.prepare_vvz_mass`
- `xnp.record_document_hash`
- `xnp.record_uvz_attestation`
- `xnp.record_vvz_attestation`
- `xnotar.validate_exchange_folder`
- Evidence-JSON-Schema
- Beispielworkflow für UVZ-Eintrag mit Dokumenthash
- Beispielworkflow für XNotar-Vorgangsordner mit XJustiz-XML

Nicht im MVP:

- direkter XNP-API-Aufruf
- Login-Ausloesung über XNP
- Speichern von API-Keys in NaC SaaS
- Remotezugriff auf XNP-`localhost`
- automatisierter XNotar-Import
- beN/eBeurkundung-Steuerung
- Upload von Urkundeninhalten in NaC ohne Mandantenpolicy

## Sicherheitsanforderungen

- XNP-REST-Schnittstelle nur über `localhost`.
- Kein Cloud-zu-Localhost-Tunnel.
- Keine PIN-, Passwort-, API-Key- oder Token-Speicherung in der SaaS.
- Lokale Secrets nur im Secret Store des Betriebssystems oder in XNP selbst.
- Benutzer- und Session-Trennung bei Terminalservern.
- Amtstätigkeitskontext muss explizit aus XNP/Notariatssoftware kommen.
- Evidence append-only und revisionsfest.
- Hash-first-Design für Dokumente.
- Keine Prompt-/Telemetry-Erfassung notarieller Inhalte.
- Datenschutz-Folgenabschaetzung vor Verarbeitung von Urkunden-, Beteiligten- oder Verwahrungsdaten in der SaaS.
- CIS-/C5-orientierte OCI-Baseline: IAM least privilege, MFA, Vault, KMS, Logging, Budgets, Security Zones wo sinnvoll.

## SaaS-Anbieter-Runbook

1. BNotK-Schnittstellendefinition für XNP-NSW-API beschaffen und Nutzungsbedingungen klären.
2. Rolle klären: NaC als lokale Companion-Software, Notariatssoftware-Erweiterung oder technischer Dienstleister.
3. MVP ohne direkte API-Calls bauen.
4. Lokalen Companion für Windows-User-Kontext entwerfen.
5. XNP-Konfigurationsleser für `XNP_HOME_CONFIG/Configuration/@xna/main.yml` implementieren.
6. Keine Secrets in NaC SaaS speichern.
7. Evidence-Schema und Retention je Notarbürokunde festlegen.
8. XNotar-/XJustiz-Validierung getrennt vom XNP-REST-Adapter bauen.
9. Pilot mit manuellen XNP-Aktionen und NaC-Evidence durchführen.
10. Erst danach lokale API-Aufrufe aktivieren.

## Kunden-Onboarding-Runbook

1. Kunde benennt Notarbüros, Arbeitsplätze, Terminalserver und Nutzerrollen.
2. Kunde bestätigt XNP-Installation und Module: UVZ, VVZ, eUSL, XNotar.
3. NaC prüft lokal, ob die XNP-NSW-Schnittstelle aktiv ist.
4. Kunde entscheidet, ob API-Key für Login-Funktion lokal hinterlegt wird.
5. NaC legt Tenant und Evidence Store an.
6. NaC aktiviert UVZ/VVZ/XNotar-Prozessvorlagen.
7. Erster Vorgang wird lokal in XNP durchgeführt.
8. NaC erfasst Hashes, Attestationen und Status.
9. Review: Welche Funktionen dürfen später per lokaler API automatisiert werden?

## Offene Entscheidungen

- Ist NaC selbst Notariatssoftware, Add-on zur Notariatssoftware oder separater Local Companion?
- Gibt die BNotK die XNP-NSW-Schnittstellendefinition für diesen Einsatz frei?
- Welche XNP-Funktionen sind für den ersten Kunden relevant: UVZ, VVZ, Dokumentanhang, Login, XNotar?
- Wie wird der Amtstätigkeitskontext lokal sicher gewonnen?
- Wie werden Terminalserver-Installationen und mehrere Windows-User getrennt?
- Soll NaC Dokumentinhalte speichern oder nur Hashes?
- Welche XJustiz-Version ist im konkreten XNotar-Zielmodul tatsächlich freigegeben?

## Akzeptanzkriterien für die erste Umsetzung

- Plugin exponiert XNP nie ins Netz.
- Plugin speichert keine XNP-API-Keys, PINs oder Login-Token in der SaaS.
- Plugin erkennt lokale XNP-Konfiguration und Schnittstellenstatus.
- Jeder Vorgang enthält Nutzer, Rolle, Amtstätigkeitskontext, Modul, Operation und Zeitstempel.
- Dokumente werden standardmäßig nur gehasht.
- XNotar-Import wird nicht von aussen automatisiert.
- Direkte XNP-API-Calls bleiben deaktiviert, bis die offizielle Schnittstellendefinition und Freigabe vorliegen.

## Quellen

- BNotK Onlinehilfe, Integration XNP mit Notariatssoftware: https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk/integration-xnp-mit-notariatssoftware.html
- BNotK Onlinehilfe, XNP - die Basisanwendung der BNotK: https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk.html
- BNotK Onlinehilfe, Elektronisches Urkundenarchiv: https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/elektronisches-urkundenarchiv.html
- BNotK Onlinehilfe, Urkundenverzeichnis: https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/elektronisches-urkundenarchiv/urkundenarchiv.html
- BNotK Onlinehilfe, Berechtigungsvergabe UVZ/VVZ: https://onlinehilfe.bnotk.de/einrichtungen/elektronisches-urkundenarchiv/urkundenverzeichnis-uvz-und-elektronische-urkundensammlung-euvz/berechtigungsvergabe-fuer-die-xnp-module-urkundenverzeichnis-uvz-sowie-eusl-und-verwahrungsverzeichnis-vvz.html
- BNotK Onlinehilfe, Integration XNP-XNotar mit weiterer Notariatssoftware: https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnotar/integration-xnp-xnotar-mit-weiterer-notariatssoftware.html
- XJustiz Startseite: https://xjustiz.justiz.de/
