# Notarkammer-Demo 2026-06: Demo-Gap-Audit

Stand: 2026-06-21

Zweck: Dieses versionierte Artefakt priorisiert für die Demo in 4 Tagen,
was zeigbar ist, was bewusst Fallback bleibt und welche Produktlücken nach
der Demo folgen. Es ist kein Marketingtext und behauptet keine
Implementierung, die nicht im Repo nachweisbar ist.

## Prioritätslegende

- P0: Zeigbar in der Demo in 4 Tagen, sofern Preflight grün ist.
- P1: Bewusster Fallback für die Demo in 4 Tagen.
- P2: Nach der Demo als Produktlücke oder Integrationsschritt einplanen.

## Kompakte Gap-Liste

| Priorität | Kategorie | Stand | Demo-Aussage | Grenze | Nächster realer Integrationsschritt |
| --- | --- | --- | --- | --- | --- |
| P0 | XNP Zugriff | XNP ist als lokale Fachsystem-Grenze dokumentiert: [notarkammer-xnp-demo-contract.md](notarkammer-xnp-demo-contract.md) beschreibt XNP, XNotar, Kartenleser, beN, UVZ/VVZ und Evidence nur als lokale oder externe Grenze. | Zeigbar: NaC macht im BPMN sichtbar, wann XNP/XNotar/Kartenleser relevant werden und welcher lokale Nachweis fehlt oder vorliegt. | Keine produktive XNP-Aktion, keine direkte Cloud-Steuerung von XNP, keine API-Keys, keine PINs, keine Login-Token und keine Mandatsdaten in NaC. | Offizielle XNP-Testzugangs- und Schnittstellendefinition beschaffen; danach lokalen Companion nur am Notariatsarbeitsplatz für Readiness und redigierte Evidence verproben. |
| P0 | BPMN Editor/Viewer | BPMN-Modelle, Profil und Validatoren sind vorhanden; die Demo-Sprechspur zum kritischen Pfad liegt in [notarkammer-bpmn-critical-path-talking-points.md](notarkammer-bpmn-critical-path-talking-points.md). | Zeigbar: Immobilienkaufvertrag und Handelsregisteranmeldung können als BPMN-/Prozessmodell mit kritischem Pfad, Dauerband und externen Gates erklärt werden. | Editor-/Viewer-Komfort ist kein Beweis für produktive Fachsystemintegration; keine Vorgangsinhalte, keine Register- oder Grundbuchdaten zeigen. | Viewer-/Editor-Pfad als stabile Demo-Oberfläche härten, BPMN-Gates für XNP, Register, Grundbuch, Signatur und Evidence im Profil weiter schärfen. |
| P0 | Workspace/Auth | Login-Intent, geschützter Workspace-Start und fail-closed Workspace sind getestet und in der Preflight-Checkliste als Sicherheitsnachweis vorgesehen. | Zeigbar: Ohne gültige Demo-Freigabe bleibt der Workspace geschlossen; das ist die korrekte Sicherheitsgrenze. | Kein echter Login im Termin ohne Owner-Freigabe; keine Mandatsdaten, keine Rollen-Secrets, keine Kundenakten und keine Sessionwerte im PR oder in der Demo. | Demo-Tenant mit synthetischen Rollen und freigegebenem OIDC-Pfad vorbereiten; Workspace danach nur metadata-only öffnen, bis Akten-/Dokumenten-Gates freigegeben sind. |
| P1 | ATP/Onboarding | Public-Onboarding, DNS-Readiness und Request-Status sind als Vorführpfad dokumentiert; ATP ist nur Store-Gate für Onboarding-Anfragen. | Bewusster Fallback: Wenn Store oder Healthcheck nicht verfügbar sind, wird `disabled`, `unavailable` oder `not_checked` als Einrichtungsstatus erklärt. | Keine OCI writes, keine Wallet-/DSN-Ausgabe, keine Secret-Prüfung im Termin, kein Provisioning jenseits von Dry-Run- oder Read-only-Nachweisen. | ATP-Healthcheck mit nicht-sensitiver Statusprojektion stabilisieren und Onboarding-Request-Store für synthetische Demo-Anfragen verbindlich vorbereiten. |
| P0 | Gebühren/GNotKG | Ein technischer Kostenentwurf ist vorhanden: [src/nac_gnotkg/costs.py](../../../src/nac_gnotkg/costs.py) und [tests/test_gnotkg_costs.py](../../../tests/test_gnotkg_costs.py) prüfen Wertgebühren, Mindestgebühr, Tabellenkappen und Review-Grenze. Demo-Verknüpfung: Kostenprüfung als fachliches Gate im Immobilienkaufvertrag. | Zeigbar: GNotKG kann als Review-Gate erklärt werden, das Wert, KV-Nummer, Tabelle und Gebühr technisch nachvollziehbar macht. | GNotKG bleibt keine produktive Gebührenabrechnung, keine Rechtsberatung, keine finale notarielle Kostenprüfung durch Software und keine echten Geschäftswerte. | Kostenansicht mit BPMN-Gate und fachlicher Freigabe verbinden; KV-Fälle und Usecase-Mapping nach Demo durch Notarreview erweitern. |
| P2 | Notariat-only Guardrails | Repo-Regeln, Demo-Preflight und XNP/BPMN-Dokumente begrenzen NaC auf notarielle Usecases und synthetische Demo-Daten. | Nach der Demo: Guardrails sollen als wiederverwendbarer Demo-/Produktcheck in Quality Gate oder Docs-Validator sichtbar werden. | Ausschließlich für Notariate; keine Mandatsdaten, keine Secrets, keine produktiven Register-/Grundbuchhandlungen, keine nicht-notariellen Produktpfade. | Validator für Demo-Artefakte ergänzen: Notariats-Scope, keine Mandatsdaten, keine OCI writes, keine Secrets und keine falschen Integrationsbehauptungen. |

