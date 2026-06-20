# Agentic 8h Current Queue

> **Stand:** 20. Juni 2026. Diese Queue ersetzt nicht die allgemeinen
> Operating Rules aus `2026-06-18-agentic-8h-work-packages.md`, sondern
> aktualisiert die Arbeitslage nach den inzwischen geschlossenen Q2Q-Q2V-,
> Track-A-C- und Release-Lane-Tracks.

## Ziel

Codex soll mehrere vorbereitende NaC-Arbeitspakete parallel bearbeiten können,
ohne den Owner alle 20 Minuten für Routine-Evidenz zu unterbrechen. Owner-Gates
werden gesammelt und nur dann angefragt, wenn sie fachlich oder governance-seitig
wirklich erforderlich sind.

## Aktueller Stand

- NaC `main` ist sauber und mit GitHub synchron.
- `oci-landing-zone` `main` ist sauber und mit GitHub synchron.
- `www-n8` `main` ist sauber und mit GitHub synchron.
- Es gibt keine offenen PRs in den drei Repos.
- Die frueheren 8h-Plan-Inputs `NaC#163`, `NaC#171` und
  `oci-landing-zone#89` sind nicht mehr offen.
- Q2Q bis Q2V sind gelandet oder geschlossen.
- Track A ist über PR #189 gelandet und released: `/workspace` verlangt neben
  dem signierten Cookie einen serverseitigen Session-Store-Eintrag.
- Track B ist über PR #191 gelandet: Role-/Case-/Purpose-Gate-Audit-Reasons
  sind explizit und redigiert.
- Track C ist über PR #192 gelandet: der kunden sichtbare Onboarding-Status
  zeigt dokumentierte Review-Information, ohne Einladungen zu senden oder
  interne Begriffe offenzulegen.
- Das Read-only-Branch-Hygiene-Audit zeigt aktuell keine gemergten
  Remote-Cleanup-Branches außer `main`.

## Owner-freie Arbeitslanes

Diese Lanes dürfen vorbereitet werden, ohne beim Owner nachzufragen:

1. **Read-only Evidence**
   - GitHub PR-/Issue-/Branch-Status lesen.
   - OCI Status lesen, soweit keine Secrets gelesen und keine Writes ausgeführt
     werden.
   - Release-Lane Context und Release Memory gegen aktuelle Repos prüfen.
   - Release Memory wird in NaC verifiziert; Release-Lane Context Pack wird im
     `oci-landing-zone`-Repo verifiziert.

2. **Lokale Baseline**
   - `scripts/quality_gate.py --profile strict` ausführen.
   - `python -m unittest discover -s tests` ausführen.
   - `git diff --check` und `git status --short --branch` prüfen.
   - Sandbox-bedingte lokale Socket-Fehler dürfen als Verifikations-Retry
     außerhalb der Sandbox wiederholt werden.

3. **Design- und Testvorbereitung**
   - Bestehende Specs, Tests und Contracts lesen.
   - Naechste Owner-Design-Gates als konkrete Texte vorbereiten.
   - Tests für bereits freigegebene Designs rot/gruen vorbereiten.
   - Keine Implementierung für neue Produkt-/Security-Scope ohne Owner Design
     Approval.

4. **Branch-Hygiene-Audit**
   - Merged/superseded Branches nur listen.
   - Exakten Cleanup-Gate-Text vorbereiten.
   - Keine Branches löschen, bevor der Owner das explizit freigibt.

## Aktuelle Cleanup-Kandidaten

Das Read-only-Audit vom 20. Juni zeigt in NaC und `oci-landing-zone` keine
gemergten Remote-Cleanup-Branches außer `origin/main`.

## Naechste Fachtracks Als Gate-Kandidaten

Im Repository ist aktuell kein vorab freigegebener nächster Fachtrack offen.
Die nächste Feature- oder Security-Grenze muss vor Implementierungsstart durch
ein Owner Design Gate eingeführt werden.

Owner-freie Arbeit kann weiterhin laufen für:

- Release-Memory- und Release-Lane-Evidenzchecks,
- lokale Baseline- und Quality-Gate-Verifikation,
- Read-only Live-Smoke-Evidenz,
- Branch-Hygiene-Audits,
- konkrete Gate-Text-Vorbereitung für einen neuen vom Owner ausgewählten
  Fachtrack.

## Gebündeltes Owner-Paket

Wenn alle owner-freien Lanes vorbereitet sind, soll der Owner nicht mit
Zwischenfragen unterbrochen werden. Stattdessen wird genau ein Paket geliefert:

```text
1. Evidenzzusammenfassung zum aktuellen Live-/Runtime-Stand.
2. Branch-Cleanup-Gate mit exakter Branchliste, nur wenn das Read-only-Audit
   gemergte Branches findet.
3. Ein empfohlenes nächstes Owner-Design-Gate, nur wenn ein konkreter nächster
   Fachtrack ausgewählt wurde.
4. Optional Release-Gate nur für einen konkret geprüften Commit.
```

## Harte Stop-Lines

Codex stoppt vor:

- Designentscheidungen für neuen Produkt- oder Security-Scope.
- OCI DevOps Release/Build/Deploy.
- Resource-Manager Variable Refresh, Plan oder Apply.
- Secret-Werten, neuen Secret-OCIDs oder Vault-Lesezugriff ohne Gate.
- Branch-Löschung oder destruktiven Git-Aktionen.
- Vollworkspace, Mandatsdaten, Dokumentlisten, Uploads oder echte Aktenzugriffe.

## Verifikation

Vor dem Abschluss dieses Queue-Updates:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
```

Die Ausführung kann über `nac time-ledger run` protokolliert werden.

Release-Lane-spezifische Nachweise:

```bash
cd /home/ubuntu/src/private/NaC
PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_release_lane_context_memory

cd /home/ubuntu/src/oci-landing-zone
PYTHONPATH=. /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_release_lane_context_pack
```
