# Windows Light Runner – Design-Spec

Status: Design freigegeben, Implementierung ausstehend
Letzte Änderung: 2026-08-09
Führendes Issue: (wird mit Implementierung verlinkt)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: windows-light-runner
leading_issue: https://github.com/notariat8/NaC/issues/632
risk_gate: Security
delivery_mode: Protected PR
review_gates:
  - Security
  - Platform
  - Human Approval
acceptance_ids:
  - AC-WLR-01
  - AC-WLR-02
  - AC-WLR-03
  - AC-WLR-04
  - AC-WLR-05
  - AC-WLR-06
validation_commands:
  - python scripts/validate_m365_azure_bff_live_activation.py
  - python scripts/nac.py doctor --profile strict
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_governance_sync.py
```

## Zweck

Den NaC M365 BFF Live Activation Runner von Linux-exklusiver Härtung
(`memfd`, Mount-Namespaces, `O_NOFOLLOW`) auf Windows-nativen Betrieb
umstellen. Gleiches Sicherheitsniveau für den Single-Operator-Notariatsarbeitsplatz
unter Windows 11, ohne WSL-Abhängigkeit.

## Scope

- `nac m365 teams-sharepoint bff-azure-activate-live` wird unter Windows
  nativ ausführbar
- Alle 12 Aktivierungsschritte bleiben erhalten
- Toolchain-Attestationen (`bff-azure-activation-attestations`) erhalten
  Windows-Pfade
- Owner-Gate (`bff-azure-activation-owner-gate`) unverändert
- Approval-Flow (GitHub Issue-Kommentar) unverändert
- Ledger, Evidence, Lock-Journal unverändert

## Randbedingungen

- Betriebssystem: Windows 11 (wie in `docs/de/minimum-requirements.md` für
  `base`-Profil spezifiziert)
- `az` CLI und `m365` CLI als native Windows-Installationen
- Keine WSL, kein Docker, kein Container erforderlich
- Single-Operator-Maschine – kein Multi-Tenant-Bedrohungsmodell
- Die gehärteten Linux-Features (`memfd`, private mount namespaces) werden
  durch Windows-Bordmittel ersetzt, nicht 1:1 emuliert

## Design-Entscheidungen

### 1. Binary-Verifikation statt memfd

**Linux (alt):** Az-CLI-Binary via `memfd_create()` versiegelt im RAM laden,
kein Dateisystem-Pfad angreifbar.

**Windows (neu):**
1. SHA-256 des Binary VOR Subprocess-Start berechnen
2. Binary auf NTFS mit Owner-only-Berechtigung (`icacls` / `SetFileSecurity`)
3. Atomic-Copy: Binary in temp-Ordner kopieren, Handle via `CreateFile` mit
   `FILE_SHARE_READ` aber ohne `FILE_SHARE_WRITE|DELETE` öffnen
4. SHA-256 des geöffneten Handle gegen Attestation prüfen
5. Subprocess aus diesem Handle starten

**Begründung:** Auf einem Single-Operator-Rechner ist die Binary-Manipulation
durch Fremdprozesse kein realistisches Bedrohungsszenario. Die Handle-basierte
Verifikation stellt sicher, dass zwischen SHA-Check und Prozessstart kein
Austausch stattfindet.

### 2. Job Objects statt Mount-Namespaces

**Linux (alt):** Az-CLI läuft in privatem Mount-Namespace mit isoliertem
Schein-Dateisystem.

**Windows (neu):**
1. Job Object mit `JOB_OBJECT_LIMIT_ACTIVE_PROCESS` = 1 erzeugen
2. Umgebungsvariablen-Allowlist vor Subprocess-Start (nur `PATH`,
   `SYSTEMROOT`, `AZURE_CONFIG_DIR`, `CLIMICROSOFT365_*`)
3. Subprocess im Job Object starten
4. Keine Dateisystem-Isolation – nicht erforderlich, da der Operator
   ohnehin Vollzugriff hat und keine fremden Prozesse isoliert werden müssen

**Begründung:** Mount-Namespaces schützen vor Dateisystem-basierten
Angriffen durch Co-Tenant-Prozesse. Auf einem Single-Operator-Rechner
existiert dieses Bedrohungsmodell nicht. Ein Job Object genügt für
Prozess-Lebenszyklus-Kontrolle.

### 3. Lock per Windows-Mutex

**Linux (alt):** `fcntl`-basiertes Datei-Lock mit append-only Journal.

**Windows (neu):**
1. Globaler Windows-Mutex via `CreateMutexW` unter
   `Local\nac-m365-bff-live-activation-{target-binding-sha256}`
2. Lock-Journal als append-only JSON-Datei – unverändert zum Linux-Modell
3. `AbandonedMutex`-Erkennung für Crash-Fenster (Windows-eigenes Feature)

**Begründung:** Windows-Kernel-Mutexe sind robuster als Datei-Locks bei
Prozess-Abstürzen. Das Journal bleibt als Audit-Trail erhalten.

### 4. Kein O_NOFOLLOW-Ersatz nötig

**Begründung:** Windows-Symlinks erfordern Administrator-Rechte
(`SeCreateSymbolicLinkPrivilege`). Der Operator-Arbeitsplatz hat keine
fremden Prozesse, die Symlinks anlegen könnten. Pfad-Kanonisierung
(`GetFinalPathNameByHandle`) vor jedem Start genügt.

## Risiken

| Risiko | Eintrittsbedingung | Maßnahme |
|---|---|---|
| Binary-Manipulation zwischen SHA-Check und Start | Zweiter Prozess mit Admin-Rechten auf dem Rechner | Handle-basierte Verifikation; Admin-Rechte auf Notariats-Workstation nur für Installation |
| Umgebungsvariablen-Leak | `az`/`m365`-CLI lesen sensitive Variablen | Allowlist vor Subprocess |
| Concurrent Activation | Zwei `nac`-Instanzen gleichzeitig | Globaler Windows-Mutex |
| NTFS-Berechtigungen nicht gesetzt | Operator hat `icacls` nicht ausgeführt | Validator prüft vor erstem Write |

## Akzeptanzkriterien

| ID | Kriterium | Validierung |
|---|---|---|
| AC-WLR-01 | `nac m365 teams-sharepoint bff-azure-activate-live` läuft unter Windows 11 ohne WSL | Manueller Lauf auf Windows-Notariatsarbeitsplatz |
| AC-WLR-02 | Alle 12 Aktivierungsschritte werden ausgeführt und produzieren identische Ledger-Events wie Linux (bis auf Plattform-spezifische Felder) | Ledger-Vergleich mit Linux-Referenzlauf |
| AC-WLR-03 | Toolchain-Attestationen berechnen SHA-256 von Windows-Installationspfaden | `bff-azure-activation-attestations --format json` → status=READY |
| AC-WLR-04 | `validate_m365_azure_bff_live_activation.py` PASSED | Validator-Lauf |
| AC-WLR-05 | Contract: `linux_memfd_and_proc_fd_required` = `false`, `azure_cli_private_user_and_mount_namespace_required` = `false` | Contract-File-Diff |
| AC-WLR-06 | `nac doctor --profile strict` PASSED | Doctor-Lauf nach Implementierung |

## Nicht-Ziele

- Kein 1:1-Emulation von Linux-Kernel-Features auf Windows
- Kein Container/Docker/WSL2 als Laufzeitumgebung
- Keine Änderung der 12 Aktivierungsschritte oder ihrer Reihenfolge
- Kein Verzicht auf Hash-Bindings oder Owner-Gate
- Kein Support für Multi-Tenant-Bedrohungsmodell

## Verwandte Artefakte

- `workflows/contracts/m365-azure-bff-live-activation.contract.json`
- `docs/de/minimum-requirements.md`
- `policies/technology-policy.yaml`