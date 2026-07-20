import * as React from 'react';
import BpmnViewer from 'bpmn-js/lib/Viewer';
import {
  classifyNacBffFailure,
  NAC_BFF_WORKSPACE_ID,
  NacBffWorkspace
} from '../services/NacBffClient';
import { nacBpmnViewerStyles as styles, nacBpmnViewerStyleSheet } from './NacBpmnViewer.styles';

const LOAD_TIMEOUT_MS = 10_000;

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
        setState({ kind: 'ready', workspace: value });
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

  const workspace = isApprovedWorkspace && state.kind === 'ready' ? state.workspace : null;
  const bpmnXml = workspace?.matter.bpmn.xml;

  React.useEffect(() => {
    if (!containerRef.current || workspace === null || bpmnXml === undefined) {
      return;
    }

    const viewer = new BpmnViewer({ container: containerRef.current });
    let disposed = false;
    let destroyed = false;
    const destroyViewer = (): void => {
      if (!destroyed) {
        viewer.destroy();
        destroyed = true;
      }
    };

    viewer.importXML(bpmnXml).then(() => {
      if (!disposed) {
        const canvas = viewer.get('canvas') as { zoom: (mode: string) => void };
        canvas.zoom('fit-viewport');
      }
    }).catch(() => {
      if (!disposed) {
        destroyViewer();
        setState({ kind: 'renderFailed' });
      }
    });

    return () => {
      disposed = true;
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

  const matter = state.workspace.matter;
  const stageLabel = matter.tasks[0]?.title ?? 'Keine offene Aufgabe';
  const accessMode = matter.accessMode === 'deputy'
    ? 'Vertretung (deputy)'
    : 'Zugeordnet (assigned)';
  const deadlineLabel = formatTimestamp(matter.deadline);

  return (
    <main className={styles.workspace + (props.isDarkTheme ? ' ' + styles.dark : '')} data-nac-component="test-workspace">
      <style>{nacBpmnViewerStyleSheet}</style>
      <header className={styles.header}>
        <div>
          <span className={styles.eyebrow}>NaC Testnotariat</span>
          <h1>{matter.displayName}</h1>
          <p>Immobilienkaufvertrag</p>
        </div>
        <div className={styles.headerMeta}>
          <span className={styles.status}>{matter.status}</span>
          <span>{props.hostName}</span>
        </div>
      </header>

      <section className={styles.summary} aria-label="Vorgangsstatus">
        <div><span>Aktueller Schritt</span><strong>{stageLabel}</strong></div>
        <div><span>Nächste Frist</span><strong>{deadlineLabel}</strong></div>
        <div><span>Zugriffsmodus</span><strong>{accessMode}</strong></div>
        <div><span>Angemeldet</span><strong>{props.userDisplayName}</strong></div>
      </section>

      <div className={styles.contentGrid}>
        <section className={styles.process} aria-labelledby="process-heading">
          <div className={styles.sectionHeading}>
            <div>
              <span>Prozessmodell</span>
              <h2 id="process-heading">Immobilienkaufvertrag</h2>
            </div>
            <span className={styles.fixtureBadge}>Synthetische Testdaten</span>
          </div>
          <div className={styles.canvas} ref={containerRef} aria-label="BPMN-Prozessdiagramm" />
        </section>

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
      </div>

      <footer className={styles.footer}>
        <span>Workspace {state.workspace.workspaceId}</span>
        <span>Keine Mandatsdaten</span>
      </footer>
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
