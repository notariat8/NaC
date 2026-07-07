# Microsoft-365-CLI-Admin-Beschleuniger

Status: Owner-gated Admin-Runbook
Letzte inhaltliche Anpassung: 2026-07-06

## Zweck

Dieses Runbook erlaubt die CLI for Microsoft 365 als Bedienhülle für
Tenant-Setup, Entra-App-Bootstrap und Graph-Smoke-Tests. Sie ist kein
Produktivbestandteil der NaC-Runtime und ersetzt nicht den Python-basierten
Graph-REST-Provisioner.

Die Produktregel bleibt: Datenoperationen für die Teams-SharePoint-Datenebene
laufen nur über Microsoft Graph REST v1.0 oder über MCP-Server, die intern
ebenfalls nur Microsoft Graph REST v1.0 verwenden.

## Installation

```bash
npm install -g @pnp/cli-microsoft365
m365 version
```

Alternativ kann die CLI in einem Container laufen. Für reproduzierbare
Provisioning-Läufe wird die verwendete Version im Laufprotokoll festgehalten.

## Anmeldung

Für interaktive Admin-Arbeit ist Device Code der Standard, weil kein Kennwort
oder geheimer Wert in Shell-History, Chat oder Repo abgelegt werden muss.

Wichtig: Die CLI kann Entra-App-Registrierungen anlegen. Dafür braucht sie aber
zuerst selbst eine gültige Authentifizierung gegen den Tenant. Es gibt deshalb
zwei verschiedene App-Ebenen:

| Ebene | Zweck | Wie entsteht sie |
| --- | --- | --- |
| CLI-Entra-App | Die CLI meldet sich damit am Tenant an. | Entweder über `m365 setup` oder über eine vorhandene App-Registrierung. |
| NaC-Bootstrap-/Runtime-App | NaC nutzt sie später für Provisioning oder Runtime-Zugriff. | Nach erfolgreichem CLI-Login per `m365 entra app add` oder Graph REST. |

Die CLI ist also gerade dafür nützlich, App-Registrierungen, Graph-Smokes und
Tenant-Konfiguration reproduzierbar zu steuern. Sie löst nur den ersten
Identitätsanker nicht magisch ohne irgendeine Admin-Authentifizierung.

### Bootstrap-Route A: CLI-App durch `m365 setup`

`m365 setup` kann eine neue App-Registrierung für die CLI konfigurieren. Laut
CLI-Dokumentation nutzt dieser Pfad Azure CLI Login, erstellt dann die
App-Registrierung und speichert die Informationen in der CLI-Konfiguration.

Links:

