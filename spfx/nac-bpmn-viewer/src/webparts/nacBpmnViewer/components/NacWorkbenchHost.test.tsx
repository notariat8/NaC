/// <reference types="node" />
/* eslint-disable @rushstack/pair-react-dom-render-unmount -- afterEach owns cleanup for every test root. */
import * as React from 'react';
import * as ReactDom from 'react-dom';
import { act } from 'react-dom/test-utils';
import { createHash } from 'crypto';
import { TextEncoder } from 'util';

import { WorkbenchSnapshot } from '../../../workbench/core/WorkbenchContracts';
import { VALID_WORKBENCH_SNAPSHOT } from '../../../workbench/core/parseWorkbenchSnapshot.test';
import { NacWorkbenchHost } from './NacWorkbenchHost';
import { nacWorkbenchHostStyleSheet } from './NacWorkbenchHost.styles';
import { NacBffHttpAccessDeniedError } from '../services/NacBffHttpAccessDeniedError';

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
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: {
        randomUUID: (): string => '11111111-2222-4333-8444-555555555555',
        subtle: {
          digest: async (
            _algorithm: AlgorithmIdentifier,
            data: BufferSource
          ): Promise<ArrayBuffer> => {
            const bytes = data instanceof ArrayBuffer
              ? new Uint8Array(data)
              : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
            return Uint8Array.from(createHash('sha256').update(bytes).digest()).buffer;
          }
        }
      }
    });
    Object.defineProperty(globalThis, 'TextEncoder', {
      configurable: true,
      value: TextEncoder
    });
  });

  afterEach(() => {
    act(() => {
      ReactDom.unmountComponentAtNode(root);
    });
    root.remove();
    jest.useRealTimers();
  });

  it('fails closed without an authenticated AAD subject', async () => {
    const loadSnapshot = jest.fn();
    await act(async () => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId={undefined}
        loadSnapshot={loadSnapshot}
        detailSurface={<div>BPMN detail</div>}
      />, root);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(root.textContent).toContain('Kein Zugriff auf diesen Arbeitsbereich.');
    expect(loadSnapshot).not.toHaveBeenCalled();
  });

  it('offers an explicit privacy-minimal receipt for a missing SPFx subject', async () => {
    const downloadReceipt = jest.fn();
    const downloadHttpReceipt = jest.fn();
    await act(async () => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId={undefined}
        loadSnapshot={jest.fn()}
        detailSurface={<div />}
        downloadReceipt={downloadReceipt}
        downloadHttpReceipt={downloadHttpReceipt}
      />, root);
      await Promise.resolve();
      await Promise.resolve();
    });
    const button = Array.from(root.querySelectorAll('button'))
      .find(candidate => candidate.textContent === 'Diagnosebeleg speichern');
    expect(button).toBeDefined();
    act(() => button?.click());
    expect(downloadReceipt).toHaveBeenCalledTimes(1);
    const receipt = JSON.parse(downloadReceipt.mock.calls[0][0]);
    expect(receipt.spfx_subject_available).toBe(false);
    const httpButton = Array.from(root.querySelectorAll('button'))
      .find(candidate => candidate.textContent === 'HTTP-Diagnosebeleg speichern');
    expect(httpButton).toBeDefined();
    act(() => httpButton?.click());
    expect(downloadHttpReceipt).toHaveBeenCalledTimes(1);
    expect(JSON.parse(downloadHttpReceipt.mock.calls[0][0]).client_http_class).toBe('none');
    expect(Object.keys(receipt).sort()).toEqual([
      'end_utc',
      'request_correlation_binding_sha256',
      'spfx_subject_available',
      'start_utc',
      'ui_state',
      'window_binding_sha256'
    ]);
  });

  it('maps a server denial to the deterministic neutral deny state', async () => {
    const loadSnapshot = jest.fn(async (
      _signal: AbortSignal,
      _observationCorrelationId?: string
    ) => { throw new Error('NAC_BFF_ACCESS_DENIED'); });
    const downloadReceipt = jest.fn();
    await act(async () => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={loadSnapshot}
        detailSurface={<div>BPMN detail</div>}
        downloadReceipt={downloadReceipt}
      />, root);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(root.textContent).toContain('Kein Zugriff auf diesen Arbeitsbereich.');
    expect(root.textContent).not.toContain('BPMN detail');
    expect(loadSnapshot.mock.calls[0][1])
      .toBe('spfx-11111111-2222-4333-8444-555555555555');
    const button = Array.from(root.querySelectorAll('button'))
      .find(candidate => candidate.textContent === 'Diagnosebeleg speichern');
    act(() => button?.click());
    const receipt = JSON.parse(downloadReceipt.mock.calls[0][0]);
    expect(receipt.spfx_subject_available).toBe(true);
    expect(root.textContent).not.toContain('HTTP-Diagnosebeleg speichern');
  });

  it.each([401, 403] as const)('offers a bound HTTP %i companion without automatic download', async status => {
    const downloadReceipt = jest.fn();
    const downloadHttpReceipt = jest.fn();
    const loadSnapshot = jest.fn(async () => { throw new NacBffHttpAccessDeniedError(status); });
    await act(async () => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={loadSnapshot}
        detailSurface={<div />}
        downloadReceipt={downloadReceipt}
        downloadHttpReceipt={downloadHttpReceipt}
      />, root);
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(root.textContent).toContain('Kein Zugriff auf diesen Arbeitsbereich.');
    expect(loadSnapshot).toHaveBeenCalledTimes(1);
    expect(downloadReceipt).not.toHaveBeenCalled();
    expect(downloadHttpReceipt).not.toHaveBeenCalled();
    const buttons = Array.from(root.querySelectorAll('button'));
    expect(buttons.map(button => button.textContent)).toContain('HTTP-Diagnosebeleg speichern');
    act(() => buttons.find(button => button.textContent === 'Diagnosebeleg speichern')?.click());
    act(() => buttons.find(button => button.textContent === 'HTTP-Diagnosebeleg speichern')?.click());
    expect(downloadReceipt).toHaveBeenCalledTimes(1);
    expect(downloadHttpReceipt).toHaveBeenCalledTimes(1);
    const baseJson = downloadReceipt.mock.calls[0][0];
    const sidecar = JSON.parse(downloadHttpReceipt.mock.calls[0][0]);
    expect(sidecar.client_http_class).toBe(String(status));
    expect(sidecar.base_receipt_sha256).toBe(createHash('sha256').update(baseJson).digest('hex'));
    expect(loadSnapshot).toHaveBeenCalledTimes(1);
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

  it('prevents an older abort-ignoring successful response from overwriting a newer request', async () => {
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
      oldRequest.resolve({
        ...snapshot('2026-08-01T09:00:00Z', '2026-08-01T09:04:00Z'),
        matter: {
          ...snapshot().matter,
          title: 'Veralteter Arbeitsbereich'
        }
      });
      await Promise.resolve();
    });
    expect(root.textContent).toContain('Synthetischer Immobilienkaufvertrag');
    expect(root.textContent).not.toContain('Veralteter Arbeitsbereich');
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

  it('aborts an active request during unmount and ignores its late completion', async () => {
    const pending = deferred<WorkbenchSnapshot>();
    let signal: AbortSignal | undefined;
    act(() => {
      ReactDom.render(<NacWorkbenchHost
        expectedSubjectId="actor:synthetic:001"
        loadSnapshot={(value: AbortSignal) => {
          signal = value;
          return pending.promise;
        }}
        detailSurface={<div />}
      />, root);
    });
    expect(signal?.aborted).toBe(false);
    act(() => {
      ReactDom.unmountComponentAtNode(root);
    });
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      pending.resolve(snapshot());
      await Promise.resolve();
    });
    expect(root.childElementCount).toBe(0);
  });
});
