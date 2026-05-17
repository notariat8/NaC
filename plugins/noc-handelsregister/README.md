# NoC Handelsregister

Lokaler HRA-first-Handelsregister-Begleiter fuer die Vorbereitung von Online-
Registeranmeldungspaketen, notarielle Online-Verfahrens-Readiness, eID-/App-
Voraussetzungen, Freigabepunkte und metadatenbasierte Nachweise. Fuer
notarielle Einreichungsworkflows zuerst mit `noc-bnotk-xnp` beginnen. Dieses
Plugin ruft keine Registerdaten ab und automatisiert keine geschuetzten Portale.

## Status

Installierbares MVP-Plugin-Geruest. Das Plugin stellt lokale Codex-Skill-
Fuehrung, einen maschinenlesbaren Sicherheitsvertrag und Marketplace-Metadaten
fuer die Vorbereitung von Online-Registeranmeldungen bereit. Externe
Einreichungsadapter sind in dieser ersten Version bewusst nicht aktiviert.

## Installationsgrenze

- Laeuft als lokales Codex-Plugin aus diesem Repository.
- Trennt Buerger-Preflight von notariatsseitigen Workstation-Workflows.
- Erfordert das `noc-bnotk-xnp`-Gate vor XNotar-/Registeruebergabe-Arbeit.
- Haelt Secrets, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte ausserhalb von Git.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder notariellen oder
  einreichungsbezogenen Aktion.
- Verlangt Antragstellerfreigabe, rechtliche Pruefung und notarielle Pruefung
  fuer Online-Handelsregisteranmeldungen.

## Day0

- Modus bestaetigen: Buerger-Preflight oder notariatsseitiger Workstation-Workflow.
- Fuer notariatsseitigen Workflow zuerst `noc-bnotk-xnp`-Readiness bestaetigen.
- Rechtsform, Registerspur und HRA-/HRB-Zuordnung bestaetigen.
- Antragstellerberechtigung, Notarroute, Bundesnotarkammer-App-Readiness und
  eID-Readiness bestaetigen.

## Day1

- Online-Anmeldungs-Readiness-Plan, Liste fehlender Angaben und notarielle
  Nachweischeckliste erzeugen.

## Day2

- Zurueckgewiesene Anmeldungen, fehlende Anlagen, Identitaets-/Signaturfehler
  und Nachweisvollstaendigkeit pruefen.

## Erforderliche Konten und Freigaben

- Notartermin oder Notariatsworkflow
- abgeschlossene `noc-bnotk-xnp`-Readiness fuer notarielle Workflows
- Online-Verfahrens-App der Bundesnotarkammer
- eID-faehiger amtlicher Ausweis und PIN
- Antragsteller- und Reviewer-Freigabe fuer das Registeranmeldungspaket

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