## Was in 4 Tagen zeigbar ist

- Zeigbar: Notariatsprozess mit BPMN, kritischem Pfad, XNP-/XNotar-Grenze,
  fail-closed Workspace/Auth und GNotKG-Review-Gate als technischer Entwurf.
- Zeigbar: Public-Onboarding und ATP/Onboarding-Status, falls der Read-only
  Preflight grün ist.
- Zeigbar: Fallback-Erzählung, wenn XNP, ATP oder Login nicht verfügbar sind:
  Das System bleibt dann bewusst an der Grenze stehen.

## Bewusster Fallback

- XNP Zugriff bleibt in der Demo eine lokale Readiness- und Evidence-Grenze,
  kein Live-Adapter.
- ATP/Onboarding bleibt bei fehlendem Store ein Status-Gate, kein Debugging.
- Workspace/Auth bleibt ohne freigegebene Sitzung geschlossen.
- BPMN Editor/Viewer kann durch die öffentliche Prozessmodellseite oder
  einen geprüften lokalen Tab ersetzt werden.

## Nach der Demo

1. XNP-Testzugang, Nutzungsbedingungen und lokale Schnittstellendefinition
   klären.
2. BPMN-Gates für XNP, XNotar/XJustiz, Grundbuch, Register, Signatur und
   Evidence im Profil weiter normalisieren.
3. Workspace/Auth mit synthetischem Demo-Tenant und metadata-only Workspace
   verproben.
4. ATP/Onboarding als nicht-sensitive Statusprojektion und Request-Store
   stabilisieren.
5. Gebühren/GNotKG vom technischen Kostenentwurf zum notariell geprüften
   Review-Gate ausbauen.
6. Notariat-only Guardrails als automatischen Dokumenten- und Demo-Check
   ergänzen.

## Guardrails

- NaC ist ausschließlich für Notariate und notarielle Vorgangsarten.
- Diese Demo nutzt keine Mandatsdaten, keine Secrets, keine PINs, keine
  Login-Token, keine echten Register- oder Grundbuchinhalte.
- Diese Demo führt keine OCI writes, keine produktiven Provisionierungen,
  keine Release-Aktion und keine produktive XNP-Aktion aus.
- Jede Aussage muss als Modell, lokaler Readiness-Nachweis, Fallback oder
  nächste Produktlücke erkennbar bleiben.
