# Kundenzentrierte DNS-Erfolgsseite Implementierungsplan

> **Für agentische Worker:** ERFORDERLICHE SUB-SKILL: Nutze superpowers:subagent-driven-development (empfohlen) oder superpowers:executing-plans, um diesen Plan Schritt für Schritt umzusetzen. Schritte nutzen Checkboxen (`- [ ]`) zur Nachverfolgung.

**Ziel:** Die öffentliche DNS-Erfolgsseite soll wie ein kundengerichteter notariat8-Einrichtungsstatus wirken, nicht wie eine interne DNS-Diagnoseseite.

**Architektur:** Das bestehende Routing in `NaCLocalWebApp._tenant_dns_check_page` bleibt erhalten; geändert wird nur der HTML-Zweig für den öffentlichen Kontext. Die öffentliche Ansicht bekommt klarere Labels, sichtbare Domain-/E-Mail-Rückspiegelung und keine internen oder anbieterbezogenen Begriffe. Interne DNS-Diagnosen bleiben unverändert.

**Tech Stack:** Python-stdlib-HTTP-App, `unittest`, bestehendes NaC Quality Gate.

---

### Aufgabe 1: Assertions für die DNS-Erfolgsseite

**Dateien:**
- Ändern: `tests/test_nac_web.py`
- Referenz: `src/nac_web/server.py`

- [x] **Schritt 1: Fehlenden Test schreiben**

`test_www_n8_prospect_dns_check_stays_customer_facing` so erweitern, dass die öffentliche DNS-Erfolgsseite folgende Inhalte enthalten muss:

```python
self.assertIn("Einrichtungsstatus öffnen", html)
self.assertIn("E-Mail-Adresse prüfen", html)
self.assertIn("Einladung noch nicht versendet", html)
self.assertIn("Technischer Nachweis", html)
self.assertIn("admin@kanzlei-notariat.example", html)
self.assertNotIn("Domain-Readiness öffnen", html)
self.assertNotIn("notariat8 führt Sie anschließend", html)
```

- [x] **Schritt 2: Test ausführen und erwartetes Fehlschlagen prüfen**

Ausführen:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_www_n8_prospect_dns_check_stays_customer_facing
```

Erwartung: FAIL, weil die aktuelle Seite noch `Domain-Readiness öffnen` nutzt und die neuen Kundeneinrichtungs-Labels nicht zeigt.

### Aufgabe 2: Öffentliche DNS-Seiten-Copy

**Dateien:**
- Ändern: `src/nac_web/server.py`
- Test: `tests/test_nac_web.py`

- [x] **Schritt 1: Minimale HTML-Änderung implementieren**

In `_tenant_dns_check_page` nur den `public_context`-Zweig ändern:

- `notariat8 Domain-Check` beibehalten,
- `Einrichtungsstatus öffnen` für den Link zur Einrichtungsseite nutzen,
- eine Kundenangaben-Kachel mit Domain, verantwortlicher E-Mail-Adresse, Domain-Status und Einladungsstatus anzeigen,
- den DNS-Abschnitt in `Technischer Nachweis` umbenennen,
- vage nächste Schritte durch `E-Mail-Adresse prüfen`, `Einrichtung freigeben` und `Einladung noch nicht versendet` ersetzen.

- [x] **Schritt 2: Zieltests ausführen**

Ausführen:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_nac_web.NaCLocalWebTests.test_www_n8_prospect_dns_check_stays_customer_facing tests.test_nac_web.NaCLocalWebTests.test_customer_dns_check_page_renders_live_dns_result_without_raw_json
```

Erwartung: OK.

### Aufgabe 3: Verifikation und PR

**Dateien:**
- Prüfen: `src/nac_web/server.py`
- Prüfen: `tests/test_nac_web.py`
- Prüfen: `docs/de/superpowers/specs/2026-06-10-customer-dns-success-ux-design.md`

- [x] **Schritt 1: Vollständige Tests und Quality Checks ausführen**

Ausführen:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
GITHUB_BASE_REF=main /home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Erwartung: Tests OK, keine Whitespace-Fehler, striktes Quality Gate PASSED.

- [ ] **Schritt 2: Commit erstellen und geschützten PR öffnen**

Commit-Message:

```bash
feat: clarify customer dns success page
```

PR-Titel:

```text
P1: Clarify customer DNS success page
```

Der PR-Text muss `Closes #81` verlinken und festhalten, dass das Deployment nach dem Merge ein Owner Release Approval braucht.
