# Notarielle On-Prem-Connector-Grenzen

Status: Vertragsgrenze ohne Live-Apply
Letzte inhaltliche Anpassung: 2026-06-28

## Zweck

Diese Seite beschreibt die erste prüfbare Grenze für XNP/SNP, XNotar,
Kartenarbeitsplatz und Registerpfade im NaC-On-Prem-Zielbild. Sie übersetzt
die vorbereiteten `notoclaw01`-Stubs aus der
[NaC-On-Prem-Agent-Runtime](nac-onprem-agent-runtime.md) in einen
maschinenlesbaren NaC-Vertrag, ohne produktive Fachsystemkopplung zu
behaupten.

Der Vertrag steht in
[workflows/contracts/notarial-onprem-connector-boundaries.contract.json](../../../workflows/contracts/notarial-onprem-connector-boundaries.contract.json)
und wird durch
[scripts/validate_notarial_onprem_connector_boundaries.py](../../../scripts/validate_notarial_onprem_connector_boundaries.py)
geprüft.

## Grundregel

NaC ist an dieser Grenze BPMN-, Audit- und Evidence-Rahmen. Die eigentliche
Fachsystemhandlung bleibt in der dafür vorgesehenen lokalen notariellen
Arbeitsumgebung.

Zulässig sind:

- lokale Readiness-Prüfungen,
- redigierte Status- oder Nutzerbestätigungen,
- BPMN-Gates und Abhängigkeiten,
- Nachweise ohne Mandatsdaten, PINs, Tokens, Kartenrohdaten oder
  Zertifikatsgeheimnisse,
- Testumgebungsplanung ohne produktive Einreichung.

Gesperrt sind:

- produktiver Versand an Register, Grundbuch oder andere Fachsysteme,
- Fernsteuerung von XNP, XNotar, Kartenleser oder Signaturvorgängen,
- automatisierte Datenübernahme aus XNP/XNotar in NaC,
- Speicherung von Credentials, PINs, Kartenwerten, Zertifikatsinhalten,
  Registerrohdaten oder Mandatsinhalten,
- jede Schreibaktion ohne separaten privaten Betriebsrahmen, Datenschutzprüfung,
  menschliche Freigabe und Owner-Gate.

## Connector-Grenzen

| Connector | Erlaubter NaC-Status | Gesperrte Grenze |
| --- | --- | --- |
| XNP/SNP und XNotar | Externer Zugriffspunkt, lokale Readiness, redigierte Statusbestätigung, BPMN-Gate | keine direkte Produktivkopplung, kein NaC-gesteuerter Versand, keine Rohdatenübernahme |
| cyberJack/Kartenarbeitsplatz | lokale Hardware-, PC/SC-, morris- und Kartenpfad-Readiness | keine PIN-Erfassung, keine Signaturauslösung, kein Karten- oder Zertifikatsauslesen |
| Register und Grundbuch | externe Status- und Wartegate-Modellierung, redigierte Paket- oder Rücklaufbestätigung | keine produktive Einreichung, kein Abruf oder Speichern von Register-/Grundbuchrohdaten |

## Evidence-Form

Ein Nachweis an dieser Grenze ist nur redigierte Metadaten-Evidence:

- `connector_id`,
- `readiness_status`,
- `checked_at`,
- `checked_by_role`,
- `source_system_label`,
- `redaction_class`,
- `no_secret_attestation`,
- `no_matter_data_attestation`,
- `human_review_status`,
- `audit_event_ref`.

Die Evidence darf kein technisches Geheimnis und keinen echten
Vorgangsinhalt enthalten. Lokale Pfade, Betriebsdetails, produktive
Endpunkte, Tokens und personenbezogene Details bleiben außerhalb des
Produktrepos.

Die verbindliche Datenklassifikation für diese Evidence steht in
[matter-data-classification-redaction.md](matter-data-classification-redaction.md).

## Verhältnis Zu notoclaw01

`notoclaw01` darf Connector-Stubs und Smokes in
`/home/ubuntu/nac-target-control` prüfen. Sobald echte Connector-Details,
Credentials, Fachsystemzugriffe oder produktive Schreibaktionen nötig werden,
endet der Target-Operator-Scope. Der Project Manager auf `brev01` führt dann
GitOps, Review, Datenschutzklärung und Owner-Gates.

## Nächste Freigaben

Dieser Vertrag reicht nur für Architektur, Tests und lokale Readiness-Stubs.
Vor produktiven Connectoren braucht jeder Pfad mindestens:

1. privaten Betriebsrahmen mit Rollen- und Verantwortlichkeitsmodell,
2. Datenschutz-/AVV-/DPA-Klärung für personenbezogene Daten,
3. Testmodus und Rückfallpfad,
4. menschliche fachliche Freigabe,
5. Owner-Apply-Gate für jede produktive Schreibaktion.
