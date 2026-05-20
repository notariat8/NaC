# Übersetzungsstatus

## Verbindliche Regel

`de` und `en` sind verpflichtende Standardsprachen nach
[policies/language-policy.yaml](../../policies/language-policy.yaml). Jede
Änderung an lokalisierten Inhalten muss beide Sprachen pflegen.
Für deutsches Recht und notarielle Usecases ist Deutsch die führende und
rechtlich bindende Sprache; Englisch ist nur Übersetzung oder Orientierung.

## Aktueller Stand

- [docs/de/](.) enthält die deutsche Ausgangsfassung.
- [README.md](../../README.md) ist die deutsch geführte GitHub-Startseite und
  führt Startpfade in einer Deutsch/English-Tabelle.
- [usecases/](../../usecases) wird als deutsche fachliche Usecase-Fläche
  geführt; die unmittelbaren Usecase-READMEs sind kurze deutsche
  Vorderseiten, die auf die jeweilige KG verweisen.
- `SKILL.md`-Dateien werden fachlich deutsch geführt und enthalten eine kurze
  englische Summary; technische Namen, Ordner, Commands und IDs bleiben
  englisch/ASCII.
- Englische Einstiegsfassungen werden parallel im englischen Sprachpfad
  gepflegt, aber nicht aus deutschen Leseflüssen verlinkt.
- Zielgruppenpfade, Reifegrad, Glossar und Beispielpfad werden in `de` und `en`
  gepflegt.
- Die wichtigsten englischen Einstiegs-, Governance-, Betriebs-, Eventstream-,
  Service- und aktiven Pluginplan-Dokumente sind nicht mehr nur Dateispiegel.
- Alte Omnistation-Importe im englischen Sprachpfad sind als englische
  Importnotizen geführt; die deutschen Originalartefakte
  bleiben unter
  [docs/de/plugin-plans/omnistation-imports/](plugin-plans/omnistation-imports/)
  nachvollziehbar.

## Technische Kontrolle

[scripts/validate_language_parity.py](../../scripts/validate_language_parity.py)
prüft:

- Pflicht-Sprachordner für `de` und `en`,
- Dateiparität für lokalisierte Flächen,
- Root-README- und Usecase-Sprachregeln,
- deutsche KG- und Usecase-README-Marker für unmittelbare Usecase-Ordner,
- Skill-Sprachmarker für deutsch geführte `SKILL.md`-Dateien mit englischer
  Summary,
- keine identischen Markdown-/Textspiegel zwischen `docs/de` und `docs/en`,
- sprachgleiche Markdown-Links innerhalb lokalisierter Dokumente und Prompts.

## Nächster sinnvoller Schritt

Tiefere Fachtexte können weiter stilistisch geschärft werden. Neue fachliche
Änderungen müssen aber ab jetzt wieder beide Sprachpfade direkt mitziehen.
