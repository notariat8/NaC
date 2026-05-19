const navToggle = document.querySelector(".nav-toggle");
const siteNav = document.querySelector(".site-nav");
const caseSearch = document.querySelector("[data-case-search]");
const caseList = document.querySelector("[data-case-list]");
const caseRows = Array.from(document.querySelectorAll("[data-case]"));
const panels = Array.from(document.querySelectorAll("[data-app-panel]"));
const areaTabs = Array.from(document.querySelectorAll("[data-area-tab]"));
const panelButtons = Array.from(document.querySelectorAll("[data-open-panel]"));
const areaTitle = document.querySelector("[data-area-title]");
const areaSummary = document.querySelector("[data-area-summary]");
const areaCount = document.querySelector("[data-area-count]");
const configForm = document.querySelector("[data-config-form]");
const configReload = document.querySelector("[data-config-reload]");
const configStatus = document.querySelector("[data-config-status]");
let activeArea = document.querySelector("[data-area-tab].is-active")?.dataset.areaTab || "allgemeines-zivilrecht";

const areaCopy = {
  immobilienrecht: {
    title: "Immobilienrecht",
    summary: "Immobilienkauf, Grundschuld, WEG, Löschung und Übertragung als tägliche Büroarbeit.",
  },
  "gesellschaft-register": {
    title: "Gesellschaft & Register",
    summary: "Registeranmeldung, GmbH-/UG-Gründung, Geschäftsanteile, Beschlüsse und Vereinsregister.",
  },
  erbrecht: {
    title: "Erbrecht",
    summary: "Testament, Erbvertrag, Erbschein, Erbausschlagung und Verzichtsvorgänge.",
  },
  "familienrecht-vorsorge": {
    title: "Familienrecht & Vorsorge",
    summary: "Ehevertrag, Scheidungsfolgen, Adoption, Vorsorgevollmacht und gerichtsfeste Vollmachten.",
  },
  "allgemeines-zivilrecht": {
    title: "Allgemeines Zivilrecht",
    summary: "Beglaubigungen und weitere zivilrechtliche Büroprozesse ohne eigenes Spezialgebiet.",
  },
};

if (navToggle && siteNav) {
  navToggle.addEventListener("click", () => {
    const isOpen = siteNav.classList.toggle("open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });
}

if (caseSearch && caseRows.length) {
  caseSearch.addEventListener("input", filterCases);
}

sortCaseRows();

areaTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    activeArea = tab.dataset.areaTab || activeArea;
    showPanel("cases");
    filterCases();
    closeNavigation();
  });
});

panelButtons.forEach((button) => {
  button.addEventListener("click", () => {
    showPanel(button.dataset.openPanel || "cases");
    closeNavigation();
  });
});

if (configForm) {
  configForm.addEventListener("submit", saveOperatorConfig);
}

if (configReload) {
  configReload.addEventListener("click", loadOperatorConfig);
}

showPanel("cases");
filterCases();
loadOperatorConfig();

function showPanel(panelName) {
  panels.forEach((panel) => {
    panel.classList.toggle("is-hidden", panel.dataset.appPanel !== panelName);
  });

  areaTabs.forEach((tab) => {
    const isActiveArea = panelName === "cases" && tab.dataset.areaTab === activeArea;
    tab.classList.toggle("is-active", isActiveArea);
    tab.setAttribute("aria-pressed", String(isActiveArea));
  });

  panelButtons.forEach((button) => {
    const isActivePanel = button.dataset.openPanel === panelName;
    button.classList.toggle("is-active", isActivePanel);
    button.setAttribute("aria-pressed", String(isActivePanel));
  });

  if (panelName === "konfig") {
    loadOperatorConfig();
  }
}

