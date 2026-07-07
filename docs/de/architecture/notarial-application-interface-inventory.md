# Notarielles Anwendungsschnittstellen-Inventar

Status: Offline-Inventar mit read-only MCP-Werkzeugen ohne Live-Apply
Letzte inhaltliche Anpassung: 2026-07-07

## Zweck

Diese Seite führt die vom Owner bereitgestellten BNotK- und XJustiz-
Schnittstellenquellen als NaC-Architekturinventar. Sie ist kein
Produktivzugang, kein Credential-Speicher und keine Freigabe für
Fachsystem-Schreibaktionen.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/notarial-application-interface-inventory.contract.json](../../../workflows/contracts/notarial-application-interface-inventory.contract.json)
und wird durch
[scripts/validate_notarial_application_interface_inventory.py](../../../scripts/validate_notarial_application_interface_inventory.py)
geprüft.

## Quellenstand

| Quelle | Stand | Repo-Grenze |
| --- | --- | --- |
| BNotK Onlinehilfe, Anwendungsschnittstellen: https://onlinehilfe.bnotk.de/technischer-bereich/softwarehersteller/anwendungsschnittstellen.html | Seitenstand 2026-06-01, owner-provided Offline-Archiv vom 2026-07-07 | Nur Modul-, Protokoll- und Grenzmetadaten; keine HTML-/Asset-Kopie im Repo |
| BNotK Onlinehilfe, beN: https://onlinehilfe.bnotk.de/technischer-bereich/softwarehersteller/ben.html | owner-provided Offline-Archiv vom 2026-07-07 | Nur Architekturgrenzen wie XTA-WS, OSCI, Zertifikat, IdentityToken und Polling; keine WSDL-/Beispielpayload-Kopie im Repo |
| XJustiz 3.3.1 XSD-Paket | owner-provided ZIP `xjustiz_3_3_1_xsd.zip`, Paketdateien mit Zeitstempel 2021-11-04 | Nur Paketmetadaten; keine XSD-Rohkopie ohne Lizenz- und Quellenfreigabe |

## Schnittstellenmatrix

| ID | Bereich | Aus Quelle erkennbare Schnittstellenfamilie | NaC-MVP-Bedeutung |
| --- | --- | --- | --- |
| `mandantenportal` | Mandantenportal | JSON-Export und OpenAPI | Kandidat für spätere Import-/Statusgrenze; im MVP nur als externer Quellenpunkt und Metadatenhinweis |
| `uvz` | Urkundenverzeichnis | Import aus NSW, lesender Zugriff aus UVZ, schreibender Zugriff ins UVZ | Nur Boundary-Gate; kein Produktivschreiben und keine UVZ-Rohdaten im Repo |
| `vvz` | Verwahrungsverzeichnis | Import/Export und Datenabfrage | Nur Boundary-Gate; spätere private Payload- und Rollenprüfung erforderlich |
| `xnotar_handelsregister` | Handelsregister über XNotar | Übergabe von Vorgängen und Dokumenten aus NSW nach XNotar | BPMN-Übergabepunkt und redigierte Evidence, kein NaC-gesteuerter Versand |
| `xnotar_grundbuch` | Grundbuch über XNotar | Übergabe von Vorgängen und Dokumenten aus NSW nach XNotar | BPMN-Übergabepunkt und Warte-/Rücklaufgate, keine Grundbuchrohdaten in NaC |
| `xnotar_sonstige_antraege` | Sonstige XNotar-Anträge | Übergabe von Vorgängen und Dokumenten aus NSW nach XNotar | Modelliert als externe Fachsystemgrenze |
| `enova` | XNotar-eNoVA | OpenAPI-Spezifikation und SDS-/XJAB-nahe Übergaben | Kandidat für späteres Testzugangs-Gate; kein MVP-Live-Apply |
| `zvr` | Zentrales Vorsorgeregister | REST-API-Funktionsaufrufe aus NSW | Eigener Integrationspfad mit BNotK-/ZVR-Zulassung, Zertifikaten und Owner-Gate |
| `ben` | besonderes elektronisches Notarpostfach | XTA-WS, EGVP/OSCI-Container, TLS-Clientzertifikat, IdentityToken, Postfach-Polling und Transportstatus | Lokaler Companion-/Evidence-Pfad; keine Secrets, keine Nachrichteninhalte und keine produktive Sendung im Produktrepo |
| `xjustiz_331` | XJustiz 3.3.1 | 66 XSD-Dateien mit Grunddatensatz, Nachrichten, Register, Vorsorgeregister, eEB, ZTR und weiteren Domänenmodulen | Schema-Referenz für spätere Mapping- und Validierungspipeline; kein XSD-Volltext und kein Payload-Testdatensatz im Repo |

## Architekturentscheidung

Für den M365-MVP bleibt die aktive Datenhaltung Teams, SharePoint und
Microsoft Graph REST/MCP. Die BNotK-, beN- und XJustiz-Quellen werden nicht
zur zentralen Runtime-Datenhaltung. Sie definieren Integrationsgrenzen und
spätere Connector-Gates.

Die erste zulässige NaC-Umsetzung ist:

1. Schnittstellen als BPMN-Gates oder externe Systeme modellieren.
2. MCP-Tools nur read-only als Inventar- und Planungswerkzeuge zulassen.
3. Live-Aufrufe, Zertifikate, IdentityToken, Postfachzugriffe und Payload-
   Mappings in einen privaten Betriebsrahmen auslagern.
4. Redigierte Evidence speichern, aber keine Nachrichten, Registerdaten,
   Urkundeninhalte, XML-Payloads, XSD-Rohkopien oder BNotK-Volltexte.

## Nicht-Ziele

- keine Speicherung von BNotK-HTML, BNotK-Assets, beN-Beispielpayloads oder
  XJustiz-XSD-Dateien im Produktrepo,
- keine beN-, UVZ-, VVZ-, ZVR-, Mandantenportal- oder XNotar-Live-Anbindung,
- keine Credentials, Clientzertifikate, Tokens, PINs oder Amtstätigkeits-
  Identifikatoren im Repo,
- keine produktive Fachsystem-Schreibaktion ohne separaten privaten
  Betriebsrahmen, Datenschutzprüfung, Testzugang und Owner-Apply-Gate.

## Nächste technische Ableitung

Die erste MCP-Umsetzung liegt im `teams-sharepoint-data-mcp`-Server:
`notarial_interface_inventory_list` und `notarial_interface_boundary_check`.
Diese Tools geben nur die hier gepflegten Metadaten und Gate-Entscheidungen
aus; sie rufen keine externen BNotK-Systeme, kein SharePoint und kein Microsoft
Graph auf und ingestieren keine Quellartefakte.
