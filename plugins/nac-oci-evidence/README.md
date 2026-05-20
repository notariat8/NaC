# OCI-Nachweis

OCI-Nachweisbegleiter für Landing-Zone-Day0-Prüfungen, Resource-Manager-
Planprüfung, Eventstream-/Audit-Journal-Design, Vault-Grenze sowie Day2-Drift-
und Kostenkontrollen.

## Status

Installierbares MVP-Plugin-Gerüst. Das Plugin stellt lokale Codex-Skill-
Führung, einen maschinenlesbaren Sicherheitsvertrag und Marktplatz-Metadaten
bereit. Externe Schreibadapter sind in dieser ersten Version bewusst nicht
aktiviert.

## Installationsgrenze

- Läuft als lokales Codex-Plugin aus diesem Repository.
- Hält Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte außerhalb von Git.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder sensiblen Aktion.
- Verlangt menschliche Freigabe für regulierte Einreichungen, Portalaktionen,
  notarielle Aktionen und Cloud-Anwendungen.

## Day0

- Tenancy, Compartment, Region, lokales OCI-CLI-Profil und Least-Privilege-
  Policy bestätigen.

## Day1

- Planvorschau und Nachweisverdrahtung vor jedem Apply erstellen.

## Day2

- Drift-, Kosten-, Audit-, Rotations- und Break-Glass-Prüfungen ausführen.

## Erforderliche Konten und Freigaben

- OCI-Tenancy-Zugriff
- Compartment-Admin oder delegierte Policy
- Vault-/Key-Management-Freigabe
- Budgetverantwortlicher
- Verantwortlicher für Audit-Aufbewahrung

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