function filterCases() {
  const query = (caseSearch?.value || "").trim().toLowerCase();
  const copy = areaCopy[activeArea] || areaCopy.immobilienrecht;
  let visibleCount = 0;

  if (areaTitle) {
    areaTitle.textContent = copy.title;
  }

  if (areaSummary) {
    areaSummary.textContent = copy.summary;
  }

  caseRows.forEach((row) => {
    const haystack = `${row.textContent || ""} ${row.dataset.case || ""}`.toLowerCase();
    const matchesArea = row.dataset.area === activeArea;
    const matchesQuery = query.length === 0 || haystack.includes(query);
    const isVisible = matchesArea && matchesQuery;
    row.classList.toggle("is-hidden", !isVisible);
    if (isVisible) {
      visibleCount += 1;
    }
  });

  if (areaCount) {
    const suffix = visibleCount === 1 ? "Vorgang" : "Vorgänge";
    areaCount.textContent = `${visibleCount} ${suffix}`;
  }
}

function sortCaseRows() {
  if (!caseList || !caseRows.length) {
    return;
  }

  caseRows
    .sort((left, right) => caseTitle(left).localeCompare(caseTitle(right), "de", { sensitivity: "base" }))
    .forEach((row) => caseList.appendChild(row));
}

function caseTitle(row) {
  return row.querySelector("h2")?.textContent?.trim() || "";
}

function closeNavigation() {
  if (!siteNav || !navToggle) {
    return;
  }

  siteNav.classList.remove("open");
  navToggle.setAttribute("aria-expanded", "false");
}

async function loadOperatorConfig() {
  if (!configForm || !configStatus) {
    return;
  }

  configStatus.dataset.status = "running";
  configStatus.innerHTML = "<p>Lokale Konfiguration wird geladen.</p>";

  try {
    const response = await fetch(hardwareBridgeUrl("/api/operator-config"));
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    const payload = await response.json();
    fillOperatorConfig(payload.values || {});
    renderOperatorConfigStatus(payload);
  } catch (error) {
    configStatus.dataset.status = "error";
    configStatus.innerHTML = `<h3>Konfiguration nicht erreichbar</h3><p>Lokalen Adapter starten: <code>python scripts\\nac.py operator --open</code></p>`;
  }
}

async function saveOperatorConfig(event) {
  event.preventDefault();
  if (!configForm || !configStatus) {
    return;
  }

  configStatus.dataset.status = "running";
  configStatus.innerHTML = "<p>Lokale Konfiguration wird gespeichert.</p>";

  try {
    const response = await fetch(hardwareBridgeUrl("/api/operator-config"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ values: readOperatorConfigFields() }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.error || `${response.status} ${response.statusText}`);
    }
    fillOperatorConfig(payload.values || {});
    renderOperatorConfigStatus(payload, "Konfiguration gespeichert");
  } catch (error) {
    configStatus.dataset.status = "error";
    configStatus.innerHTML = `<h3>Speichern fehlgeschlagen</h3><p>${escapeHtml(error.message || "Unbekannter Fehler")}</p>`;
  }
}

function readOperatorConfigFields() {
  const values = {};
  configForm.querySelectorAll("[data-config-field]").forEach((field) => {
    values[field.dataset.configField] = field.value.trim();
  });
  return values;
}

function fillOperatorConfig(values) {
  if (!configForm) {
    return;
  }
  configForm.querySelectorAll("[data-config-field]").forEach((field) => {
    field.value = values[field.dataset.configField] || "";
  });
}

function renderOperatorConfigStatus(payload, title = "Konfiguration geladen") {
  if (!configStatus) {
    return;
  }
  const values = payload.values || {};
  const status = payload.status || {};
  const dataRepoState = status.data_repo_exists
    ? `${status.data_repo_git_present ? "Git-Repo" : "Ordner ohne Git"}`
    : "Ordner fehlt lokal";
  const dataRemote = status.data_repo_remote || values.data_git_url || "nicht gesetzt";

  configStatus.dataset.status = "ready";
  configStatus.innerHTML = `
    <h3>${escapeHtml(title)}</h3>
    <ul>
      <li>NaC Git: ${escapeHtml(values.nac_fork_git_url || status.nac_git_origin || "nicht gesetzt")}</li>
      <li>Daten-Git: ${escapeHtml(dataRemote)}</li>
      <li>Datenordner: ${escapeHtml(values.data_repo_path || "nicht gesetzt")} (${escapeHtml(dataRepoState)})</li>
    </ul>
  `;
}

