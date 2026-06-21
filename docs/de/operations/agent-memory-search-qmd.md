# qmd Agent Memory Search

Status: optionaler lokaler Pilot für Codex-Arbeitsgedächtnis.

## Zweck

`qmd` kann als lokale Agent Memory Search für wiederkehrende Regel-,
Runbook- und Release-Memory-Fragen genutzt werden. Der Einsatz ist optional und
ersetzt keine Governance-Regel. GitHub bleibt Single Source of Truth; qmd ist
nur ein lokaler Suchindex über bereits versionierte, nicht-sensitive
Dokumentation.

## Erlaubter Index-Scope

Der Index darf nur eng begrenzte Arbeitsdokumentation enthalten:

- `docs/de/operations`
- `docs/de/superpowers`
- `docs/en/operations`
- `docs/en/superpowers`
- `oci-landing-zone/runbooks`
- repo-spezifische `AGENTS.md` nach expliziter Pattern-Prüfung

Kein Repo-Root als Collection. Ein qmd-Test hatte gezeigt, dass ein erwartetes
Pattern nicht wirkte und dadurch zu breit indexiert wurde. Root-Collections
bleiben deshalb verboten, bis das Pattern-Verhalten reproduzierbar geprüft ist.

## Verbotene Inhalte

Folgende Pfade oder Inhalte dürfen nicht in qmd indexiert werden:

- `.terraform`
- `out/`
- `attachments`
- Wallet-Dateien oder `wallet`
- `Secret`, Secret-Werte oder Secret-OCIDs
- `private key`
- Zugangsdaten, Tokens, Session-Werte oder OAuth-State
- Mandatsdaten oder mandate data
- Kunden-, Akten-, Urkunden- oder Ausweisdaten
- repo root als Collection

Der Schutz gilt auch dann, wenn qmd nur lokal läuft. Lokale Indexierung ist
kein Freibrief für vertrauliche Daten.

## Empfohlene Nutzung

Schnelle Regel- und Runbook-Suche:

```bash
qmd search "read-only GitHub OCI evidence no owner approval" --format json -n 5
```

Semantischere Suche, wenn Begriffe unscharf sind:

```bash
qmd query --no-rerank "release approval stack variable refresh image digest" --format json -n 5
```

Einzelnes Dokument abrufen:

```bash
qmd get qmd://oci-runbooks/no-ssh-functions-release.md:560:30
```

## Default-Regeln

- BM25 (`qmd search`) ist der Standard für klare technische Begriffe.
- `qmd query --no-rerank` ist erlaubt, wenn BM25 nicht genügend Kontext liefert.
- Embeddings sind erlaubt, aber nur für den erlaubten Scope.
- Kein Reranking als Standard.
- Kein MCP/HTTP-Daemon als Standard.
- Kein automatisches `qmd embed` auf breiten Collections.
- Kein `git pull` über qmd update commands.

## Plattformentscheidung aus dem Pilot

Der lokale Test auf der aktuellen Codex/Brev-Umgebung ergab:

- BM25-only war schnell und stabil.
- Embeddings funktionierten, brauchten aber initial mehrere Minuten und luden
  ein lokales Modell.
- Warmes `qmd query --no-rerank` war brauchbar für gezielte Memory-Fragen.
- Lokales Reranking auf CPU war zu langsam und instabil für den Standardpfad.
- Der MCP/HTTP-Daemon war im Test nicht verlässlich erreichbar.

Empfehlung: qmd als optionale CLI-Hilfe verwenden, nicht als verpflichtenden
Build-, Release- oder Agent-Gate-Bestandteil.

## Governance-Abgrenzung

qmd darf keine Owner-Gates ersetzen. Design-, Review/Merge-, Release-, Apply-,
Secret- und destruktive Gates bleiben unverändert. qmd darf nur helfen, die
passende Regelstelle schneller zu finden und dadurch unnötige Rückfragen zu
vermeiden.
