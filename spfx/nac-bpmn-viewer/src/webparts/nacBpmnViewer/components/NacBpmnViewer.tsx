import * as React from 'react';
import BpmnViewer from 'bpmn-js/lib/Viewer';
import 'bpmn-js/dist/assets/diagram-js.css';
import {
  classifyNacBffFailure,
  NAC_BFF_WORKSPACE_ID,
  NacBffWorkspace
} from '../services/NacBffClient';
import { nacBpmnViewerStyles as styles, nacBpmnViewerStyleSheet } from './NacBpmnViewer.styles';

const LOAD_TIMEOUT_MS = 10_000;
const RENDER_TIMEOUT_MS = 10_000;
let nextTaskDetailsId = 0;

export interface NacBpmnViewerProps {
  workspaceId: string;
  userDisplayName: string;
  hostName: string;
  isDarkTheme: boolean;
  loadWorkspace: (signal: AbortSignal) => Promise<NacBffWorkspace>;
}

type ViewerState =
  | { readonly kind: 'loading' }
  | { readonly kind: 'accessDenied' }
  | { readonly kind: 'unavailable' }
  | { readonly kind: 'invalidAsset' }
  | { readonly kind: 'renderFailed' }
  | { readonly kind: 'rendering'; readonly workspace: NacBffWorkspace }
  | {
    readonly kind: 'ready';
    readonly workspace: NacBffWorkspace;
    readonly selectedTaskId: string;
  };

interface ViewerCanvas {
  addMarker: (elementId: string, marker: string) => void;
  removeMarker: (elementId: string, marker: string) => void;
  resized: () => void;
  zoom: (mode: string) => void;
}

interface ViewerRuntime {
  readonly canvas: ViewerCanvas;
  selectedStepCode: string;
  failClosed: () => void;
}

