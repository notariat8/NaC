/* eslint-disable @rushstack/pair-react-dom-render-unmount -- afterEach owns cleanup for every test root. */
import * as React from 'react';
import * as ReactDom from 'react-dom';
import { act } from 'react-dom/test-utils';

import { WorkbenchSnapshot } from '../../../workbench/core/WorkbenchContracts';
import { VALID_WORKBENCH_SNAPSHOT } from '../../../workbench/core/parseWorkbenchSnapshot.test';
import { NacWorkbenchHost } from './NacWorkbenchHost';
import { nacWorkbenchHostStyleSheet } from './NacWorkbenchHost.styles';

interface Deferred<T> {
  readonly promise: Promise<T>;
  readonly resolve: (value: T) => void;
  readonly reject: (error: Error) => void;
}

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((_resolve, _reject) => {
    resolve = _resolve;
    reject = _reject;
  });
  return { promise, resolve, reject };
}

function snapshot(
  generatedAt: string = '2026-08-01T09:00:00Z',
  expiresAt: string = '2026-08-01T09:04:00Z'
): WorkbenchSnapshot {
  return {
    ...VALID_WORKBENCH_SNAPSHOT,
    generatedAt,
    expiresAt,
    access: { ...VALID_WORKBENCH_SNAPSHOT.access, issuedAt: generatedAt, expiresAt }
  } as WorkbenchSnapshot;
}

