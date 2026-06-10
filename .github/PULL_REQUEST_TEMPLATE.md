## Geschäftsvorgang

- Prozessklasse:
- Request-ID:
- Fachlicher Zweck:
- Ausführende Rolle:
- Entscheidungstyp (`self_resolve|requires_review|requires_approval`):
- Qualifikation erforderlich (falls ja, welche):

## GitHub-first Steuerung

- Führendes Issue:
- Project: `NaC Control Plane`
- Delivery Mode: `Owner Direct | Protected PR | Sync PR`
- Risk Gate: `None | Privacy | Secrets | Workflow | Policy | External Service | Human Approval`
- Project-Status:
- Blocker:
- Secrets/Mandatsdaten: keine Secrets, PINs, Tokens, privaten Dokumentinhalte oder echten Mandatsdaten enthalten

## Spec-Traceability

- Spec:
- Plan:
- Akzeptanzkriterien:
  - AC-001:
- AC-IDs:
- Test-/Validator-Nachweis:

## Validierung

- [ ] Prozessdatei liegt unter `processes/`
- [ ] Python-Validierung war erfolgreich
- [ ] Idempotenz wurde geprüft
- [ ] Keine unnötigen vertraulichen Daten im Diff
- [ ] Keine echten personenbezogenen Daten im Diff
- [ ] Keine Secrets oder Zugangsdaten im Diff

## Freigabe

- [ ] Fachliche Freigabe erfolgt
- [ ] Bei sensiblen Prozessen ist ein Reviewer zugewiesen
- [ ] Notwendige Folgeaktionen oder externe Abgaben sind dokumentiert

## Nachweise

- Referenzen:
- Externe Tickets:
- Export- oder Abschlussbedarf:
- Bei Prozessversion/Release:
  [docs/de/operations/release-checklist.md](https://github.com/notariat8/NaC/blob/main/docs/de/operations/release-checklist.md)
  ausgefüllt oder im führenden Issue nachvollziehbar referenziert
