---
name: nac-release-memory
description: Nutzen, wenn ein NaC-Release über OCI DevOps, OCI Functions, OCIR, API Gateway oder den No-SSH-Release-Pfad vorbereitet, gestartet, überwacht oder nachbereitet wird; besonders bei wiederholten Build-/Release-Reibungen, OCI-Timeouts, Resource-Manager-Variablenabgleich oder Owner-Release-Freigaben.
---

# NaC Release Memory

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen,
Variablennamen, Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Supports commit-bound NaC OCI DevOps releases. It keeps the
release lane from rediscovering the same facts, enforces owner gates, avoids
broad OCI discovery loops, and records repeated friction as durable process
improvements.

## Einsatzgrenze

Laufzeitmodus: `release-operator-memory`.

Dieser Skill ist eine agentenlesbare Erinnerung für wiederkehrende NaC-Releases.
Er ersetzt keine Owner-Freigabe und startet keine OCI-Schreibaktion selbst.
Er führt den Agenten zur vorhandenen Release-Prozedur, zu zulässigen Quellen
und zu einem wiederholbaren Umgang mit Timeouts und Reibungspunkten.

## Vor jedem Release lesen

1. Dieses Skill-Dokument.
2. `references/release-lane.md`.
3. Das OCI-Landing-Zone-Runbook
   `/home/ubuntu/src/oci-landing-zone/runbooks/no-ssh-functions-release.md`.
4. Bei Status-/Benachrichtigungsthemen zusätzlich
   `/home/ubuntu/src/oci-landing-zone/runbooks/event-driven-release-monitor.md`.

## Harte Regeln

- Keine Secrets, Tokens, TLS-Schlüssel, Session-Werte, OAuth-States, Nonces,
  Mandatsdaten oder privaten Zertifikatsmaterialien lesen, loggen, posten oder
  in Git schreiben.
- Keine realen OCIDs in neue Git-Artefakte schreiben, wenn das zuständige
  Runbook Operator-Variablen, Resource Manager oder lokale Shell-Umgebungen als
  Speicherort vorsieht.
- Keine OCI-Schreibaktion ohne passende Owner-Freigabe starten:
  `Owner Release Approval` für Release-Builds, `Owner Apply Approval` für
  Apply-/Infra-Schreibaktionen.
- `commit-info` ist nur Audit-Metadatum. Jeder manuelle Release-Build muss den
  geprüften Commit zusätzlich als `NAC_RELEASE_COMMIT` erhalten.
- Der Release-Hotpath nutzt gezielte Kommandos mit bekannten Inputs. Breite
  `list`-Discovery ist Diagnose, nicht Standardpfad.

## Standardablauf

1. GitHub-Zielstand prüfen: PR gemerged, `main...origin/main` sauber,
   freigegebener Commit exakt notieren.
2. Owner-Release-Freigabe gegen diesen Commit prüfen.
3. Mirror aktualisieren:
   `oci devops repository mirror --repository-id "$NAC_DEVOPS_REPOSITORY_ID"`.
4. Commit im OCI-Mirror prüfen:
   `oci devops repository get-commit --repository-id "$NAC_DEVOPS_REPOSITORY_ID" --commit-id "$REVIEWED_GIT_COMMIT"`.
5. Build-Run mit `commit-info` und `NAC_RELEASE_COMMIT` starten.
6. Build/Deploy über OCI DevOps und Release Monitor verfolgen.
7. Smoke-Tests nur mit kundensicheren Endpunkten durchführen.
8. Nach erfolgreichem Deploy Image-Tag und Digest ermitteln.
9. Resource-Manager-Stack-Variablenrefresh als separates Owner-Gate behandeln.
10. GitHub Issue/PR/Project mit sanitisierten Ergebnissen aktualisieren.

## Umgang mit OCI-Timeouts

Wenn OCI-IAM erreichbar ist, aber DevOps oder Resource Manager wiederholt
timeouten:

1. Nicht in breite `list`-Schleifen fallen.
2. Ein gezieltes Kommando höchstens zweimal mit klarer kurzer Wartezeit
   wiederholen.
3. Danach den Pfad als externe OCI-/Netzwerkgrenze behandeln, nicht als
   Codeproblem.
4. Den Status mit CET/CEST-Zeit, Kommando-Klasse und nächstem sicheren Schritt
   dokumentieren, ohne Secrets oder Rohkonfiguration zu posten.
5. Erst nach neuer Evidenz erneut versuchen.

## Observability

Bei jedem größeren Releaseblock das NaC Time Ledger nutzen:

```bash
PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/nac time-ledger run \
  --session-id YYYY-MM-DD-nac-release \
  --task "NaC release" \
  --phase <phase> \
  --category <category> \
  -- <command>
```

Bei manuell protokollierten Phasen `time-ledger add` nutzen. Am Ende eines
Blocks `time-ledger summary` ausführen und die wichtigsten Warte- oder
Reibungspunkte in GitHub oder im Abschlussstatus zusammenfassen.

## Wiederholte Reibung

Wenn derselbe Release-Reibungspunkt zweimal in einer Session oder dreimal über
Issues, PRs oder Releases hinweg auftritt:

1. Muster benennen.
2. Fehlende Regel, fehlendes Runbook, unpassende Freigabeformulierung oder
   fehlende Tooling-Kante benennen.
3. Vor dem nächsten Retry eine kleine dauerhafte Optimierung vorschlagen.
4. Erst nach passender Owner-Freigabe ändern oder weiter automatisieren.

## Rückgabeformat

Nutze knappe Abschnitte:

- `Stand`
- `Validierung`
- `Nächster Schritt`
- `Von dir brauche ich`

Wenn nichts vom Owner benötigt wird, muss `Von dir brauche ich: nichts` stehen
und die Arbeit fortgesetzt werden, sofern kein externer Blocker besteht.
