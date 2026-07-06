# Private-Payload-Zielarchitektur

Status: logisches Design ohne Apply
Letzte inhaltliche Anpassung: 2026-07-06

## Zweck

Diese Seite beschreibt das erste logische Zielbild für spätere private
Mandatsdaten-Payloads. Sie folgt dem
[privaten Betriebsrahmen](private-operating-frame-gate.md), aktiviert aber
noch keinen produktiven Speicher, kein DDL-Artefakt und keinen Zugriff auf
echte Mandatsdaten.

Der maschinenlesbare Vertrag steht in
[workflows/contracts/private-payload-target-design.contract.json](../../../workflows/contracts/private-payload-target-design.contract.json)
und wird durch
[scripts/validate_private_payload_target_design.py](../../../scripts/validate_private_payload_target_design.py)
geprüft.

## Designentscheidung

NaC modelliert private Payloads als Envelope- und Pointer-Architektur:

- Der Envelope hält nur Bindung, Zweck, Datenklasse, Speicherziel,
  Pointer, Hash, Schlüsselreferenz, Retention, Zugriffspolitik und Audit.
- Der private Inhalt liegt nicht in Git, nicht in GitHub-Artefakten, nicht in
  lokaler Target-Control und nicht in M365/SharePoint-Metadatenlisten ohne
  Private-Payload-Gate.
- Zugriffe laufen über zweckgebundene Access Grants mit Ablauf, Widerruf,
  Rollenklasse, Step-up und Human Review.
- Dokumente werden als verschlüsselte Objekte oder lokale Fachsystemobjekte
  referenziert; NaC speichert dazu nur redigierte Metadaten.

Die Rollen-, Zweck- und Zugriffsmatrix dazu steht in
[private-payload-access-policy.md](private-payload-access-policy.md).

Damit bleibt die Architektur prüfbar, ohne einen privaten Payload im Repo zu
erzeugen.

## Logische Komponenten

| Komponente | Rolle | Inhalt |
| --- | --- | --- |
| `private_payload_envelope` | Metadaten- und Policy-Hülle | Payload-ID, Tenant, Vorgang, Zweck, Datenklasse, Speicherziel, Pointer, Hash, Schlüssel-, Retention-, Zugriffs- und Audit-Referenzen |
| `private_payload_access_grant` | zweckgebundene Zugriffentscheidung | Rolle, Zweck, Ablauf, Widerruf, Step-up, Human-Review- und Audit-Referenz |
| `encrypted_document_object_pointer` | Dokumentreferenz ohne Inhalt | Speicherziel, Objektpointer, Hash, MIME-Klasse, Scan-, Retention- und Audit-Referenz |
| `redacted_private_payload_audit` | append-only Nachweis | Ereignistyp, Entscheidungsstatus, Rollenklasse, Zweck und Attestierung ohne Payload |

Keine dieser Komponenten enthält Klartext-Payloads.

## Speicherziele

| Ziel | Status | Aufgabe |
| --- | --- | --- |
| Private-Payload-Metadatenstore | künftiges Schema-Design | Envelopes, Access Grants und redigierte Audit-Events. |
| Microsoft-365-geschützte Dokumentablage | künftiges Storage-Design | Aktengebundene Dokumentbibliotheken, Versionen, Hashes, Kurzzeitlinks und redigierte Zugriffsnachweise. |
| Verschlüsselte Object-Storage-Payloads | künftiges Storage-Design | Dokumentobjekte, Hashes und kurzlebige Zugriffspfade. |
| On-Prem Private Store | künftiges Integrationsdesign | lokale DMS-/Fachsystemreferenzen und redigierte Evidence zurück nach NaC. |

## Noch Gesperrt

Bis zu einem separaten Owner-Apply-Gate bleiben gesperrt:

- private Payload-Tabellen anlegen,
- private Payloads schreiben oder lesen,
- private Dokumentlinks ausstellen,
- private Payloads in Graphen projizieren,
- Live-DMS oder Fachsysteme anbinden,
- Migrationen mit echten Mandatsdaten ausführen.

## Verhältnis Zum Graph-Modell

Graph- und Ontologiearbeit darf weiterhin nur über Metadaten laufen. Ein Graph
kann Prozessabhängigkeiten, Gates, Rollen, Fristen und Audit-Beziehungen
zeigen. Private Payloads selbst werden nicht in den Graph projiziert. Wenn
später ein privater Graph-Bezug nötig wird, muss er über Envelope-IDs,
Klassifikation, Zweckbindung und redigierte Auditkanten erfolgen.

## Nächster Schritt

Der nächste Schritt ist kein Apply, sondern ein Review der Kontrollfragen:

- welche Datenklasse braucht welches Speicherziel,
- welche Rollen dürfen welchen Zugriff beantragen,
- welche Retention und Löschung gelten,
- welche Schlüssel- und Backup-Grenzen gelten,
- welche Evidence reicht für Notariat, Datenschutz und Betrieb aus.