document.querySelectorAll("[data-hardware-test]").forEach((hardwareTest) => {
  const triggers = Array.from(hardwareTest.querySelectorAll("[data-hardware-test-trigger]"));
  const result = hardwareTest.querySelector("[data-hardware-test-result]");

  triggers.forEach((trigger) => trigger.addEventListener("click", async () => {
    if (!result) {
      return;
    }

    triggers.forEach((button) => {
      button.disabled = true;
    });
    result.dataset.status = "running";
    result.innerHTML = `<p>${hardwareTest.dataset.runningLabel}</p>`;

    try {
      const response = await fetch(hardwareBridgeUrl("/api/hardware-readiness"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ requested_by: trigger.dataset.requestedBy || "nac-local-operator-webapp" }),
      });

      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }

      const payload = await response.json();
      renderHardwareResult(result, payload, hardwareTest.dataset.emptyLabel || "No detailed checks received.");
    } catch (error) {
      result.dataset.status = "error";
      result.innerHTML = `<h3>${hardwareTest.dataset.unavailableLabel}</h3><p>Lokalen Adapter starten: <code>python scripts\\nac.py operator --open</code></p>`;
    } finally {
      triggers.forEach((button) => {
        button.disabled = false;
      });
    }
  }));
});

function hardwareBridgeUrl(path) {
  const isLocalHttp = (window.location.protocol === "http:" || window.location.protocol === "https:")
    && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  if (isLocalHttp) {
    return path;
  }

  return `http://127.0.0.1:8766${path}`;
}

function renderHardwareResult(target, payload, emptyLabel) {
  const locale = currentLocale();
  const status = payload?.overall_status || "unknown";
  const checks = Array.isArray(payload?.readiness?.checks) ? payload.readiness.checks : [];
  const visibleChecks = checks.slice(0, 8);
  target.dataset.status = status;

  const counts = countCheckStatuses(checks);
  const summary = [
    `${uiText(locale, "passed")}: ${counts.passed || 0}`,
    `${uiText(locale, "manual")}: ${counts.manual_review || 0}`,
    `${uiText(locale, "failed")}: ${(counts.failed || 0) + (counts.blocked || 0)}`,
  ].join(" · ");

  const checkItems = visibleChecks.map((check) => {
    const copy = localizedCheck(check, locale);
    const title = escapeHtml(copy.title);
    const checkStatus = escapeHtml(statusLabel(check.status || "unknown", locale));
    const message = escapeHtml(copy.message);
    return `<li><span class="hardware-status">${checkStatus}</span> ${title}<br>${message}</li>`;
  }).join("");

  const warnings = Array.isArray(payload?.startup_check?.warnings) ? payload.startup_check.warnings : [];
  const warningText = warnings.length
    ? `<div class="hardware-warning"><strong>${uiText(locale, "notes")}</strong><ul>${warnings.slice(0, 3).map((warning) => `<li>${escapeHtml(cleanWarning(warning))}</li>`).join("")}</ul></div>`
    : "";
  const hint = status === "manual_review"
    ? `<p class="hardware-hint">${uiText(locale, "manualHint")}</p>`
    : "";

  target.innerHTML = `
    <h3>${uiText(locale, "overallStatus")}: ${escapeHtml(statusLabel(status, locale))}</h3>
    <p class="hardware-summary">${escapeHtml(summary)}</p>
    ${hint}
    ${warningText}
    ${checkItems ? `<ul class="hardware-check-list">${checkItems}</ul>` : `<p>${escapeHtml(emptyLabel)}</p>`}
  `;
}

