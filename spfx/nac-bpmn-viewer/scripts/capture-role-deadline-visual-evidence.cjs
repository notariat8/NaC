'use strict';

const childProcess = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

let chromium;
let playwrightVersion;
try {
  ({ chromium } = require('playwright'));
  playwrightVersion = require('playwright/package.json').version;
} catch {
  throw new Error('NAC_VISUAL_PLAYWRIGHT_MISSING: run npm ci in the SPFx package');
}
if (playwrightVersion !== '1.55.0') {
  throw new Error('NAC_VISUAL_PLAYWRIGHT_VERSION_INVALID');
}

const packageRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(packageRoot, '..', '..');
const fixturePath = '/tmp/nac-spfx-role-deadline-cockpit.html';
const outputRoot = path.resolve(process.argv[2] || '/tmp/nac-spfx-role-deadline-evidence');
const CURRENT_STEP = 'Task_EntwurfAbstimmen';
const DEADLINE_STEP = 'Task_NachweiseNachhalten';
const CURRENT_TASK = 'NAC-SYN-TASK-001';
const DEADLINE_TASK = 'NAC-SYN-DEADLINE-001';
const cases = [
  { id: 'VIS-710-01', file: 'VIS-710-01-desktop-light.png', width: 1440, height: 1000, query: '?selected=deadline', expected: { dark: false, filter: 'all', current: [CURRENT_STEP], selected: [DEADLINE_STEP], selectedTasks: [DEADLINE_TASK], detailTitle: 'Abschlussfrist überwachen' } },
  { id: 'VIS-710-02', file: 'VIS-710-02-narrow-light.png', width: 390, height: 844, query: '?filter=deadline', expected: { dark: false, filter: 'deadline', current: [CURRENT_STEP], selected: [DEADLINE_STEP], selectedTasks: [DEADLINE_TASK], detailTitle: 'Abschlussfrist überwachen' } },
  { id: 'VIS-710-03', file: 'VIS-710-03-desktop-dark.png', width: 1440, height: 1000, query: '?theme=dark&filter=notary', expected: { dark: true, filter: 'notary', current: [CURRENT_STEP], selected: [CURRENT_STEP], selectedTasks: [CURRENT_TASK], detailTitle: 'Entwurf prüfen' } },
  { id: 'VIS-710-04', file: 'VIS-710-04-narrow-dark-empty.png', width: 390, height: 844, query: '?theme=dark&state=empty', expected: { dark: true, filter: 'notary', current: [CURRENT_STEP], selected: [], selectedTasks: [], detailTitle: null }, verifyEmptyRecovery: true },
  { id: 'VIS-710-05', file: 'VIS-710-05-error-retry.png', width: 390, height: 320, query: '?state=error', expected: { dark: false, filter: null, current: [], selected: [], selectedTasks: [], detailTitle: null }, verifyRetry: true },
  { id: 'VIS-710-06', file: 'VIS-710-06-narrow-container-light.png', width: 1440, height: 1000, query: '?selected=deadline', containerWidth: 390, expected: { dark: false, filter: 'all', current: [CURRENT_STEP], selected: [DEADLINE_STEP], selectedTasks: [DEADLINE_TASK], detailTitle: 'Abschlussfrist überwachen' } }
];

