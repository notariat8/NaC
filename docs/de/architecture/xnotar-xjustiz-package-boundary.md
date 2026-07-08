# XNotar-/XJustiz-Paketgrenze

Status: Offline-Metadatenvertrag ohne Live-Apply

## Zweck

Diese Seite beschreibt die NaC-Grenze für spätere XNotar-/XJustiz-
Austauschpakete. Sie erweitert das notarielle Anwendungsschnittstellen-
Inventar, ersetzt aber keine XNotar- oder Registeranbindung.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/xnotar-xjustiz-package-boundary.contract.json](../../../workflows/contracts/xnotar-xjustiz-package-boundary.contract.json)
und wird durch
[scripts/validate_xnotar_xjustiz_package_boundary.py](../../../scripts/validate_xnotar_xjustiz_package_boundary.py)
geprüft.

## Paketform

Für das MVP ist nur eine redigierte Paketbereitschaft zulässig:

- BPMN-Kanal: `xnotar_xjustiz`
- XJustiz-Stand: XJustiz 3.3.1
- erwartete Nachrichtendatei: `xjustiz_nachricht.xml`
- erwarteter Anlagenordner: `attachments/`
- erlaubte Nachweise: Status, Interface-ID, Modulziel, Version-Pin,
  Dateizähler, Hash-/Pointer-Status sowie No-Secret- und
  No-Matter-Data-Bestätigung

Nicht zulässig sind XML-Inhalt, XSD-Inhalt, Anlageninhalt, Registerdaten,
Grundbuchdaten, Mandatsinhalt, absolute Pfade, Credentials, Zertifikate oder
IdentityTokens im Produktrepo.

## Owner-Gates

Folgende Schritte bleiben getrennt freizugeben:

- XNotar-Testzugang,
- XJustiz-Payload-Mapping,
- Lizenzprüfung vor Rohschema-Nutzung,
- Verarbeitung von Anlageninhalten,
- produktive XNotar-Übergabe,
- Versand an Register- oder Grundbuchsysteme.

## Architekturentscheidung

NaC modelliert XNotar/XJustiz zunächst als externes Fachsystem-Gate. Der
M365-MVP bleibt Teams, SharePoint und Microsoft Graph REST/MCP. Diese
Paketgrenze darf nur Metadaten und redigierte Evidence liefern; sie darf keine
Pakete lesen, schreiben, versenden oder gegen Roh-XSD validieren.

Damit kann BPMN heute bereits die Übergabe- und Wartepunkte abbilden, ohne
Fachsystemzugang, Mandatsdaten oder XJustiz-Payloads in NaC zu ziehen.
