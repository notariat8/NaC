# Persistente Onboarding-Anfrage Und Admin-Queue

Datum: 2026-06-10

NaC-Issue: https://github.com/notariat8/NaC/issues/83

NaC-Adapter-Issue: https://github.com/notariat8/NaC/issues/85

OCI-Issue: https://github.com/notariat8/oci-landing-zone/issues/44

## Entscheidung

Nach erfolgreicher DNS-Bestätigung erzeugt notariat8 eine echte
Onboarding-Anfrage mit stabiler `request_id`. Diese Anfrage ist der erste
persistente Status im Neukunden-Onboarding. Sie ersetzt statische Admin-Queue-
Vorschauen durch einen nachvollziehbaren Request-Lifecycle.

Die Zielpersistenz ist OCI ATP. Ohne produktiv konfigurierten Store darf die
öffentliche POST-Route nicht still in lokale Dateien, `/tmp`, Git oder
In-Memory-State schreiben. Sie muss fail-closed antworten oder sichtbar als
nicht aktiviert gelten.

## Alternativen

### Nicht Gewählt: Lokale Datei Oder `/tmp`

Eine lokale Datei wäre schnell, aber kein echter SaaS-Betrieb. Sie würde im
Functions-Betrieb nicht belastbar sein, könnte nach Cold Starts verschwinden
und würde die Architektur später vernebeln.

### Nicht Gewählt: GitHub Issues Als Kundenqueue

GitHub ist die Steuerungs- und Review-Ebene für Entwicklung und Governance,
nicht die produktive Kunden-Onboarding-Datenbank. Kunden-E-Mail-Adressen und
Lifecycle-Status gehören nicht als produktiver App-State in GitHub Issues.

### Gewählt: ATP-Backed Request Store

ATP ist der Zielstore für `tenant_registry` und `onboarding_requests`. NaC
spricht diesen Store über einen kleinen Repository-Vertrag an. Die Function
nutzt nur serverseitige Konfiguration und später Vault/Resource-Principal-
fähige Secrets. Keine Credentials stehen in Git, Chat, Query-Parametern oder
HTML.

## Customer Workflow

1. Kunde öffnet die DNS-Erfolgsseite.
2. Kunde sieht Domain, verantwortliche E-Mail-Adresse und Status.
3. Kunde klickt `Einrichtung anfragen`.
4. NaC validiert Domain, Tenant-Referenz, E-Mail-Adresse und DNS-Status.
5. NaC erzeugt eine stabile `request_id`.
6. Kunde sieht `Anfrage eingegangen`, `E-Mail-Prüfung ausstehend` und
   `Einladung noch nicht versendet`.

Die Kundensicht verwendet nur `notariat8` als Produktbegriff. Sie zeigt keine
OCI-, Oracle-, NaC-internen, Admin-Queue-, Tenant-Slug- oder Provider-Details.

## SaaS-Admin Workflow

1. `/admin/onboarding` listet echte Onboarding-Anfragen aus dem Store.
2. Jede Anfrage zeigt `request_id`, Domain, verantwortliche E-Mail-Adresse,
   DNS-Status, Request-Status und nächsten Owner-Schritt.
3. Der SaaS-Admin kann daraus ein Review-Artefakt vorbereiten.
4. Produktive Identity-, Compartment-, ATP- oder Einladungs-Writes bleiben an
   separate Owner-Apply-Gates gebunden.

## Request Contract

Minimaler Request:

```json
{
  "schema_version": "nac.onboarding-request/v0.1",
  "request_id": "onr_...",
  "domain": "kanzlei-notariat.example",
  "tenant_slug": "kanzlei-notariat",
  "admin_email": "verwaltung@kanzlei-notariat.example",
  "dns_status": "verified",
  "request_status": "submitted",
  "invitation_status": "not_sent",
  "created_at": "2026-06-10T00:00:00Z",
  "updated_at": "2026-06-10T00:00:00Z"
}
```

`request_id` ist nicht geheim. Es ist ein stabiler, auditierbarer Identifier
und darf in Links oder Admin-Views erscheinen. Er darf keine E-Mail-Adresse,
Domain-Hash-Geheimnisse oder Credentials enthalten.

## API Boundary

Die Functions-Runtime bleibt grundsätzlich GET/HEAD-only. Genau eine neue
POST-Ausnahme wird zugelassen:

- `POST /onboarding/requests`

Diese Route akzeptiert nur Domain, Tenant-Referenz und verantwortliche
E-Mail-Adresse. Sie akzeptiert keine Mandatsdaten, keine Dateien, keine
Ausweise, keine Geschäftswerte, keine API Keys und keine Tokens.

Wenn kein Store konfiguriert ist, antwortet die Route mit einem klaren
Service-Status und schreibt nichts.

## Store Boundary

Der NaC-Code definiert einen kleinen Store-Vertrag:

- `create_request(payload)`,
- `get_request(request_id)`,
- `list_requests(limit)`.

Der produktive Adapter ist ATP-backed. Ein Testadapter darf nur in Unit-Tests
verwendet werden und nicht in der live Function-Konfiguration aktiviert sein.

## ATP-Zielmodell

Erste Tabellen:

- `tenant_registry`
- `onboarding_requests`

Pflichtfelder in `onboarding_requests`:

- `request_id`
- `tenant_id`
- `tenant_slug`
- `domain`
- `admin_email`
- `dns_status`
- `request_status`
- `invitation_status`
- `created_at`
- `updated_at`
- `created_by_surface`

Spätere Erweiterungen für Audit-Events, Vertragsstatus, AVV-Status und
Apply-Artefakte müssen ohne Schema-Bruch möglich sein.

## Sicherheitsgrenzen

- Keine Mandatsdaten im Onboarding-Request.
- Keine Credentials im Request, HTML, Querystring, Log oder Git.
- Kein lokaler produktiver Fallback-Speicher.
- Kein produktiver Identity-Apply in diesem Slice.
- Kein E-Mail-Versand in diesem Slice.
- Kein Endkunden-Zugriff auf OCI Console.

## Akzeptanz

- Die Kundenseite bietet nach DNS-Erfolg `Einrichtung anfragen`.
- Bei deaktiviertem Store schreibt `POST /onboarding/requests` nichts und
  antwortet fail-closed.
- Tests belegen, dass keine internen oder Anbieterbegriffe in Kunden-HTML
  erscheinen.
- Die Admin-Queue kann echte Request-Objekte rendern.
- Der ATP-Infrastruktur-Track ist getrennt und Apply-gated.