function sha256File(filePath) {
  return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function sourceInputs() {
  return [
    'bpmn/immobilienkaufvertrag.bpmn',
    'spfx/nac-bpmn-viewer/package.json',
    'spfx/nac-bpmn-viewer/package-lock.json',
    'spfx/nac-bpmn-viewer/scripts/capture-role-deadline-visual-evidence.cjs',
    'spfx/nac-bpmn-viewer/scripts/generate-role-deadline-visual-fixture.cjs',
    'spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacBpmnViewer.styles.ts',
    'spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacBpmnViewer.tsx',
    'spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/WorkspaceViewModel.ts'
  ].map(relativePath => ({
    path: relativePath,
    sha256: sha256File(path.join(repoRoot, relativePath))
  }));
}

function embeddedAssets() {
  return [
    'spfx/nac-bpmn-viewer/node_modules/bpmn-js/dist/assets/diagram-js.css',
    'spfx/nac-bpmn-viewer/node_modules/bpmn-js/dist/bpmn-viewer.production.min.js'
  ].map(relativePath => ({
    path: relativePath,
    sha256: sha256File(path.join(repoRoot, relativePath))
  }));
}

async function inspect(page) {
  return page.evaluate(() => {
    const root = document.querySelector('main') || document.querySelector('.nacBpmnViewer__messageHost');
    const visible = element => {
      const style = getComputedStyle(element);
      return style.display !== 'none' && style.visibility !== 'hidden';
    };
    const clippedText = Array.from(document.querySelectorAll('button,strong,span,h1,h2,h3,small'))
      .filter(visible)
      .filter(element => element.scrollWidth > element.clientWidth + 2)
      .map(element => (element.textContent || '').trim().slice(0, 100));
    const elementIds = selector => Array.from(document.querySelectorAll(selector))
      .map(element => element.getAttribute('data-element-id'))
      .filter(value => value !== null);
    const rootRect = root === null ? null : root.getBoundingClientRect();
    const containerOverflowElements = root === null || rootRect === null ? [] :
      Array.from(root.querySelectorAll('*'))
        .filter(visible)
        .filter(element => element.closest('.nacBpmnViewer__canvasScroller') === null)
        .filter(element => element.closest('.nacBpmnViewer__visuallyHidden') === null)
        .filter(element => {
          const rect = element.getBoundingClientRect();
          return rect.left < rootRect.left - 2 ||
            rect.right > rootRect.right + 2 ||
            element.scrollWidth > element.clientWidth + 2;
        })
        .map(element => element.className || element.tagName);
    const visibleText = root === null ? '' : root.innerText;
    const forbiddenTextPatterns = [
      /Bearer\s/i,
      /token/i,
      /funktion8\.de/i,
      /sharepoint\.com/i,
      /@[a-z0-9.-]+\.[a-z]{2,}/i
    ];
    return {
      rootWidth: root === null ? null : Math.round(root.getBoundingClientRect().width),
      rootHeight: root === null ? null : Math.round(root.getBoundingClientRect().height),
      documentOverflow: document.documentElement.scrollWidth > innerWidth,
      containerOverflow: root !== null && root.scrollWidth > root.clientWidth + 2,
      containerOverflowElements,
      clippedText,
      svgElements: document.querySelectorAll('#canvas svg .djs-element').length,
      currentStepCodes: elementIds('.djs-element.nac-current-step'),
      selectedStepCodes: elementIds('.djs-element.nac-selected-step'),
      selectedTaskIds: Array.from(document.querySelectorAll('[data-nac-task-id][aria-pressed="true"]'))
        .map(element => element.getAttribute('data-nac-task-id'))
        .filter(value => value !== null),
      detailTitle: document.querySelector('.nacBpmnViewer__taskDetails h3')?.textContent || null,
      diagramStatus: document.getElementById('diagram-status')?.textContent || null,
      activeFilter: document.querySelector('[data-filter][aria-pressed="true"]')?.getAttribute('data-filter') || null,
      retryButtons: Array.from(document.querySelectorAll('button')).filter(button => button.textContent === 'Erneut laden').length,
      dark: document.querySelector('.nacBpmnViewer__dark') !== null,
      syntheticMarkers: {
        fixture: visibleText.includes('Synthetische Testdaten'),
        noMatterData: visibleText.includes('Keine Mandatsdaten')
      },
      forbiddenTextMatches: forbiddenTextPatterns
        .filter(pattern => pattern.test(visibleText))
        .map(pattern => pattern.source)
    };
  });
}

async function verifyMaximumTextLayout(page) {
  await page.evaluate(() => {
    const repeat = (value, length) => value.repeat(length);
    const title = document.querySelector('.nacBpmnViewer__header h1');
    const host = document.querySelector('.nacBpmnViewer__headerMeta span:last-child');
    const taskTitle = document.querySelector('.nacBpmnViewer__taskCopy strong');
    const taskMeta = document.querySelector('.nacBpmnViewer__taskCopy span');
    const status = document.querySelector('.nacBpmnViewer__taskOpen');
    if (!title || !host || !taskTitle || !taskMeta || !status) {
      throw new Error('NAC_VISUAL_MAX_TEXT_TARGET_MISSING');
    }
    title.textContent = repeat('M', 160);
    host.textContent = repeat('H', 160);
    taskTitle.textContent = repeat('T', 160);
    taskMeta.textContent = repeat('I', 80) + ' · ' + repeat('C', 120);
    status.textContent = repeat('S', 80);
  });
  const checks = await inspect(page);
  if (checks.documentOverflow || checks.containerOverflow ||
      checks.containerOverflowElements.length !== 0 || checks.clippedText.length !== 0) {
    throw new Error('VIS-710-06: NAC_VISUAL_MAX_TEXT_LAYOUT_INVALID');
  }
  return true;
}

async function capture() {
  fs.mkdirSync(outputRoot, { recursive: true });
  childProcess.execFileSync(
    process.execPath,
    [path.join(__dirname, 'generate-role-deadline-visual-fixture.cjs'), fixturePath],
    { stdio: 'ignore' }
  );

  const browser = await chromium.launch({ headless: true });
  const browserVersion = browser.version();
  const evidence = [];
  try {
    for (const visualCase of cases) {
      const page = await browser.newPage({
        viewport: { width: visualCase.width, height: visualCase.height },
        deviceScaleFactor: 1
      });
      await page.goto('file://' + fixturePath + visualCase.query, { waitUntil: 'load' });
      await page.waitForFunction(() => document.documentElement.dataset.nacVisualReady === 'true');
      if (visualCase.containerWidth !== undefined) {
        await page.evaluate(width => {
          const fixtureApp = document.getElementById('app');
          if (fixtureApp === null) throw new Error('NAC_VISUAL_APP_MISSING');
          fixtureApp.style.width = width + 'px';
          canvas.resized();
          canvas.zoom('fit-viewport');
        }, visualCase.containerWidth);
      }

      const checks = await inspect(page);
      if (checks.documentOverflow || checks.containerOverflow ||
          checks.containerOverflowElements.length !== 0 || checks.clippedText.length !== 0) {
        throw new Error(visualCase.id + ': NAC_VISUAL_LAYOUT_INVALID ' + JSON.stringify({ documentOverflow: checks.documentOverflow, containerOverflow: checks.containerOverflow, containerOverflowElements: checks.containerOverflowElements, clippedText: checks.clippedText }));
      }
      const same = (left, right) => JSON.stringify(left) === JSON.stringify(right);
      if (checks.dark !== visualCase.expected.dark ||
          checks.activeFilter !== visualCase.expected.filter ||
          !same(checks.currentStepCodes, visualCase.expected.current) ||
          !same(checks.selectedStepCodes, visualCase.expected.selected) ||
          !same(checks.selectedTaskIds, visualCase.expected.selectedTasks) ||
          checks.detailTitle !== visualCase.expected.detailTitle) {
        throw new Error(visualCase.id + ': NAC_VISUAL_STATE_INVALID');
      }
      const expectedSelectionLabel = visualCase.expected.detailTitle || 'Keine ausgewählte Aufgabe';
      if (visualCase.id !== 'VIS-710-05') {
        if (checks.svgElements < 1 ||
            checks.diagramStatus !== 'Aktueller Prozessschritt: Entwurf prüfen. Ausgewählte Aufgabe: ' + expectedSelectionLabel + '.' ||
            !checks.syntheticMarkers.fixture || !checks.syntheticMarkers.noMatterData ||
            checks.forbiddenTextMatches.length !== 0) {
          throw new Error(visualCase.id + ': NAC_VISUAL_BPMN_OR_PRIVACY_INVALID');
        }
      } else if (checks.retryButtons !== 1 ||
          checks.syntheticMarkers.fixture || checks.syntheticMarkers.noMatterData ||
          checks.forbiddenTextMatches.length !== 0) {
        throw new Error(visualCase.id + ': NAC_VISUAL_RETRY_INVALID');
      }
      if (visualCase.id === 'VIS-710-01' &&
          visualCase.expected.current[0] === visualCase.expected.selected[0]) {
        throw new Error('VIS-710-01: NAC_VISUAL_MARKERS_NOT_DISTINCT');
      }

      const target = page.locator(visualCase.id === 'VIS-710-05' ? '.nacBpmnViewer__messageHost' : 'main');
      const outputPath = path.join(outputRoot, visualCase.file);
      await target.screenshot({ path: outputPath });
      fs.chmodSync(outputPath, 0o644);

      let recoveryVerified = false;
      if (visualCase.verifyRetry) {
        await page.getByRole('button', { name: 'Erneut laden' }).click();
        await page.waitForFunction(() => document.documentElement.dataset.nacVisualReady === 'true' && document.querySelector('main') !== null);
        recoveryVerified = (await inspect(page)).currentStepCodes.length === 1;
      }
      if (visualCase.verifyEmptyRecovery) {
        await page.getByRole('button', { name: 'Alle Aufgaben' }).click();
        recoveryVerified = (await inspect(page)).selectedStepCodes.length === 1;
      }
      if ((visualCase.verifyRetry || visualCase.verifyEmptyRecovery) && !recoveryVerified) {
        throw new Error(visualCase.id + ': NAC_VISUAL_RECOVERY_INVALID');
      }
      checks.maximumTextLayoutVerified = visualCase.id === 'VIS-710-06'
        ? await verifyMaximumTextLayout(page)
        : false;

      evidence.push({
        id: visualCase.id,
        file: visualCase.file,
        sha256: sha256File(outputPath),
        viewport: { width: visualCase.width, height: visualCase.height },
        containerWidth: visualCase.containerWidth ?? null,
        query: visualCase.query,
        elementCrop: true,
        recoveryVerified,
        checks
      });
      await page.close();
    }
  } finally {
    await browser.close();
  }

  const inputs = sourceInputs();
  const aggregateSourceSha256 = crypto.createHash('sha256')
    .update(inputs.map(item => item.path + ':' + item.sha256).join('\n'))
    .digest('hex');
  const manifest = {
    schemaVersion: 'nac.spfx-role-deadline-visual-evidence/v0.2',
    browser: 'Chromium ' + browserVersion,
    nodeVersion: process.version,
    playwrightVersion,
    embeddedAssets: embeddedAssets(),
    evaluationTimestamp: '2026-08-25T16:00:00Z',
    containsOnlySyntheticData: true,
    tenantAccess: false,
    componentE2e: false,
    evidenceKind: 'offline_visual_contract',
    aggregateSourceSha256,
    sourceInputs: inputs,
    evidence
  };
  const manifestPath = path.join(outputRoot, 'VIS-710-manifest.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n', { encoding: 'utf8', mode: 0o644 });
  console.log(JSON.stringify(manifest, null, 2));
}

capture().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
