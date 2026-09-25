# Versionierter Read-only-Treiber für die Teams-Current-State-Diagnose – Implementierungsplan

Status: Plan freigegeben; geschützte Offline-Paketvorbereitung und inaktive Authentifizierungs-Designrevision am 25. September 2026 genehmigt, Finalisierung, Treiber-Release und Real-Read nicht freigegeben

Datum: 23. September 2026

Spec: [Versionierter Read-only-Treiber](../specs/2026-09-23-m365-current-state-read-driver-design.md)

Führendes Issue: [#748](https://github.com/notariat8/NaC/issues/748)

Ausgangsbasis: `main` `1b65259b9b4953a3b048be850c7953897b8eab83` / Tree `1723094af6a398077be25f7897888faf0159069c`. Der neue geschützte Draft-PR wird separat von den gelieferten PR #749 und #751 beurteilt.

Delivery Mode: Protected PR. Risk Gate: Human Approval.

Die spätere Owner-Freigabe auf `main`-Commit `862c87e1e378657f0066faed1bd36b830be2146d` / Tree `3b1cfe5a4cfd7972912b961bfad46b713469f9fa` öffnet ausschließlich den `prepare`-Schritt für einen neuen geschützten Offline-Kandidaten. `build` und `finalize` bleiben kontrakt- und lizenzseitig blockiert. Ein funktionsfähiger No-Refresh-Authentifizierungskanal ist damit nicht nachgewiesen; die Produktions-Port-Factory bleibt fail-closed. Die beiden neuen Clientbelege grenzen die sichtbare Teams-Störung auf eine HTTP-403-Antwort bei vorhandenem SPFx-Subject ein, ohne die serverseitige Ursache zu beweisen.

## Lieferumfang und Reihenfolge

1. **Release-Vertrag zuerst:** Einen eigenen `workflows/verification-contracts/m365-current-state-read-driver.verification.json` mit exakten ACs, Artefakten, zwei getrennten Zuständen `OFFLINE_REVIEWABLE` und `LIVE_CAPABLE`, Abhängigkeits- und Null-Seiteneffektmatrix erstellen. Er bindet den bestehenden [#748-Vertrag](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml) durch dessen Dateidigest; dieser historische Vertrag und seine gelieferten PR-/Merge-Belege werden nicht geändert.
2. **Geschlossene Ressourcen:** `workflows/contracts/m365-current-state-read-driver-resources.contract.json` definiert die sechs festen Microsoft-GET-Familien, Origins, API-Versionen, Pfadschablonen, zulässige gebundene Platzhalter, feste Query-Felder, Responseprojektionen und Obergrenzen. Für den Request-Log-Port ist ausschließlich Application-Insights-Query-GET mit einem kompilierten, parametergebundenen KQL-Template zulässig. Fehlt für Entra- oder SharePoint-Evidence eine vollständige Projektion mit einem GET, blockiert der Port; die Zählermatrix des #748-Vertrags wird nicht erweitert.
3. **Test-first Bindung:** `tests/test_m365_current_state_read_driver.py`, `tests/test_m365_current_state_access_gate.py`, `tests/test_spec_traceability.py` und Negativfälle im bestehenden #748-Diagnosetest prüfen zunächst Rotfälle für Dummy-/fehlende Source-, Binary-, Bundle-, CycloneDX-, SPDX-, korrespondierende Quellcode- oder Lizenzbelege und unvollständiges Drittanbieter-Attributionsinventar; unbekannte Runtime-Datei; falschen Owner/DACL/Datei-ID/Hash/Hardlink/Reparse; gefälschte Ressourcenschablone; falsche Methode, Host, Query, Status, `Location`, `nextLink`, Retry, Login-/Refresh-Versuch und Roh-/PII-Ausgabe. Die Governance-Fixtures belegen Same-Principal-Aliase ohne Vier-Augen- oder Berechtigungserweiterung, blockierte unzitierte Zwei-Personen-Behauptungen, `OWNER_SOLO_APPROVAL` mit `four_eyes_satisfied=false` und `BLOCKED_SINGLE_PRINCIPAL` bei zitierter anwendbarer Pflicht. Die Read-Fixtures zählen vier Microsoft-GETs für zwei `SPFX_SUBJECT_MISSING`-Erhebungen beziehungsweise zwölf für jede andere vollständige Zweifacherhebung und null weitere Requests nach blockierter Projektion. Auch Request-URL, Query und Ziel-ID dürfen nicht im Fehler oder Log erscheinen. Die Tests bleiben hermetisch und benutzen Fakes.
4. **Schmale Python-Quelle:** `src/nac_bff/current_state_read_driver.py` implementiert ausschließlich die geschlossenen Operationen und die Redaktionsprojektionen. HTTP-Transport und Authentisierungsfähigkeit sind getrennte Interfaces. Die Microsoft-Port-Factory bleibt ohne nachgewiesene No-Refresh-Fähigkeit `BLOCKED_NO_REFRESH_CAPABILITY`, bevor sie Credentials, Authentisierung oder Netzwerk berührt. Weder Azure- noch M365-CLI wird als stillschweigender Ersatz eingesetzt. Die bestehende #748-Komposition und der Prozess-Adapter werden so ergänzt, dass sie den Release-Beleg und alle Bundle-Dateien vor dem One-Shot-Consume tatsächlich verifizieren.
5. **Windows-Build und Lizenz-Gate:** `scripts/build_m365_current_state_read_driver.py` pinnt Python, ein lizenzgeprüftes Build-Werkzeug und Abhängigkeiten. Ein Verzeichnis-Bundle ist Ausgangspunkt; ein Ein-Datei-Bundle mit ungebundener temporärer Entpackung ist ausgeschlossen. `prepare` erstellt repository-extern das geschützte Bundle, Source-/Tool-/Commit-/Tree-Bindung, Binary-Hashes und echte CycloneDX-/SPDX-SBOMs, jedoch nur `preparation.json` mit `AWAITING_INDEPENDENT_LICENSE_EVIDENCE`, keinen Release-Beleg. Der Parser gleicht Syft-Paketorte und SPDX-Kanten ab; das Datei-Manifest bleibt auch für nicht entdeckte Pakete vollständig. Erst nach unabhängiger Prüfung von Quell-Hashes, Lizenztexten, Tool-Identität, SBOM-Hashes und jeder Dateizuordnung wird der [versionierte Lizenzkatalog](../../../../workflows/contracts/m365-current-state-read-driver-license-catalog.json) separat reviewt und `APPROVED`; ein `PENDING`-Katalog blockiert. Der erste vorbereitete Stand ist **nur Review-Evidence**: Weil die Katalogfreigabe HEAD/Tree ändert, muss danach eine frische Vorbereitung auf dem freigegebenen Commit erfolgen. Die Finalisierung verlangt exakte Übereinstimmung ihrer Datei-, Tool-, SBOM-, Treiberquell- und Ressourcen-Hashes mit der vorab reviewten Vorbereitung; jede Abweichung braucht neue unabhängige Prüfung. `finalize` verlangt außerdem geschützte externe Lizenzbelege, ergänzt NaC-/Drittanbieter-Attribution sowie Lizenztexte und erstellt erst dann einen Release-Beleg. Der Release-Validator `scripts/validate_m365_current_state_read_driver.py` prüft alle Dateien selbst. `CANDIDATE_BUILT` belegt keine unabhängig verifizierte Source-/Binary-Korrespondenz; ohne einen solchen Nachweis wird weder Byte-Reproduzierbarkeit noch `OFFLINE_REVIEWABLE` behauptet. Die ursprüngliche Reparatur endete **vor** einem neuen Paketkandidaten; die spätere Freigabe erlaubt nur die geschützte Vorbereitung, nicht die Finalisierung.
6. **Integration und Doku:** Die vorhandene `nac`-CLI bleibt Bedienkante; keine neue freie URL-/KQL-/Token-Option. DE/EN-[Diagnoseanleitung](../../m365-current-state-access-diagnostic.md), Spec-Traceability, AI-SBOM-Negativentscheidung, Lizenz-/SBOM-Dokumentation und Windows-CI werden synchronisiert. Realer Providerzugriff, SPFx-/BFF-Deployment und #739/#632-Pfade bleiben ausgeschlossen.
7. **Review und Abnahme:** `implement -> review -> fix` mit unabhängiger Policy-, Docs-Parity- und Validation-Sicht; danach fokussierte Negativtests, komplette lokale Windows-Testsuite, Graft Build/Check und Strict Doctor. Der vollständige `main...HEAD`-Diff samt Commit- und Dateiliste wird geprüft. Separate Vorwärtscommits, Push ohne Force-Push und alle verpflichtenden Remote-CI-Checks. Der PR bleibt Draft und stoppt vor Treiber-Release-Freigabe oder realem Read.

Der Verification Contract trennt nun `repository_external_preparation_candidate=true`
von `repository_external_release_candidate=false`. Die Vorbereitung ist die
einzige freigegebene externe Dateierstellung; sie erzeugt keinen Release-Beleg.
Die ursprüngliche Reparaturfreigabe endete vor jedem Kandidaten; die spätere
oben gebundene Freigabe erweitert nur die Vorbereitung.

## Plan der genehmigten Designrevision – ohne Laufzeitfreigabe

Der neue [Silent-Refresh-Entwurf](../../../../workflows/contracts/m365-current-state-silent-refresh.design.json) ist `DESIGN_ONLY_NOT_AUTHORIZED`. Der historische #748-Vertrag, der aktuelle Release-Vertrag und ihre Validatoren bleiben unverändert; insbesondere bleiben `token_refresh=0`, `credential_write=0`, `LIVE_CAPABLE=false` und `BLOCKED_NO_REFRESH_CAPABILITY` wirksam. AC-748-RD-04 und seine Null-Effekt-Tests gelten für den **aktuellen** Pfad unverändert. Die Designrevision allein erfüllt keinen Authentifizierungsnachweis und autorisiert keinen Paketkandidaten, Release oder Microsoft-Read.

Für eine **später separat zu genehmigende** Implementierung lautet die Reihenfolge: (1) die sechs GET-Ressourcen auf eine geschlossene Audience-Menge abbilden und die technische Beobachtbarkeit von Refresh-Versuch und Cache-Schreibwirkung nachweisen; (2) test-first einen Credential-Adapter mit höchstens einem stillen Versuch je gebundener Audience, höchstens vier insgesamt, ohne Retry, Browser-/Broker-/Gerätecode-Login, Kontowechsel oder Tokenimport/-export entwerfen; (3) Konto, Tenant, `principal_id` und Current-User-only-Auth-Speicher geschützt binden, ohne Identitätszuordnung oder Token in Git/Evidence auszugeben; (4) historische Verträge nur vorwärtsversionieren, ausschließlich Refresh-spezifische Nullzähler durch technisch gebundene Grenzen ersetzen und alle übrigen Gates mit Validatoren und Negativtests erhalten; (5) vor jeder RED-eingestuften, dedizierten Credential-Operation eine eigene exakt gebundene Owner-Freigabe einholen und Treiber-Release sowie genau einen realen Read danach getrennt freigeben. Bei nicht beobachtbaren Wirkungen, Audience-Drift, fehlender Berechtigung oder unvollständiger AVV-/DPA-/Receipt-Bindung stoppt der Pfad vor Providerzugriff. Die weiterhin ausstehende unabhängige Lizenzprüfung bleibt ein eigenes Gate.

## Nachweismatrix

| AC | Testziel | Nachweis |
| --- | --- | --- |
| AC-748-RD-01 | Tatsächliche Source-, Binary-, klassische SBOM-, Lizenz- und Manifestbindung | Release-Validator und manipulierte Digest-/Datei-Fixtures |
| AC-748-RD-02 | Vollständige Windows-Bundle-Attestation | SID-/DACL-, Datei-ID-, Hash-, Hardlink-, Reparse- und Zusatzdatei-Negativtests |
| AC-748-RD-03 | Nur geschlossene GET-Ressourcen, ein Read je Provider-Port | Methoden-/Origin-/Pfad-/Query-/Redirect-/Retry-/Pagination-Negativtests und Zähler |
| AC-748-RD-04 | Authentifizierung ohne Refresh-Nachweis und unzulässige Governance-Entscheidungen blockieren vor Provider-I/O | Factory-/Prozess-Fake mit Null-Credential-/Netzwerk-/Providerzählern; Gate-Tests für Same-Principal-Aliase, unzitierte Zwei-Personen-Behauptung, Solo-Owner mit `four_eyes_satisfied=false` und zitierte Pflicht mit `BLOCKED_SINGLE_PRINCIPAL` |
| AC-748-RD-05 | Nur redigierte Portfelder verlassen den Treiber | PII-, Rohantwort-, Header-, Größen- und unbekannte-Feld-Fixtures |
| AC-748-RD-06 | Hermetische Integration mit #748-Gate und vier Klassen | positive/negative Adapter-, One-Shot-, Drift- und Klassifikationstests; exakt vier beziehungsweise zwölf Microsoft-GETs über zwei Erhebungen und null weitere Requests nach blockierter Projektion |
| AC-748-RD-07 | DE/EN-, Contract-, SBOM-, AI-SBOM- und CLI-Parität | Spec-Traceability, Sprache, Links, klassischer SBOM-Validator und unabhängiger Review |
| AC-748-RD-08 | Geschützter Draft-PR ohne Live-Ausführung | vollständiger Diff, lokale Pflichtgates, Remote-CI, keine Provider-Evidence |

## Validierungsbefehle für die spätere Implementierung

```text
python -m unittest discover -s tests -p test_m365_current_state_read_driver.py
python -m unittest discover -s tests -p test_build_m365_current_state_read_driver.py
python -m unittest discover -s tests -p test_m365_current_state_read_driver_sbom.py
python -m unittest discover -s tests -p test_m365_current_state_access_gate.py
python -m unittest discover -s tests -p test_m365_current_state_access_diagnostic.py
python -m unittest discover -s tests -p test_spec_traceability.py
python scripts/validate_m365_current_state_read_driver.py
python scripts/validate_m365_current_state_read_driver.py --candidate <geschützter-externer-Kandidatenpfad>
python scripts/validate_m365_current_state_access_diagnostic.py
python scripts/validate_spec_traceability.py
python scripts/validate_language_parity.py
python scripts/validate_doc_links.py
python -m unittest discover -s tests
graft build
graft check
python scripts/nac.py doctor --profile strict
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
```

`OFFLINE_REVIEWABLE` ist nur Review- und CI-Nachweis. `LIVE_CAPABLE` erfordert **zusätzlich und gleichzeitig** einen technisch geprüften No-Refresh-Kanal, tatsächliche aktuelle Resource-/Bundle-/SBOM-Bindungen und alle bisherigen #748-Gates: geschützte AVV-/DPA-Vertrags- und Receipt-Bindung, Provider-/Tenant-/Zielscope, kontospezifische Leseberechtigung, `principal_id`, `OWNER_SOLO_APPROVAL` oder `BLOCKED_SINGLE_PRINCIPAL` nach konkretem Quellenbeleg, verpflichtende Checks, One-Shot-Marker und Autorisierung vor Port-Factory sowie vor jedem Read. Die Freigabe des Treiber-Release und die Freigabe genau eines realen Reads sind getrennt. Ein bestandener synthetischer Lauf ist kein Microsoft-Zugriffsbeleg.

## Plan-Review vor Implementierung

Policy-Review prüft Lizenz, Datenschutz, AVV-/DPA- und Providergrenze; Docs-Review prüft DE/EN-Parität und Links; Validation-Review prüft die Gegenbeispiele und ob Gates vor Credential-/Provider-I/O laufen. Befunde werden im Implementierungs-Review korrigiert. Der Befehl mit `--candidate` ist erst für ein tatsächlich erzeugtes, geschütztes Paket ausführbar; der reine Quellvertragstest ersetzt ihn nicht. In dieser Arbeit erfolgen weder Login noch realer Diagnose-Lauf.
