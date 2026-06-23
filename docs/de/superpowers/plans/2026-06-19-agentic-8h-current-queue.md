# Agentic 8h Current Queue

> **Stand:** 23. Juni 2026. Diese Queue ersetzt nicht die allgemeinen
> Operating Rules aus `2026-06-18-agentic-8h-work-packages.md`, sondern
> aktualisiert die Arbeitslage nach den inzwischen geschlossenen Q2Q-Q3J-,
> Track-A-C-, Release-Lane- und Notarkammer-Demo-Tracks.

## Ziel

Codex soll mehrere vorbereitende NaC-Arbeitspakete parallel bearbeiten können,
ohne den Owner alle 20 Minuten für Routine-Evidenz zu unterbrechen. Owner-Gates
werden gesammelt und nur dann angefragt, wenn sie fachlich oder governance-seitig
wirklich erforderlich sind.

## Aktueller Stand

- NaC `main` ist sauber und mit GitHub synchron.
- `oci-landing-zone` `main` ist sauber und mit GitHub synchron.
- `www-n8` `main` ist sauber und mit GitHub synchron.
- Offene PRs aus dem aktuellen owner-freien 3h-Block:
  - NaC PR #264: Runtime bindet den serverseitigen Session-Store auch im
    `nac-web` Serverpfad.
  - NaC PR #265: Immobilienkaufvertrag-BPMN wird als XNP-/XNotar- und
    Vollzug-Demofluss vertieft.
- Die frueheren 8h-Plan-Inputs `NaC#163`, `NaC#171` und
  `oci-landing-zone#89` sind nicht mehr offen.
- Q2Q bis Q3J sind gelandet oder geschlossen.
- Track A ist über PR #189 gelandet und released: `/workspace` verlangt neben
  dem signierten Cookie einen serverseitigen Session-Store-Eintrag.
- Track B ist über PR #191 gelandet: Role-/Case-/Purpose-Gate-Audit-Reasons
  sind explizit und redigiert.
- Track C ist über PR #192 gelandet: der kunden sichtbare Onboarding-Status
  zeigt dokumentierte Review-Information, ohne Einladungen zu senden oder
  interne Begriffe offenzulegen.
- Das Read-only-Branch-Hygiene-Audit zeigt aktuell drei superseded/merged
  NaC-Remote-Branches, die nur nach expliziter Owner-Cleanup-Freigabe gelöscht
  werden dürfen.

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

Read-only-Audit vom 23. Juni:

- NaC:
  - `agent/q3h-role-gate-issuer-normalization`
  - `agent/q3h-role-gate-issuer-claim-normalization`
  - `agent/q3j-server-side-oci-role-lookup`
- `www-n8`: keine bestätigten Cleanup-Kandidaten aus diesem Audit.
- `oci-landing-zone`: keine bestätigten Cleanup-Kandidaten aus diesem Audit.

Cleanup bleibt ein eigenes Owner Gate. Codex darf diese Branches nur listen und
den Gate-Text vorbereiten, aber nicht löschen.

## Naechste Fachtracks Als Gate-Kandidaten

Aktuell vorbereitete Fachtracks:

- Runtime/Login: PR #264 schließt eine Inkonsistenz zwischen Functions-Runtime
  und lokalem `nac-web` Serverpfad beim Session-Store.
- Notarkammer/XNP: PR #265 vertieft den Immobilienkaufvertrag als primären
  XNP-/XNotar-/Grundbuch-/Vollzug-Demofluss.

Neue Feature- oder Security-Grenzen brauchen weiterhin ein Owner Design Gate
vor Implementierungsstart.

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

Aktueller gebündelter Gate-Satz:

```text
Owner Review/Merge PR #264 und PR #265.

Owner Approval to delete merged/superseded NaC head branches
agent/q3h-role-gate-issuer-normalization,
agent/q3h-role-gate-issuer-claim-normalization and
agent/q3j-server-side-oci-role-lookup locally and remotely.
```

Release-Gates werden erst nach Merge mit konkretem Commit formuliert.

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