- [CLI for Microsoft 365 setup](https://pnp.github.io/cli-microsoft365/cmd/setup/)
- [Azure CLI authentication](https://learn.microsoft.com/de-de/cli/azure/authenticate-azure-cli?view=azure-cli-latest)

Sichtbare Kommandos:

```bash
az login --tenant "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
m365 setup
```

Diese Route ist in der aktuellen Codex-Umgebung nur eingeschränkt möglich,
weil `az` hier nicht installiert ist und Host-Paketinstallation blockiert ist.
Auf einem Admin-Arbeitsplatz oder in Azure Cloud Shell ist sie der sauberste
Bootstrap-Pfad.

### Bootstrap-Route B: vorhandene CLI-App verwenden

```bash
m365 setup
m365 login --appId "<cli-entra-app-id>" --tenant "<tenant-id>" --authType deviceCode
m365 status
```

Der Login muss durch einen Tenant-Admin im Browser abgeschlossen werden. Die CLI
zeigt dafür eine Microsoft-Device-Login-URL und einen einmaligen Code an.
`<cli-entra-app-id>` ist die Entra-App, die die CLI selbst für interaktive
Admin-Arbeit nutzt. Sie ist nicht identisch mit der späteren NaC-Runtime-App.

### Nach Login: NaC-App per CLI anlegen

Nach erfolgreichem CLI-Login kann die CLI die eigentlichen NaC-App-
Registrierungen anlegen:

```bash
m365 entra app add --name "NaC Graph Bootstrap" --certificateFile "<public-certificate.cer>" --apisApplication "https://graph.microsoft.com/Team.Create,https://graph.microsoft.com/Sites.Manage.All" --grantAdminConsent
```

Dieser Schritt ändert Tenant-Zustand und bleibt deshalb separat owner-gated.

## Pflicht-Handoff Vor Nutzeraktion

Bevor der Agent Werte vom Owner anfordert oder eine Aktion im Microsoft-Tenant
braucht, muss er ein vorbereitetes Handoff liefern. Eine nackte Bitte wie
`tenant-id und app-id senden` ist nicht zulässig.

Das Handoff enthält mindestens:

| Abschnitt | Pflichtinhalt |
| --- | --- |
| Zweck und Risiko | Warum die Aktion nötig ist und ob sie nur liest oder Tenant-Zustand ändern kann. |
| Exakte Werte oder Aktionen | Konkrete Feldnamen, erwartetes Format und welche Werte nicht in den Chat gehören. |
| Quelllinks | Direkte Links zu Microsoft Entra, Device Login und relevanter Dokumentation. |
| Copy-Paste-Kommandos | Kommandos mit Platzhaltern, die vor Ausführung sichtbar sind. |
| Secret-Behandlung | Secrets, Zertifikate und Tokens werden nicht im Chat oder Repo abgelegt. |
| Owner-Gate und Stop-Bedingung | Was ohne ausdrückliche Freigabe nicht passiert. |
| Nächster Schritt | Was der Agent nach der Owner-Aktion konkret ausführt. |

Vorbereiteter Login-Handoff für diesen MVP:

| Benötigt | Wo finden | Kommentar |
| --- | --- | --- |
| Tenant ID | [Microsoft Entra Admin Center: Tenant Overview](https://entra.microsoft.com/#view/Microsoft_AAD_IAM/TenantOverview.ReactView) | Kein Secret, aber tenant-spezifischer Identifier. |
| CLI Entra App ID | [Microsoft Entra Admin Center: App registrations](https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) | App für CLI-Login, nicht die spätere NaC-Runtime-App. |
| Device-Code-Bestätigung | [Microsoft Device Login](https://microsoft.com/devicelogin) | Nur nach Start des Kommandos nötig. |
| CLI-Login-Doku | [CLI for Microsoft 365 login](https://pnp.github.io/cli-microsoft365/cmd/login/) | Referenz für `--appId`, `--tenant` und `--authType deviceCode`. |

Der Agent darf danach nur dieses sichtbare Kommando starten:

```bash
HOME=/tmp/nac-m365-tools/home PATH=/tmp/nac-m365-tools/node-v24.18.0-linux-x64/bin:/tmp/nac-m365-tools/m365-cli/bin:$PATH m365 login --appId "<cli-entra-app-id>" --tenant "<tenant-id>" --authType deviceCode
```

Nach erfolgreichem Login ist der erste erlaubte Smoke-Test ein lesender
Graph-Aufruf:

```bash
m365 request --url "@graph/organization" --method get --output json
```

Produktive Schreibaktionen, Admin Consent und Team-/SharePoint-Provisioning
bleiben danach separat owner-gated.

## Fehlerbild AADSTS7000218

Wenn der Token-Abruf mit `AADSTS7000218` fehlschlägt, ist die CLI-App nicht als
Public Client für Device Code nutzbar. Nicht mit einem Secret reparieren.

Korrektur in der App-Registrierung:

1. [Microsoft Entra App registrations](https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. App `NaC M365 CLI Admin` öffnen.
3. `Authentication` öffnen.
4. Plattform `Mobile und Desktopanwendungen` hinzufügen.
5. Redirect URI setzen:

```text
https://login.microsoftonline.com/common/oauth2/nativeclient
```

6. `Öffentliche Clientflows zulassen` auf `Ja` setzen.

Danach einen neuen Device-Code-Login starten. Alte Codes müssen nicht
wiederverwendet werden.

## Erlaubte Nutzung

Erlaubt sind nur diese Nutzungen:

```bash
m365 setup
m365 login --appId "<cli-entra-app-id>" --tenant "<tenant-id>" --authType deviceCode
m365 status
m365 request --url "@graph/organization" --method get --output json
m365 request --url "@graph/groups" --method get --output json
```

Für einen owner-gated Entra-App-Bootstrap ist außerdem zulässig:

```bash
m365 entra app add --name "NaC Graph Bootstrap" --certificateFile "<public-certificate.cer>" --apisApplication "https://graph.microsoft.com/Team.Create,https://graph.microsoft.com/Sites.Manage.All" --grantAdminConsent
```

Der private Schlüssel zum Zertifikat liegt niemals im Repo. Wenn eine Ausgabe
App-IDs, Tenant-IDs oder andere identifiers enthält, dürfen sie nur in lokalen
Admin-Notizen oder einer sicheren Secret-Verwaltung gespeichert werden.

## Gesperrte Nutzung

Diese Nutzungen sind für den MVP-Datenpfad gesperrt:

```text
m365 spo ...
m365 request --url "@spo/..."
m365 request --url ".../_api/..."
m365 request --url "@graphbeta/..."
CSOM
PnPjs als Runtime-Abhängigkeit
Microsoft Graph SDKs im Provisioner
```

Hubsites, SharePoint-Admin-Kommandos oder PnP-spezifische SharePoint-Funktionen
sind nur spätere Admin-Ausnahmen. Sie sind nicht Teil des MVP.

## Smoke-Test

Nach erfolgreichem Login ist der kleinste sinnvolle Test:

```bash
m365 request --url "@graph/organization" --method get --output json
```

Danach läuft der Produktpfad über die zentrale NaC-CLI:

```bash
python3 scripts/nac.py m365 teams-sharepoint plan --format json
python3 scripts/nac.py m365 teams-sharepoint privileged-plan --format json
```

Der wiederholbare privilegierte Apply-Pfad nutzt ebenfalls nur Microsoft Graph
REST v1.0. Er ist kein Standardnutzerpfad und benötigt eine explizite
Owner-Freigabe:

```bash
M365_GRAPH_ACCESS_TOKEN_FILE="<lokale-token-datei>" python3 scripts/nac.py m365 teams-sharepoint privileged-apply --owner-approved --format json
```

Alternativ kann später eine app-only Konfiguration mit `M365_TENANT_ID`,
`M365_PROVISIONER_CLIENT_ID` und `M365_PROVISIONER_CLIENT_SECRET` genutzt
werden. Tokens, Client Secrets, Zertifikate und private Schlüssel werden nicht
in Chat, Shell-Ausgabe oder Repo-Artefakten abgelegt.

Ein weiterer Live-Apply bleibt owner-gated und darf erst nach Review des Plans,
Bestätigung der Ziel-Teams, Drift-Snapshot und Admin Consent ausgeführt werden.

Nach einem separat freigegebenen Runtime-App-Credential kann der kleinste
produktnahe Read-Smoke die vorhandenen SharePoint-Listen mit der Runtime-App
prüfen:

```bash
M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE="<lokale-runtime-token-datei>" python3 scripts/nac.py m365 teams-sharepoint runtime-smoke --owner-approved --runtime-smoke-output out/m365/teams-sharepoint/runtime-smoke.redacted.json --format json
M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE="<lokale-runtime-token-datei>" python3 scripts/nac.py m365 teams-sharepoint runtime-metadata --owner-approved --runtime-metadata-output out/m365/teams-sharepoint/runtime-metadata.redacted.json --format json
```

Alternativ nutzt der Smoke `M365_TENANT_ID`, `M365_RUNTIME_CLIENT_ID` und
`M365_RUNTIME_CLIENT_SECRET`. Dieser Schritt liest nur die im nicht-geheimen
Provisioning-State referenzierten Sites und vergleicht die gefundenen Listen
und Dokumentbibliotheken mit dem deklarativen MVP-Schema.
`runtime-metadata` liest ausdrücklich keine Listenelemente und keine
Mandatsdaten. Er setzt keine Teams, Gruppen, App-Rollen, Site-Permissions oder
SharePoint-Listenelemente.

Diese Einzelbefehle sind der Read-only-Diagnosepfad. Für den vollständigen
Runtime-/MCP-Betriebsnachweis nach Änderungen ist unten `release-gate-run` der
Standard.

## Kanonische M365-MVP-Betriebssequenz

Für neue Operator-Läufe ist die zentrale `nac`-CLI die führende Bedienkante.
Direkte Aufrufe von `scripts/provision_teams_sharepoint_graph.py` bleiben als
interne Kompatibilität zulässig, Produktdokumentation und Agenten-Handoffs
führen aber über `nac`.

Die normale Reihenfolge ist:

```bash
python3 scripts/nac.py m365 teams-sharepoint privileged-plan --format json
python3 scripts/nac.py m365 teams-sharepoint privileged-apply --owner-approved --format json
python3 scripts/nac.py m365 teams-sharepoint release-gate-run --owner-approved --mcp-smoke-workspace-id notary_team_01 --mcp-smoke-correlation-id <correlation-id> --format json
```

`privileged-plan` ist lesend und erzeugt den Review-Plan. `privileged-apply`
ändert Tenant-Zustand und darf erst nach Review, Drift-Snapshot und
Owner-Freigabe laufen. `release-gate-run` ist danach der Standard-
Betriebsnachweis nach MCP-/Runtime-Änderungen, weil der One-Shot-Runner
den offline Zertifikatsablauf-Monitor, Runtime-Smoke, Runtime-Metadata,
synthetischen Write/Read/Cleanup, Leftover-Dry-Run und Evidence Export in einem
owner-gated Lauf ausführt. Die intern abgedeckten Runtime-Schritte prüfen den
Zertifikatsablauf und den Sites.Selected-Zugriff ohne Listenelemente oder
Mandatsdaten und schreiben redigierte Evidence-Artefakte ohne Thumbprint,
Site-IDs, URLs, Listen-/Drive-IDs, Graph-Rohantworten, Tokens, Secrets oder
Dateiinhalte.

Der `mcp-smoke-leftover-cleanup`-Dry-Run ist der Nachlauf, wenn die Suite
fehlgeschlagen ist, ein vorheriger Smoke abgebrochen wurde oder der Operator
synthetische Reste ausschließen will. Zeigt der Dry-Run Treffer, bleibt der
Delete-Lauf ein separates Owner-Gate:

```bash
python3 scripts/nac.py m365 teams-sharepoint mcp-smoke-leftover-cleanup --owner-approved --format json
```

Alle Evidence-Dateien liegen redigiert unter `out/m365/teams-sharepoint/` und
werden nicht versioniert. Tokens, private Schlüssel, Roh-Graph-Antworten,
echte Aktenwerte und SharePoint-Dateiinhalte gehören weder in den Chat noch in
das Repository. `release-gate-run` lässt `release-gate-evidence` am Ende
laufen und fasst die vorhandenen redigierten Runtime- und MCP-Artefakte in
`out/m365/teams-sharepoint/release-gate-evidence.redacted.md` zusammen und
führt im Evidence-Schritt selbst keine Graph-Anfrage aus.

Die komplette Runtime-/MCP-Sequenz kann als wiederholbares Release-Gate offline
gerendert werden:

```bash
python3 scripts/nac.py batch-approval m365 --batch-mode release-gate --workspace-id notary_team_01 --correlation-id <correlation-id> --format json
```

Wenn der freigegebene One-Shot-Lauf direkt das redigierte Audit-Pack schreiben
soll, rendert der Batch-Befehl denselben Owner-Gate inklusive Audit-Pack-Flags:

```bash
python3 scripts/nac.py batch-approval m365 \
  --batch-mode release-gate \
  --workspace-id notary_team_01 \
  --correlation-id <correlation-id> \
  --release-gate-write-audit-pack \
  --release-gate-compare-left <baseline-correlation-id> \
  --format json
```

Der Renderer führt keine Graph-Anfrage aus. Er erzeugt den kopierbaren
Freigabetext für genau den One-Shot-Runner `release-gate-run --owner-approved`
und dokumentiert die intern abgedeckten Schritte. Einzelbefehle bleiben
Diagnose-/Fallback-Pfad, wenn ein Runner-Schritt isoliert reproduziert werden
muss.
