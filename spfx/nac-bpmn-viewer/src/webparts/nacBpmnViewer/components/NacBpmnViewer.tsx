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
  | { readonly kind: 'ready'; readonly workspace: NacBffWorkspace };

export function NacBpmnViewer(props: NacBpmnViewerProps): JSX.Element {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
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

        const elementRegistry = viewer.get('elementRegistry') as {
          get: (elementId: string) => unknown;
        };
        const canvas = viewer.get('canvas') as {
          addMarker: (elementId: string, marker: string) => void;
          resized: () => void;
          zoom: (mode: string) => void;
        };
        const currentElement = elementRegistry.get(currentTask.stepCode);
        if (currentElement === undefined || currentElement === null) {
          throw new Error('Current BPMN element is missing.');
        }

        canvas.addMarker(currentTask.stepCode, 'nac-current-step');
        const fitViewport = (): void => {
          canvas.resized();
          canvas.zoom('fit-viewport');
        };
        fitViewport();
        if (typeof ResizeObserver !== 'undefined' && containerRef.current !== null) {
          resizeObserver = new ResizeObserver(() => {
            if (!disposed && !destroyed) {
              try {
                fitViewport();
              } catch {
                resizeObserver?.disconnect();
                destroyViewer();
                setState({ kind: 'renderFailed' });
              }
            }
          });
          resizeObserver.observe(containerRef.current);
        }
        finished = true;
        window.clearTimeout(timeoutId);
        setState({ kind: 'ready', workspace });
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
      destroyViewer();
    };
  }, [bpmnXml, workspace]);

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
                  <div><strong>{task.title}</strong><span>{task.taskId} · {task.stepCode}</span><span>{task.dueAt ? formatTimestamp(task.dueAt) : 'Vor Fristablauf'}</span></div>
                  <span className={styles.taskOpen}>{task.status}</span>
                </li>
              ))}
            </ul>
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
