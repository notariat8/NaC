'use strict';

const fs = require('fs');
const path = require('path');

const packageRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(packageRoot, '..', '..');
const output = path.resolve(process.argv[2] || '/tmp/nac-spfx-role-deadline-cockpit.html');
const styleSource = fs.readFileSync(
  path.join(packageRoot, 'src/webparts/nacBpmnViewer/components/NacBpmnViewer.styles.ts'),
  'utf8'
);
const delimiter = String.fromCharCode(96);
const prefix = 'export const nacBpmnViewerStyleSheet = ' + delimiter;
const styleStart = styleSource.indexOf(prefix);
const styleEnd = styleSource.lastIndexOf(delimiter + ';');
if (styleStart < 0 || styleEnd <= styleStart) {
  throw new Error('NAC_VISUAL_FIXTURE_STYLE_INVALID');
}
const componentCss = styleSource.slice(styleStart + prefix.length, styleEnd);
const diagramStyleSource = fs.readFileSync(
  path.join(packageRoot, 'src/webparts/nacBpmnViewer/components/DiagramJs.styles.ts'),
  'utf8'
);
const diagramPrefix = 'export const diagramJsStyleSheet = String.raw' + delimiter + '\n';
const diagramStyleStart = diagramStyleSource.indexOf(diagramPrefix);
const diagramStyleEnd = diagramStyleSource.lastIndexOf('\n' + delimiter + ';');
if (diagramStyleStart < 0 || diagramStyleEnd <= diagramStyleStart) {
  throw new Error('NAC_VISUAL_FIXTURE_DIAGRAM_STYLE_INVALID');
}
const diagramCss = diagramStyleSource.slice(
  diagramStyleStart + diagramPrefix.length,
  diagramStyleEnd
);
const dependencyDiagramCss = fs.readFileSync(
  path.join(packageRoot, 'node_modules/bpmn-js/dist/assets/diagram-js.css'),
  'utf8'
);
if (diagramCss !== dependencyDiagramCss) {
  throw new Error('NAC_VISUAL_FIXTURE_DIAGRAM_STYLE_DRIFT');
}
const bpmnBundle = fs.readFileSync(
  path.join(packageRoot, 'node_modules/bpmn-js/dist/bpmn-viewer.production.min.js'),
  'utf8'
).replace(/<\/script/gi, '<\\/script');
const bpmnXml = fs.readFileSync(
  path.join(repoRoot, 'bpmn/immobilienkaufvertrag.bpmn'),
  'utf8'
);

