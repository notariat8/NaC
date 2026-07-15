# M365 Azure BFF Live-Runner Implementierungsplan

**Datum:** 14. Juli 2026
**Aktivierungs-Issue:** [#632](https://github.com/notariat8/NaC/issues/632)
**Parent-Kontext:** [#620](https://github.com/notariat8/NaC/issues/620)
**AC-IDs:** `AC-632-01` bis `AC-632-08`
**Delivery Mode:** Protected PR
**Status:** `OFFLINE_READY`; Live-Runner und Live-Aktivierung sind noch nicht als `PASSED` nachgewiesen

## Ziel

Der Live-Runner setzt den bestehenden hashgebundenen
[Offline-Aktivierungsplan](../../../../workflows/contracts/m365-azure-bff-activation-plan.contract.json)
in genau zwölf Schritten um. Der
[Live-Runner-Vertrag](../../../../workflows/contracts/m365-azure-bff-live-activation.contract.json)
und der
[Verification-Vertrag](../../../../workflows/verification-contracts/m365-azure-bff-live-activation.verification.contract.yaml)
binden Freigabe, Commit, Tree, Targets, Rechte, Toolchain-Attestations,
globalen Lock, Ledger, hostweiten Success-Receipt und redigierte Evidence.
Resume ist für den MVP ausdrücklich deaktiviert, bis für
jeden Provider-Write und jedes Crash-Fenster eine providerspezifische
read-only Reconciliation implementiert und unabhängig geprüft ist. Eine
Offline-Readiness oder dieser Plan ist keine Live-Freigabe und kein
Erfolgsnachweis.

## Traceability

- `AC-632-01`: Exakter Owner-Login `ofunk` und unveränderlicher Approval-Snapshot aus Issue #632; Issue #620 bleibt Parent-Kontext.
- `AC-632-02`: Vollständige read-only Duplikat- und Rechteinventur vor dem ersten Provider-Write.
- `AC-632-03`: Ein hostweiter zielglobaler Lock blockiert konkurrierende Läufe aus allen Worktrees und Klonen auf dem einzelnen Ausführungshost unabhängig von Output-Pfad, Aktivierungs-Hash oder Correlation-ID; eine hostübergreifende Koordination ist nicht enthalten.
- `AC-632-04`: Function-Paket, site-scoped SPFx-Paket und Bicep-Snapshot sind vor dem finalen Git-/Plan-Gate gebaut und hashgebunden; der auf die erzeugte oder wiederverwendete Entra-App-ID aufgelöste Parameter-Snapshot und das vollständige Manifest werden nach dem exakten Step-3-Readback und vor dem Bicep-Write atomar gebunden.
- `AC-632-05`: Entra, UAMI, `Sites.Selected`, Site-`read`, site-scoped SPFx und `Matter.Read` werden exakt angelegt oder wiederverwendet und zurückgelesen.
- `AC-632-06`: `healthz` läuft vor Auth, `readyz` erst nach authentifiziertem Read; Deny-/Manipulationsfälle schließen fail-closed und PASSED erfordert die verifizierte Wiederherstellung des synthetischen Ausgangszustands. Bei Prozessabbruch vor diesem Nachweis bleibt der Lauf ohne Erfolg und benötigt read-only Reconciliation plus manuelle Wiederherstellung; eine SIGKILL-Wiederherstellung wird nicht behauptet.
- `AC-632-07`: Ledger und Evidence sind hashverkettet, redigiert und durch exakte Feld-Allowlists begrenzt.
- `AC-632-08`: Der erste Teilfehler stoppt den Lauf; Resume bleibt für den MVP deaktiviert.

## Exakte Bindung

| Ziel | Exakter Wert |
|---|---|
| Aktivierungs-Hash | Exakter 64-stelliger Lowercase-SHA-256 aus dem Offline-Plan des finalen sauberen und freigegebenen Commits; Pflichtwert des Owner-Gates |
| Toolchain-Attestations-Hash | Exakter 64-stelliger Lowercase-SHA-256 über die acht nicht-geheimen Ausführungs-Digests für Azure-CLI-Toolchain, M365-Runtime-Vollbaum, M365 Node, Build Python, Build Node, Build-NPM-Runtime-Vollbaum, die fest gepinnte GitHub CLI und das öffentliche Provisioning-Zertifikat; Pflichtwert desselben Owner-Gates |
| Tenant | `870c862b-56f7-4c9b-b0d9-f1f7d32c835c` |
| Subscription | `37cd9645-6cb9-4278-88ee-e80377cd951c` |
| Workspace | `notary_team_01` |
| Site | `https://funktion8.sharepoint.com/sites/NaC-Notar-01` |
| Site-ID | `funktion8.sharepoint.com,31324d31-3074-4f1c-ba45-3b3fd5f5ce97,56fc9349-e123-4252-ae2a-05d5d61c9b38` |
| Team | `NaC-Notar-01` / `124f1b11-207d-4307-bfd1-ac0fd73aa90a` |
| CLI-Test-Client | `c86dded6-9723-4b8d-91f2-e0fd70e25839`, nur für delegierte Allow-/Deny-Live-Verifikation |
| Listen | `Akten=588d4a41-f538-4f37-acfb-63ff283e0910`, `AufgabenFristen=720ef1d4-8496-4ecb-aa1f-5fa4568343f2`, `Vertretungsfreigaben=ec12d339-d9b7-45e9-be45-38dadd917746`, `AuditJournalLite=327181c2-e402-48e9-bcfa-1f5081b45d9c` |
| App Catalog | Tenant-Katalog auf `funktion8.sharepoint.com`, exakt eine Lösung mit `ProductId=b7a5417c-0dd3-4e69-87c7-95adfd7e8a58`; die Record-ID wird read-only eindeutig aufgelöst und geprüft |
| SPFx-Lösung | `nac-bpmn-viewer-client-side-solution`, Version `0.2.0.0`, site-scoped, `skipFeatureDeployment=false` |
| Seite | `NaC-Testumgebung.aspx`, Titel `NaC-Testumgebung`, Layout `Article` |
| Webpart | `NacBpmnViewerWebPart` / `3a7bba0c-f8c4-41d6-9ec9-f8a3f7e6fa21` |
| Synthetische Akte | `NAC-SYN-MATTER-001`, Typ `immobilienkaufvertrag`, Zweck `view_synthetic_matter_workspace` |

Die App-Catalog-Record-ID wird nicht erfunden oder dauerhaft im Repository
gespeichert. Eindeutige `ProductId`-Auflösung, UUID-Prüfung und Readback binden
genau den zulässigen Katalogeintrag. Null Treffer erlauben das Anlegen; mehr
als ein Treffer stoppt den Lauf.

## Ein konsolidiertes Owner-Gate

Der Runner akzeptiert genau eine Owner-Freigabe. Ein unveränderlich gebundener
Snapshot eines Kommentars des exakten GitHub-Logins `ofunk` in Issue #632 muss exakt folgende Felder
enthalten:

```json
{
  "owner-approved": true,
  "expected_activation_sha256": "<64 lowercase hex from the final clean approved commit>",
  "approved_commit_sha": "<40 lowercase hex>",
  "approved_tree_sha": "<40 lowercase hex>",
  "toolchain_attestations_sha256": "<64 lowercase hex>",
  "target_binding_sha256": "<64 lowercase hex>",
  "permission_boundary_sha256": "<64 lowercase hex>",
  "step_sequence_sha256": "<64 lowercase hex>",
  "no_automatic_rollback_or_deletion": true
}
```

Der Runner bindet URL, Comment-Datenbank-ID, Autor, Erstellungszeit und
Body-SHA-256. `updatedAt` muss `createdAt` entsprechen. Die Freigabe darf nicht
für einen anderen Hash, Commit, Tree, Zielstand, Rechteumfang oder eine andere
Toolchain wiederverwendet werden. Es gibt keine zusätzlichen stillen oder
schrittweisen Freigaben.

Der Runner erhält die acht Einzel-Digests über separate erforderliche CLI-
Argumente, berechnet daraus den kombinierten Hash und vergleicht ihn mit dem
einzigen Toolchain-Feld im Approval-Payload.

`toolchain_attestations_sha256` ist der Lowercase-SHA-256 über ein UTF-8-
kodiertes kanonisches JSON-Objekt mit exakt den Feldern
`azure_cli_toolchain_sha256`, `m365_cli_sha256`, `m365_node_sha256`,
`build_python_sha256`, `build_node_sha256`, `build_npm_cli_sha256`, `gh_cli_sha256` und `provisioner_certificate_sha256`. Der letzte Wert bindet ausschließlich das öffentliche Zertifikat; Private-Key-Inhalt und -Digest bleiben ausgeschlossen. Jeder Einzelwert ist ein
64-stelliger Lowercase-SHA-256 und nicht geheim; die Keys werden sortiert,
kompakte Separatoren und genau ein abschließender Zeilenumbruch verwendet. Ändert
sich ein Einzelwert oder der kombinierte Hash, ist eine neue konsolidierte
Owner-Freigabe erforderlich. Abschluss-Evidence und hostweiter Success-Receipt
müssen denselben kombinierten Hash enthalten, sonst ist `PASSED` gesperrt.

Unmittelbar vor jedem lokalen Python- oder Node-Prozess werden ausführbare
Bytes über genau einen `O_NOFOLLOW`-/`fstat`-/SHA-256-geprüften Lesezugriff
in versiegelte Linux-`memfd`-Dateien kopiert. `m365_cli_sha256` und
`build_npm_cli_sha256` binden nicht nur Einstiegsskripte, sondern
deterministische Vollbaum-Manifeste der jeweiligen Runtime-Module; ausgenommen
sind ausschließlich npm-generierte `node_modules/.bin`-Kommandoshims, die
nicht als Module geladen werden dürfen. Versiegelte CommonJS-/ESM-Loader
verwerfen unbekannte, veränderte, verlinkte oder native Module und kompilieren
beziehungsweise evaluieren nur die bei jedem Ladevorgang erneut mit
`O_NOFOLLOW`, `fstat` und SHA-256 geprüften exakten Bytes.
Der Aktivierungs-Hash wird erst nach Vorliegen des finalen Commits erzeugt,
weil der Offline-Plan Commit und Live-Runner-Artefakte selbst bindet; ein im
selben Commit fest codierter Ergebnis-Hash wäre zirkulär und ist unzulässig.

## Pre-Write-Gate

Vor der ersten Schreibaktion wird in dieser Reihenfolge geprüft:

1. Approval-Snapshot, Azure-/M365-Session und alle exakten Zielwerte read-only prüfen.
2. Eine vollständige read-only Inventur aller Entra-App-/Service-Principal-, UAMI-Rollen-, Site-Grant-, App-Catalog-, SPFx-Permission-/Install-, Seiten-/Webpart- und synthetischen Schlüssel-Treffer ausführen; Duplikate und breitere Rechte vor jedem möglichen Write ausschließen.
3. Den zielglobalen, nicht blockierenden Lock für Tenant, Subscription und Workspace unabhängig von Output-Pfad, Aktivierungs-Hash und Correlation-ID erwerben.
4. Ausschließlich ein neues Ledger initialisieren; bestehende oder partielle Läufe sind im MVP nicht fortsetzbar.
5. Function-OneDeploy-Paket, site-scoped `.sppkg`, unveränderlichen Bicep-Snapshot und aufgelösten Bicep-Parameter-Snapshot vorbauen, hashen und an Commit, Tree sowie Aktivierungs-Hash binden.
6. Leeren Output von `git status --porcelain=v1 --untracked-files=all` verlangen.
7. `HEAD` und `HEAD^{tree}` mit freigegebenem Commit und Tree vergleichen.
8. Offline-Plan erneut erzeugen und `READY` plus erwarteten Aktivierungs-Hash prüfen.
9. Den Hash ein zweites und letztes Mal unmittelbar vor dem ersten Write berechnen.
10. `PRE_WRITE_BINDING` atomar schreiben und fsyncen, Git-Status nochmals prüfen und ohne dazwischenliegende Repo- oder Planänderung den ersten allowlisteten Write ausführen.

Jede Abweichung stoppt mit null Writes. Tracked Änderungen, untracked Dateien,
Submodule-Drift, falsche Targets, Hash-Abweichung oder ein belegter Lock sind
nicht automatisch reparierbar.

## Ausführung und Rechte

Die zwölf Schritte bleiben in der Reihenfolge des Offline-Plans:

1. drei Azure-Provider registrieren,
2. die exakte Resource Group anlegen oder wiederverwenden,
3. genau eine Single-Tenant-Entra-API mit `Matter.Read` und Token-Version 2 anlegen oder wiederverwenden,
4. die hashgebundene Bicep-Baseline mit der read-back-geprüften API-`appId` bereitstellen,
5. der UAMI ausschließlich `Sites.Selected` zuweisen,
6. ausschließlich `read` auf der exakten Site erteilen,
7. die vorgebauten und hashgebundenen Function-Paketbytes per Flex OneDeploy mit `--build-remote true` bereitstellen,
8. die vorgebauten und hashgebundenen site-scoped `.sppkg`-Bytes ohne Live-Rebuild bereitstellen,
9. ausschließlich `NaC M365 BFF/Matter.Read` für SPFx genehmigen,
10. nur die kanonische synthetische Akte und ihre Datensätze anlegen oder exakt wiederverwenden,
11. `healthz` vor Auth prüfen, authentifizierte Allow-/Deny-/Manipulations-Readbacks ausführen, den erfassten synthetischen Assigned-Ausgangszustand deterministisch wiederherstellen, erneut authentifiziert lesen und erst danach `readyz` prüfen,
12. read-only Konvergenz, Duplikatfreiheit, kausale Deployment-Input-Bindung, Ledger und Evidence abschließen; ein erneutes Abspielen der Provider-Writes wird nicht behauptet.

Microsoft-Graph-Zugriffe verwenden ausschließlich rohe REST-Aufrufe gegen
`https://graph.microsoft.com/v1.0`. Graph beta, SDKs, PnP und alte
SharePoint-APIs bleiben gesperrt. Azure Resource Manager und die bereits
dokumentierte M365-CLI-Control-Plane-Kante werden nur über argv-Allowlisten
ohne Shell ausgeführt. Die UAMI darf genau `Sites.Selected`, der Site-Grant
genau `read` und SPFx genau den delegierten BFF-Scope `Matter.Read` besitzen.

## Ledger, Fehler und gesperrtes Resume

Die einzigen Laufzustände sind `OFFLINE_READY`, `LIVE_APPROVED`,
`FAILED_PARTIAL` und `PASSED`. Jeder Schritt schreibt append-only,
hashverkettete, atomar umbenannte und gefsyncte redigierte Events. Provider-
Write und lokales Ledger werden nicht fälschlich als verteilte Transaktion
dargestellt. Ein Crash-Fenster bleibt `FAILED_PARTIAL`; es wird im MVP nicht
automatisch abgeglichen oder fortgesetzt.

Der erste Fehler stoppt alle Folgeschritte. Nach mindestens einem Write wird
der Zustand `FAILED_PARTIAL`. Es gibt keinen automatischen Rollback und keine
automatische Löschung, Deinstallation, Retraktion, Berechtigungsabsenkung oder
Restebereinigung. Die gebundene Wiederherstellung des temporär veränderten
synthetischen Testzustands ist Teil von Schritt 11 und kein Provider-Rollback.
`--resume` wird nicht angeboten. Jeder Resume-Versuch stoppt vor Lock,
Provider-Read und Provider-Write mit `RESUME_DISABLED_FOR_MVP`. Eine spätere
Freischaltung braucht providerspezifische read-only Reconciliation für jeden
Write-Schritt und jedes Crash-Fenster sowie eine unabhängige Prüfung. Ein
unklarer Providerzustand bleibt `FAILED_PARTIAL` und braucht eine neue
menschliche Entscheidung.

## Evidence und Negativtests

Die lokale Hashkette und der Success-Receipt erkennen versehentliche oder konkurrierende Manipulationen, sind aber gegenüber demselben kontrollierten OS-Benutzer nicht kryptografisch authentisch. Dieser synthetische MVP erhebt deshalb keinen formalen revisions- oder beweissicheren Audit-Anspruch; dafür ist später eine separat freizugebende externe unveränderliche Ablage oder Signatur-Lane erforderlich.

Die Abschluss-Evidence folgt einer strikten Feld-Allowlist. Sie enthält nur
Status, Zeitpunkte, Hashbindungen einschließlich
`toolchain_attestations_sha256`, stabile Fehlercodes, HTTP-Status und
gehashte Request-, Response- und Ressourcenreferenzen. Raw-IDs, URLs,
Graph-Pfade, Commands, Providerantworten, stdout/stderr, Header, Tokens,
Cookies, Credentials, Zertifikate, Umgebungswerte sowie Personen-, Mandats-,
Dokument- oder Produktivdaten sind verboten. Unbekannte Felder invalidieren
das Artefakt.

Auch `summary` besitzt eine exakte Allowlist: `required_step_count`,
`passed_step_count`, `failed_step_count`, `duplicate_count`,
`broader_permission_count`, `automatic_rollback_count`,
`automatic_deletion_count`, `writes_started`, `ledger_hash_chain_valid`,
`prebuilt_inputs_verified`, `healthz_before_auth_passed`,
`authenticated_read_passed`, `readyz_after_authenticated_read_passed`,
`synthetic_state_restored` und `resume_enabled`. Für `PASSED` müssen die
Probe-/Restore-Felder `true` und `resume_enabled` muss `false` sein.

Verpflichtende Negativtests decken falschen Hash, dirty Tree, falsches Target,
Duplikate, breitere Rechte, zwei konkurrierende Runner, Secret-Sentinel-Leaks,
Fehler nach dem ersten Write, falsche Probe-Reihenfolge, fehlgeschlagene
synthetische Wiederherstellung und jeden Resume-Versuch ab. Jeder
Pre-Write-Fall beweist null Writes; jeder Partial-Fall beweist Stop-on-first-
error sowie null automatische Rollbacks und Löschungen.

## Implementierungsreihenfolge

1. CLI-Argumente, exakten Owner-Login `ofunk`, Approval-Snapshot-Prüfung und Commit-/Tree-/Hash-Gate implementieren.
2. Zielglobalen Lock und atomaren, hashverketteten Ledger implementieren.
3. Azure-, Entra-, Graph-REST-v1.0- und M365-CLI-Adapter strikt allowlisten und redigieren.
4. Vollständige Pre-Write-Inventur, vorgebaute hashgebundene Pakete/Bicep-Snapshots und zwölf Schritte mit eindeutiger Read-before-write-Klassifikation und Readback implementieren.
5. `healthz`-vor-Auth, authentifizierten Read, `readyz`-danach und deterministische synthetische Zustandswiederherstellung implementieren; MVP-Resume fail-closed deaktivieren.
6. Evidence-Allowlist und alle Negativtests implementieren.
7. Fokussierte Tests, Contract-Verifikation, Spec-Traceability, Sprachparität, Linkprüfung, Strict-Gate und Protected-PR-Checks ausführen.

`PASSED` darf erst ausgegeben werden, wenn alle zwölf Schritte genau für die
gebundenen Ziele bestanden haben, die Rechte exakt sind, keine Duplikate
existieren, Ledger und Evidence valide sind und kein automatischer Rollback
oder Delete stattgefunden hat.
