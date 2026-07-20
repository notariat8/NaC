export const nacBpmnViewerStyles: Record<string, string> = {
  workspace: 'nacBpmnViewer__workspace',
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
  taskOpen: 'nacBpmnViewer__taskOpen',
  taskPrepared: 'nacBpmnViewer__taskPrepared',
  footer: 'nacBpmnViewer__footer',
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
  --success-bg: #e7f4ea;
  --success-text: #176b35;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  font-family: "Segoe UI", Arial, sans-serif;
  min-height: 620px;
}
.nacBpmnViewer__dark {
  --surface: #202124;
  --surface-muted: #292b2f;
  --border: #45484d;
  --text: #f4f5f6;
  --muted: #c0c5ca;
  --current-step-fill: #ffe08a;
  --current-step-stroke: #5c2100;
  --success-bg: #183d28;
  --success-text: #a9e9bd;
}
.nacBpmnViewer__header {
  align-items: flex-start;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  padding: 24px 28px 20px;
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
  white-space: nowrap;
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
  width: 100%;
}
.nacBpmnViewer__workspace .djs-element.nac-current-step .djs-visual > :first-child {
  fill: var(--current-step-fill) !important;
  stroke: var(--current-step-stroke) !important;
  stroke-width: 4px !important;
}
.nacBpmnViewer__tasks ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.nacBpmnViewer__tasks li {
  align-items: center;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 12px;
  justify-content: space-between;
  min-height: 58px;
  padding: 10px 0;
}
.nacBpmnViewer__tasks li div {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.nacBpmnViewer__tasks li strong {
  font-size: 14px;
  overflow-wrap: anywhere;
}
.nacBpmnViewer__taskOpen {
  background: #fff2cc;
  color: #6f5300 !important;
}
.nacBpmnViewer__footer {
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  padding: 10px 22px;
}
.nacBpmnViewer__error {
  background: #fde7e9;
  border: 1px solid #d13438;
  color: #a4262c;
  padding: 16px;
}
@media (max-width: 760px) {
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
}
`;
