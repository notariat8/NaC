# Register

Lokaler HRA-zuerst-Handelsregister-Begleiter für die Vorbereitung von Online-
Registeranmeldungspaketen, notarielle Online-Verfahrensbereitschaft, eID-/App-
Voraussetzungen, Freigabepunkte und metadatenbasierte Nachweise. Für
notarielle Einreichungsabläufe zuerst mit `nac-bnotk-xnp` beginnen. Dieses
Plugin ruft keine Registerdaten ab und automatisiert keine geschützten Portale.

## Status

Installierbares MVP-Plugin-Gerüst. Das Plugin stellt lokale Codex-Skill-
Führung, einen maschinenlesbaren Sicherheitsvertrag und Marktplatz-Metadaten
für die Vorbereitung von Online-Registeranmeldungen bereit. Externe
Einreichungsadapter sind in dieser ersten Version bewusst nicht aktiviert.

## Installationsgrenze

- Läuft als lokales Codex-Plugin aus diesem Repository.
- Trennt Bürger-Vorprüfung von notariatsseitigen Workstation-Arbeitsabläufen.
- Erfordert die `nac-bnotk-xnp`-Prüfung vor XNotar-/Registerübergabe-Arbeit.
- Hält Geheimnisse, PINs, Zertifikate, Portalsitzungen und Mandatsinhalte außerhalb von Git.
- Erzeugt Planvorschauen und Nachweis-Metadaten vor jeder notariellen oder
  einreichungsbezogenen Aktion.
- Verlangt Antragstellerfreigabe, rechtliche Prüfung und notarielle Prüfung
  für Online-Handelsregisteranmeldungen.

## Day0

- Modus bestätigen: Bürger-Vorprüfung oder notariatsseitiger Arbeitsplatz-Arbeitsablauf.
- Für notariatsseitigen Arbeitsablauf zuerst `nac-bnotk-xnp`-Bereitschaft bestätigen.
- Rechtsform, Registerspur und HRA-/HRB-Zuordnung bestätigen.
- Antragstellerberechtigung, Notarroute, Bundesnotarkammer-App-Bereitschaft und
  eID-Bereitschaft bestätigen.

## Day1

- Online-Anmeldungs-Bereitschaft-Plan, Liste fehlender Angaben und notarielle
  Nachweischeckliste erzeugen.

## Day2

- Zurückgewiesene Anmeldungen, fehlende Anlagen, Identitäts-/Signaturfehler
  und Nachweisvollständigkeit prüfen.

## Erforderliche Konten und Freigaben

- Notartermin oder Notariatsarbeitsablauf
- abgeschlossene `nac-bnotk-xnp`-Bereitschaft für notarielle Arbeitsabläufe
- Online-Verfahrens-App der Bundesnotarkammer
- eID-fähiger amtlicher Ausweis und PIN
- Antragsteller- und Reviewer-Freigabe für das Registeranmeldungspaket

Die konsolidierte Anforderungsliste steht in
[docs/de/plugin-operations/account-and-approval-requests.md](../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../docs/en/plugin-operations/account-and-approval-requests.md).
