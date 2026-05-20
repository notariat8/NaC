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
const matterForm = document.querySelector("[data-matter-form]");
const matterFormTitle = document.querySelector("[data-matter-form-title]");
const matterFormStatus = document.querySelector("[data-matter-form-status]");
const matterSearch = document.querySelector("[data-matter-search]");
const matterList = document.querySelector("[data-matter-list]");
const matterListTitle = document.querySelector("[data-matter-list-title]");
const importList = document.querySelector("[data-import-list]");
const importCount = document.querySelector("[data-import-count]");
const importUploadForm = document.querySelector("[data-import-upload-form]");
const importUploadStatus = document.querySelector("[data-import-upload-status]");
const importExtractButton = document.querySelector("[data-import-extract]");
const importUploadFileInput = document.querySelector("[data-import-upload-files]");
let activeArea = document.querySelector("[data-area-tab].is-active")?.dataset.areaTab || "allgemeines-zivilrecht";
let activePanel = "cases";
let activeMatterUsecase = "";
let panelBackStack = [];
let matterState = { counts: {}, matters: [], status_labels: { open: "offen", waiting: "warten", completed: "abgeschlossen" } };
let importState = { counts: { pending: 0 }, proposals: [], status_labels: { pending: "neu", accepted: "übernommen", rejected: "abgelehnt" } };
let importExtractState = { metadata: {} };

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
enhanceCaseRows();
installPanelNavigation();

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

if (matterForm) {
  matterForm.addEventListener("submit", saveMatter);
}

if (matterSearch) {
  matterSearch.addEventListener("input", () => renderMatterList(activeMatterUsecase));
}

if (importUploadForm) {
  importUploadForm.addEventListener("submit", saveImportUpload);
}

if (importExtractButton) {
  importExtractButton.addEventListener("click", extractImportUploadMetadata);
}

if (importUploadFileInput) {
  importUploadFileInput.addEventListener("change", resetImportExtractState);
}

importUploadForm?.querySelector('[data-import-upload-field="person_name"]')?.addEventListener("input", resetImportExtractState);

window.addEventListener("focus", refreshVisibleData);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) {
    refreshVisibleData();
  }
});
setInterval(refreshVisibleData, 5000);

showPanel("cases", { pushHistory: false });
filterCases();
loadOperatorConfig();
loadMatters();
loadImportProposals();

function showPanel(panelName, options = {}) {
  if (options.pushHistory !== false && panelName !== activePanel) {
    panelBackStack.push(activePanel);
    panelBackStack = panelBackStack.slice(-12);
  }
  activePanel = panelName;
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

  if (panelName === "matters") {
    Promise.all([loadMatters(), loadImportProposals()]).then(() => renderMatterList(activeMatterUsecase));
  }

  if (panelName === "imports") {
    loadImportProposals().then(renderImportList);
  }
}

function installPanelNavigation() {
  panels.forEach((panel) => {
    if (panel.dataset.appPanel === "cases") {
      return;
    }
    const heading = panel.querySelector(".section-heading");
    if (!heading || heading.querySelector(".panel-navigation")) {
      return;
    }
    const navigation = document.createElement("div");
    navigation.className = "panel-navigation";
    navigation.innerHTML = `
      <button type="button" data-panel-back>← Zurück</button>
      <button type="button" data-panel-home>Übersicht</button>
    `;
    navigation.querySelector("[data-panel-back]")?.addEventListener("click", goBackPanel);
    navigation.querySelector("[data-panel-home]")?.addEventListener("click", goCasesPanel);
    heading.appendChild(navigation);
  });
}

function goBackPanel() {
  const previous = panelBackStack.pop() || "cases";
  showPanel(previous, { pushHistory: false });
  if (previous === "cases") {
    filterCases();
  }
}

function goCasesPanel() {
  panelBackStack = [];
  activeMatterUsecase = "";
  showPanel("cases", { pushHistory: false });
  filterCases();
}

