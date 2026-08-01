'use strict';

const childProcess = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const packageRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(packageRoot, '..', '..');
const fixtureRoot = '/tmp/nac-workbench-live-read-visual';
const fixture = path.join(fixtureRoot, 'index.html');
const outputRoot = path.resolve(
  process.argv[2] || path.join(repoRoot, 'assets/docs/workbench-live-read-binding')
);
const cases = [
  { id: 'VIS-725-01', state: 'ready', layout: 'desktop', file: 'VIS-725-01-desktop-ready.png', width: 1440, height: 900 },
  { id: 'VIS-725-02', state: 'ready', layout: 'narrow-spfx-column', file: 'VIS-725-02-narrow-spfx-ready.png', width: 720, height: 980 },
  { id: 'VIS-725-03', state: 'ready', layout: 'mobile', file: 'VIS-725-03-mobile-ready.png', width: 390, height: 844 },
  { id: 'VIS-725-04', state: 'loading', layout: 'state', file: 'VIS-725-04-loading.png', width: 720, height: 420 },
  { id: 'VIS-725-05', state: 'deny', layout: 'state', file: 'VIS-725-05-deny.png', width: 720, height: 420 },
  { id: 'VIS-725-06', state: 'unavailable', layout: 'state', file: 'VIS-725-06-unavailable.png', width: 720, height: 420 }
];
const sourceBindingPaths = {
  host: 'spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.tsx',
  styles: 'spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.styles.ts',
  client: 'spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.ts',
  webPart: 'spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts',
  parser: 'spfx/nac-bpmn-viewer/src/workbench/core/parseWorkbenchSnapshot.ts',
  projection: 'spfx/nac-bpmn-viewer/src/workbench/nac/NacWorkbenchProjection.ts',
  contract: 'workflows/contracts/workbench-live-read-binding.contract.json'
};
const harnessPaths = [
  'scripts/validate_workbench_live_read_binding.py',
  'spfx/nac-bpmn-viewer/package.json',
  'spfx/nac-bpmn-viewer/package-lock.json',
  'spfx/nac-bpmn-viewer/scripts/workbench-live-read-synthetic-snapshot.cjs',
  'spfx/nac-bpmn-viewer/scripts/generate-workbench-live-read-visual-fixture.cjs',
  'spfx/nac-bpmn-viewer/scripts/capture-workbench-live-read-visual-evidence.cjs',
  'workflows/verification-contracts/workbench-live-read-binding.verification.json'
];
const buildArtifactPaths = [
  'spfx/nac-bpmn-viewer/lib-commonjs/webparts/nacBpmnViewer/components/NacWorkbenchHost.js',
  'spfx/nac-bpmn-viewer/lib-commonjs/webparts/nacBpmnViewer/components/NacWorkbenchHost.styles.js',
  'spfx/nac-bpmn-viewer/lib-commonjs/workbench/core/parseWorkbenchSnapshot.js',
  'spfx/nac-bpmn-viewer/lib-commonjs/workbench/nac/NacWorkbenchProjection.js',
  'spfx/nac-bpmn-viewer/lib-commonjs/workbench/react/WorkbenchPanel.js',
  'spfx/nac-bpmn-viewer/lib-commonjs/workbench/react/WorkbenchPanel.styles.js'
];

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function binding(relativePath) {
  return { relativePath, sha256: sha256(path.join(repoRoot, relativePath)) };
}

function pngDimensions(file) {
  const bytes = fs.readFileSync(file);
  const signature = '89504e470d0a1a0a';
  if (bytes.subarray(0, 8).toString('hex') !== signature || bytes.toString('ascii', 12, 16) !== 'IHDR') {
    throw new Error('NAC_WORKBENCH_LIVE_SCREENSHOT_NOT_PNG: ' + file);
  }
  return { imageWidth: bytes.readUInt32BE(16), imageHeight: bytes.readUInt32BE(20) };
}

async function inspect(page, item) {
  return page.evaluate(expected => {
    const frame = document.querySelector('[data-nac-evidence-frame]');
    const host = document.querySelector('.nacWorkbenchHost');
    if (!frame || !host) throw new Error('NAC_WORKBENCH_LIVE_HOST_MISSING');
    const text = host.textContent || '';
    const clipped = Array.from(host.querySelectorAll('h1,h2,strong,span,p,button'))
      .filter(element => element.scrollWidth > element.clientWidth + 2)
      .map(element => (element.textContent || '').trim());
    return {
      state: expected.state,
      documentOverflow: document.documentElement.scrollWidth > innerWidth + 2,
      frameOverflow: frame.scrollWidth > frame.clientWidth + 2,
      hostOverflow: host.scrollWidth > host.clientWidth + 2,
      clipped,
      text,
      hasSnapshot: Boolean(host.querySelector('[data-nac-workbench-schema]')),
      hasHostComponent: Boolean(host.matches('[data-nac-component="workbench-host"]'))
    };
  }, item);
}

