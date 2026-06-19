# Agentic 8h Current Queue

> **Stand:** 19. Juni 2026. Diese Queue ersetzt nicht die allgemeinen
> Operating Rules aus `2026-06-18-agentic-8h-work-packages.md`, sondern
> aktualisiert die Arbeitslage nach den inzwischen geschlossenen Q2Q-Q2V- und
> Release-Lane-Tracks.

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

## Owner-freie Arbeitslanes

Diese Lanes dürfen vorbereitet werden, ohne beim Owner nachzufragen:

1. **Read-only Evidence**
   - GitHub PR-/Issue-/Branch-Status lesen.
   - OCI Status lesen, soweit keine Secrets gelesen und keine Writes ausgeführt
     werden.
   - Release-Lane Context und Release Memory gegen aktuelle Repos prüfen.

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

Diese Branches sind nach aktuellem Read-only-Audit merged und können als
Cleanup-Gate vorgeschlagen werden.

NaC:

```text
agent/178-q2t-session-store-adapter
agent/179-q2u-workspace-binding-normalizers
agent/181-q2v-onboarding-review-audit
agent/release-memory-parity-check
```

OCI Landing Zone:

```text
agent/93-owner-gate-text-normalizer
agent/release-memory-parity-check
```

`www-n8`: keine sichtbaren Cleanup-Branches.

## Naechste Fachtracks Als Gate-Kandidaten

### Track A: Session-Store Pflicht Für `/workspace`

Owner-Gate:

```text
Owner Design Approval for next Workspace/Auth Track A: make the server-side session-store mandatory for /workspace and every route beyond protected start; a signed cookie alone is no longer sufficient, missing/unavailable/revoked/expired store records fail closed, audit remains redacted metadata-only, no full workspace, no mandate data, no OCI writes.
```

Stop-Lines:

- Kein produktiver Store-Adapter.
- Kein Vault-/Secret-Zugriff.
- Keine OCI Runtime-Konfiguration.
- Keine Live-Session-Migration.

### Track B: Role/Case/Purpose Gate Audit Schärfen

Owner-Gate:

```text
Owner Design Approval for next Workspace/Auth Track B: formalize the /workspace role-case-purpose gate as a metadata-only authorization contract with explicit reason classes, optional four-eyes requirement, redacted audit evidence, and no exposure of tenant hints, case IDs, session IDs, claims, emails, provider details or mandate content; fail closed, protected PR, no OCI writes.
```

Stop-Lines:

- Keine echten Tenant- oder Akten-Lookups.
- Keine echten Vorgangskennungen in Browser oder Log.
- Keine produktiven IdP-Rollen- oder Gruppenveränderungen.

### Track C: Customer Status Nach Admin Review

Owner-Gate:

```text
Owner Design Approval for next Onboarding Track C: improve the customer-facing request status page after admin review using only existing request_status and invitation_status fields and customer-safe copy; show that review is documented and invitation remains pending; no customer mail dispatch, no mandate data, no internal provider or admin terminology.
```

Stop-Lines:

- Kein Kundenmailversand.
- Keine Einladung senden.
- Keine neuen Lifecycle-States ohne Contract.
- Keine internen Provider-/Admin-Begriffe in Customer-HTML.

## Gebündeltes Owner-Paket

Wenn alle owner-freien Lanes vorbereitet sind, soll der Owner nicht mit
Zwischenfragen unterbrochen werden. Stattdessen wird genau ein Paket geliefert:

```text
1. Branch-Cleanup-Gate mit exakter Branchliste.
2. Ein empfohlenes naechstes Owner-Design-Gate.
3. Optional Release-Gate nur für einen konkret geprüften Commit.
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
