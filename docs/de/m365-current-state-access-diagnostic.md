# Current-State-Diagnose für Teams- und BFF-Zugriff

## Stand vom 24. September 2026: Treiber-Release noch nicht bereit

Nach den dokumentierten Merges von [PR #749](https://github.com/notariat8/NaC/pull/749)
und [PR #751](https://github.com/notariat8/NaC/pull/751) ist die
Client-Receipt-Bedienkante vorhanden. Das erklärt die Teams-Meldung noch nicht:
Der neue [Read-only-Treiber-Entwurf](superpowers/specs/2026-09-23-m365-current-state-read-driver-design.md)
in Draft-PR #752 ist eine eigene Liefergrenze. Sein aktueller Quellvertrag
blockiert Microsoft-Zugriffe mit `BLOCKED_NO_REFRESH_CAPABILITY`, bevor das
einmalige Diagnose-Gate konsumiert wird. Ein Contract-Test oder eine
synthetische Diagnose ist weder ein gebautes Windows-Release noch ein realer
Providerbefund. Für `OFFLINE_REVIEWABLE` fehlen bis zur gesonderten Prüfung
insbesondere das vollständige Bundle, Source-/Runtime-/SBOM-/Lizenzbelege und
die geschlossene lokale Dateiattestation. `LIVE_CAPABLE` benötigt darüber
hinaus einen technisch bewiesenen No-Refresh-Kanal, vollständige Projektionen
und eigene exakt gebundene Freigaben für Treiber-Release und einen Read.

Die bestehenden CLI-Befehle erhalten keine freien URL-, Query-, Token- oder
Login-Optionen. Der verlorene #739-Lauf und #632 bleiben unberührt.

Historischer Status des ursprünglichen #749-Drafts: Repository- und synthetische Implementierung abgeschlossen; Merge, SPFx-Bereitstellung und realer Providerlauf waren jeweils separat freigabepflichtig. Für den aktuellen Stand gilt der datierte Abschnitt oben.

Die Diagnose untersucht ausschließlich den aktuellen lesbaren Zustand von
`notary_team_01` und der Teams-App „NaC Vorgangsansicht“. Sie ersetzt den
terminalen Issue-#739-Lauf nicht und autorisiert keine Issue-#632-Aktion.

## Bedienung

Voraussetzung für den ersten Schritt ist, dass die Receipt-fähige SPFx-Version
nach erfolgreicher PR-Abnahme separat freigegeben, im Test-App-Catalog
bereitgestellt und ihre Paket-/Source-Bindung read-only verifiziert wurde. Die
Repository-Implementierung oder die spätere Freigabe des Read-only-Laufs
autorisiert kein Deployment. Erst in der tatsächlich bereitgestellten neutralen
Ansicht „Kein Zugriff auf diesen Arbeitsbereich“ wird ausdrücklich
„Diagnosebeleg speichern“ gewählt.

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

Die committed Windows-Screenshots bleiben der visuell geprüfte Referenzbeleg.
Linux-CI erzeugt dieselben synthetischen Fälle in einem temporären
Runner-Verzeichnis und prüft Zustände, Überlauf, Receipt-Schaltfläche,
Bindungen sowie Null-Netzwerk- und Null-Autodownload-Grenzen. Plattformabhängige
Schrift- und PNG-Bytes werden nicht fälschlich als fachliche Gleichheit
behandelt.

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
Hardlink- und Hashbindung. Das Betriebssystem kann jedoch nicht allein
attestieren, welche HTTP-Methode dieser Treiber intern verwendet. Der reale
Lauf bleibt daher gesperrt, bis der konkrete Treiber als reviewbares,
versioniertes Release mit Source-Bindung, klassischer SBOM, Lizenz,
GET-only-Ressourcen-Allowlist sowie Null-Login-, Null-Refresh-,
Null-Redirect-, Null-Retry- und Null-Write-Vertrag separat freigegeben ist.
PR #749 liefert dieses Treiber-Release nicht. Eine Owner-Freigabe oder ein
Binärhash allein ersetzt diese Lieferketten- und Verhaltensprüfung nicht.

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

Der separate [Read-driver-Entwurf](superpowers/specs/2026-09-23-m365-current-state-read-driver-design.md)
besitzt eine rein lokale Build- und Prüfkante. `python
scripts/validate_m365_current_state_read_driver.py` prüft nur die eingecheckten
Verträge. Ein tatsächliches externes Paket muss zusätzlich mit `--candidate
<absoluter-pfad>` gegen den aktuellen Git-Commit, den Source-Archivinhalt,
sämtliche Bundle-Dateien, die Windows-Eigentümer-/DACL-Bindung sowie
CycloneDX-, SPDX- und Lizenzbelege geprüft werden. Ein bestandener Quelltest
ist kein Paketnachweis. Die Paketvorbereitung erzeugt nur
`AWAITING_INDEPENDENT_LICENSE_EVIDENCE`; erst ein separat geprüfter,
im Git-Tree gebundener [Lizenzkatalog](../../workflows/contracts/m365-current-state-read-driver-license-catalog.json)
mit Status `APPROVED` und geschützte externe Lizenzbelege erlauben die
Finalisierung. Syft-entdeckte Pakete und das vollständige Bundle-Dateimanifest
werden getrennt abgeglichen. In diesem Schritt wird kein neues Paket gebaut.
Der Produktionsport blockiert weiterhin mit
`BLOCKED_NO_REFRESH_CAPABILITY`; es gibt keine Freigabe für einen realen Read.

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
