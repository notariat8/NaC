# Codex Time Ledger

Status: eingeführt am 2026-06-15

## Zweck

Das Codex Time Ledger macht agentische NaC-Arbeit auswertbar. Es protokolliert
abgeschlossene Arbeitsblöcke als JSONL und summiert anschließend, wie viel Zeit
in lokale I/O, lokale CPU, Remote-Zugriffe, Freigaben, Nutzerwartezeit,
Review, Validierung und geschätzte LLM-Backend-Zeit geflossen ist.

Das Ledger ersetzt keine OpenAI- oder Workspace-Telemetrie. Es zeigt nicht
exakt, wie OpenAI intern zwischen Queue, Modellcompute und Tokenstream
aufteilt. Es ist das lokale Arbeitsprotokoll für die Frage: Wo verliert ein
NaC-Tag Zeit, und welche wiederkehrenden Reibungen sollten wir dauerhaft
verbessern?

## Speicherort

Der Standardpfad ist generierter Output und wird nicht als fachliche Wahrheit
versioniert:

```bash
out/observability/codex-time-ledger.jsonl
```

Für überprüfbare Berichte kann eine Summary als Markdown oder JSON in einen
Review-Artefaktpfad kopiert werden. Rohlogs dürfen keine Mandatsdaten,
personenbezogenen Daten, Secrets, Promptvolltexte oder Command-Ausgaben
enthalten.

## Kategorien

| Kategorie | Bedeutung | Grenze |
| --- | --- | --- |
| `llm_backend` | geschätzte Zeit für Modellantwort, Streaming und agentische Synthese | keine exakte interne OpenAI-Aufteilung |
| `local_cpu` | lokale Tests, Builds, Validatoren und rechenlastige Kommandos | CPU-Anteil nur mit zusätzlichem Systemtool exakt |
| `local_io` | Repo lesen, Dateien suchen, lokale Logs öffnen | kann auch kleine CPU-Anteile enthalten |
| `remote_io` | GitHub, Web, Registry, API oder CI-Abrufe | Remote-Systemzeit bleibt meist nur indirekt sichtbar |
| `remote_cpu` | CI- oder Cloud-Laufzeit, wenn als Dauer bekannt | nicht automatisch aus lokalem Wall-Clock ableitbar |
| `approval_wait` | Warten auf Sandbox-, Netzwerk- oder Tool-Freigabe | nur eintragen, wenn der Block wirklich wartet |
| `user_wait` | Warten auf Nutzerantwort, Scope-Entscheidung oder Review | nicht mit LLM-Denkzeit mischen |
| `editing` | lokale Code-, Doku- oder Contract-Änderungen | keine fachliche Reviewzeit |
| `review` | Diff-Review, Ergebnisprüfung, Architekturabgleich | keine Testlaufzeit |
| `validation` | Qualitätsgate, Privacy-Lint, Linkcheck, Parität, Unit Tests | bei CPU-lastigen Einzellaufzeiten zusätzlich `local_cpu` nutzen |
| `other` | Restkategorie für nicht sauber trennbare Blöcke | bei Wiederholung neue Kategorie prüfen |

## Befehle

Manuellen Block eintragen:

```bash
python scripts/nac.py time-ledger add \
  --session-id 2026-06-15-nac \
  --task "NaC Time Ledger" \
  --phase context-read \
  --category local_io \
  --started-at 2026-06-15T10:00:00Z \
  --ended-at 2026-06-15T10:08:00Z
```

Kommando ausführen und automatisch messen:

```bash
python scripts/nac.py time-ledger run \
  --session-id 2026-06-15-nac \
  --task "NaC Time Ledger" \
  --phase unit-tests \
  --category local_cpu \
  -- /home/ubuntu/.venvs/nac/bin/python -m unittest tests/test_codex_time_ledger.py
```

Session zusammenfassen:

```bash
python scripts/nac.py time-ledger summary \
  --session-id 2026-06-15-nac
```

Maschinenlesbare Summary:

```bash
python scripts/nac.py time-ledger summary \
  --session-id 2026-06-15-nac \
  --format json
```

## Arbeitsregel

Bei längeren NaC-Sessions wird der führende Codex-Lauf das Ledger für
wesentliche Blöcke pflegen:

1. Kontext- und Recherchephasen werden als `local_io` oder `remote_io`
   eingetragen.
2. Tests, Validatoren und Quality Gates laufen nach Möglichkeit über
   `time-ledger run`.
3. Freigabe- und Nutzerwartezeiten werden getrennt von LLM- und Toolzeit
   protokolliert.
4. Am Ende eines größeren Blocks wird `time-ledger summary` in der Antwort
   zusammengefasst.
5. Wiederkehrende Zeitfresser führen zu konkreten Verbesserungen: engerer
   Testbefehl, Cache, Runbook, Command-Regel, parallele Agenten oder klarere
   Done-Kriterien.