async function refreshVisibleData() {
  if (document.hidden) {
    return;
  }
  if (activePanel === "imports") {
    await loadImportProposals();
    renderImportList();
    return;
  }
  if (activePanel === "matters") {
    await Promise.all([loadMatters(), loadImportProposals()]);
    renderMatterList(activeMatterUsecase);
    return;
  }
  if (activePanel === "cases") {
    await Promise.all([loadMatters(), loadImportProposals()]);
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

function enhanceCaseRows() {
  caseRows.forEach((row) => {
    const actions = row.querySelector(".case-actions");
    const slug = caseSlug(row);
    if (!actions || !slug || actions.dataset.enhanced === "true") {
      return;
    }
    actions.dataset.enhanced = "true";
    const title = caseTitle(row);

    const badges = document.createElement("div");
    badges.className = "matter-badges";
    badges.dataset.matterBadges = slug;
    badges.innerHTML = "<span>0 offen</span><span>0 warten</span><span>0 abgeschlossen</span>";

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.textContent = "Akten öffnen";
    openButton.className = "action-button primary";
    openButton.dataset.openMatters = slug;
    openButton.addEventListener("click", () => {
      activeMatterUsecase = slug;
      renderMatterList(slug);
      showPanel("matters");
    });

    const newButton = document.createElement("button");
    newButton.type = "button";
    newButton.textContent = "Neu";
    newButton.className = "action-button secondary";
    newButton.dataset.newMatter = slug;
    newButton.addEventListener("click", () => openMatterForm(slug, title));

    const dailyActions = document.createElement("div");
    dailyActions.className = "case-action-group case-action-group-daily";
    dailyActions.innerHTML = '<span class="case-action-label">Aktenverwaltung</span>';
    const dailyButtons = document.createElement("div");
    dailyButtons.className = "case-action-buttons";
    dailyButtons.append(openButton, newButton);
    dailyActions.append(badges, dailyButtons);

    const reviewActions = document.createElement("div");
    reviewActions.className = "case-action-group case-action-group-review";
    reviewActions.innerHTML = '<span class="case-action-label">Kontrolle</span>';
    const checklistLink = caseActionLink(`/kg/${slug}`, "Checkliste prüfen", "action-button secondary");
    reviewActions.append(checklistLink);

    const workflowActions = document.createElement("details");
    workflowActions.className = "case-workflow-actions";
    workflowActions.innerHTML = `
      <summary>Kanzlei-Workflow</summary>
      <p>Ablauf und Bearbeitung sind freigegebene Stammdaten des Notariats.</p>
    `;
    const workflowButtons = document.createElement("div");
    workflowButtons.className = "case-action-buttons";
    workflowButtons.append(
      caseActionLink(`/bpmn/${slug}`, "Ablauf ansehen", "action-button subtle"),
      caseActionLink(`/bpmn/${slug}/edit`, "Änderung vorschlagen", "action-button subtle"),
    );
    workflowActions.append(workflowButtons);

    actions.replaceChildren(dailyActions, reviewActions, workflowActions);
  });
}

function caseActionLink(href, label, className) {
  const link = document.createElement("a");
  link.href = href;
  link.textContent = label;
  link.className = className;
  return link;
}

function caseSlug(row) {
  const kgLink = row.querySelector('a[href^="/kg/"]');
  return kgLink?.getAttribute("href")?.replace("/kg/", "") || "";
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

async function loadMatters() {
  try {
    const response = await fetch(hardwareBridgeUrl("/api/matters"));
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    matterState = await response.json();
    updateMatterBadges();
  } catch (error) {
    matterState = { counts: {}, matters: [], status_labels: { open: "offen", waiting: "warten", completed: "abgeschlossen" } };
    updateMatterBadges();
    if (matterList) {
      matterList.dataset.status = "error";
      matterList.innerHTML = `<p>Akten konnten nicht geladen werden: ${escapeHtml(error.message || "unbekannter Fehler")}</p>`;
    }
  }
}

async function loadImportProposals() {
  try {
    const response = await fetch(hardwareBridgeUrl("/api/import-proposals"));
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    importState = await response.json();
    updateImportCount();
  } catch (error) {
    importState = { counts: { pending: 0 }, proposals: [], status_labels: { pending: "neu", accepted: "übernommen", rejected: "abgelehnt" } };
    updateImportCount();
    if (importList) {
      importList.dataset.status = "error";
      importList.innerHTML = `<p>Eingang konnte nicht geladen werden: ${escapeHtml(error.message || "unbekannter Fehler")}</p>`;
    }
  }
}

function updateImportCount() {
  if (importCount) {
    importCount.textContent = String(importState.counts?.pending || 0);
  }
}

function updateMatterBadges() {
  document.querySelectorAll("[data-matter-badges]").forEach((badges) => {
    const counts = matterState.counts?.[badges.dataset.matterBadges] || {};
    badges.innerHTML = `
      <span>${counts.open || 0} offen</span>
      <span>${counts.waiting || 0} warten</span>
      <span>${counts.completed || 0} abgeschlossen</span>
    `;
  });
}

function openMatterForm(slug, title) {
  activeMatterUsecase = slug;
  if (matterFormTitle) {
    matterFormTitle.textContent = `${title} starten`;
  }
  if (matterForm) {
    setMatterField("usecase_slug", slug);
    setMatterField("usecase_title", title);
    setMatterField("title", `${title} Demo-Vorgang`);
    setMatterField("client_name", "");
    setMatterField("participant_name", "");
    setMatterField("document_title", "");
    setMatterField("status", "open");
    setMatterField("status_reason", "");
  }
  if (matterFormStatus) {
    matterFormStatus.dataset.status = "ready";
    matterFormStatus.innerHTML = `
      <p>Nur Demo- oder Testdaten in das öffentliche Datenrepo eintragen.</p>
      <p>Diese Akte wird beim Anlegen an die aktuell freigegebene Kanzlei-Workflow-Version gebunden.</p>
    `;
  }
  showPanel("matter-new");
}

function setMatterField(name, value) {
  const field = matterForm?.querySelector(`[data-matter-field="${name}"]`);
  if (field) {
    field.value = value;
  }
}

async function saveMatter(event) {
  event.preventDefault();
  if (!matterForm || !matterFormStatus) {
    return;
  }
  matterFormStatus.dataset.status = "running";
  matterFormStatus.innerHTML = "<p>Akte wird im Datenrepo angelegt.</p>";
  try {
    const response = await fetch(hardwareBridgeUrl("/api/matters"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ values: readMatterFields() }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.error || `${response.status} ${response.statusText}`);
    }
    matterFormStatus.dataset.status = "ready";
    matterFormStatus.innerHTML = `<h3>Akte angelegt</h3><p>${escapeHtml(payload.matter?.aktenzeichen || payload.matter?.matter_id || "Neue Akte")} wurde im Datenrepo gespeichert.</p>`;
    activeMatterUsecase = payload.matter?.usecase_slug || activeMatterUsecase;
    await loadMatters();
    await loadImportProposals();
    renderMatterList(activeMatterUsecase);
    showPanel("matters");
  } catch (error) {
    matterFormStatus.dataset.status = "error";
    matterFormStatus.innerHTML = `<h3>Speichern fehlgeschlagen</h3><p>${escapeHtml(error.message || "Unbekannter Fehler")}</p>`;
  }
}

function readMatterFields() {
  const values = {};
  matterForm.querySelectorAll("[data-matter-field]").forEach((field) => {
    values[field.dataset.matterField] = field.value.trim();
  });
  return values;
}

function renderMatterList(slug = "") {
  if (!matterList) {
    return;
  }
  const title = slug ? usecaseTitleBySlug(slug) : "Alle Akten";
  const query = (matterSearch?.value || "").trim();
  if (matterListTitle) {
    matterListTitle.textContent = slug ? `${title}: vorhandene Akten` : "Vorhandene Akten";
  }
  const matters = (matterState.matters || [])
    .filter((matter) => !slug || matter.usecase_slug === slug)
    .filter((matter) => !query || searchableMatterText(matter).includes(query.toLowerCase()));
  const relatedImports = (importState.proposals || [])
    .filter((proposal) => proposal.status === "pending")
    .filter((proposal) => !slug || proposal.matter_values?.usecase_slug === slug)
    .filter((proposal) => !query || searchableImportText(proposal).includes(query.toLowerCase()));
  matterList.dataset.status = "ready";
  const html = [];
  if (matters.length) {
    html.push(matters.map((matter) => matterCardHtml(matter)).join(""));
  } else if (relatedImports.length) {
    html.push(`<p>Keine Akte für ${escapeHtml(title)}${query ? ` mit „${escapeHtml(query)}“` : ""} vorhanden. Im Eingang liegt aber ein passender Import-Vorschlag.</p>`);
  } else {
    html.push(`<p>Keine Akten für ${escapeHtml(title)}${query ? ` mit „${escapeHtml(query)}“` : ""} vorhanden.</p>`);
  }
  if (relatedImports.length) {
    html.push(`
      <section class="matter-related" aria-label="Passende Eingangsvorschläge">
        <h3>${matters.length ? "Offene Eingangsvorschläge" : "Passender Eingang"}</h3>
        ${relatedImports.map((proposal) => importCardHtml(proposal)).join("")}
      </section>
    `);
  }
  matterList.innerHTML = html.join("");
  bindMatterStatusButtons(matterList);
  bindImportAcceptButtons(matterList);
}

function bindMatterStatusButtons(scope) {
  scope.querySelectorAll("[data-matter-status-save]").forEach((button) => {
    button.addEventListener("click", () => saveMatterStatus(button.dataset.matterStatusSave || ""));
  });
}

function bindImportAcceptButtons(scope) {
  scope.querySelectorAll("[data-import-accept]").forEach((button) => {
    button.addEventListener("click", () => acceptImportProposal(button.dataset.importAccept || ""));
  });
}

function searchableMatterText(matter) {
  const workflow = matter.workflow_binding || {};
  const checklist = matter.checklist_summary || {};
  const nextStep = checklist.next_step || {};
  return [
    matter.matter_id,
    matter.aktenzeichen,
    matter.title,
    matter.usecase_slug,
    matter.status,
    matter.status_label,
    matter.status_reason,
    workflow.workflow_id,
    workflow.workflow_version,
    workflow.workflow_revision_hash,
    nextStep.label,
    nextStep.section,
    nextStep.owner_role,
    ...(Array.isArray(matter.participants) ? matter.participants : []),
  ].join(" ").toLowerCase();
}

function searchableImportText(proposal) {
  const values = proposal.matter_values || {};
  const metadata = values.metadata || {};
  const files = proposal.source_files || [];
  return [
    proposal.proposal_id,
    proposal.status,
    proposal.status_label,
    proposal.summary,
    values.title,
    values.client_name,
    values.participant_name,
    values.document_title,
    values.usecase_slug,
    values.usecase_title,
    ...Object.values(metadata),
    ...files.map((file) => `${file.label || ""} ${file.filename || ""}`),
  ].join(" ").toLowerCase();
}

function matterCardHtml(matter) {
  const participants = Array.isArray(matter.participants) && matter.participants.length
    ? matter.participants.join(", ")
    : "keine Beteiligten";
  const reason = matter.status_reason ? ` · ${matter.status_reason}` : "";
  const workflow = matter.workflow_binding || {};
  const workflowVersion = workflow.workflow_version || "v1";
  const workflowRevision = workflow.workflow_revision_hash ? ` · Rev ${workflow.workflow_revision_hash}` : "";
  const checklist = matter.checklist_summary || {};
  const nextStep = checklist.next_step || {};
  const nextStepText = nextStep.label || "Checkliste prüfen";
  const nextStepContext = [nextStep.section, nextStep.owner_role ? ownerRoleLabel(nextStep.owner_role) : ""].filter(Boolean).join(" · ");
  const checklistText = checklist.total_count
    ? `${checklist.open_count || 0} offen · ${checklist.completed_count || 0} erledigt · ${checklist.total_count} gesamt`
    : "Checklistenstand wird aus dem Kanzlei-Workflow gebildet";
  return `
    <article class="matter-card">
      <div>
        <h3>${escapeHtml(matter.aktenzeichen || matter.matter_id)} · ${escapeHtml(matter.title)}</h3>
        <p class="matter-meta">${escapeHtml(statusLabelForMatter(matter.status))}${escapeHtml(reason)} · ${escapeHtml(participants)} · ${matter.document_count || 0} Dokumente</p>
        <p class="matter-workflow">Kanzlei-Workflow ${escapeHtml(workflowVersion)}${escapeHtml(workflowRevision)} · bei Aktenanlage gebunden</p>
        <div class="matter-checklist">
          <p><strong>Nächster Schritt:</strong> ${escapeHtml(nextStepText)}${nextStepContext ? ` <span>${escapeHtml(nextStepContext)}</span>` : ""}</p>
          <p>Akten-Checkliste: ${escapeHtml(checklistText)}</p>
        </div>
      </div>
      <div class="matter-card-actions">
        <select data-matter-status="${escapeHtml(matter.matter_id)}">
          <option value="open"${matter.status === "open" ? " selected" : ""}>offen</option>
          <option value="waiting"${matter.status === "waiting" ? " selected" : ""}>warten</option>
          <option value="completed"${matter.status === "completed" ? " selected" : ""}>abgeschlossen</option>
        </select>
        <button class="button secondary" type="button" data-matter-status-save="${escapeHtml(matter.matter_id)}">Status speichern</button>
      </div>
    </article>
  `;
}

function ownerRoleLabel(role) {
  return {
    notary: "Notar",
    notary_clerk: "Sachbearbeitung",
    assistant: "Assistenz",
    client: "Mandant",
  }[role] || role;
}

async function saveMatterStatus(matterId) {
  const selector = matterList?.querySelector(`[data-matter-status="${cssEscape(matterId)}"]`);
  if (!selector) {
    return;
  }
  try {
    const response = await fetch(hardwareBridgeUrl("/api/matters/status"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ matter_id: matterId, status: selector.value }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.error || `${response.status} ${response.statusText}`);
    }
    await loadMatters();
    renderMatterList(activeMatterUsecase);
  } catch (error) {
    matterList.dataset.status = "error";
    matterList.insertAdjacentHTML("afterbegin", `<p>Status konnte nicht gespeichert werden: ${escapeHtml(error.message || "unbekannter Fehler")}</p>`);
  }
}

function importUploadFiles() {
  return Array.from(importUploadFileInput?.files || []);
}

function resetImportExtractState() {
  importExtractState = { metadata: {} };
}

function readImportUploadFields() {
  const values = {};
  importUploadForm?.querySelectorAll("[data-import-upload-field]").forEach((field) => {
    values[field.dataset.importUploadField] = field.value.trim();
  });
  return values;
}

function setImportUploadField(name, value) {
  const field = importUploadForm?.querySelector(`[data-import-upload-field="${name}"]`);
  if (field && !field.value.trim()) {
    field.value = value;
  }
}

function extractImportUploadMetadata() {
  if (!importUploadStatus) {
    return {};
  }
  const files = importUploadFiles();
  if (!files.length) {
    importUploadStatus.dataset.status = "error";
    importUploadStatus.innerHTML = "<p>Bitte zuerst ein synthetisches Demo-Bild auswählen.</p>";
    return {};
  }

  const fields = readImportUploadFields();
  const inferred = inferImportMetadata(files, fields.person_name);
  importExtractState = { metadata: inferred.metadata };
  setImportUploadField("person_name", inferred.personName);
  setImportUploadField("document_title", inferred.documentTitle);
  setImportUploadField("title", `${inferred.usecaseTitle} ${inferred.personName}`);
  importUploadStatus.dataset.status = "ready";
  importUploadStatus.innerHTML = `
    <h3>Metadaten vorbereitet</h3>
    <p>${escapeHtml(inferred.personName)} · ${escapeHtml(inferred.documentTitle)} · ${files.length} Datei${files.length === 1 ? "" : "en"}</p>
  `;
  return inferred.metadata;
}

function inferImportMetadata(files, personName) {
  const personText = String(personName || "").trim();
  const haystack = files.map((file) => file.name).join(" ").toLowerCase();
  const isErika = haystack.includes("erika") || haystack.includes("mustermann") || personText.toLowerCase().includes("mustermann");
  const inferredPerson = personText || (isErika ? "Erika Mustermann" : "Demo Person");
  const documentTitle = haystack.includes("ausweis") || isErika
    ? "Personalausweis zur Identitätsprüfung"
    : "Eingangsdokument zur Prüfung";
  const metadata = {
    document_kind: documentTitle.startsWith("Personalausweis") ? "Personalausweis" : "Eingangsdokument",
    uploaded_file_names: files.map((file) => file.name),
    uploaded_file_count: files.length,
    manual_review_required: true,
  };
  if (isErika) {
    Object.assign(metadata, {
      document_number: "LZ6311T47",
      family_name: "Mustermann",
      birth_name: "Gabler",
      given_names: "Erika",
      date_of_birth: "1983-08-12",
      place_of_birth: "Berlin",
      nationality: "Deutsch",
      valid_until: "2034-05-01",
      address: "Heidestrasse, 51147 Köln",
      height_cm: 160,
      eye_color: "grün",
      issuing_authority: "Stadt Köln",
      issue_or_reference_date: "2024-05-02",
      mrz_document_code: "IDD",
      mrz_lines_present: true,
      extraction_source: "synthetic_demo_profile",
    });
  } else {
    metadata.extraction_source = "browser_file_metadata_only";
  }
  return {
    metadata,
    personName: inferredPerson,
    documentTitle,
    usecaseTitle: "Unterschriftsbeglaubigung",
  };
}

async function saveImportUpload(event) {
  event.preventDefault();
  if (!importUploadForm || !importUploadStatus) {
    return;
  }
  const files = importUploadFiles();
  if (!files.length) {
    importUploadStatus.dataset.status = "error";
    importUploadStatus.innerHTML = "<p>Bitte mindestens ein synthetisches Demo-Bild auswählen.</p>";
    return;
  }
  const tooLarge = files.find((file) => file.size > 5 * 1024 * 1024);
  if (tooLarge) {
    importUploadStatus.dataset.status = "error";
    importUploadStatus.innerHTML = `<p>${escapeHtml(tooLarge.name)} ist größer als 5 MB.</p>`;
    return;
  }

  importUploadStatus.dataset.status = "running";
  importUploadStatus.innerHTML = "<p>Import-Vorschlag wird im Demo-Datenrepo gespeichert.</p>";

  try {
    const fields = readImportUploadFields();
    const inferred = inferImportMetadata(files, fields.person_name);
    const metadata = Object.keys(importExtractState.metadata || {}).length
      ? importExtractState.metadata
      : inferred.metadata;
    const personName = fields.person_name || inferred.personName;
    const documentTitle = fields.document_title || inferred.documentTitle;
    const sourceFiles = await Promise.all(files.map((file, index) => fileToImportSource(file, index)));
    const title = fields.title || `Unterschriftsbeglaubigung ${personName}`;
    const response = await fetch(hardwareBridgeUrl("/api/import-proposals"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        values: {
          title,
          usecase_slug: "unterschriftsbeglaubigung",
          usecase_title: "Unterschriftsbeglaubigung",
          client_name: personName,
          participant_name: personName,
          document_title: documentTitle,
          document_type: documentTitle.startsWith("Personalausweis") ? "id_document_scan" : "input_document",
          media_type: files[0]?.type || "application/octet-stream",
          data_classification: "synthetic_identity_document",
          status: "open",
          status_reason: "Ausweisdaten aus synthetischem Demo-Bildupload übernommen, manuelle Prüfung offen",
          source: "operator_upload",
          source_type: "scan_image",
          summary: `${documentTitle} für ${personName}`,
          synthetic_test_data: true,
          metadata,
          source_files: sourceFiles,
        },
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.error || `${response.status} ${response.statusText}`);
    }
    importUploadStatus.dataset.status = "ready";
    importUploadStatus.innerHTML = `<h3>Import-Vorschlag gespeichert</h3><p>${escapeHtml(payload.proposal?.proposal_id || title)} ist sofort unten sichtbar.</p>`;
    await loadImportProposals();
    renderImportList();
  } catch (error) {
    importUploadStatus.dataset.status = "error";
    importUploadStatus.innerHTML = `<h3>Upload fehlgeschlagen</h3><p>${escapeHtml(error.message || "Unbekannter Fehler")}</p>`;
  }
}

function fileToImportSource(file, index) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const dataUrl = String(reader.result || "");
      resolve({
        label: index === 0 ? "Vorderseite" : `Datei ${index + 1}`,
        filename: file.name,
        media_type: file.type || "application/octet-stream",
        data_url: dataUrl,
      });
    });
    reader.addEventListener("error", () => reject(reader.error || new Error("Datei konnte nicht gelesen werden.")));
    reader.readAsDataURL(file);
  });
}