const html = [
  '<!doctype html>',
  '<html lang="de">',
  '<head>',
  '<meta charset="utf-8">',
  '<meta name="viewport" content="width=device-width,initial-scale=1">',
  '<title>NaC Rollen- und Fristen-Cockpit - synthetische Evidence</title>',
  '<style>',
  'html,body{margin:0;min-height:100%;background:#f3f4f6;}',
  'body{box-sizing:border-box;padding:24px;}',
  '@media(max-width:420px){body{padding:0;}}',
  diagramCss,
  componentCss,
  '</style>',
  '</head>',
  '<body>',
  '<div id="app"></div>',
  '<script>',
  bpmnBundle,
  '</script>',
  '<script>',
  "'use strict';",
  'const query = new URLSearchParams(location.search);',
  "const theme = query.get('theme') === 'dark' ? 'dark' : 'light';",
  "const requestedFilter = query.get('filter') || 'all';",
  "const visualState = query.get('state') || 'ready';",
  "const requestedSelection = query.get('selected') || 'current';",
  "const referenceTimestamp = '2026-08-25T16:00:00Z';",
  'const tasks = [',
  "{taskId:'NAC-SYN-TASK-001',title:'Entwurf prüfen',stepCode:'Task_EntwurfAbstimmen',status:'Offen',requiresNotaryApproval:true,dueAt:null},",
  "{taskId:'NAC-SYN-DEADLINE-001',title:'Abschlussfrist überwachen',stepCode:'Task_NachweiseNachhalten',status:'Offen',requiresNotaryApproval:false,dueAt:'2026-08-31T16:00:00Z'}",
  '];',
  "if (visualState === 'empty') tasks.forEach(task => { task.requiresNotaryApproval = false; });",
  "const filters = [{id:'all',label:'Alle Aufgaben'},{id:'open',label:'Offene Aufgaben'},{id:'deadline',label:'Aufgaben mit Frist'},{id:'notary',label:'Aufgaben mit Notarfreigabe'}];",
  "let activeFilter = visualState === 'empty' ? 'notary' : requestedFilter;",
  "let selectedTaskId = requestedSelection === 'deadline' ? 'NAC-SYN-DEADLINE-001' : 'NAC-SYN-TASK-001';",
  'let viewer;',
  'let canvas;',
  'const app = document.getElementById("app");',
  "if (visualState === 'error') {",
  "  app.innerHTML = '<div class=\"nacBpmnViewer__messageHost'+(theme==='dark'?' nacBpmnViewer__dark':'')+'\"><div class=\"nacBpmnViewer__error\" role=\"alert\" aria-live=\"assertive\"><span>Vorgangsdaten sind derzeit nicht verfügbar.</span><button type=\"button\">Erneut laden</button></div></div>';",
  "  app.querySelector('button').addEventListener('click',function(){location.search=theme==='dark'?'?theme=dark':'';});",
  "  document.documentElement.dataset.nacVisualReady = 'true';",
  '} else {',
  '  renderShell();',
  '  viewer = new BpmnJS({container: "#canvas"});',
  '  viewer.importXML(' + JSON.stringify(bpmnXml) + ').then(function(){',
  "    canvas = viewer.get('canvas');",
  "    canvas.addMarker('Task_EntwurfAbstimmen','nac-current-step');",
  "    canvas.addMarker(tasks.find(function(task){return task.taskId===selectedTaskId;}).stepCode,'nac-selected-step');",
  "    canvas.zoom('fit-viewport');",
  '    applyFilter(activeFilter);',
  "    document.documentElement.dataset.nacVisualReady = 'true';",
  '  }).catch(function(error){',
  "    app.innerHTML = '<div class=\"nacBpmnViewer__error\"><span>Prozessmodell ist derzeit nicht verfügbar.</span></div>';",
  "    document.documentElement.dataset.nacVisualError = String(error);",
  '  });',
  '}',
  'function renderShell(){',
  "  app.innerHTML = '<main class=\"nacBpmnViewer__workspace'+(theme==='dark'?' nacBpmnViewer__dark':'')+'\" data-nac-component=\"test-workspace\">'+",
  "  '<header class=\"nacBpmnViewer__header\"><div><span class=\"nacBpmnViewer__eyebrow\">NaC Testnotariat</span><h1>Synthetischer Immobilienkaufvertrag</h1><p>Immobilienkaufvertrag</p></div><div class=\"nacBpmnViewer__headerMeta\"><span class=\"nacBpmnViewer__status\">Entwurf</span><span>Microsoft Teams</span></div></header>'+",
  "  '<section class=\"nacBpmnViewer__summary\" aria-label=\"Vorgangsstatus\"><div><span>Aktueller Schritt</span><strong>Entwurf prüfen</strong></div><div><span>Nächste Frist</span><strong>31.08.2026, 18:00 Uhr (2026-08-31T16:00:00Z)</strong><span class=\"nacBpmnViewer__deadlineState nacBpmnViewer__deadlineUrgent\">Frist innerhalb von sieben Tagen</span><small>Stand: 25.08.2026, 18:00 Uhr ('+referenceTimestamp+')</small></div><div><span>Zugriffsmodus</span><strong>'+(theme==='dark'?'Aktive Vertretung (deputy)':'Zugeordnetes Team (assigned)')+'</strong></div><div><span>Rollenrahmen</span><strong>Synthetische Testperson</strong><small>1 notarielle Freigabe</small></div></section>'+",
  "  '<div class=\"nacBpmnViewer__contentGrid\"><section class=\"nacBpmnViewer__process\" aria-labelledby=\"process-heading\"><div class=\"nacBpmnViewer__sectionHeading\"><div><span>Prozessmodell</span><h2 id=\"process-heading\">Immobilienkaufvertrag</h2></div><span class=\"nacBpmnViewer__fixtureBadge\">Synthetische Testdaten</span></div><p id=\"diagram-status\" class=\"nacBpmnViewer__visuallyHidden\" aria-live=\"polite\" aria-atomic=\"true\"></p><div class=\"nacBpmnViewer__canvasScroller\"><div id=\"canvas\" class=\"nacBpmnViewer__canvas\" role=\"img\" aria-label=\"BPMN-Prozessdiagramm\" aria-describedby=\"diagram-status\"></div></div></section>'+",
  "  '<aside class=\"nacBpmnViewer__tasks\" aria-labelledby=\"tasks-heading\"><div class=\"nacBpmnViewer__sectionHeading\"><div><span>Arbeitsvorrat</span><h2 id=\"tasks-heading\">Aufgaben</h2></div><strong id=\"count\" aria-live=\"polite\" aria-atomic=\"true\"></strong></div><div id=\"filters\" class=\"nacBpmnViewer__filters\" role=\"group\" aria-label=\"Aufgaben filtern\"></div><ul id=\"tasks\"></ul><div id=\"details\"></div></aside></div>'+",
  "  '<footer class=\"nacBpmnViewer__footer\"><span>Workspace notary_team_01</span><span>Keine Mandatsdaten</span></footer></main>';",
  "  document.getElementById('filters').innerHTML = filters.map(function(filter){return '<button type=\"button\" data-filter=\"'+filter.id+'\" aria-pressed=\"false\">'+filter.label+'</button>';}).join('');",
  "  document.getElementById('filters').addEventListener('click',function(event){const button=event.target.closest('button[data-filter]');if(button)applyFilter(button.dataset.filter);});",
  '}',
  'function visibleTasks(){return tasks.filter(function(task){if(activeFilter==="all")return true;if(activeFilter==="open")return task.status.toLowerCase()==="offen";if(activeFilter==="deadline")return task.dueAt!==null;return task.requiresNotaryApproval;});}',
  'function applyFilter(filter){',
  '  activeFilter=filter;',
  '  const visible=visibleTasks();',
  '  document.querySelectorAll("[data-filter]").forEach(function(button){button.setAttribute("aria-pressed",String(button.dataset.filter===filter));});',
  '  if(!visible.some(function(task){return task.taskId===selectedTaskId;})){',
  '    const previous=tasks.find(function(task){return task.taskId===selectedTaskId;});',
  '    if(canvas&&previous){canvas.removeMarker(previous.stepCode,"nac-selected-step");}',
  '    selectedTaskId=visible.length?visible[0].taskId:null;',
  '    if(canvas&&selectedTaskId){canvas.addMarker(visible[0].stepCode,"nac-selected-step");}',
  '  }',
  '  document.getElementById("count").textContent=visible.length+"/"+tasks.length;',
  '  document.getElementById("tasks").innerHTML=visible.map(taskMarkup).join("");',
  '  document.getElementById("tasks").onclick=function(event){const button=event.target.closest("button[data-nac-task-id]");if(button)selectTask(button.dataset.nacTaskId);};',
  '  const selected=tasks.find(function(task){return task.taskId===selectedTaskId;});',
  '  document.getElementById("diagram-status").textContent="Aktueller Prozessschritt: Entwurf prüfen. Ausgewählte Aufgabe: "+(selected?selected.title:"Keine ausgewählte Aufgabe")+".";',
  '  document.getElementById("details").innerHTML=visible.length===0?\'<div class="nacBpmnViewer__emptyState" role="status" aria-live="polite"><strong>Keine passenden Aufgaben</strong><span>Wählen Sie einen anderen Filter.</span></div>\':detailMarkup(selected);',
  '}',
  'function selectTask(taskId){const next=tasks.find(function(task){return task.taskId===taskId;});const previous=tasks.find(function(task){return task.taskId===selectedTaskId;});if(!next||next===previous)return;if(canvas&&previous)canvas.removeMarker(previous.stepCode,"nac-selected-step");if(canvas)canvas.addMarker(next.stepCode,"nac-selected-step");selectedTaskId=taskId;applyFilter(activeFilter);}',
  'function taskMarkup(task){const selected=task.taskId===selectedTaskId;const deadline=task.dueAt?\'<span class="nacBpmnViewer__deadlineState nacBpmnViewer__deadlineUrgent">Frist innerhalb von sieben Tagen</span>\':\'\';const notary=task.requiresNotaryApproval?\'<span class="nacBpmnViewer__approvalBadge">Notar</span>\':\'\';return \'<li><button type="button" class="nacBpmnViewer__taskButton" data-nac-task-id="\'+task.taskId+\'" aria-pressed="\'+selected+\'"><span class="nacBpmnViewer__taskCopy"><strong>\'+task.title+\'</strong><span>\'+task.taskId+\' · \'+task.stepCode+\'</span><span>\'+(task.dueAt?\'31.08.2026, 18:00 Uhr (2026-08-31T16:00:00Z)\':\'Ohne eigene Frist\')+\'</span></span><span class="nacBpmnViewer__taskBadges"><span class="nacBpmnViewer__taskOpen">\'+task.status+\'</span>\'+notary+deadline+\'</span></button></li>\';}',
  'function detailMarkup(task){if(!task)return "";return \'<section class="nacBpmnViewer__taskDetails"><span>Ausgewählte Aufgabe</span><h3>\'+task.title+\'</h3><dl><div><dt>Status</dt><dd>\'+task.status+\'</dd></div><div><dt>Eigene Frist</dt><dd>\'+(task.dueAt?\'31.08.2026, 18:00 Uhr (2026-08-31T16:00:00Z)\':\'Keine eigene Frist\')+\'</dd></div><div><dt>Freigabe</dt><dd>\'+(task.requiresNotaryApproval?\'Notarielle Freigabe erforderlich\':\'Keine notarielle Freigabe erforderlich\')+\'</dd></div></dl></section>\';}',
  '</script>',
  '</body>',
  '</html>'
].join('\n');

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, html, { encoding: 'utf8', mode: 0o600 });
console.log(output);
