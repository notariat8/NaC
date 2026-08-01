/* eslint-disable @rushstack/no-new-null -- The exact JSON wire contract uses explicit null values. */

import * as React from 'react';
import { WorkbenchSnapshot, WorkbenchViewId } from '../core/WorkbenchContracts';
import { activeMatterAttention, isSnapshotFreshAt, snapshotEffectiveExpiry } from '../core/WorkbenchSelectors';
import { workbenchStyleSheet } from './WorkbenchPanel.styles';

export interface WorkbenchPanelProps {
  readonly snapshot: WorkbenchSnapshot;
  readonly initialView?: WorkbenchViewId;
  readonly now?: () => Date;
}

const views: readonly { readonly id: WorkbenchViewId; readonly label: string }[] = [
  { id: 'today', label: 'Heute' },
  { id: 'matter', label: 'Akte' },
  { id: 'decisions', label: 'Entscheidungen' }
];

export function WorkbenchPanel(props: WorkbenchPanelProps): React.ReactElement {
  const [view, setView] = React.useState<WorkbenchViewId>(props.initialView ?? 'today');
  const snapshot = props.snapshot;
  const now = React.useMemo(() => props.now ?? (() => new Date()), [props.now]);
  const [nowMillis, setNowMillis] = React.useState(() => now().getTime());
  React.useEffect(() => {
    const remaining = snapshotEffectiveExpiry(snapshot) - now().getTime();
    if (remaining <= 0) {
      setNowMillis(now().getTime());
      return undefined;
    }
    const timer = window.setTimeout(() => setNowMillis(now().getTime()), remaining + 1);
    return () => window.clearTimeout(timer);
  }, [now, snapshot]);
  if (!isSnapshotFreshAt(snapshot, nowMillis)) {
    return <div className="nacWorkbenchAccessDenied" role="alert">Arbeitsbereich nicht verfügbar. Zugriff erneut prüfen.</div>;
  }
  return <div className="nacWorkbench" data-nac-workbench-schema={snapshot.schemaVersion}>
    <style>{workbenchStyleSheet}</style>
    <nav aria-label="Arbeitsbereich">
      <strong>NaC</strong>
      {views.map(item => <button
        key={item.id}
        type="button"
        aria-pressed={view === item.id}
        onClick={() => setView(item.id)}
      >{item.label}</button>)}
    </nav>
    <main>
      <header>
        <div>
          <p>{snapshot.matter.businessCaseTypeId}</p>
          <h1>{snapshot.matter.title}</h1>
          <p>{snapshot.matter.status} · Frist {formatDate(snapshot.matter.deadline)}</p>
        </div>
        <span className="nacWorkbench__badge">Synthetische Testdaten</span>
      </header>
      {view === 'today' && <Today snapshot={snapshot} />}
      {view === 'matter' && <Matter snapshot={snapshot} />}
      {view === 'decisions' && <Decisions snapshot={snapshot} />}
    </main>
    <aside>
      <section><h2>Zugriff</h2><strong>{snapshot.access.mode}</strong><p>gültig bis {formatDate(snapshot.access.expiresAt)}</p></section>
      <section><h2>Assistenz</h2>{snapshot.agents.map(agent => <p key={agent.id}><strong>{agent.label}</strong><br />{agent.status}: {agent.detail}</p>)}</section>
      <section><h2>Aktionsgrenze</h2>{snapshot.capabilities.map(capability => <p key={capability.id} className="nacWorkbench__denied">Gesperrt: {capability.mode}<br /><small>{capability.reason}</small></p>)}</section>
    </aside>
  </div>;
}

function Today({ snapshot }: { readonly snapshot: WorkbenchSnapshot }): React.ReactElement {
  const items = activeMatterAttention(snapshot);
  return <div className="nacWorkbench__grid">
    <section><h2>Aufmerksamkeit in dieser Akte</h2>{items.length === 0 ? <p className="nacWorkbench__empty">Keine priorisierte Intervention.</p> : <ul>{items.map(item => <li key={item.id}><strong>{item.title}</strong><span>{item.reason} · {formatDate(item.dueAt)}</span></li>)}</ul>}</section>
    <section><h2>Nächste Aufgaben</h2><TaskList snapshot={snapshot} /></section>
  </div>;
}

function Matter({ snapshot }: { readonly snapshot: WorkbenchSnapshot }): React.ReactElement {
  return <div className="nacWorkbench__grid">
    <section><h2>Aufgaben</h2><TaskList snapshot={snapshot} /></section>
    <section><h2>Prozessmodell</h2><p>{snapshot.matter.modelReference.modelKey}</p><p>BPMN-Modellreferenz, kein unveränderlicher Nachweis.</p></section>
  </div>;
}

function Decisions({ snapshot }: { readonly snapshot: WorkbenchSnapshot }): React.ReactElement {
  return <div className="nacWorkbench__grid">
    <section><h2>Decision Center</h2>{snapshot.decisions.length === 0 ? <p className="nacWorkbench__empty">Keine serverseitig freigegebene Entscheidung.</p> : <ul>{snapshot.decisions.map(decision => <li key={decision.id}><strong>{decision.title}</strong><span className="nacWorkbench__risk">{decision.riskClass} · {decision.status}</span></li>)}</ul>}</section>
    <section><h2>Nachweise</h2><ul>{snapshot.evidence.map(evidence => <li key={evidence.id}><strong>{evidence.title}</strong><span>{evidence.kind} · {evidence.authority}</span></li>)}</ul></section>
  </div>;
}

function TaskList({ snapshot }: { readonly snapshot: WorkbenchSnapshot }): React.ReactElement {
  return <ul>{snapshot.tasks.map(task => <li key={task.id}><strong>{task.title}</strong><span>{task.status} · {formatDate(task.dueAt)}</span></li>)}</ul>;
}

function formatDate(value: string | null): string {
  return value === null ? 'keine' : value.replace('T', ' ').replace('Z', ' UTC');
}
