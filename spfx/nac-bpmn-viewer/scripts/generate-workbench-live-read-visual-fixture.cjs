'use strict';

const fs = require('fs');
const path = require('path');
const webpack = require('webpack');

const packageRoot = path.resolve(__dirname, '..');
const outputRoot = path.resolve(process.argv[2] || '/tmp/nac-workbench-live-read-visual');
const entryPath = path.join(outputRoot, 'entry.cjs');
const bundlePath = path.join(outputRoot, 'bundle.js');
const htmlPath = path.join(outputRoot, 'index.html');
const snapshot = require('./workbench-live-read-synthetic-snapshot.cjs');
const hostPath = path.join(
  packageRoot,
  'lib-commonjs/webparts/nacBpmnViewer/components/NacWorkbenchHost.js'
);
const projectionPath = path.join(
  packageRoot,
  'lib-commonjs/workbench/nac/NacWorkbenchProjection.js'
);

function browserEntry() {
  return `'use strict';
const React = require('react');
const ReactDOM = require('react-dom');
const { NacWorkbenchHost } = require(${JSON.stringify(hostPath)});
const { parseNacWorkbenchProjectionJson } = require(${JSON.stringify(projectionPath)});
const snapshotJson = ${JSON.stringify(JSON.stringify(snapshot))};
const fixedNow = Date.parse('2026-08-01T09:01:00Z');
const RealDate = Date;
class FixedDate extends RealDate {
  constructor(...args) { super(...(args.length ? args : [fixedNow])); }
  static now() { return fixedNow; }
}
window.Date = FixedDate;

const evidenceCase = new URLSearchParams(window.location.search).get('case') || 'ready-desktop';
const expectedState = evidenceCase.replace(/^ready-.+$/, 'ready');
document.body.dataset.evidenceCase = evidenceCase;
document.body.dataset.evidenceLayout = evidenceCase.startsWith('ready-')
  ? evidenceCase.slice('ready-'.length)
  : 'state';

function loader(snapshot) {
  if (expectedState === 'ready') return async () => snapshot;
  if (expectedState === 'loading') return () => new Promise(() => undefined);
  if (expectedState === 'deny') {
    return async () => { throw new Error('NAC_BFF_ACCESS_DENIED'); };
  }
  return async () => { throw new Error('NAC_BFF_UNAVAILABLE'); };
}

function waitUntilRendered() {
  const root = document.querySelector('[data-nac-evidence-root]');
  const text = root ? root.textContent || '' : '';
  const ready = expectedState === 'ready'
    ? Boolean(root && root.querySelector('[data-nac-component="workbench-host"]'))
    : expectedState === 'loading'
      ? text.includes('Arbeitsbereich wird geladen.')
      : expectedState === 'deny'
        ? text.includes('Kein Zugriff auf diesen Arbeitsbereich.')
        : text.includes('Arbeitsbereich ist derzeit nicht verfügbar.');
  if (!ready) {
    window.requestAnimationFrame(waitUntilRendered);
    return;
  }
  window.requestAnimationFrame(() => {
    document.documentElement.dataset.nacVisualReady = evidenceCase;
  });
}

parseNacWorkbenchProjectionJson(snapshotJson, '2026-08-01T09:01:00Z', {
  subjectId: 'actor:synthetic:001',
  workspaceId: 'notary_team_01',
  matterId: 'NAC-SYN-MATTER-001',
  purpose: 'view_synthetic_matter_workspace'
}).then(snapshot => {
  ReactDOM.render(React.createElement(NacWorkbenchHost, {
    expectedSubjectId: expectedState === 'deny' ? undefined : 'actor:synthetic:001',
    loadSnapshot: loader(snapshot),
    detailSurface: React.createElement('div', null, 'Synthetische BPMN-Detailansicht')
  }), document.querySelector('[data-nac-evidence-root]'));
  waitUntilRendered();
}).catch(error => {
  document.documentElement.dataset.nacVisualError = error instanceof Error ? error.message : String(error);
});
`;
}

function html() {
  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>NaC Workbench Live Read Host - synthetische Evidence</title>
  <style>
    *{box-sizing:border-box}
    html,body{margin:0;min-height:100%;background:#eef1f3;color:#17202a;font-family:Segoe UI,Arial,sans-serif;letter-spacing:0}
    body{padding:20px}
    .evidenceFrame{background:#fff;border:1px solid #c8ced5;margin:0 auto;min-height:220px;width:min(1280px,calc(100vw - 40px))}
    .evidenceChrome{align-items:center;background:#24323b;color:#fff;display:flex;font-size:13px;font-weight:600;height:44px;padding:0 16px}
    .evidencePage{background:#f7f8f9;padding:20px}
    .evidenceColumn{background:#fff;margin:0 auto;max-width:100%;width:100%}
    body[data-evidence-layout=narrow-spfx-column] .evidenceFrame{width:min(600px,calc(100vw - 40px))}
    body[data-evidence-layout=narrow-spfx-column] .evidenceColumn{width:480px}
    body[data-evidence-layout=narrow-spfx-column] .nacWorkbench header{display:block}
    body[data-evidence-layout=narrow-spfx-column] .nacWorkbench__badge{display:inline-block;margin-top:12px}
    body[data-evidence-layout=state] .evidenceFrame{width:min(680px,calc(100vw - 40px))}
    body[data-evidence-layout=state] .evidencePage{min-height:176px}
    body[data-evidence-layout=mobile]{padding:0}
    body[data-evidence-layout=mobile] .evidenceFrame{border-left:0;border-right:0;width:100%}
    body[data-evidence-layout=mobile] .evidenceChrome{height:40px;padding:0 12px}
    body[data-evidence-layout=mobile] .evidencePage{padding:0}
    @media(max-width:440px){body{padding:0}.evidenceFrame{border-left:0;border-right:0;width:100%}.evidencePage{padding:0}}
  </style>
</head>
<body>
  <section class="evidenceFrame" data-nac-evidence-frame>
    <div class="evidenceChrome">NaC · Synthetische Teamwebsite</div>
    <main class="evidencePage">
      <div class="evidenceColumn" data-nac-evidence-root></div>
    </main>
  </section>
  <script src="bundle.js"></script>
</body>
</html>`;
}

async function compile() {
  fs.mkdirSync(outputRoot, { recursive: true });
  for (const required of [hostPath, projectionPath]) {
    if (!fs.existsSync(required)) {
      throw new Error('NAC_WORKBENCH_LIVE_BUILD_ARTIFACT_MISSING: ' + required);
    }
  }
  fs.writeFileSync(entryPath, browserEntry(), { encoding: 'utf8', mode: 0o600 });
  fs.writeFileSync(htmlPath, html(), { encoding: 'utf8', mode: 0o600 });
  const stats = await new Promise((resolve, reject) => {
    webpack({
      mode: 'production',
      target: 'web',
      entry: entryPath,
      devtool: false,
      output: { path: outputRoot, filename: path.basename(bundlePath) },
      resolve: { modules: [path.join(packageRoot, 'node_modules')] },
      performance: { hints: false }
    }, (error, value) => error ? reject(error) : resolve(value));
  });
  if (!stats || stats.hasErrors()) {
    throw new Error('NAC_WORKBENCH_LIVE_FIXTURE_BUILD_FAILED\n' +
      (stats ? stats.toString({ all: false, errors: true }) : 'missing webpack stats'));
  }
  fs.chmodSync(bundlePath, 0o600);
  console.log(htmlPath);
}

compile().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
