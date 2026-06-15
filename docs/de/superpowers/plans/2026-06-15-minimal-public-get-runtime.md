# Implementierungsplan: Minimaler Public-GET-Runtime

Status: gestartet am 2026-06-15

## Ziel

Die kundenseitigen Public-GET-Routen von notariat8 sollen nicht mehr den
vollständigen lokalen Webserver-Pfad starten. Der Public-GET-Entrypoint nutzt
stattdessen einen kleinen, eigenständigen Runtime-Pfad für:

- `/healthz`
- `/api/tenant/login-intent`
- `/onboarding/readiness`
- `/onboarding/dns-check`

Der bestehende stateful Runtime-Pfad bleibt für POST, Callback, Operator,
BPMN, Knowledge-Graph, GNotKG und weitere interne Routen zuständig.

## Architekturentscheidung

Ansatz A: minimaler Public-GET-Runtime zuerst, Protected PR only, kein OCI
Apply. Der neue Runtime-Pfad darf nicht `nac_web.server`,
`NaCLocalWebApp` oder den generischen `nac_web.oci_functions`-Dispatcher
importieren. Er verwendet nur die leichten Identitäts- und
Onboarding-Helfer, die für die öffentlichen GET-Seiten nötig sind.

## Umsetzung

1. Einen roten Adapter-Test ergänzen, der den Import des generischen
   Dispatchers im Public-GET-Adapter verbietet.
2. Einen minimalen Public-GET-Dispatcher mit eigenem Response-Objekt,
   Request-Parsing, JSON-/HTML-Helfern und fail-closed Routen-Grenze
   ergänzen.
3. `/healthz`, Login-Intent, Readiness und DNS-Check im minimalen Pfad
   abbilden.
4. Kundenseitige Texte ohne Anbieter- oder Infrastruktursprache halten:
   sichtbar ist `notariat8`, nicht der Cloud-Anbieter.
5. Stateful Routen im Public-GET-Adapter weiter geschlossen halten.

## Tests

Pflichtnachweise vor PR:

- fokussierte Public-GET-Tests in `tests.test_oci_functions_adapter`
- vollständiger OCI-Functions-Adaptertest
- Web-Test `tests.test_nac_web`
- striktes NaC Quality Gate

## Governance

Dieser Track erzeugt nur einen Protected PR. Er enthält keine OCI-Schreibaktion,
keinen Resource-Manager-Apply, keinen Function-Deploy und keine Secret-Ausgabe.
