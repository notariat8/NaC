'use strict';

const fs = require('fs');
const path = require('path');
const React = require('react');
const ReactDOMServer = require('react-dom/server');
const { parseNacWorkbenchProjectionJson } = require('../lib-commonjs/workbench/nac/NacWorkbenchProjection.js');
const { WorkbenchPanel } = require('../lib-commonjs/workbench/react/WorkbenchPanel.js');
const snapshotFixture = require('./workbench-synthetic-snapshot.cjs');

const output = path.resolve(process.argv[2] || '/tmp/nac-generic-workbench.html');
const nowIso = '2026-08-01T09:01:00Z';
async function main() {
  const snapshot = await parseNacWorkbenchProjectionJson(
    JSON.stringify(snapshotFixture),
    nowIso,
    {
      ...snapshotFixture.scope,
      subjectId: snapshotFixture.access.subjectId,
      role: snapshotFixture.access.role
    }
  );
  const markup = ReactDOMServer.renderToStaticMarkup(React.createElement(WorkbenchPanel, {
    snapshot,
    now: () => new Date(nowIso)
  }));
  const html = `<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NaC Generic Workbench - synthetische Evidence</title><style>html,body{margin:0;min-height:100%;background:#eef1f3}body{padding:24px}@media(max-width:440px){body{padding:0}}</style></head>
<body>${markup}<script>document.documentElement.dataset.nacVisualReady='true';</script></body></html>`;

  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, html, { encoding: 'utf8', mode: 0o600 });
  console.log(output);
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
