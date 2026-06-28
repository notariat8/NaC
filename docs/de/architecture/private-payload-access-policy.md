# Private-Payload-Zugriffsmatrix

Status: Policy-Vertrag ohne Live-Zugriff
Letzte inhaltliche Anpassung: 2026-06-28

## Zweck

Diese Seite definiert die logische Zugriffsmatrix für spätere private
Mandatsdaten-Payloads. Sie ergänzt die
[Private-Payload-Zielarchitektur](private-payload-target-design.md) um Rollen,
Zwecke, Datenklassen, Aktionen, Step-up, Human Review und Audit.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/private-payload-access-policy.contract.json](../../../workflows/contracts/private-payload-access-policy.contract.json)
und wird durch
[scripts/validate_private_payload_access_policy.py](../../../scripts/validate_private_payload_access_policy.py)
geprüft.

## Grundregel

Dieser Vertrag aktiviert keinen Live-Zugriff. Er beschreibt nur, welche
Zugriffe nach privatem Betriebsrahmen, Datenschutzfreigabe, Rollenbindung,
Tenant-/Vorgangs-/Zweckbindung und Owner-Apply überhaupt zulässig werden
könnten.

Automation darf private Payloads nicht lesen und keine Freigaben erteilen.
Gäste haben keinen Default-Lesezugriff. `notoclaw01`, GitHub, öffentliche Demo
und Quality-Gate-Artefakte bleiben für private Payloads immer gesperrt.

## Rollenklassen

| Rolle | Erlaubter Grundsatz |
| --- | --- |
| `notar_fachlich` | fachliche notarielle Prüfung und Freigabe nach Step-up und Audit |
| `notariatsfachkraft` | Fallbearbeitung und Vorbereitung, sensible Klassen nur nach notarieller oder Owner-Freigabe |
| `kostenverantwortung` | Kostenprüfung mit begrenzten Finanz-, Objekt- und Identifikationsdaten |
| `revision_audit` | redigierte Audit- und Evidence-Sicht, keine privaten Payloads |
| `owner` | Owner-Apply und Policy-Ausnahmen, aber keine Umgehung von Datenschutz- und Auditgrenzen |
| `automation` | Policy-Metadaten auswerten, Ablehnungen und redigierte Audits schreiben |
| `client_guest_user` | Upload-Link oder eigener Dokumentstatus nach separatem Secure-Document-Gate |

## Zugriffszwecke

Zugriff ist nur zweckgebunden erlaubt. Der Vertrag kennt:

- notarielle Prüfung,
- Fallbearbeitungsvorbereitung,
- Kostenprüfung,
- Mandatszuordnung,
- externer Upload,
- redigiertes Audit,
- Owner-Apply,
- Incident Response.

Jeder Zugriff braucht einen Grant mit Ablauf, Widerruf, Rollenklasse, Zweck,
Audit-Ereignis und Attestierung, dass keine privaten Payloads in GitHub oder
Target-Control geschrieben wurden.

## Globale Ablehnungen

Immer abgelehnt werden:

- Lesen, Schreiben oder Exportieren privater Payloads über GitHub,
  `notoclaw01`, öffentliche Demo oder Quality-Gate-Artefakte,
- Freigabe privater Payloads durch Automation,
- Default-Lesezugriff für Gäste oder Auditoren,
- Browsing über private Payloads ohne Vorgangs- und Zweckbindung.

## Nachweisform

Ein Zugriffsnachweis enthält nur Metadaten:

- `grant_id`,
- `payload_id`,
- `tenant_id`,
- `matter_id`,
- `role_class`,
- `purpose`,
- `data_classes`,
- `decision_status`,
- `decision_reason`,
- `expires_at`,
- `revocation_status`,
- `step_up_status`,
- `human_review_ref`,
- `audit_event_ref`,
- `no_github_payload_attestation`,
- `no_target_control_payload_attestation`.

Der Nachweis ist kein Payload-Transport. Er dokumentiert nur Entscheidung,
Zweck und Grenze.
