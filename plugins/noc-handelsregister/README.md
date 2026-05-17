# NoC Handelsregister-Begleiter

Lokaler HRA-zuerst-Handelsregister-Begleiter fuer die Vorbereitung von Online-
Registeranmeldungspaketen, notarielle Online-Verfahrensbereitschaft, eID-/App-
Voraussetzungen, Freigabepunkte und metadatenbasierte Nachweise. Fuer
notarielle Einreichungsablaeufe zuerst mit `noc-bnotk-xnp` beginnen. Dieses
Plugin ruft keine Registerdaten ab und automatisiert keine geschuetzten Portale.

## Status

Installierbares MVP-Plugin-Geruest. Das Plugin stellt lokale Codex-Skill-
Fuehrung, einen maschinenlesbaren Sicherheitsvertrag und Marktplatz-Metadaten
fuer die Vorbereitung von Online-Registeranmeldungen bereit. Externe
Einreichungsadapter sind in dieser ersten Version bewusst nicht aktiviert.

## Installationsgrenze

- Laeuft als lokales Codex-Plugin aus diesem Repository.
- Trennt Buerger-Vorpruefung von notariatsseitigen Workstation-Arbeitsablaeufen.
- Erfordert die `noc-bnotk-xnp`-Pruefung vor XNotar-/Registeruebergabe-Arbeit.
- Haelt Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte ausserhalb von Git.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder notariellen oder
  einreichungsbezogenen Aktion.
- Verlangt Antragstellerfreigabe, rechtliche Pruefung und notarielle Pruefung
  fuer Online-Handelsregisteranmeldungen.

## Day0

- Modus bestaetigen: Buerger-Vorpruefung oder notariatsseitiger Arbeitsplatz-Arbeitsablauf.
- Fuer notariatsseitigen Arbeitsablauf zuerst `noc-bnotk-xnp`-Bereitschaft bestaetigen.
- Rechtsform, Registerspur und HRA-/HRB-Zuordnung bestaetigen.
- Antragstellerberechtigung, Notarroute, Bundesnotarkammer-App-Bereitschaft und
  eID-Bereitschaft bestaetigen.

## Day1

- Online-Anmeldungs-Bereitschaft-Plan, Liste fehlender Angaben und notarielle
  Nachweischeckliste erzeugen.

## Day2

- Zurueckgewiesene Anmeldungen, fehlende Anlagen, Identitaets-/Signaturfehler
  und Nachweisvollstaendigkeit pruefen.

## Erforderliche Konten und Freigaben

- Notartermin oder Notariatsarbeitsablauf
- abgeschlossene `noc-bnotk-xnp`-Bereitschaft fuer notarielle Arbeitsablaeufe
- Online-Verfahrens-App der Bundesnotarkammer
- eID-faehiger amtlicher Ausweis und PIN
- Antragsteller- und Reviewer-Freigabe fuer das Registeranmeldungspaket

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
