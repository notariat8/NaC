import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { VALID_WORKBENCH_SNAPSHOT } from '../core/parseWorkbenchSnapshot.test';
import { WorkbenchSnapshot } from '../core/WorkbenchContracts';
import { WorkbenchPanel } from './WorkbenchPanel';

describe('generic workbench panel', () => {
  it('renders a quiet, read-only active-matter workspace', () => {
    const markup = renderToStaticMarkup(<WorkbenchPanel
      snapshot={VALID_WORKBENCH_SNAPSHOT as WorkbenchSnapshot}
      now={() => new Date('2026-08-01T09:01:00Z')}
    />);
    expect(markup).toContain('Aufmerksamkeit in dieser Akte');
    expect(markup).toContain('Synthetische Testdaten');
    expect(markup).toContain('Gesperrt: approve');
    expect(markup).not.toContain('callbackUrl');
  });

  it('renders server-authored decisions and evidence without an action executor', () => {
    const markup = renderToStaticMarkup(<WorkbenchPanel
      snapshot={VALID_WORKBENCH_SNAPSHOT as WorkbenchSnapshot}
      initialView="decisions"
      now={() => new Date('2026-08-01T09:01:00Z')}
    />);
    expect(markup).toContain('Decision Center');
    expect(markup).toContain('Entwurf notariell prüfen');
    expect(markup).toContain('BPMN-Prozessmodell');
    expect(markup).toContain('non_authoritative');
  });

  it('fails closed without rendering matter data after expiry', () => {
    const markup = renderToStaticMarkup(<WorkbenchPanel
      snapshot={VALID_WORKBENCH_SNAPSHOT as WorkbenchSnapshot}
      now={() => new Date('2026-08-01T09:04:00Z')}
    />);
    expect(markup).toContain('Arbeitsbereich nicht verfügbar');
    expect(markup).not.toContain('Synthetischer Immobilienkaufvertrag');
    expect(markup).not.toContain('NAC-SYN-MATTER-001');
  });
});