function renderImportList() {
  if (!importList) {
    return;
  }
  const proposals = importState.proposals || [];
  importList.dataset.status = "ready";
  if (!proposals.length) {
    importList.innerHTML = "<p>Keine Import-Vorschläge vorhanden.</p>";
    return;
  }
  importList.innerHTML = proposals.map((proposal) => importCardHtml(proposal)).join("");
  bindImportAcceptButtons(importList);
}

function importCardHtml(proposal) {
  const values = proposal.matter_values || {};
  const metadata = values.metadata || {};
  const files = proposal.source_files || [];
  const fileText = files.length ? `${files.length} Datei${files.length === 1 ? "" : "en"}` : "keine Datei";
  const accepted = proposal.status !== "pending";
  const identityLine = [
    metadata.document_number ? `Ausweis ${metadata.document_number}` : "",
    metadata.date_of_birth ? `Geboren ${metadata.date_of_birth}` : "",
    metadata.valid_until ? `Gültig bis ${metadata.valid_until}` : "",
  ].filter(Boolean).join(" · ");
  return `
    <article class="import-card">
      <div>
        <h3>${escapeHtml(proposal.summary || values.title || proposal.proposal_id)}</h3>
        <p class="matter-meta">${escapeHtml(importStatusLabel(proposal.status))} · ${escapeHtml(values.usecase_title || values.usecase_slug || "Vorgang")} · ${escapeHtml(fileText)}</p>
        <dl class="import-fields">
          <div><dt>Aktenbetreff</dt><dd>${escapeHtml(values.title || "")}</dd></div>
          <div><dt>Person</dt><dd>${escapeHtml(values.participant_name || values.client_name || "")}</dd></div>
          <div><dt>Dokument</dt><dd>${escapeHtml(values.document_title || "")}</dd></div>
          ${identityLine ? `<div><dt>Ausweis</dt><dd>${escapeHtml(identityLine)}</dd></div>` : ""}
        </dl>
      </div>
      <div class="import-actions">
        <button class="button primary" type="button" data-import-accept="${escapeHtml(proposal.proposal_id)}"${accepted ? " disabled" : ""}>Übernehmen</button>
      </div>
    </article>
  `;
}

