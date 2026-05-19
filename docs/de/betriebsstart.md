# Betriebsstart: Privater Fork Und Lokale Prüfung

Dieses Dokument richtet sich an Office-Admin, IT-Betrieb und technische
Verantwortliche, die NaC lokal prüfen oder als privaten Betriebs-Fork
vorbereiten.

## Ziel

Der öffentliche NaC-Stand ist eine Vorlage. Produktiver Betrieb gehört in eine
private Umgebung mit eigener Zugriffskontrolle, eigenen Rollen, eigenen
Freigaben und ohne echte Mandatsdaten im öffentlichen Muster.

## Minimaler Ablauf

1. Repository klonen.
2. Python-Umgebung nach [docs/de/minimum-requirements.md](minimum-requirements.md)
   einrichten.
3. Lokalen Basischeck ausführen.
4. Privaten Fork oder internes Repository anlegen.
5. Rollen, CODEOWNER und Branch-Schutz für den eigenen Betrieb definieren.
6. Erst danach lokale Arbeitsplatz-, Plugin- und Fachsystempfade prüfen.

## Lokale Checks

```bash
python scripts/startup_check.py --profile base --ide auto --run-tests
python scripts/nac.py doctor --profile strict
```

Bei Plugin- oder Arbeitsplatzarbeit:

```bash
python scripts/nac.py plugins validate
python scripts/nac.py plugins install --mode link
python scripts/startup_check.py --profile plugin-dev --ide auto
python scripts/startup_check.py --profile notary-workstation --ide auto
```

Nach `nac plugins install --mode link` Codex neu öffnen, damit die lokale Plugin-
Discovery die repo-lokalen Plugins in der neuen Session sieht.

## Betriebsgrenzen

- Der private Fork darf keine Geheimnisse im Klartext enthalten.
- Mandatsdaten gehören in geprüfte Fachsysteme, DMS oder Evidence Stores,
  nicht in das öffentliche Muster.
- Lokale Karten-, Signatur- und Portalpfade werden zuerst als Readiness
  geprüft.
- Schreibende Adapter brauchen getrennte Freigabe, Datenschutzklärung und
  nachvollziehbare Verantwortlichkeit.

## Nächste Dokumente

- [docs/de/minimum-requirements.md](minimum-requirements.md)
- [cli.md](cli.md)
- [ausfuehrungsmodell.md](ausfuehrungsmodell.md)
- [docs/de/startup-verification.md](startup-verification.md)
- [docs/de/plugin-operations/install-local-plugins.md](plugin-operations/install-local-plugins.md)
- [docs/de/operations/fork-and-release-operating-model.md](operations/fork-and-release-operating-model.md)
- [pruefung-standardisierung-start.md](pruefung-standardisierung-start.md)
