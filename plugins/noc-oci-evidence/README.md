# NoC OCI-Nachweisbegleiter

OCI-Nachweisbegleiter fuer Landing-Zone-Day0-Pruefungen, Resource-Manager-
Planpruefung, Eventstream-/Audit-Journal-Design, Vault-Grenze sowie Day2-Drift-
und Kostenkontrollen.

## Status

Installierbares MVP-Plugin-Geruest. Das Plugin stellt lokale Codex-Skill-
Fuehrung, einen maschinenlesbaren Sicherheitsvertrag und Marktplatz-Metadaten
bereit. Externe Schreibadapter sind in dieser ersten Version bewusst nicht
aktiviert.

## Installationsgrenze

- Laeuft als lokales Codex-Plugin aus diesem Repository.
- Haelt Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte ausserhalb von Git.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder sensiblen Aktion.
- Verlangt menschliche Freigabe fuer regulierte Einreichungen, Portalaktionen,
  notarielle Aktionen und Cloud-Anwendungen.

## Day0

- Tenancy, Compartment, Region, lokales OCI-CLI-Profil und Least-Privilege-
  Policy bestaetigen.

## Day1

- Planvorschau und Nachweisverdrahtung vor jedem Apply erstellen.

## Day2

- Drift-, Kosten-, Audit-, Rotations- und Break-Glass-Pruefungen ausfuehren.

## Erforderliche Konten und Freigaben

- OCI-Tenancy-Zugriff
- Compartment-Admin oder delegierte Policy
- Vault-/Key-Management-Freigabe
- Budgetverantwortlicher
- Verantwortlicher fuer Audit-Aufbewahrung

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
