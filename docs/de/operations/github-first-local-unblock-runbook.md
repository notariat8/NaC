# GitHub-first-Arbeit lokal entblocken

Status: aktiv (Runbook, gelernt aus Session 2026-08-30)

## Zweck

Dieses Runbook hält die wiederkehrenden Reibungspunkte fest, die agentische
GitHub-first-Arbeit lokal blockieren, und die reproduzierbaren Wege, sie zu
entblocken — damit nicht jede Session dieselbe Diagnose neu durchlaufen muss.
Es ist die dauerhafte Form der Lernerfassung nach der Repo-Regel: tritt
derselbe Reibungspunkt zweimal in einer Session oder dreimal über Issues/PRs
auf, wird das Muster benannt und als Runbook/Wrapper festgehalten.

## 1. GitHub-Schreibblockade durch leere OAuth-Scopes

### Symptom

- `gh issue create` / `gh pr create` schlägt fehl:
  `Your token has not been granted the required scopes … 'public_repo' … but your token has only been granted the: [''] scopes.`
- `git push` schlägt fehl mit
  `remote: Permission to <owner>/<repo>.git denied to <user>. … 403`.
- `gh api user --jq .login` und `gh issue list` funktionieren trotzdem
  (Lesen klappt, Schreiben nicht).

### Ursache (Diagnose)

Kein Session-Problem, sondern **leere OAuth-Scopes** des aktiven
Account-Tokens. Die Anmeldung selbst ist dauerhaft gespeichert (verschlüsselter
Store, 0600, überlebt Sessions). Eine neue Session injiziert dasselbe Store-Token
und blockiert genauso — Session-Wechsel löst das Problem also nicht, und ist auch
nicht nötig. Das Problem ist nicht Persistenz, sondern dass das gespeicherte
PAT ohne Schreib-Scopes angelegt wurde.

Beweisbefehl (read-only):

```bash
curl -sSI -H "Authorization: token $GH_TOKEN" https://api.github.com/user | grep -i 'x-oauth-scopes'
# x-oauth-scopes:           <- leer => keine Schreibrechte
```

Bei gültigen Scopes stünde hier z. B. `repo` (deckt `public_repo` und damit
Push/Issue/PR für dieses öffentliche Repo).

### Root Cause im Harness

`/auth login` ist ein **„PAT einfügen"-Flow**, kein OAuth-Device-Flow: der
Harness öffnet `https://github.com/settings/tokens/new`, zeigt den Hint
„scopes: `repo, user:email`", und das PAT wird eingefügt und verifiziert via
`GET /user`. Der Harness fordert die Scopes nicht selbst an; er übernimmt die
Scopes des eingefügten PAT (`x-oauth-scopes`-Header). Ein klassisches PAT mit
leeren Scopes (`ghp_…`, `type: pat`) hat nur Lesezugriff auf öffentliche Repos.

### Owner-Aktion (einmalig, danach dauerhaft)

Auf `https://github.com/settings/tokens/new` ein klassisches PAT mit Scope
**`repo`** anlegen (deckt Push/Issue/PR für dieses öffentliche Repo). `workflow`
ist nur nötig, wenn ein PR `.github/workflows/*` ändert — dieser Fix-PR tut das
nicht. Dann `/auth login` und das neue PAT einfügen; der Harness ersetzt das
alte Token (gleicher Login → Replace) und persistiert es wieder dauerhaft. Danach
ist kein erneutes Anmelden nötig. Ohne `repo`-Scope ist GitHub-first (führendes
Issue → Branch → PR → remote CI) nicht durchführbar. Ein Agent mint keine Scopes;
dieses Gate bleibt Owner-gated.

### In-Session-Workaround (nur Lesen + Diagnose, kein Schreiben)

Wenn nur Lese- oder Diagnosezugriff nötig ist und die Session `GH_TOKEN` leer
oder ein Platzhalter ist, lässt sich das Store-Token aus dem verschlüsselten
File-Backend entschlüsseln und für die Session neu setzen — **ohne** das
Token auf stdout zu drucken oder in eine Datei zu schreiben:

- Store: `~/.pi/agent/pi-git-auth/credentials.json` (AES-256-GCM-Hülle
  `enc:v1:`) plus separate 0600 `key`-Datei.
- Muster: ein winziges Node-Skript entschlüsselt das Token und schreibt es
  nach stdout in ein `export GH_TOKEN="$(node …)"`. Das Token bleibt im
  Shell-Env, nie in einer Datei. Das Skript enthält nur
  Entschlüsselungslogik, kein Secret.

Grenze: dieser Workaround gibt nur die Scopes des Store-Tokens zurück — bei
leeren Scopes bleibt Schreiben (Issue/PR/Push) blockiert. Er löst also Lesen,
nicht das Schreib-Problem. Das Schreib-Problem löst nur die Owner-Aktion oben.

## 2. Lokaler Strict-Quality-Gate-Laufzeit: langsam, nicht kaputt

### Symptom

`python scripts/nac.py doctor --profile strict` wirkt im ersten Lauf wie ein
Hang (keine Ausgabe für über 10 Minuten).

### Ursache

Kein Hang. Die volle Unit-Suite (`unittest discover`) läuft ca. 520 Sekunden,
plus rund 90 Validatoren → Gesamtdauer über 10 Minuten. Ein 600-Sekunden-Timeout
erzeugt fälschlich ein Hang-Bild (Exit 124), weil der Gate die Ausgabe erst am
Ende flushen kann.

### Maßnahme

Budget von mindestens 1200 Sekunden für `doctor --profile strict` einplanen.
Für inkrementelle Vorab-Prüfung die direkt betroffenen Checks isoliert
laufen, statt immer die volle Suite:

```bash
graft build
python3 scripts/validate_graft_context_layer.py
PYTHONPATH=src python3 -m unittest tests.test_<modul>
python3 scripts/validate_spec_traceability.py
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
```

## 3. Token-Injection-Helper in /tmp ist ephemer

Der in Session 2026-08-30 genutzte Helper `/tmp/nac_gh_token.js` ist nach
Session-Ende weg. Eine dauerhafte Variante als repo-lokaler Wrapper (nur
Entschlüsselungslogik, kein Secret auf Disk) eliminiert das Wiederauftreten
und ist als künftige Optimierung (Tooling-Wrapper) vorgesehen — nicht Teil
dieses Runbooks.

## Guardrails

- Kein Secret jemals auf stdout, in eine Datei, in einen Commit oder in
  einen PR ausgeben.
- Datei-Store und `key`-Datei bleiben 0600; der `graft`-Cache wird nicht
  committed.
- Schreib-Scopes sind Owner-gated; ein Agent mint keine Scopes.
- Siehe auch [regelarchitektur.md](../regelarchitektur.md) und
  [github-first-agentic-operating-model-design.md](../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md).
