# Notarkammer-Demo: Einstieg

Dieser Ordner enthält die vorbereitete Demo-Landkarte für die Vorstellung von
notariat8 bei der Notarkammer. Der Pfad ist auf eine ungefähr einstündige
Vorführung ausgelegt: öffentliche Orientierung auf `notariat8.de`, fachliche
Prozessmodellierung (BPMN), XNP-/Kartenleser-Grenzen, Login in
`app.notariat8.de` und ein bewusst geschlossener Arbeitsbereich, bis Sitzung
und Rolle geprüft sind.

## Vorführbarer Kernpfad

1. Öffentliche Orientierung über `https://notariat8.de`.
2. Vorgang `Immobilienkaufvertrag` und BPMN-Ansicht zeigen.
3. Immobilienkaufvertrag als Primärfluss erläutern: Entwurf, Beurkundung,
   Vollzug, Grundbuch, Finanzierung, Gemeinde/Steuer, Löschungen und
   Rückläufe.
4. Dauer, parallele Schritte und kritischen Pfad erläutern.
5. XNP, SNP, Kartenleser, Register und Grundbuch als fachliche
   Zugriffspunkte erklären, ohne produktive Einreichungen oder produktiven
   API-Zugriff zu behaupten.
6. Wechsel zu `https://app.notariat8.de`, Login und fail-closed-Grenze zeigen.
7. ATP-Healthcheck und Store-Gate nur als technischen Statusnachweis nennen,
   nicht als Mandatsdatenansicht.

## Dokumente in empfohlener Reihenfolge

| Zweck | Dokument |
| --- | --- |
| Vorbereitung vor der Vorführung | [notarkammer-2026-06-demo-preflight.md](notarkammer-2026-06-demo-preflight.md) |
| Live-Reihenfolge und Browserpfade | [notarkammer-2026-06-live-demo-runbook.md](notarkammer-2026-06-live-demo-runbook.md) |
| Login-/Portal-Diagnose und Fallback-Ampel | [notarkammer-2026-06-login-portal-diagnostics-runbook.md](notarkammer-2026-06-login-portal-diagnostics-runbook.md) |
| 60-Minuten-Skript | [notarkammer-2026-06-60-minute-live-demo-script.md](notarkammer-2026-06-60-minute-live-demo-script.md) |
| Smoke-Readiness und Fallbacks | [notarkammer-2026-06-demo-smoke-readiness.md](notarkammer-2026-06-demo-smoke-readiness.md) |
| Go/No-Go-Entscheidung | [notarkammer-2026-06-demo-go-no-go.md](notarkammer-2026-06-demo-go-no-go.md) |
| Merge-Reihenfolge und Live-Test-Karte | [notarkammer-2026-06-merge-order-live-test-card.md](notarkammer-2026-06-merge-order-live-test-card.md) |
| Bekannte Lücken und Grenzen | [notarkammer-2026-06-demo-gap-audit.md](notarkammer-2026-06-demo-gap-audit.md) |
| Fragen und Einwände | [notarkammer-2026-06-demo-qa-objection-handling.md](notarkammer-2026-06-demo-qa-objection-handling.md) |
| Dauer, Parallelität und kritischer Pfad | [notarkammer-bpmn-critical-path-talking-points.md](notarkammer-bpmn-critical-path-talking-points.md) |
| Immobilienkaufvertrag als XNP/SNP-Vollzugspfad | [notarkammer-immobilienkaufvertrag-xnp-vollzug-map.md](notarkammer-immobilienkaufvertrag-xnp-vollzug-map.md) |
| Evidence-Matrix zum Immobilienkaufvertrag | [notarkammer-immobilienkaufvertrag-xnp-evidence-matrix.md](notarkammer-immobilienkaufvertrag-xnp-evidence-matrix.md) |
| XNP/BPMN-Demotiefe | [notarkammer-xnp-bpmn-demo-depth.md](notarkammer-xnp-bpmn-demo-depth.md) |
| XNP-Demovertrag und Grenzen | [notarkammer-xnp-demo-contract.md](notarkammer-xnp-demo-contract.md) |
| Quellenmatrix zu XNP, XNotar, Register, Grundbuch und Kartenleser | [notarkammer-xnp-quellenmatrix.md](notarkammer-xnp-quellenmatrix.md) |
| ISV-Fragen zu XNP/SNP API- und Testzugang | [notarkammer-xnp-snp-api-testzugang.md](notarkammer-xnp-snp-api-testzugang.md) |

## Grenzen

- no mandate data
- no secrets
- no productive filing
- Keine echten Mandatsdaten, Ausweise, Urkunden, Registerabrufe oder
  Grundbuchabrufe.
- Keine produktive XNP-Handlung und keine produktive Register- oder
  Grundbucheinreichung.
- Keine Behauptung produktiver XNP-/SNP-API-Nutzung; API- und Testzugänge
  werden als offene ISV-Fragen an BNotK und Notarkammer formuliert.
- Keine Zugangsdaten, Tokens, Secrets, PINs oder Anbieterbetriebsdetails in der
  Vorführung.
- Wenn Login, Sitzung, Rollenprüfung oder Store-Gate nicht sauber öffnen,
  bleibt die App fail-closed und die Demo wechselt auf Skript, BPMN und
  dokumentierte Nachweise.
