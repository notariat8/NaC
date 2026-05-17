# Betriebsstart: Privater Fork Und Lokale Pruefung

Dieses Dokument richtet sich an Office-Admin, IT-Betrieb und technische
Verantwortliche, die NoC lokal pruefen oder als privaten Betriebs-Fork
vorbereiten.

## Ziel

Der oeffentliche NoC-Stand ist eine Vorlage. Produktiver Betrieb gehoert in eine
private Umgebung mit eigener Zugriffskontrolle, eigenen Rollen, eigenen
Freigaben und ohne echte Mandatsdaten im oeffentlichen Muster.

## Minimaler Ablauf

1. Repository klonen.
2. Python-Umgebung nach [docs/de/minimum-requirements.md](minimum-requirements.md)
   einrichten.
3. Lokalen Basischeck ausfuehren.
4. Privaten Fork oder internes Repository anlegen.
5. Rollen, CODEOWNER und Branch-Schutz fuer den eigenen Betrieb definieren.
6. Erst danach lokale Arbeitsplatz-, Plugin- und Fachsystempfade pruefen.

## Lokale Checks

```bash
python scripts/startup_check.py --profile base --ide auto --run-tests
python scripts/quality_gate.py --profile strict
```

Bei Plugin- oder Arbeitsplatzarbeit:

```bash
python scripts/startup_check.py --profile plugin-dev --ide auto
python scripts/startup_check.py --profile notary-workstation --ide auto
```

## Betriebsgrenzen

- Der private Fork darf keine Geheimnisse im Klartext enthalten.
- Mandatsdaten gehoeren in gepruefte Fachsysteme, DMS oder Evidence Stores,
  nicht in das oeffentliche Muster.
- Lokale Karten-, Signatur- und Portalpfade werden zuerst als Readiness
  geprueft.
- Schreibende Adapter brauchen getrennte Freigabe, Datenschutzklaerung und
  nachvollziehbare Verantwortlichkeit.

## Naechste Dokumente

- [docs/de/minimum-requirements.md](minimum-requirements.md)
- [docs/de/startup-verification.md](startup-verification.md)
- [docs/de/plugin-operations/install-local-plugins.md](plugin-operations/install-local-plugins.md)
- [docs/de/operations/fork-and-release-operating-model.md](operations/fork-and-release-operating-model.md)
- [docs/de/pruefung-standardisierung-start.md](pruefung-standardisierung-start.md)
