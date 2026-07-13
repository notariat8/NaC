import * as React from 'react';
import BpmnViewer from 'bpmn-js/lib/Viewer';
import { syntheticWorkspaceFixture } from '../fixtures/syntheticWorkspace';
import styles from './NacBpmnViewer.module.scss';

export interface NacBpmnViewerProps {
  workspaceId: string;
  userDisplayName: string;
  hostName: string;
  isDarkTheme: boolean;
}

export function NacBpmnViewer(props: NacBpmnViewerProps): JSX.Element {
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const fixture = syntheticWorkspaceFixture;

  React.useEffect(() => {
    if (!containerRef.current || props.workspaceId !== fixture.workspaceId) {
      return;
    }

    const viewer = new BpmnViewer({ container: containerRef.current });
    let disposed = false;
    viewer.importXML(fixture.bpmnXml).then(() => {
      if (!disposed) {
        const canvas = viewer.get('canvas') as { zoom: (mode: string) => void };
        canvas.zoom('fit-viewport');
      }
    }).catch(() => undefined);

    return () => {
      disposed = true;
      viewer.destroy();
    };
  }, [fixture.bpmnXml, props.workspaceId]);

  if (props.workspaceId !== fixture.workspaceId) {
    return <div className={styles.error}>Workspace nicht freigegeben.</div>;
  }

  return (
    <main className={`${styles.workspace} ${props.isDarkTheme ? styles.dark : ''}`} data-nac-component="test-workspace">
      <header className={styles.header}>
        <div>
          <span className={styles.eyebrow}>NaC Testnotariat</span>
          <h1>{fixture.matterLabel}</h1>
          <p>{fixture.businessCaseType}</p>
        </div>
        <div className={styles.headerMeta}>
          <span className={styles.status}>{fixture.lifecycleStatus}</span>
          <span>{props.hostName}</span>
        </div>
      </header>

      <section className={styles.summary} aria-label="Vorgangsstatus">
        <div><span>Aktueller Schritt</span><strong>{fixture.stageLabel}</strong></div>
        <div><span>Nächste Frist</span><strong>{fixture.deadlineLabel}</strong></div>
        <div><span>Zuständig</span><strong>{fixture.assignedRole}</strong></div>
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
            <strong>{fixture.tasks.length}</strong>
          </div>
          <ul>
            {fixture.tasks.map(task => (
              <li key={task.id}>
                <div><strong>{task.title}</strong><span>{task.id} · {task.stepCode}</span><span>{task.dueLabel}</span></div>
                <span className={styles.taskOpen}>{task.status}</span>
              </li>
            ))}
          </ul>
        </aside>
      </div>

      <footer className={styles.footer}>
        <span>Workspace {fixture.workspaceId}</span>
        <span>Keine Mandatsdaten</span>
      </footer>
    </main>
  );
}
