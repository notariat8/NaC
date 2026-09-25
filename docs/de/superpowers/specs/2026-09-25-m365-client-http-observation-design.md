# HTTP-Zusatzbeleg für die NaC-Registerkarte in Teams

Status: Lokal umgesetzt und auf Windows einschließlich Strict-Doctor validiert; PR, App-Bereitstellung und realer Providerbefund offen.

Datum: 25. September 2026

Führendes Issue: [#748](https://github.com/notariat8/NaC/issues/748); sichtbares Produktziel: [#620](https://github.com/notariat8/NaC/issues/620).

Ausgangsbasis: `main`-Commit `957d8b9ac9a8c6a3d9cbbf26de679d220f302432`, Tree `e1edb34d0a1518166bd31b9facde13eb7fdd2478` nach dem Merge von [PR #752](https://github.com/notariat8/NaC/pull/752).

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-client-http-observation
leading_issue: https://github.com/notariat8/NaC/issues/748
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/de/superpowers/plans/2026-09-25-m365-client-http-observation.md
review_gates:
  - Privacy
  - Secrets
  - External Service
  - Human Approval
affected_artifacts:
  - assets/docs/workbench-live-read-binding/VIS-725-05-deny.png
  - assets/docs/workbench-live-read-binding/VIS-725-06-unavailable.png
  - assets/docs/workbench-live-read-binding/VIS-725-manifest.json
  - docs/de/superpowers/specs/2026-09-25-m365-client-http-observation-design.md
  - docs/en/superpowers/specs/2026-09-25-m365-client-http-observation-design.md
  - docs/de/superpowers/plans/2026-09-25-m365-client-http-observation.md
  - docs/en/superpowers/plans/2026-09-25-m365-client-http-observation.md
  - docs/de/m365-current-state-access-diagnostic.md
  - docs/en/m365-current-state-access-diagnostic.md
  - spfx/nac-bpmn-viewer/scripts/validate-read-only-boundary.cjs
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffHttpAccessDeniedError.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/ClientObservationReceipt.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/ClientHttpObservationReceipt.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.tsx
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.styles.ts
  - src/nac_bff/client_http_observation_receipt.py
  - workflows/verification-contracts/m365-client-http-observation.verification.json
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/ClientHttpObservationReceipt.test.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.test.tsx
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.test.ts
  - tests/test_m365_client_http_observation_receipt.py
acceptance_ids:
  - AC-748-HTTP-01
  - AC-748-HTTP-02
  - AC-748-HTTP-03
  - AC-748-HTTP-04
  - AC-748-HTTP-05
validation_commands:
  - python -m unittest discover -s tests -p test_m365_client_http_observation_receipt.py
  - heft test --production
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - graft check
  - python scripts/nac.py doctor --profile strict
```

## Zweck und Ausgangslage

Die bereitgestellte Registerkarte zeigt „Kein Zugriff auf diesen Arbeitsbereich“. Ihr bestehender, ausdrücklich herunterladbarer [Clientbeleg](../../../../spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/ClientObservationReceipt.ts) enthält nur den neutralen UI-Zustand, die Verfügbarkeit einer SPFx-Benutzer-ID, ein geschlossenes Zeitfenster und opake Hash-Bindungen. Der [BFF-Client](../../../../spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.ts) bildet HTTP 401 und 403 absichtlich auf dieselbe neutrale Meldung ab. Der Beleg unterscheidet diese beiden Clientantworten deshalb nicht. Er beweist auch nicht, ob die Azure Function den Request empfangen hat.

Ziel dieser Ergänzung ist ausschließlich eine lokale, datensparsame Unterscheidung der **vom SPFx-Client beobachteten** HTTP-Klasse. Sie ersetzt weder die zwei Provider-Snapshots noch die vier serverseitigen Diagnoseklassen des [bestehenden #748-Designs](2026-09-20-m365-current-state-access-diagnostic-design.md).

## Designentscheidung und Alternativen

1. **Empfohlen: separater, versionierter HTTP-Zusatzbeleg.** Der bestehende sechs Felder umfassende Beleg und sein [Verification Contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml) bleiben byte- und schemaunverändert. Ein zweiter ausdrücklich betätigter Download enthält nur eine geschlossene Client-HTTP-Klasse und den SHA-256-Digest des gleichzeitig erzeugten Basisbelegs. Das bewahrt alte Downloads, Validatoren und historische Commit-/Contract-Bindungen. Der zusätzliche Klick ist der bewusste Nachteil.
2. Ein neues Feld direkt im alten JSON wäre für den Nutzer einfacher, würde aber dessen exakte Feldliste, Validator und historische Vertragsbindung brechen. Diese Variante ist ausgeschlossen.
3. Browser- oder Desktop-Entwicklerwerkzeuge ändern zwar keinen Code, sind für die tatsächlich sichtbare Desktop-Registerkarte nicht zuverlässig ohne zusätzliche UI-/Preview-Voraussetzungen verfügbar und erzeugen leicht unredigierte Netzwerkdetails. Sie sind kein Produktpfad.

Der Zusatzbeleg ist eine **ergänzende lokale Beobachtung**, kein neuer produktiver Read-Treiber und keine Abkürzung um das #748-Gate. Der alte Beleg darf weiter allein verwendet werden; ein Zusatzbeleg ohne passenden Basisbeleg wird nicht als gebundene Evidence akzeptiert. Der [DE/EN-Implementierungsplan](../plans/2026-09-25-m365-client-http-observation.md) und ein eigener Verification Contract binden den lokalen Entwurf.

## Geschlossene Daten- und UI-Grenze

Der neue JSON-Beleg hat einen eigenen Dateinamen und exakt diese Felder:

| Feld | Wert |
| --- | --- |
| `schema_version` | Konstante `nac.client-http-observation/v0.1` |
| `base_receipt_sha256` | SHA-256 über die kanonischen UTF-8-Bytes des zugleich erzeugten unveränderten Basisbelegs |
| `client_http_class` | Exakt `none`, `401` oder `403` |
| `observation_binding_sha256` | SHA-256 über die übrigen drei Felder als UTF-8-JSON mit alphabetischen Schlüsseln und ohne Leerzeichen |

`none` bedeutet ausschließlich, dass der Client für diese Beobachtung **keine passende HTTP-Antwort** vorliegen hat; es behauptet weder einen fehlenden Serverrequest noch einen BFF-Deploymentzustand. `401` und `403` stammen nur aus dem tatsächlich erhaltenen `HttpClientResponse.status` des bestehenden `/workbench-snapshot`-Aufrufs. Ein String aus einer Exception, einer URL, einem Header, einem Antwortkörper oder einer anderen Anfrage darf niemals in diese Klasse umgedeutet werden. Andere Statuswerte, Abbruch, Timeout, fehlende Korrelation oder inkonsistente Beobachtung erzeugen keinen HTTP-Zusatzbeleg. Der UI-Text bleibt unverändert neutral.

Der neue Button „HTTP-Diagnosebeleg speichern“ erscheint nur im bestehenden verweigerten Zustand und startet erst nach ausdrücklichem Klick einen Download. Er sendet keine Telemetrie, stellt keinen zusätzlichen BFF-Request und öffnet keinen Login. Der Basisbeleg und Zusatzbeleg werden aus derselben eingefrorenen Beobachtung erzeugt; Re-Render, Refresh, Unmount oder konkurrierende Ladeversuche dürfen Status und Basisdigest nicht vermischen. Der Browser speichert weder Roh-Korrelations-ID noch Benutzer-/Objekt-ID, Name, E-Mail-Adresse, Tenant, URL, Query, Header, Antwortinhalt, Token oder Credential im Zusatzbeleg. Dessen maximale Größe beträgt 1024 Bytes.

Der Zusatzbeleg wird nur nach expliziter späterer Freigabe und eigener Validator-/CLI-Erweiterung repository-extern und Current-User-only materialisiert. Bis dahin ist er **kein** Input für den historischen #748-Preflight, keine `OWNER_SOLO_APPROVAL`-Evidence und kein Ersatz für die serverseitig korrelierte Request-Log-Prüfung.

## Akzeptanzkriterien

- **AC-748-HTTP-01:** Für einen synthetischen SPFx-Subject mit tatsächlicher HTTP-401- beziehungsweise HTTP-403-Antwort entsteht nach explizitem Klick ein Zusatzbeleg mit exakt `401` beziehungsweise `403`; die Teams-Meldung bleibt in beiden Fällen identisch neutral.
- **AC-748-HTTP-02:** Ohne passende HTTP-Antwort lautet die Klasse ausschließlich `none`, soweit der bestehende verweigerte UI-Zustand einen vollständigen Basisbeleg erzeugt; unklare, abgebrochene oder widersprüchliche Zustände erzeugen keinen Zusatzbeleg. Kein Clientwert behauptet, dass der BFF den Request gesehen hat.
- **AC-748-HTTP-03:** Beide Dateien sind für exakt dieselbe eingefrorene Beobachtung gebunden. Änderung, Austausch, Wiederverwendung oder Vermischung eines Basisbelegs lässt die Zusatzbelegprüfung fail-closed scheitern. Der alte Beleg und sein historischer Contract bleiben unverändert gültig.
- **AC-748-HTTP-04:** Synthetische Negativtests prüfen unbekannte Felder und Statuswerte, PII-/Token-/URL-/Header-/Body-Leaks, unerlaubten automatischen Download, zusätzlichen Request, falsche Korrelation und konkurrierende Lade-Generationen. Sichtbare UI und Download werden visuell geprüft.
- **AC-748-HTTP-05:** DE/EN-Spec, nachfolgender Plan, Verification Contract, Spec-Traceability, Datenschutz-/AI-SBOM-Entscheidung und Windows-/SPFx-Gates sind vor Implementierungsabnahme synchron; kein Microsoft-Read, Provider-Write, Login, Deployment oder #739/#632-Lauf wird dadurch freigegeben.

## Risiken und Nicht-Ziele

Eine HTTP-401/403-Antwort kann von einer vorgeschalteten Schicht stammen. Die Clientklasse ist daher ein Wegweiser für den nächsten gezielten Prüfschritt, **keine abschließende Ursache**. Ein Hash schützt die Bindung zweier lokaler Dateien, belegt aber keine Serverauthentizität. Es werden keine bestehenden #748-Snapshots, Release-Gates, Authentifizierungsgrenzen oder alten Issue-#739-/Issue-#632-Artefakte gelockert. Der lokale Entwurf autorisiert weder Paket-/App-Release noch produktiven Diagnosezugriff. Es wird kein AI-Modell oder externer AI-Aufruf eingeführt; die AI-SBOM-Oberfläche bleibt unverändert.