function currentLocale() {
  return (document.documentElement.lang || "de").toLowerCase().startsWith("en") ? "en" : "de";
}

function countCheckStatuses(checks) {
  return checks.reduce((counts, check) => {
    const status = check?.status || "unknown";
    counts[status] = (counts[status] || 0) + 1;
    return counts;
  }, {});
}

function statusLabel(status, locale) {
  const labels = {
    de: {
      passed: "erfolgreich",
      ready: "bereit",
      manual_review: "manuelle Prüfung erforderlich",
      blocked: "blockiert",
      failed: "fehlgeschlagen",
      error: "Fehler",
      running: "läuft",
      unknown: "unbekannt",
    },
    en: {
      passed: "passed",
      ready: "ready",
      manual_review: "manual review required",
      blocked: "blocked",
      failed: "failed",
      error: "error",
      running: "running",
      unknown: "unknown",
    },
  };
  return labels[locale][status] || status;
}

function uiText(locale, key) {
  const labels = {
    de: {
      overallStatus: "Gesamtstatus",
      passed: "Erfolgreich",
      manual: "Manuell offen",
      failed: "Fehler",
      notes: "Hinweise",
      manualHint: "Die lokale Hardware-Basis ist teilweise erfolgreich. Für die fachliche Freigabe bleiben manuelle Bestätigungen oder XNP-/SAK-/secureFramework-Pfade offen.",
    },
    en: {
      overallStatus: "Overall status",
      passed: "Passed",
      manual: "Manual",
      failed: "Failed",
      notes: "Notes",
      manualHint: "The local hardware baseline is partially successful. Domain approval still needs manual confirmations or XNP/SAK/secureFramework paths.",
    },
  };
  return labels[locale][key] || key;
}

function localizedCheck(check, locale) {
  const fallback = {
    title: check.title || check.id || "Check",
    message: check.message || "",
  };
  const copy = {
    de: {
      bnotk_card_present: {
        title: "BNotK Chip-/Signaturkarte",
        message: "Die Verfügbarkeit der Karte muss manuell bestätigt werden.",
      },
      rfid_disabled: {
        title: "RFID für BNotK-Chipkartenworkflow deaktiviert",
        message: "RFID-off oder Nichtnutzung muss manuell bestätigt werden.",
      },
      windows_driver_stack: {
        title: "Windows REINER SCT Treiberstack",
        message: "DriverPackage und SmartCardReader-Treiberanbieter sind sichtbar.",
      },
      windows_morris_stack: {
        title: "Windows morris Browser-Middleware",
        message: "REINER SCT morris ist installiert und läuft lokal.",
      },
      windows_morris_loopback_api: {
        title: "Windows morris Loopback-API",
        message: "morris erreicht PC/SC und meldet einen REINER SCT/cyberJack-Leser.",
      },
      pcsc_service: {
        title: "PC/SC-Dienst",
        message: "Der Windows-Smartcard-Dienst läuft.",
      },
      reader_detection: {
        title: "Kartenleser-Erkennung",
        message: "Mindestens ein relevanter lokaler Kartenleser wurde erkannt.",
      },
      sak_or_xnp_card_path: {
        title: "BNotK SAK lite oder XNP-Kartenpfad",
        message: "SAK-lite oder XNP-Kartenpfad wurde nicht automatisch erkannt.",
      },
      secureframework: {
        title: "secureFramework",
        message: "secureFramework wurde nicht automatisch erkannt.",
      },
      xnp_local_interface: {
        title: "XNP-Localhost-Schnittstelle",
        message: "Im erwarteten Portbereich wurde keine XNP-Localhost-Schnittstelle erreicht.",
      },
      ausweisapp_status: {
        title: "AusweisApp-Status",
        message: "Der lokale AusweisApp-Statusendpunkt ist nicht erreichbar.",
      },
    },
  };
  return copy[locale]?.[check.id] || fallback;
}

function cleanWarning(warning) {
  return String(warning).replace(/^WARN:\s*/, "");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
