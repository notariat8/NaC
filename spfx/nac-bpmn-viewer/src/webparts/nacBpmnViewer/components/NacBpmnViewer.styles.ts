export const nacBpmnViewerStyles: Record<string, string> = {
  workspace: 'nacBpmnViewer__workspace',
  messageHost: 'nacBpmnViewer__messageHost',
  dark: 'nacBpmnViewer__dark',
  header: 'nacBpmnViewer__header',
  eyebrow: 'nacBpmnViewer__eyebrow',
  headerMeta: 'nacBpmnViewer__headerMeta',
  status: 'nacBpmnViewer__status',
  summary: 'nacBpmnViewer__summary',
  contentGrid: 'nacBpmnViewer__contentGrid',
  process: 'nacBpmnViewer__process',
  tasks: 'nacBpmnViewer__tasks',
  sectionHeading: 'nacBpmnViewer__sectionHeading',
  fixtureBadge: 'nacBpmnViewer__fixtureBadge',
  canvasScroller: 'nacBpmnViewer__canvasScroller',
  canvas: 'nacBpmnViewer__canvas',
  filters: 'nacBpmnViewer__filters',
  taskButton: 'nacBpmnViewer__taskButton',
  taskCopy: 'nacBpmnViewer__taskCopy',
  taskBadges: 'nacBpmnViewer__taskBadges',
  taskDetails: 'nacBpmnViewer__taskDetails',
  taskOpen: 'nacBpmnViewer__taskOpen',
  taskPrepared: 'nacBpmnViewer__taskPrepared',
  approvalBadge: 'nacBpmnViewer__approvalBadge',
  deadlineState: 'nacBpmnViewer__deadlineState',
  deadlinenone: 'nacBpmnViewer__deadlineNone',
  deadlineoverdue: 'nacBpmnViewer__deadlineOverdue',
  deadlineurgent: 'nacBpmnViewer__deadlineUrgent',
  deadlinescheduled: 'nacBpmnViewer__deadlineScheduled',
  emptyState: 'nacBpmnViewer__emptyState',
  visuallyHidden: 'nacBpmnViewer__visuallyHidden',
  footer: 'nacBpmnViewer__footer',
  message: 'nacBpmnViewer__message',
  error: 'nacBpmnViewer__error'
};

