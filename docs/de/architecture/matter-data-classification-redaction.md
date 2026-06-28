# Mandatsdaten-Klassifikation und Redaktion

Status: Vertragsgrenze für metadata-only Betrieb
Letzte inhaltliche Anpassung: 2026-06-28

## Zweck

Diese Seite definiert die Datenklassifikation zwischen NaC-GitOps,
`notoclaw01`-Target-Control, Webapp-Status, ATP-Metadaten und späteren
privaten Runtime-Speichern. Sie beantwortet die Frage, wann ein Datum noch
als sichere Prozessmetadaten gilt und wann es als Mandatsdatum einen
separaten privaten Betriebsrahmen braucht.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/matter-data-classification-redaction.contract.json](../../../workflows/contracts/matter-data-classification-redaction.contract.json)
und wird durch
[scripts/validate_matter_data_classification_redaction.py](../../../scripts/validate_matter_data_classification_redaction.py)
geprüft.

## Grundregel

GitHub, das Produktrepo, die öffentliche Demo, der geschützte Startstatus,
ATP in der ersten Metadaten-Scheibe und `/home/ubuntu/nac-target-control`
speichern keine echten Mandatsdaten. Sie dürfen nur Prozessmetadaten,
synthetische Beispiele, Policy-Verweise und redigierte Evidence führen.

Echte Mandatsinhalte beginnen bereits bei Beteiligten-, Objekt-, Register-,
Grundbuch-, Zahlungs-, Familien-, Erb-, Dokument- oder Ausweisbezug. Diese
Daten dürfen erst nach separatem privaten Betriebsrahmen, Datenschutz-/DPA-
Klärung, Rollen-, Tenant-, Vorgangs- und Zweckbindung, Verschlüsselungs-,
Aufbewahrungs- und Owner-Gate verarbeitet werden.

## Erlaubte Daten Vor Dem Privaten Gate

- `safe_metadata_only`: Status, Gate, Prozess, Template, Rolle und Audit ohne
  private Inhaltswerte.
- `synthetic_demo_data`: eindeutig synthetische Beispiele nach
  Datenschutzrichtlinie.
- `policy_reference`: Verweise auf Regeln, Runbooks, Vertraege und Doku.
- `validation_evidence_without_secret_values`: Prüfergebnisse ohne
  technische Geheimnisse oder Rohinhalte.
- `redacted_evidence_metadata`: redigierte Nachweise mit Zweck, Rolle,
  Zeitpunkt, Quelle und Attestierung.
- `approved_public_source_reference`: freigegebene öffentliche Quelle ohne
  Mandatsbezug.
- `hash_or_pointer_without_private_payload`: Hash oder Pointer ohne
  eingebetteten privaten Payload.

## Gesperrte Daten Vor Dem Privaten Gate

Gesperrt bleiben insbesondere:

- echte Mandats-, Urkunden-, Upload- und Dokumentvolltexte,
- Ausweis-, eID- und Ident-Rohdaten,
- Register- und Grundbuchrohdaten,
- Objekt-, Grundstücks-, Kaufpreis-, Konto-, Zahlungs- und Steuerdaten,
- echte Familien-, Erb-, Gesundheits-, Betreuungs- oder Vorsorgedaten,
- Personenidentifikatoren ohne separaten Gate,
- externe Payloads aus Fachsystemen, Portalen, Uploads oder Provider-APIs,
- Tokens, Credentials, Kartenrohdaten, Zertifikatsgeheimnisse und Provider-
  Claim-Dumps.

## Flächen

| Fläche | Grenze |
| --- | --- |
| Produktrepo und GitHub | Nur Quellartefakte, Policies, synthetische Beispiele und redigierte Evidence. Private Payloads sind hier nicht erlaubt. |
| `notoclaw01` Target-Control | Nur Manifeste, Smokes, Stubs und nicht-sensitive Evidence. Sobald private Payloads nötig werden, erfolgt Handoff an den Project Manager. |
| Webapp-Startstatus | Nur geschuetzter Status ohne Mandatsdaten. Der eigentliche Arbeitsbereich bleibt bis zum privaten Gate geschlossen. |
| ATP-Metadaten-Scheibe | Nur sichere Runtime-Metadaten, Events, Bindungen und Hashes ohne Rohinhalt. Private Payloads brauchen ein separates Schema- und Apply-Gate. |
| Secure-Document-Link-Evidence | Nur Zweck, Ablauf, Bindung, Widerruf, Audit und Hash/Pointer. Dokumentinhalt bleibt außerhalb der Evidence. |

## Redaktionsnachweis

Jede redigierte Evidence muss mindestens festhalten:

- `schema_version`,
- `payload_type`,
- `redaction_class`,
- `purpose`,
- `tenant_binding`,
- `matter_binding_status`,
- `role_class`,
- `checked_at`,
- `checked_by_role`,
- `source_system_label`,
- `hash_or_reference`,
- `no_secret_attestation`,
- `no_matter_data_attestation`,
- `audit_event_ref`.

Diese Evidence beweist nicht den privaten Inhalt. Sie beweist nur, dass eine
Grenze geprüft wurde und keine Secrets oder Mandatsdaten in die falsche
Fläche gelangt sind.

## Bezug Zu NemoClaw Und ATP

NemoClaw/OpenClaw darf im Zielsystem Agenten, Connector-Stubs und lokale Smokes
führen. Es wird dadurch nicht zum Speicher für Mandatsdaten und nicht zur
Quelle der NaC-Verträge. ATP darf in der ersten Runtime-Schicht nur
Metadaten, Ereignisse, Bindungen und Hashes halten. Ein Graph- oder Ontologie-
Ausbau kann darauf modellieren, muss aber Mandatsinhalte bis zum privaten Gate
ausklammern.

Damit bleibt die Aufteilung klar:

- NaC-GitOps führt Contracts, BPMN, KG, Policies, Tests und PRs.
- `notoclaw01` führt Zielsystem-Smokes und nicht-sensitive Evidence.
- Ein späterer privater Runtime-Speicher führt echte Mandatsdaten erst nach
  explizitem Owner-, Datenschutz-, Sicherheits- und Rollen-Gate.