export function NacBpmnViewer(props: NacBpmnViewerProps): JSX.Element {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const viewerRuntimeRef = React.useRef<ViewerRuntime | null>(null);
  const taskDetailsIdRef = React.useRef<string | null>(null);
  if (taskDetailsIdRef.current === null) {
    nextTaskDetailsId += 1;
    taskDetailsIdRef.current = 'nac-selected-task-details-' + nextTaskDetailsId;
  }
  const taskDetailsId = taskDetailsIdRef.current;
  const taskDetailsHeadingId = taskDetailsId + '-heading';
  const [state, setState] = React.useState<ViewerState>({ kind: 'loading' });
  const isApprovedWorkspace = props.workspaceId === NAC_BFF_WORKSPACE_ID;

  React.useEffect(() => {
    if (!isApprovedWorkspace) {
      setState({ kind: 'accessDenied' });
      return undefined;
    }

    const controller = new AbortController();
    let disposed = false;
    let finished = false;
    const timeoutId = window.setTimeout(() => {
      finished = true;
      controller.abort();
      if (!disposed) {
        setState({ kind: 'unavailable' });
      }
    }, LOAD_TIMEOUT_MS);

    setState({ kind: 'loading' });
    props.loadWorkspace(controller.signal).then(value => {
      if (!disposed && !finished) {
        finished = true;
        setState({ kind: 'rendering', workspace: value });
      }
    }).catch(error => {
      if (!disposed && !finished) {
        finished = true;
        setState({ kind: classifyNacBffFailure(error) });
      }
    }).finally(() => window.clearTimeout(timeoutId));

    return () => {
      disposed = true;
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [isApprovedWorkspace, props.loadWorkspace]);

  const workspace = isApprovedWorkspace && (state.kind === 'rendering' || state.kind === 'ready')
    ? state.workspace
    : null;
  const bpmnXml = workspace?.matter.bpmn.xml;

  React.useEffect(() => {
    if (!containerRef.current || workspace === null || bpmnXml === undefined) {
      return;
    }

    const viewer = new BpmnViewer({ container: containerRef.current });
    let disposed = false;
    let destroyed = false;
    let finished = false;
    let resizeObserver: ResizeObserver | undefined;
    const destroyViewer = (): void => {
      if (!destroyed) {
        viewer.destroy();
        destroyed = true;
      }
    };
    const timeoutId = window.setTimeout(() => {
      if (!disposed && !finished) {
        finished = true;
        destroyViewer();
        setState({ kind: 'renderFailed' });
      }
    }, RENDER_TIMEOUT_MS);

    viewer.importXML(bpmnXml).then(() => {
      if (!disposed && !finished) {
        const currentTask = workspace.matter.tasks[0];
        if (currentTask === undefined) {
          throw new Error('Current BPMN task is missing.');
        }

        const taskIds = new Set<string>();
        const stepCodes = new Set<string>();
        for (const task of workspace.matter.tasks) {
          if (taskIds.has(task.taskId)) {
            throw new Error('Duplicate taskId is not allowed.');
          }
          if (stepCodes.has(task.stepCode)) {
            throw new Error('Duplicate stepCode is not allowed.');
          }
          taskIds.add(task.taskId);
          stepCodes.add(task.stepCode);
        }

        const elementRegistry = viewer.get('elementRegistry') as {
          get: (elementId: string) => unknown;
        };
        const canvas = viewer.get('canvas') as ViewerCanvas;
        const currentElement = elementRegistry.get(currentTask.stepCode);
        if (!isCanonicalBpmnTask(currentElement, currentTask.stepCode)) {
          throw new Error('Current BPMN element is missing.');
        }
        for (const task of workspace.matter.tasks.slice(1)) {
          const taskElement = elementRegistry.get(task.stepCode);
          if (!isCanonicalBpmnTask(taskElement, task.stepCode)) {
            throw new Error('Task BPMN element is missing.');
          }
        }

        canvas.addMarker(currentTask.stepCode, 'nac-current-step');
        canvas.addMarker(currentTask.stepCode, 'nac-selected-step');
        const fitViewport = (): void => {
          canvas.resized();
          canvas.zoom('fit-viewport');
        };
        const failClosed = (): void => {
          if (!disposed) {
            resizeObserver?.disconnect();
            resizeObserver = undefined;
            destroyViewer();
            viewerRuntimeRef.current = null;
            setState({ kind: 'renderFailed' });
          }
        };
        fitViewport();
        if (typeof ResizeObserver !== 'undefined' && containerRef.current !== null) {
          resizeObserver = new ResizeObserver(() => {
            if (!disposed && !destroyed) {
              try {
                fitViewport();
              } catch {
                failClosed();
              }
            }
          });
          resizeObserver.observe(containerRef.current);
        }
        viewerRuntimeRef.current = {
          canvas,
          selectedStepCode: currentTask.stepCode,
          failClosed
        };
        finished = true;
        window.clearTimeout(timeoutId);
        setState({ kind: 'ready', workspace, selectedTaskId: currentTask.taskId });
      }
    }).catch(() => {
      if (!disposed && !finished) {
        finished = true;
        window.clearTimeout(timeoutId);
        destroyViewer();
        setState({ kind: 'renderFailed' });
      }
    });

    return () => {
      disposed = true;
      window.clearTimeout(timeoutId);
      resizeObserver?.disconnect();
      viewerRuntimeRef.current = null;
      destroyViewer();
    };
  }, [bpmnXml, workspace]);

  const selectTask = React.useCallback((taskId: string): void => {
    if (state.kind !== 'ready') {
      return;
    }
    const runtime = viewerRuntimeRef.current;
    const task = state.workspace.matter.tasks.find(candidate => candidate.taskId === taskId);
    if (runtime === null || task === undefined || runtime.selectedStepCode === task.stepCode) {
      return;
    }
    try {
      runtime.canvas.removeMarker(runtime.selectedStepCode, 'nac-selected-step');
      runtime.canvas.addMarker(task.stepCode, 'nac-selected-step');
      runtime.selectedStepCode = task.stepCode;
      setState({ ...state, selectedTaskId: task.taskId });
    } catch {
      runtime.failClosed();
    }
  }, [state]);

  if (!isApprovedWorkspace) {
    return <ViewerMessage message="Kein Zugriff auf diesen Vorgang." />;
  }
  if (state.kind === 'loading') {
    return <ViewerMessage message="Vorgangsdaten werden geladen." />;
  }
  if (state.kind === 'accessDenied') {
    return <ViewerMessage message="Kein Zugriff auf diesen Vorgang." />;
  }
  if (state.kind === 'unavailable') {
    return <ViewerMessage message="Vorgangsdaten sind derzeit nicht verfügbar." />;
  }
  if (state.kind === 'invalidAsset' || state.kind === 'renderFailed') {
    return <ViewerMessage message="Prozessmodell ist derzeit nicht verfügbar." />;
  }

  const matter = state.kind === 'ready' ? state.workspace.matter : null;
  const currentTask = matter?.tasks[0] ?? null;
  const selectedTaskId = state.kind === 'ready' ? state.selectedTaskId : null;
  const selectedTask = state.kind === 'ready'
    ? state.workspace.matter.tasks.find(task => task.taskId === state.selectedTaskId) ?? null
    : null;
  const stageLabel = currentTask?.title ?? 'Keine offene Aufgabe';
  const accessMode = matter?.accessMode === 'deputy'
    ? 'Vertretung (deputy)'
    : 'Zugeordnet (assigned)';
  const deadlineLabel = matter === null ? '' : formatTimestamp(matter.deadline);

  return (
    <main className={styles.workspace + (props.isDarkTheme ? ' ' + styles.dark : '')} data-nac-component="test-workspace">
      <style>{nacBpmnViewerStyleSheet}</style>
      <header className={styles.header}>
        <div>
          <span className={styles.eyebrow}>NaC Testnotariat</span>
          <h1>{matter === null ? 'Prozessmodell wird geladen.' : matter.displayName}</h1>
          <p>Immobilienkaufvertrag</p>
        </div>
        {matter !== null && (
          <div className={styles.headerMeta}>
            <span className={styles.status}>{matter.status}</span>
            <span>{props.hostName}</span>
          </div>
        )}
      </header>

      {matter !== null && (
        <section className={styles.summary} aria-label="Vorgangsstatus">
          <div><span>Aktueller Schritt</span><strong>{stageLabel}</strong></div>
          <div><span>Nächste Frist</span><strong>{deadlineLabel}</strong></div>
          <div><span>Zugriffsmodus</span><strong>{accessMode}</strong></div>
          <div><span>Angemeldet</span><strong>{props.userDisplayName}</strong></div>
        </section>
      )}

      <div className={styles.contentGrid}>
        <section className={styles.process} aria-labelledby="process-heading">
          <div className={styles.sectionHeading}>
            <div>
              <span>Prozessmodell</span>
              <h2 id="process-heading">Immobilienkaufvertrag</h2>
            </div>
            <span className={styles.fixtureBadge}>Synthetische Testdaten</span>
          </div>
          <div className={styles.canvasScroller}>
            <div
              className={styles.canvas}
              ref={containerRef}
              aria-label="BPMN-Prozessdiagramm"
              data-nac-current-step={currentTask?.stepCode}
              data-nac-selected-step={selectedTask?.stepCode}
            />
          </div>
        </section>

        {matter !== null && (
          <aside className={styles.tasks} aria-labelledby="tasks-heading">
            <div className={styles.sectionHeading}>
              <div>
                <span>Arbeitsvorrat</span>
                <h2 id="tasks-heading">Aufgaben</h2>
              </div>
              <strong>{matter.tasks.length}</strong>
            </div>
            <ul>
              {matter.tasks.map(task => (
                <li key={task.taskId}>
                  <button
                    type="button"
                    className={styles.taskButton}
                    data-nac-task-id={task.taskId}
                    aria-pressed={task.taskId === selectedTaskId}
                    aria-controls={taskDetailsId}
                    onClick={() => selectTask(task.taskId)}
                  >
                    <span className={styles.taskCopy}>
                      <strong>{task.title}</strong>
                      <span>{task.taskId} · {task.stepCode}</span>
                    </span>
                    <span className={styles.taskOpen}>{task.status}</span>
                  </button>
                </li>
              ))}
            </ul>
            {selectedTask !== null && (
              <section
                id={taskDetailsId}
                className={styles.taskDetails}
                aria-labelledby={taskDetailsHeadingId}
              >
                <span>Ausgewählte Aufgabe</span>
                <h3 id={taskDetailsHeadingId}>{selectedTask.title}</h3>
                <dl>
                  <div><dt>Status</dt><dd>{selectedTask.status}</dd></div>
                  <div>
                    <dt>Eigene Frist</dt>
                    <dd>{selectedTask.dueAt ? formatTimestamp(selectedTask.dueAt) : 'Keine eigene Frist'}</dd>
                  </div>
                  <div>
                    <dt>Freigabe</dt>
                    <dd>{selectedTask.requiresNotaryApproval
                      ? 'Notarielle Freigabe erforderlich'
                      : 'Keine notarielle Freigabe erforderlich'}</dd>
                  </div>
                </dl>
              </section>
            )}
          </aside>
        )}
      </div>

      {matter !== null && (
        <footer className={styles.footer}>
          <span>Workspace {state.workspace.workspaceId}</span>
          <span>Keine Mandatsdaten</span>
        </footer>
      )}
    </main>
  );
}

function isCanonicalBpmnTask(value: unknown, expectedStepCode: string): boolean {
  if (typeof value !== 'object' || value === null) {
    return false;
  }
  const element = value as {
    id?: unknown;
    businessObject?: { $instanceOf?: (bpmnType: string) => boolean };
  };
  const businessObject = element.businessObject;
  return element.id === expectedStepCode &&
    typeof businessObject?.$instanceOf === 'function' &&
    businessObject.$instanceOf('bpmn:Task') === true;
}

function ViewerMessage(props: { message: string }): JSX.Element {
  return (
    <>
      <style>{nacBpmnViewerStyleSheet}</style>
      <div className={styles.error}>{props.message}</div>
    </>
  );
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Berlin'
  }).format(date) + ' Uhr (' + value + ')';
}