export const nacBpmnViewerStyleSheet = `
.nacBpmnViewer__workspace {
  --surface: #ffffff;
  --surface-muted: #f5f6f7;
  --border: #d7dce1;
  --text: #17202a;
  --muted: #5f6b76;
  --accent: #005a9e;
  --current-step-fill: #fff4ce;
  --current-step-stroke: #8a0c12;
  --selected-step-stroke: #0078d4;
  --selected-task-bg: #eef6fc;
  --success-bg: #e7f4ea;
  --success-text: #176b35;
  --danger-bg: #fde7e9;
  --danger-text: #a4262c;
  --warning-bg: #fff4ce;
  --warning-text: #6f5300;
  --info-bg: #eaf2fb;
  --info-text: #174f7c;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  container-type: inline-size;
  font-family: "Segoe UI", Arial, sans-serif;
  max-width: 100%;
  min-height: 620px;
  overflow-wrap: anywhere;
}
.nacBpmnViewer__messageHost {
  --surface: #ffffff;
  --text: #17202a;
  --border: #d7dce1;
  --muted: #5f6b76;
  --info-bg: #eaf2fb;
  --info-text: #174f7c;
  --danger-bg: #fde7e9;
  --danger-text: #a4262c;
  --selected-step-stroke: #0078d4;
  background: var(--surface);
  color: var(--text);
  container-type: inline-size;
  font-family: "Segoe UI", Arial, sans-serif;
}
.nacBpmnViewer__dark {
  --accent: #6cb8f6;
  --surface: #202124;
  --surface-muted: #292b2f;
  --border: #45484d;
  --text: #f4f5f6;
  --muted: #c0c5ca;
  --current-step-fill: #ffe08a;
  --current-step-stroke: #5c2100;
  --selected-step-stroke: #6cb8f6;
  --selected-task-bg: #25394a;
  --success-bg: #183d28;
  --success-text: #a9e9bd;
  --danger-bg: #4a2024;
  --danger-text: #ffb3b8;
  --warning-bg: #493b16;
  --warning-text: #ffe08a;
  --info-bg: #20384b;
  --info-text: #a9d5f5;
}
.nacBpmnViewer__header {
  align-items: flex-start;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  padding: 24px 28px 20px;
}
.nacBpmnViewer__header > div,
.nacBpmnViewer__headerMeta,
.nacBpmnViewer__taskButton,
.nacBpmnViewer__taskCopy,
.nacBpmnViewer__taskBadges,
.nacBpmnViewer__footer span {
  max-width: 100%;
  min-width: 0;
}
.nacBpmnViewer__header h1,
.nacBpmnViewer__header p,
.nacBpmnViewer__headerMeta span,
.nacBpmnViewer__taskCopy span,
.nacBpmnViewer__footer span {
  overflow-wrap: anywhere;
}
.nacBpmnViewer__header h1,
.nacBpmnViewer__sectionHeading h2 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 0;
  line-height: 1.25;
  margin: 3px 0 4px;
}
.nacBpmnViewer__header p,
.nacBpmnViewer__headerMeta,
.nacBpmnViewer__sectionHeading span,
.nacBpmnViewer__summary span,
.nacBpmnViewer__tasks li span,
.nacBpmnViewer__footer {
  color: var(--muted);
  font-size: 13px;
}
.nacBpmnViewer__eyebrow {
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}
.nacBpmnViewer__headerMeta {
  align-items: flex-end;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.nacBpmnViewer__status,
.nacBpmnViewer__fixtureBadge,
.nacBpmnViewer__taskOpen,
.nacBpmnViewer__taskPrepared {
  border-radius: 4px;
  display: inline-flex;
  font-weight: 600;
  padding: 4px 8px;
  max-width: 100%;
  overflow-wrap: anywhere;
  white-space: normal;
}
.nacBpmnViewer__status,
.nacBpmnViewer__taskPrepared {
  background: var(--success-bg);
  color: var(--success-text) !important;
}
.nacBpmnViewer__fixtureBadge {
  background: #eaf2fb;
  color: #174f7c !important;
}
.nacBpmnViewer__summary {
  background: var(--surface-muted);
  border-bottom: 1px solid var(--border);
  display: grid;
  gap: 1px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.nacBpmnViewer__summary div {
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
  padding: 15px 20px;
}
.nacBpmnViewer__summary strong {
  font-size: 14px;
  overflow-wrap: anywhere;
}
.nacBpmnViewer__summary small {
  color: var(--muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.nacBpmnViewer__contentGrid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(260px, 1fr);
  min-height: 420px;
}
.nacBpmnViewer__process,
.nacBpmnViewer__tasks {
  min-width: 0;
  padding: 22px;
}
.nacBpmnViewer__tasks {
  border-left: 1px solid var(--border);
}
.nacBpmnViewer__sectionHeading {
  align-items: center;
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
.nacBpmnViewer__sectionHeading h2 {
  font-size: 17px;
}
.nacBpmnViewer__canvasScroller {
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  overscroll-behavior-inline: contain;
}
.nacBpmnViewer__canvas {
  background: #ffffff;
  border: 1px solid var(--border);
  box-sizing: border-box;
  height: 340px;
  overflow: hidden;
  min-width: 0;
  width: 100%;
}
.nacBpmnViewer__workspace .djs-element.nac-current-step .djs-visual > :first-child {
  fill: var(--current-step-fill) !important;
  stroke: var(--current-step-stroke) !important;
  stroke-width: 4px !important;
}
.nacBpmnViewer__workspace .djs-element.nac-selected-step .djs-visual > :first-child {
  filter: drop-shadow(0 0 4px var(--selected-step-stroke));
}
.nacBpmnViewer__workspace .djs-element.nac-selected-step:not(.nac-current-step) .djs-visual > :first-child {
  stroke: var(--selected-step-stroke) !important;
  stroke-width: 3px !important;
}
.nacBpmnViewer__filters {
  border: 1px solid var(--border);
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-bottom: 14px;
}
.nacBpmnViewer__filters button {
  appearance: none;
  background: var(--surface);
  border: 0;
  border-bottom: 1px solid var(--border);
  color: var(--text);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
  min-height: 36px;
  padding: 7px 9px;
}
.nacBpmnViewer__filters button:nth-child(odd) {
  border-right: 1px solid var(--border);
}
.nacBpmnViewer__filters button:nth-last-child(-n + 2) {
  border-bottom: 0;
}
.nacBpmnViewer__filters button[aria-pressed="true"] {
  background: var(--selected-task-bg);
  box-shadow: inset 0 -3px 0 var(--selected-step-stroke);
  color: var(--accent);
  font-weight: 600;
}
.nacBpmnViewer__filters button:focus-visible {
  outline: 2px solid var(--selected-step-stroke);
  outline-offset: -2px;
}
.nacBpmnViewer__tasks ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.nacBpmnViewer__tasks li {
  border-top: 1px solid var(--border);
}
.nacBpmnViewer__taskButton {
  align-items: flex-start;
  appearance: none;
  background: transparent;
  border: 0;
  color: var(--text);
  cursor: pointer;
  display: flex;
  font: inherit;
  gap: 12px;
  justify-content: space-between;
  min-height: 58px;
  padding: 10px 0;
  text-align: left;
  width: 100%;
}
.nacBpmnViewer__taskButton[aria-pressed="true"] {
  background: var(--selected-task-bg);
  box-shadow: inset 3px 0 0 var(--selected-step-stroke);
  padding-left: 10px;
  padding-right: 8px;
}
.nacBpmnViewer__taskButton:focus-visible {
  outline: 2px solid var(--selected-step-stroke);
  outline-offset: 2px;
}
.nacBpmnViewer__taskCopy {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.nacBpmnViewer__taskButton strong {
  font-size: 14px;
  overflow-wrap: anywhere;
}
.nacBpmnViewer__taskBadges {
  align-items: flex-end;
  display: flex;
  flex-direction: column;
  flex-shrink: 1;
  gap: 5px;
  max-width: 50%;
  min-width: 0;
}
.nacBpmnViewer__taskOpen {
  background: var(--warning-bg);
  color: var(--warning-text) !important;
}
.nacBpmnViewer__approvalBadge,
.nacBpmnViewer__deadlineState {
  align-self: flex-start;
  border-radius: 4px;
  display: inline-flex;
  font-size: 11px;
  font-weight: 600;
  max-width: 100%;
  overflow-wrap: anywhere;
  padding: 3px 6px;
  white-space: normal;
}
.nacBpmnViewer__approvalBadge {
  background: var(--info-bg);
  color: var(--info-text) !important;
}
.nacBpmnViewer__deadlineOverdue {
  background: var(--danger-bg);
  color: var(--danger-text) !important;
}
.nacBpmnViewer__deadlineUrgent {
  background: var(--warning-bg);
  color: var(--warning-text) !important;
}
.nacBpmnViewer__deadlineScheduled {
  background: var(--success-bg);
  color: var(--success-text) !important;
}
.nacBpmnViewer__deadlineNone {
  color: var(--muted) !important;
}
.nacBpmnViewer__emptyState {
  align-items: flex-start;
  border-top: 1px solid var(--border);
  color: var(--muted);
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 18px 0;
}
.nacBpmnViewer__emptyState strong {
  color: var(--text);
  font-size: 14px;
}
.nacBpmnViewer__taskDetails {
  border-top: 1px solid var(--border);
  margin-top: 12px;
  padding-top: 18px;
}
.nacBpmnViewer__taskDetails > span,
.nacBpmnViewer__taskDetails dt {
  color: var(--muted);
  font-size: 12px;
}
.nacBpmnViewer__taskDetails h3 {
  font-size: 16px;
  margin: 4px 0 14px;
  overflow-wrap: anywhere;
}
.nacBpmnViewer__taskDetails dl {
  display: grid;
  gap: 10px;
  margin: 0;
}
.nacBpmnViewer__taskDetails dl div {
  display: grid;
  gap: 3px;
}
.nacBpmnViewer__taskDetails dd {
  font-size: 14px;
  margin: 0;
  overflow-wrap: anywhere;
}
.nacBpmnViewer__footer {
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  padding: 10px 22px;
}
.nacBpmnViewer__visuallyHidden {
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  height: 1px;
  overflow: hidden;
  position: absolute;
  white-space: nowrap;
  width: 1px;
}
.nacBpmnViewer__message,
.nacBpmnViewer__error {
  align-items: center;
  background: var(--info-bg);
  border: 1px solid var(--border);
  color: var(--info-text);
  display: flex;
  font-family: "Segoe UI", Arial, sans-serif;
  gap: 16px;
  justify-content: space-between;
  overflow-wrap: anywhere;
  padding: 16px;
}
.nacBpmnViewer__error {
  background: var(--danger-bg);
  border-color: var(--danger-text);
  color: var(--danger-text);
}
.nacBpmnViewer__error button {
  appearance: none;
  background: var(--surface);
  border: 1px solid var(--danger-text);
  color: var(--danger-text);
  cursor: pointer;
  font: inherit;
  font-weight: 600;
  min-height: 36px;
  padding: 7px 12px;
}
.nacBpmnViewer__error button:focus-visible {
  outline: 2px solid var(--selected-step-stroke);
  outline-offset: 2px;
}
@container (max-width: 760px) {
  .nacBpmnViewer__header,
  .nacBpmnViewer__sectionHeading {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }
  .nacBpmnViewer__headerMeta {
    align-items: flex-start;
  }
  .nacBpmnViewer__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .nacBpmnViewer__contentGrid {
    grid-template-columns: 1fr;
  }
  .nacBpmnViewer__tasks {
    border-left: 0;
    border-top: 1px solid var(--border);
  }
  .nacBpmnViewer__canvas {
    min-width: 720px;
  }
  .nacBpmnViewer__error,
  .nacBpmnViewer__footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
@container (max-width: 420px) {
  .nacBpmnViewer__header,
  .nacBpmnViewer__process,
  .nacBpmnViewer__tasks {
    padding-left: 14px;
    padding-right: 14px;
  }
  .nacBpmnViewer__summary {
    grid-template-columns: 1fr;
  }
  .nacBpmnViewer__summary div {
    border-right: 0;
  }
  .nacBpmnViewer__taskButton {
    align-items: stretch;
    flex-direction: column;
  }
  .nacBpmnViewer__taskBadges {
    align-items: flex-start;
    flex-direction: row;
    flex-wrap: wrap;
  }
}
`;
