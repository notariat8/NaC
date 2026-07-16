import * as React from 'react';
import BpmnViewer from 'bpmn-js/lib/Viewer';
import { syntheticWorkspaceFixture } from '../fixtures/syntheticWorkspace';
import { NacBffWorkspace, verifyBpmnAsset } from '../services/NacBffClient';
import { nacBpmnViewerStyles as styles, nacBpmnViewerStyleSheet } from './NacBpmnViewer.styles';

const LOAD_TIMEOUT_MS = 10_000;

export interface NacBpmnViewerProps {
  workspaceId: string;
  userDisplayName: string;
  hostName: string;
  isDarkTheme: boolean;
  loadWorkspace: (signal: AbortSignal) => Promise<NacBffWorkspace>;
}

export function NacBpmnViewer(props: NacBpmnViewerProps): JSX.Element {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const fixture = syntheticWorkspaceFixture;
  const [workspace, setWorkspace] = React.useState<NacBffWorkspace | null>(null);
  const [loadFailed, setLoadFailed] = React.useState(false);
  const [renderFailed, setRenderFailed] = React.useState(false);

  React.useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    const timeoutId = window.setTimeout(() => {
      controller.abort();
      if (!disposed) {
        setLoadFailed(true);
      }
    }, LOAD_TIMEOUT_MS);
    setWorkspace(null);
    setLoadFailed(false);
    setRenderFailed(false);
    props.loadWorkspace(controller.signal).then(async value => {
      await verifyBpmnAsset(value, fixture.bpmnXml, fixture.bpmnSha256);
      if (!disposed) {
        setWorkspace(value);
      }
    }).catch(() => {
      if (!disposed) {
        setLoadFailed(true);
      }
    }).finally(() => window.clearTimeout(timeoutId));

    return () => {
      disposed = true;
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [props.loadWorkspace]);

  React.useEffect(() => {
    if (!containerRef.current || props.workspaceId !== fixture.workspaceId || workspace === null) {
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

    setRenderFailed(false);
    viewer.importXML(fixture.bpmnXml).then(() => {
      if (!disposed) {
        const canvas = viewer.get('canvas') as { zoom: (mode: string) => void };
        canvas.zoom('fit-viewport');
      }
    }).catch(() => {
      if (!disposed) {
        destroyViewer();
        setRenderFailed(true);
      }
    });

    return () => {
      disposed = true;
      destroyViewer();
    };
  }, [fixture.bpmnXml, props.workspaceId, workspace]);

  if (props.workspaceId !== fixture.workspaceId) {
    return <ViewerError message="Workspace nicht freigegeben." />;
  }
  if (loadFailed) {
    return <ViewerError message="Vorgangsdaten sind derzeit nicht verfügbar." />;
  }
  if (workspace === null) {
    return <ViewerError message="Vorgangsdaten werden geladen." />;
  }
  if (renderFailed) {
    return <ViewerError message="Prozessmodell ist derzeit nicht verfügbar." />;
  }

  const matter = workspace.matter;
  const stageLabel = matter.tasks[0]?.title ?? 'Keine offene Aufgabe';
  const assignedRole = matter.accessMode === 'deputy' ? 'Aktive Vertretung' : 'Zugeordnete Fachkraft';
  const deadlineLabel = formatTimestamp(matter.deadline);

  return (
    <main className={styles.workspace + (props.isDarkTheme ? ' ' + styles.dark : '')} data-nac-component="test-workspace">
      <style>{nacBpmnViewerStyleSheet}</style>
      <header className={styles.header}>
        <div>
          <span className={styles.eyebrow}>NaC Testnotariat</span>
          <h1>{matter.displayName}</h1>
          <p>{fixture.businessCaseType}</p>
        </div>
        <div className={styles.headerMeta}>
          <span className={styles.status}>{matter.status}</span>
          <span>{props.hostName}</span>
        </div>
      </header>

      <section className={styles.summary} aria-label="Vorgangsstatus">
        <div><span>Aktueller Schritt</span><strong>{stageLabel}</strong></div>
        <div><span>Nächste Frist</span><strong>{deadlineLabel}</strong></div>
        <div><span>Zuständig</span><strong>{assignedRole}</strong></div>
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
        <span>Workspace {workspace.workspaceId}</span>
        <span>Keine Mandatsdaten</span>
      </footer>
    </main>
  );
}

function ViewerError(props: { message: string }): JSX.Element {
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
