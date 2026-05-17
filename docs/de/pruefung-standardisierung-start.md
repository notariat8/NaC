# Pruefung Und Standardisierung: Nachvollziehbarkeit Von NoC

Dieses Dokument richtet sich an Stellen und Personen, die NoC aus Sicht von
Kontrolle, Standardisierung, Zertifizierung, Aufsichtnaehe oder fachlicher
Vergleichbarkeit bewerten. Es benennt keine konkrete Institution, sondern den
Pruefpfad im Repository.

## Was Bewertbar Ist

NoC macht nicht nur Prompts sichtbar, sondern auch:

- Rollen und Freigaben,
- technische und fachliche Gates,
- Datenschutz- und Datenklassenregeln,
- SBOM- und AI-SBOM-Bestandteile,
- Plugin-Grenzen und Integrationsannahmen,
- usecase-lokale Knowledge Graphs,
- Tests, Validatoren und Quality Gates.

## Was Nicht Bewertet Werden Sollte

- echte Mandatsdaten, weil sie nicht in dieses oeffentliche Repository gehoeren,
- produktive Arbeitsplatzkonfigurationen einzelner Bueros,
- externe Fachsysteminhalte, die nur referenziert werden,
- KI-Ausgaben als finale rechtliche Entscheidung.

## Pruefpfad

1. Sprach- und Rollenregeln lesen.
2. Datenschutz- und Speichergrenzen pruefen.
3. Usecase-KGs gegen fachliche Mindestanforderungen lesen.
4. Plugin-Grenzen und lokale Readiness-Checks pruefen.
5. Quality Gate lokal ausfuehren.
6. Version, Release, Fork- und Rueckflussmodell bewerten.

## Relevante Dateien

- [docs/de/reifegrad.md](reifegrad.md)
- [docs/de/glossar.md](glossar.md)
- [docs/de/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md)
- [policies/language-policy.yaml](../../policies/language-policy.yaml)
- [policies/data-protection-policy.yaml](../../policies/data-protection-policy.yaml)
- [policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)
- [docs/de/security-and-dsgvo.md](security-and-dsgvo.md)
- [docs/de/sbom-for-ai.md](sbom-for-ai.md)
- [docs/de/quality-gate.md](quality-gate.md)
- [usecases/README.md](../../usecases/README.md)
- [roadmap/GANTT.md](../../roadmap/GANTT.md)

## Lokale Reproduzierbarkeit

```bash
python scripts/quality_gate.py --profile strict
python scripts/validate_language_parity.py
python scripts/validate_knowledge_graph.py
python scripts/validate_plugins.py
```

## Standardisierungsfrage

NoC ist geeignet, wiederholbare fachliche Muster versioniert zu diskutieren:
Welche Vorgangsknoten sind erforderlich, welche Freigaben sind zwingend, welche
Nachweise duerfen nur referenziert werden, und welche Automatisierung bleibt
bewusst gesperrt?
