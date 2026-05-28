# Single-Repo-Plan Für Notariats-Usecases

## Ziel

Dieser Plan ersetzt die frühere Mehrbranchen-Migrationsidee. NaC bleibt ein
Repository für Notariat as Code. Die Zielstruktur trennt gemeinsame
Notariatsregeln, konkrete notarielle Usecases, Runtime und Integrationen.

## Zielstruktur

```text
usecases/
  immobilienkaufvertrag/
  unterschriftsbeglaubigung/
  online-gmbh-gruendung/
  handelsregisteranmeldung/
workflows/
plugins/
policies/
docs/
```

## Prinzipien

- Neue fachliche Beispiele entstehen nur als notarielle Usecases unter
  [usecases/](../../../usecases).
- Gemeinsame Regeln gehören in [policies/](../../../policies) und werden in
  Agentenflächen gespiegelt.
- Technische Runtime-Fixtures unter [processes/](../../../processes) sind keine
  zusätzlichen Produktbeispiele.
- Nicht-notarielle Produktpfade werden nicht aufgenommen.

## Umsetzungsschritte

1. **Scope fixieren**
   - Notariats-Scope in Policy, README, START_HERE und Agentenregeln spiegeln.
2. **Usecase-Katalog führen**
   - bestehende Usecases nach Reifegrad und Pilotfähigkeit pflegen.
3. **Runtime-Fixtures abgrenzen**
   - technische Prozessbeispiele als Kompatibilitäts- und Testmaterial
     kennzeichnen.
4. **Pilot-Usecase auswählen**
   - zuerst Immobilienkaufvertrag oder Unterschriftsbeglaubigung mit
     synthetischen Daten pilotieren.
5. **Release-Binding prüfen**
   - laufende Vorgänge bleiben auf gebundener Version; neue Versionen gelten
     nur für neue Vorgänge.

## Risiken Und Maßnahmen

- **Risiko:** alte Mehrbranchenbegriffe tauchen in Doku oder Prompts wieder auf.
  **Maßnahme:** Suchlauf nach nicht-notariellen Produktpfaden vor PR-Abschluss.
- **Risiko:** technische Fixtures werden als Produktbeispiele missverstanden.
  **Maßnahme:** README und Startdokumente verweisen für Beispiele nur auf
  [usecases/](../../../usecases).
- **Risiko:** lokale Notariatsvarianten verwischen den Referenzstandard.
  **Maßnahme:** Varianten nur per Change Request, Review und Version-Binding.

## Exit-Kriterien

- README-, START_HERE-, Policy- und Agentenflächen nennen NaC als
  Notariat-only.
- Onboarding-Prompts verweisen nur auf Notariats-Usecases.
- Issue #3 beschreibt notarielle Beispielprozesse statt nicht-notarieller Produktpfade.
- `nac doctor --profile strict` besteht.
