'use strict';

const childProcess = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const packageRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(packageRoot, '..', '..');
const fixture = '/tmp/nac-generic-workbench.html';
const outputRoot = path.resolve(process.argv[2] || path.join(repoRoot, 'assets/docs/generic-workbench'));
const cases = [
  { id: 'VIS-721-01', file: 'VIS-721-01-desktop.png', width: 1440, height: 900 },
  { id: 'VIS-721-02', file: 'VIS-721-02-mobile.png', width: 390, height: 844 }
];

function sha256(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function normalizedNpmUserAgent() {
  return (process.env.npm_config_user_agent || '').replace(/\s+ci\/[^\s]+$/u, '');
}

async function run() {
  childProcess.execFileSync(
    process.execPath,
    [path.join(__dirname, 'generate-workbench-visual-fixture.cjs'), fixture],
    { stdio: 'ignore' }
  );
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
      await page.goto('file://' + fixture);
      await page.waitForFunction(() => document.documentElement.dataset.nacVisualReady === 'true');
      const inspection = await page.evaluate(() => {
        const root = document.querySelector('.nacWorkbench');
        if (!root) throw new Error('NAC_WORKBENCH_ROOT_MISSING');
        const clipped = Array.from(root.querySelectorAll('h1,h2,strong,span,p,button'))
          .filter(element => element.scrollWidth > element.clientWidth + 2)
          .map(element => (element.textContent || '').trim());
        return {
          documentOverflow: document.documentElement.scrollWidth > innerWidth,
          rootOverflow: root.scrollWidth > root.clientWidth + 2,
          clipped,
          text: root.innerText
        };
      });
      if (inspection.documentOverflow || inspection.rootOverflow || inspection.clipped.length) {
        throw new Error(item.id + ': NAC_WORKBENCH_VISUAL_OVERFLOW');
      }
      for (const required of ['Synthetische Testdaten', 'Aufmerksamkeit in dieser Akte', 'Gesperrt: approve']) {
        if (!inspection.text.includes(required)) throw new Error(item.id + ': missing ' + required);
      }
      const output = path.join(outputRoot, item.file);
      await page.locator('.nacWorkbench').screenshot({ path: output });
      evidence.push({ ...item, sha256: sha256(output) });
      await page.close();
    }
  } finally {
    await browser.close();
  }
  const sourcePaths = [
    '.github/workflows/quality-gate.yml',
    'scripts/quality_gate.py',
    'scripts/validate_generic_workbench_foundation.py',
    'spfx/nac-bpmn-viewer/package.json',
    'spfx/nac-bpmn-viewer/package-lock.json',
    'spfx/nac-bpmn-viewer/src/workbench/core/WorkbenchContracts.ts',
    'spfx/nac-bpmn-viewer/src/workbench/core/WorkbenchSelectors.ts',
    'spfx/nac-bpmn-viewer/src/workbench/core/parseWorkbenchSnapshot.ts',
    'spfx/nac-bpmn-viewer/src/workbench/nac/NacWorkbenchProjection.ts',
    'spfx/nac-bpmn-viewer/src/workbench/react/WorkbenchPanel.tsx',
    'spfx/nac-bpmn-viewer/src/workbench/react/WorkbenchPanel.styles.ts',
    'spfx/nac-bpmn-viewer/scripts/workbench-synthetic-snapshot.cjs',
    'spfx/nac-bpmn-viewer/scripts/generate-workbench-visual-fixture.cjs',
    'spfx/nac-bpmn-viewer/scripts/capture-workbench-visual-evidence.cjs',
    'workflows/contracts/generic-workbench.contract.json',
    'workflows/verification-contracts/generic-workbench.verification.json',
    'workflows/fixtures/generic-workbench-conformance.json'
  ];
  const buildArtifactPaths = [
    'spfx/nac-bpmn-viewer/lib-commonjs/workbench/core/WorkbenchContracts.js',
    'spfx/nac-bpmn-viewer/lib-commonjs/workbench/core/WorkbenchSelectors.js',
    'spfx/nac-bpmn-viewer/lib-commonjs/workbench/core/parseWorkbenchSnapshot.js',
    'spfx/nac-bpmn-viewer/lib-commonjs/workbench/nac/NacWorkbenchProjection.js',
    'spfx/nac-bpmn-viewer/lib-commonjs/workbench/react/WorkbenchPanel.js',
    'spfx/nac-bpmn-viewer/lib-commonjs/workbench/react/WorkbenchPanel.styles.js'
  ];
  const sources = sourcePaths.map(relativePath => ({
    relativePath,
    sha256: sha256(path.join(repoRoot, relativePath))
  }));
  const buildArtifacts = buildArtifactPaths.map(relativePath => ({
    relativePath,
    sha256: sha256(path.join(repoRoot, relativePath))
  }));
  const manifest = {
    schemaVersion: 'nac.generic-workbench-visual-evidence/v1',
    syntheticOnly: true,
    browserNetworkRequests,
    cases: evidence,
    sources,
    buildArtifacts,
    runtime: {
      nodeVersion: process.version,
      npmUserAgent: normalizedNpmUserAgent(),
      playwrightVersion: require('playwright/package.json').version,
      typescriptVersion: require('typescript/package.json').version,
      heftVersion: require('@rushstack/heft/package.json').version
    }
  };
  if (browserNetworkRequests !== 0) throw new Error('NAC_WORKBENCH_NETWORK_REQUEST_DETECTED');
  fs.writeFileSync(path.join(outputRoot, 'VIS-721-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  console.log(JSON.stringify(manifest, null, 2));
}

run().catch(error => { console.error(error); process.exitCode = 1; });