async function acceptImportProposal(proposalId) {
  if (!proposalId || !importList) {
    return;
  }
  importList.dataset.status = "running";
  try {
    const response = await fetch(hardwareBridgeUrl("/api/import-proposals/accept"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ proposal_id: proposalId }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload?.error || `${response.status} ${response.statusText}`);
    }
    activeMatterUsecase = payload.matter?.usecase_slug || activeMatterUsecase;
    await loadImportProposals();
    await loadMatters();
    renderMatterList(activeMatterUsecase);
    showPanel("matters");
  } catch (error) {
    importList.dataset.status = "error";
    importList.insertAdjacentHTML("afterbegin", `<p>Import konnte nicht übernommen werden: ${escapeHtml(error.message || "unbekannter Fehler")}</p>`);
  }
}

function usecaseTitleBySlug(slug) {
  const row = caseRows.find((candidate) => caseSlug(candidate) === slug);
  return row ? caseTitle(row) : slug;
}

function statusLabelForMatter(status) {
  return matterState.status_labels?.[status] || status;
}

function importStatusLabel(status) {
  return importState.status_labels?.[status] || status;
}

function cssEscape(value) {
  if (window.CSS?.escape) {
    return window.CSS.escape(value);
  }
  return String(value).replaceAll('"', '\\"');
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