describe('NaC workbench live host', () => {
  let root: HTMLDivElement;

  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-08-01T09:01:00Z'));
    root = document.createElement('div');
    document.body.appendChild(root);
  });

  afterEach(() => {
    act(() => {
      ReactDom.unmountComponentAtNode(root);
    });
    root.remove();
    jest.useRealTimers();
  });

  it('fails closed without an authenticated AAD subject', () => {
    const loadSnapshot = jest.fn();
    act(() => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId={undefined}
        loadSnapshot={loadSnapshot}
        detailSurface={<div>BPMN detail</div>}
      />, root);
    });
    expect(root.textContent).toContain('Kein Zugriff auf diesen Arbeitsbereich.');
    expect(loadSnapshot).not.toHaveBeenCalled();
  });

  it('maps a server denial to the deterministic neutral deny state', async () => {
    await act(async () => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={async () => { throw new Error('NAC_BFF_ACCESS_DENIED'); }}
        detailSurface={<div>BPMN detail</div>}
      />, root);
      await Promise.resolve();
    });
    expect(root.textContent).toContain('Kein Zugriff auf diesen Arbeitsbereich.');
    expect(root.textContent).not.toContain('BPMN detail');
  });

  it('shows the workbench first and retains BPMN as an explicit detail surface', async () => {
    await act(async () => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={async () => snapshot()}
        detailSurface={<div data-testid="bpmn-detail">BPMN detail</div>}
      />, root);
      await Promise.resolve();
    });
    expect(root.querySelector('[data-nac-workbench-schema]')).not.toBeNull();
    expect(root.querySelector('[data-testid="bpmn-detail"]')).toBeNull();
    const detailButton = Array.from(root.querySelectorAll('button'))
      .find(button => button.textContent === 'BPMN-Detail') as HTMLButtonElement;
    act(() => detailButton.click());
    expect(root.querySelector('[data-testid="bpmn-detail"]')).not.toBeNull();
  });

  it('connects tabs and panels with a WCAG-compatible roving tab stop', async () => {
    await act(async () => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={async () => snapshot()}
        detailSurface={<div>BPMN detail</div>}
      />, root);
      await Promise.resolve();
    });

    const tabs = Array.from(root.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
    const panels = Array.from(root.querySelectorAll<HTMLDivElement>('[role="tabpanel"]'));
    expect(tabs).toHaveLength(2);
    expect(panels).toHaveLength(2);
    expect(tabs.map(tab => tab.tabIndex)).toEqual([0, -1]);
    tabs.forEach((tab, index) => {
      const panel = panels[index];
      expect(tab.id).not.toBe('');
      expect(tab.getAttribute('aria-controls')).toBe(panel.id);
      expect(panel.getAttribute('aria-labelledby')).toBe(tab.id);
    });
    expect(panels[0].hidden).toBe(false);
    expect(panels[1].hidden).toBe(true);
  });

  it('moves and activates tabs with ArrowLeft, ArrowRight, Home and End', async () => {
    await act(async () => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={async () => snapshot()}
        detailSurface={<div>BPMN detail</div>}
      />, root);
      await Promise.resolve();
    });

    const tabs = Array.from(root.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
    const press = (tab: HTMLButtonElement, key: string): void => {
      act(() => {
        tab.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key }));
      });
    };
    tabs[0].focus();
    press(tabs[0], 'ArrowRight');
    expect(document.activeElement).toBe(tabs[1]);
    expect(tabs.map(tab => tab.tabIndex)).toEqual([-1, 0]);

    press(tabs[1], 'ArrowRight');
    expect(document.activeElement).toBe(tabs[0]);
    press(tabs[0], 'ArrowLeft');
    expect(document.activeElement).toBe(tabs[1]);
    press(tabs[1], 'Home');
    expect(document.activeElement).toBe(tabs[0]);
    press(tabs[0], 'End');
    expect(document.activeElement).toBe(tabs[1]);
    expect(tabs[1].getAttribute('aria-selected')).toBe('true');
  });

  it('defines container breakpoints with a viewport fallback for narrow hosts', () => {
    expect(nacWorkbenchHostStyleSheet).toContain('container-type:inline-size');
    expect(nacWorkbenchHostStyleSheet).toContain('@container nac-workbench-host (max-width:820px)');
    expect(nacWorkbenchHostStyleSheet).toContain('@container nac-workbench-host (max-width:440px)');
    expect(nacWorkbenchHostStyleSheet).toContain('@supports not (container-type:inline-size)');
    expect(nacWorkbenchHostStyleSheet).toContain('@media(max-width:820px)');
  });

  it('refreshes before effective expiry and discards data immediately on failure', async () => {
    const refresh = deferred<WorkbenchSnapshot>();
    const loadSnapshot = jest.fn()
      .mockResolvedValueOnce(snapshot())
      .mockImplementationOnce(() => refresh.promise);
    await act(async () => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={loadSnapshot}
        detailSurface={<div>BPMN detail</div>}
      />, root);
      await Promise.resolve();
    });
    expect(loadSnapshot).toHaveBeenCalledTimes(1);

    await act(async () => {
      jest.advanceTimersByTime(144_001);
      await Promise.resolve();
    });
    expect(loadSnapshot).toHaveBeenCalledTimes(2);
    expect(root.querySelector('[data-nac-workbench-schema]')).not.toBeNull();

    await act(async () => {
      refresh.reject(new Error('NAC_BFF_UNAVAILABLE'));
      await Promise.resolve();
    });
    expect(root.textContent).toContain('Arbeitsbereich ist derzeit nicht verfügbar.');
    expect(root.querySelector('[data-nac-workbench-schema]')).toBeNull();
  });

  it('prevents an older abort-ignoring response from committing after a new request', async () => {
    const oldRequest = deferred<WorkbenchSnapshot>();
    const newRequest = deferred<WorkbenchSnapshot>();
    const firstLoader = jest.fn(() => oldRequest.promise);
    const secondLoader = jest.fn(() => newRequest.promise);
    act(() => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={firstLoader}
        detailSurface={<div />}
      />, root);
    });
    act(() => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={secondLoader}
        detailSurface={<div />}
      />, root);
    });
    await act(async () => {
      newRequest.resolve(snapshot('2026-08-01T09:01:00Z', '2026-08-01T09:05:00Z'));
      await Promise.resolve();
    });
    expect(root.textContent).toContain('Synthetischer Immobilienkaufvertrag');
    await act(async () => {
      oldRequest.reject(new Error('NAC_BFF_UNAVAILABLE'));
      await Promise.resolve();
    });
    expect(root.textContent).toContain('Synthetischer Immobilienkaufvertrag');
    expect(root.textContent).not.toContain('Arbeitsbereich ist derzeit nicht verfügbar.');
  });

  it('aborts on timeout and ignores an abort-ignoring late completion', async () => {
    const pending = deferred<WorkbenchSnapshot>();
    let signal: AbortSignal | undefined;
    const loadSnapshot = jest.fn((value: AbortSignal) => {
      signal = value;
      return pending.promise;
    });
    act(() => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={loadSnapshot}
        detailSurface={<div />}
      />, root);
    });
    act(() => jest.advanceTimersByTime(10_001));
    expect(signal?.aborted).toBe(true);
    expect(root.textContent).toContain('Arbeitsbereich ist derzeit nicht verfügbar.');

    await act(async () => {
      pending.resolve(snapshot());
      await Promise.resolve();
    });
    expect(root.textContent).toContain('Arbeitsbereich ist derzeit nicht verfügbar.');
    expect(root.querySelector('[data-nac-workbench-schema]')).toBeNull();
  });

  it('aborts an active request during unmount', () => {
    let signal: AbortSignal | undefined;
    act(() => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={(value: AbortSignal) => {
          signal = value;
          return new Promise<WorkbenchSnapshot>(() => undefined);
        }}
        detailSurface={<div />}
      />, root);
    });
    expect(signal?.aborted).toBe(false);
    act(() => {
      ReactDom.unmountComponentAtNode(root);
    });
    expect(signal?.aborted).toBe(true);
  });
});
