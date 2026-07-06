# Mandatsdaten-Klassifikation und Redaktion

Status: Vertragsgrenze für metadata-only Betrieb
Letzte inhaltliche Anpassung: 2026-07-06

## Zweck

Diese Seite definiert die Datenklassifikation zwischen NaC-GitOps,
Webapp-Status, M365/SharePoint-Metadaten, redigierter Evidence und späteren
privaten Runtime-Speichern. Sie beantwortet die Frage, wann ein Datum noch als
sichere Prozessmetadaten gilt und wann es als Mandatsdatum einen separaten
privaten Betriebsrahmen braucht. Frühere ATP-Metadaten-Slices sind archivierte
Legacy-Referenzen, nicht aktive MVP-Datenhaltung.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/matter-data-classification-redaction.contract.json](../../../workflows/contracts/matter-data-classification-redaction.contract.json)
und wird durch
[scripts/validate_matter_data_classification_redaction.py](../../../scripts/validate_matter_data_classification_redaction.py)
geprüft.

## Grundregel

GitHub, das Produktrepo, die öffentliche Demo, der geschützte Startstatus,
M365/SharePoint-Metadatenlisten und lokale Target-Control-Smokes speichern
keine echten Mandatsdaten. Sie dürfen nur Prozessmetadaten, synthetische
Beispiele, Policy-Verweise, Hashes, Pointer und redigierte Evidence führen.

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
| Lokale Target-Control-Smokes | Nur Manifeste, Smokes, Stubs und nicht-sensitive Evidence. Sobald private Payloads nötig werden, erfolgt Handoff an den Project Manager. |
| Webapp-Startstatus | Nur geschuetzter Status ohne Mandatsdaten. Der eigentliche Arbeitsbereich bleibt bis zum privaten Gate geschlossen. |
| M365/SharePoint-Metadatenebene | Nur sichere Runtime-Metadaten, Events, Bindungen, Hashes und Pointer ohne Rohinhalt. Private Payloads brauchen ein separates Speicher-, Rollen- und Apply-Gate. |
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

## Bezug Zu Lokalen Smokes Und M365

Lokale Sidecars oder Target-Control-Smokes dürfen Agenten, Connector-Stubs und
Arbeitsplatzprüfungen führen. Sie werden dadurch nicht zum Speicher für
Mandatsdaten und nicht zur Quelle der NaC-Verträge. Die M365/SharePoint-
Metadatenebene darf im MVP nur Metadaten, Ereignisse, Bindungen, Hashes und
Pointer halten. Ein Graph- oder Ontologie-Ausbau kann darauf modellieren, muss
aber Mandatsinhalte bis zum privaten Gate ausklammern.

Damit bleibt die Aufteilung klar:

- NaC-GitOps führt Contracts, BPMN, KG, Policies, Tests und PRs.
- lokale Sidecars führen Arbeitsplatz-Smokes und nicht-sensitive Evidence.
- Ein späterer privater Runtime-Speicher führt echte Mandatsdaten erst nach
  explizitem Owner-, Datenschutz-, Sicherheits- und Rollen-Gate nach
  [private-operating-frame-gate.md](private-operating-frame-gate.md).