function assertInspection(item, inspection) {
  if (
    inspection.documentOverflow ||
    inspection.frameOverflow ||
    inspection.hostOverflow ||
    inspection.clipped.length
  ) {
    throw new Error(item.id + ': NAC_WORKBENCH_LIVE_VISUAL_OVERFLOW');
  }
  if (item.state === 'ready') {
    for (const required of [
      'Arbeitsbereich',
      'BPMN-Detail',
      'Synthetische Testdaten',
      'Keine priorisierte Intervention.',
      'Entwurf prüfen'
    ]) {
      if (!inspection.text.includes(required)) throw new Error(item.id + ': missing ' + required);
    }
    if (!inspection.hasSnapshot || !inspection.hasHostComponent) {
      throw new Error(item.id + ': NAC_WORKBENCH_LIVE_READY_HOST_INVALID');
    }
    return;
  }
  const expectedText = {
    loading: 'Arbeitsbereich wird geladen.',
    deny: 'Kein Zugriff auf diesen Arbeitsbereich.',
    unavailable: 'Arbeitsbereich ist derzeit nicht verfügbar.'
  }[item.state];
  if (!inspection.text.includes(expectedText) || inspection.hasSnapshot) {
    throw new Error(item.id + ': NAC_WORKBENCH_LIVE_STATE_INVALID');
  }
}

async function run() {
  childProcess.execFileSync(process.execPath, [
    path.join(__dirname, 'generate-workbench-live-read-visual-fixture.cjs'),
    fixtureRoot
  ], { stdio: 'ignore' });
  fs.mkdirSync(outputRoot, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const evidence = [];
  let browserNetworkRequests = 0;
  try {
    for (const item of cases) {
      const page = await browser.newPage({ viewport: { width: item.width, height: item.height } });
      page.on('request', request => {
        if (/^https?:/i.test(request.url())) browserNetworkRequests += 1;
      });
      const fixtureCase = item.state === 'ready' ? 'ready-' + item.layout : item.state;
      await page.goto('file://' + fixture + '?case=' + encodeURIComponent(fixtureCase));
      await page.waitForFunction(expected =>
        document.documentElement.dataset.nacVisualReady === expected,
      fixtureCase);
      const inspection = await inspect(page, item);
      assertInspection(item, inspection);
      const output = path.join(outputRoot, item.file);
      await page.locator('[data-nac-evidence-frame]').screenshot({ path: output });
      evidence.push({
        id: item.id,
        state: item.state,
        layout: item.layout,
        file: item.file,
        viewport: { width: item.width, height: item.height },
        ...pngDimensions(output),
        sha256: sha256(output)
      });
      await page.close();
    }
  } finally {
    await browser.close();
  }
  if (browserNetworkRequests !== 0) {
    throw new Error('NAC_WORKBENCH_LIVE_NETWORK_REQUEST_DETECTED');
  }
  const manifest = {
    schemaVersion: 'nac.workbench-live-read-host-visual-evidence/v1',
    syntheticOnly: true,
    browserNetworkRequests,
    fixtureClock: '2026-08-01T09:01:00Z',
    cases: evidence,
    sourceBindings: Object.fromEntries(
      Object.entries(sourceBindingPaths).map(([name, relativePath]) => [name, binding(relativePath)])
    ),
    visualHarness: harnessPaths.map(binding),
    buildArtifacts: buildArtifactPaths.map(binding),
    runtime: {
      nodeVersion: process.version,
      npmUserAgent: process.env.npm_config_user_agent || '',
      playwrightVersion: require('playwright/package.json').version,
      webpackVersion: require('webpack/package.json').version,
      typescriptVersion: require('typescript/package.json').version,
      heftVersion: require('@rushstack/heft/package.json').version
    }
  };
  fs.writeFileSync(
    path.join(outputRoot, 'VIS-725-manifest.json'),
    JSON.stringify(manifest, null, 2) + '\n'
  );
  console.log(JSON.stringify(manifest, null, 2));
}

run().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
