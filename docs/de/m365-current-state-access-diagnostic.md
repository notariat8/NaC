# Current-State-Diagnose für Teams- und BFF-Zugriff

Status: Repository- und synthetische Implementierung für Issue #748 in Arbeit; Abnahme und realer Providerlauf separat gesperrt

Die Diagnose untersucht ausschließlich den aktuellen lesbaren Zustand von
`notary_team_01` und der Teams-App „NaC Vorgangsansicht“. Sie ersetzt den
terminalen Issue-#739-Lauf nicht und autorisiert keine Issue-#632-Aktion.

## Bedienung

Vor dem Preflight wird der ausdrücklich im SPFx-Webpart ausgelöste Download
lokal und ohne Providerzugriff materialisiert. Der Beleg enthält ausschließlich
den neutralen UI-Zustand, den Subject-Boolean, ein geschlossenes UTC-Fenster
sowie Fenster- und Korrelationsbindings:

```powershell
python scripts/nac.py m365 teams-sharepoint current-state-access-client-receipt-stage `
  --current-state-access-client-receipt C:\Downloads\nac-issue748-client-observation.json `
  --current-state-access-input-root C:\geschützt\issue748\input `
  --format json
```

Der Befehl prüft exakt `end_utc`,
`request_correlation_binding_sha256`, `spfx_subject_available`, `start_utc`,
`ui_state` und `window_binding_sha256`. `ui_state` muss `no_access` sein; das
geschlossene UTC-Fenster muss positiv und höchstens 15 Minuten lang sein.
Anschließend erstellt der Befehl
`client-observation-receipt.json` exklusiv. Ein vorhandener Beleg wird nicht
überschrieben. Login, Netzwerk, Provider und Deployment bleiben unberührt.

Der lokale Preflight erhält nur zwei absolute, repository-externe und über das
Windows-Sicherheitsbackend geschützte Verzeichnisse:

- Das Eingabeverzeichnis enthält die geschlossenen, hashgebundenen Vertrags-,
  Resolver-, Ziel-, Client-, Toolchain- und Owner-Belege. Der AVV-Receipt
  bindet zusätzlich einen getrennten geschützten AVV-Vertragsbeleg sowie den
  frisch gemessenen Repository-Blob
  `policies/data-protection-policy.yaml`. Selbst behauptete Status- oder
  Digestwerte genügen nicht.
- Das Evidence-Verzeichnis nimmt ausschließlich den einmaligen Consume-Marker
  und das redigierte Endergebnis auf.

Das geschützte `toolchain.json` bindet zusätzlich den absoluten Pfad und den
SHA-256-Wert eines repository-externen Read-only-Treibers. Vor jeder Ausführung
prüft das Windows-Sicherheitsbackend dessen Owner-, DACL-, Reparse-, Datei-ID-,
Hardlink- und Hashbindung. Der Treiber akzeptiert nur die fest definierten
Gate- und Diagnoseoperationen, läuft mit bereinigter Umgebung,
Credential-Schreibschutz, begrenzter Ausgabe und ohne Retry. Eine
Owner-Freigabe allein ersetzt diese technische Attestierung nicht.

```powershell
python scripts/nac.py m365 teams-sharepoint current-state-access-diagnostic-preflight `
  --current-state-access-input-root C:\geschützt\issue748\input `
  --current-state-access-evidence-root C:\geschützt\issue748\evidence `
  --format json
```

Der spätere reale Lauf verwendet dieselben Pfadargumente:

```powershell
python scripts/nac.py m365 teams-sharepoint current-state-access-diagnostic-run-read-only `
  --current-state-access-input-root C:\geschützt\issue748\input `
  --current-state-access-evidence-root C:\geschützt\issue748\evidence `
  --format json
```

Ohne neue, final gebundene Owner-Freigabe bleibt der zweite Befehl mit einem
redigierten `BLOCKED`-Ergebnis gesperrt. Es gibt keine CLI-Argumente für
Tenant-, Account-, Principal-, Team-, Site-, Function- oder Korrelationswerte
und keine Login-, Retry-, Force-, Redirect-, Deployment- oder Write-Option.

## Ergebnis

Nur zwei unabhängige, kanonisch identische und redigierte Erhebungen dürfen
genau eine dieser Klassen erzeugen:

- `SPFX_SUBJECT_MISSING`;
- `BFF_REQUEST_NOT_OBSERVED`;
- `BFF_AUTHENTICATION_REJECTED_401`;
- `BFF_AUTHORIZATION_REJECTED_403`.

Jede Abweichung blockiert ohne Retry. Das Ergebnis erlaubt nur einen neuen
Fixplan, keine produktive Änderung.

## Sicherheitsgrenze

- Autorisierung vor Port-Factory und erneut vor jedem Read;
- sieben geschlossene Ports, keine allgemeine Provider- oder Suchschnittstelle;
- keine Token-, Header-, Credential- oder Cache-Inhalte in Evidence;
- kein Login, Refresh, Credential-Write, Redirect oder Retry;
- genau ein geschützter lokaler Evidence-Sink;
- ohne konkret zitierte anwendbare Zwei-Personen-Pflicht ist
  `OWNER_SOLO_APPROVAL` zulässig und keine Vier-Augen-Freigabe;
- verlangt eine konkret zitierte anwendbare Pflicht zwei natürliche Personen,
  blockiert ein einzelner Principal mit `BLOCKED_SINGLE_PRINCIPAL`;
- verschiedene Accounts desselben Principals erweitern keine Berechtigung;
- #739 und #632 bleiben terminal beziehungsweise unberührt.

Verbindlich sind die [Spec](superpowers/specs/2026-09-20-m365-current-state-access-diagnostic-design.md),
der [Plan](superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md)
und der [Verification Contract](../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml).
