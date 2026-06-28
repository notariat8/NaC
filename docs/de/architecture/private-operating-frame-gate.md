# Privater Betriebsrahmen und Private-Payload-Gate

Status: Vertragsgrenze ohne produktiven Apply
Letzte inhaltliche Anpassung: 2026-06-28

## Zweck

Diese Seite definiert, was passieren muss, bevor echte Mandatsdaten die
metadata-only Grenze von NaC verlassen dürfen. Sie ergänzt die
[Mandatsdaten-Klassifikation](matter-data-classification-redaction.md) um den
privaten Betriebsrahmen für spätere ATP-Private-Payload-Schemas, verschlüsselte
Dokumentablage oder lokale Fachsystem-/DMS-Pfade.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/private-operating-frame-gate.contract.json](../../../workflows/contracts/private-operating-frame-gate.contract.json)
und wird durch
[scripts/validate_private_operating_frame_gate.py](../../../scripts/validate_private_operating_frame_gate.py)
geprüft.

## Entscheidung

Dieser Vertrag aktiviert keine produktive Verarbeitung. Er ist ein Gate:
Solange er nicht mit konkreten Datenschutz-, Sicherheits-, Rollen-,
Aufbewahrungs- und Owner-Nachweisen erfüllt ist, bleiben echte Mandatsdaten aus
GitHub, `notoclaw01`, öffentlicher Demo, Quality-Gate-Artefakten und
metadata-only ATP-Slices ausgeschlossen.

Nach diesem Gate können private Runtime-Designs entstehen. Das kann ein
separates ATP-Private-Payload-Schema, verschlüsselte Object-Storage-Ablage oder
ein lokaler Fachsystem-/DMS-Pfad sein. Jeder dieser Pfade braucht weiterhin
einen separaten Apply- oder Live-Gate.

## Mindestkontrollen

Vor produktiver Verarbeitung sind mindestens erforderlich:

- dokumentierte Owner-Entscheidung,
- Datenschutz-/AVV-/DPA-Review und DSFA-Screening,
- Rollen-, Tenant-, Vorgangs- und Zweckbindung,
- Feldklassifikation und privates Payload-Schema,
- Verschlüsselung bei Speicherung und Transport,
- Schlüsselmanagement,
- Aufbewahrungs- und Löschkonzept,
- Zugriffreview,
- append-only Audit,
- Prozess für Betroffenenrechte,
- Incident-Response- und Backup-/Restore-Grenze,
- Trennung von Testdaten und produktiven Daten,
- menschliche Prüfung vor fachlicher Mandatszuordnung.

## Ohne Gate Gesperrt

Ohne diesen privaten Betriebsrahmen bleiben gesperrt:

- produktive Verarbeitung personenbezogener Mandatsdaten,
- Speicherung von Urkunden-, Dokument-, Ausweis-, Register- oder
  Grundbuchrohdaten,
- XNP-/XNotar-Payloads,
- private Secure-Document-Links,
- ATP-Private-Payload-Schema-Apply,
- Object-Storage-Dokumentwrites,
- lokale DMS- oder Fachsystemwrites,
- Graph-Projektionen über private Payloads.

## Speicherziele

| Ziel | Status | Mindestgrenze |
| --- | --- | --- |
| ATP-Private-Payload-Schema | künftiges Design | Tenant-, Vorgangs-, Zweck-, Rollen-, Verschlüsselungs-, Retention-, Audit- und Owner-Apply-Gate |
| Verschlüsselte Dokumentablage | künftiges Design | Dokumentklassifikation, Kurzzeitlink, Widerruf, Malware-/Dateitypprüfung, Retention, Audit und Human Review |
| On-Prem-DMS oder Fachsystem | künftiges Design | lokale Operator-Grenze, Credential Vault, Human Review, keine Fernsteuerung per Default, redigierte Evidence zurück nach NaC |

## Nachweisform

Ein Gate-Nachweis enthält nur Metadaten:

- `gate_id`,
- `decision_status`,
- `decided_at`,
- `decided_by_role`,
- `scope`,
- `data_classes`,
- `storage_target`,
- `tenant_binding`,
- `matter_binding`,
- `purpose_binding`,
- `retention_policy_ref`,
- `encryption_policy_ref`,
- `access_policy_ref`,
- `audit_event_ref`,
- `no_github_payload_attestation`,
- `no_target_control_payload_attestation`.

Der Nachweis darf den privaten Payload nicht selbst enthalten. Er belegt nur,
dass die Freigabegrenze erfüllt wurde.

## Bezug Zu ATP Und NemoClaw

ATP bleibt bis zu einem separaten Schema-Apply metadata-only. `notoclaw01`
bleibt Target-Control für Smokes, Stubs und redigierte Evidence. Beide Flächen
werden durch diesen Vertrag nicht automatisch zu Mandatsdatenspeichern.

Erst ein späterer, explizit freigegebener privater Betriebsrahmen darf echte
Mandatsdaten führen. NaC-GitOps bleibt trotzdem Quelle für Verträge, Tests,
BPMN, KG, Policies und Reviews.
