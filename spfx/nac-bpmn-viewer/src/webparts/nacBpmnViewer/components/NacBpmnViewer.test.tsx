/// <reference types="node" />
/* eslint-disable @rushstack/pair-react-dom-render-unmount -- afterEach owns cleanup for every test root. */
jest.mock('@microsoft/sp-http', () => ({
  AadHttpClient: {
    configurations: {
      v1: {}
    }
  }
}));
jest.mock('bpmn-js/lib/Viewer', () => ({
  __esModule: true,
  default: jest.fn()
}));

import * as React from 'react';
import * as ReactDom from 'react-dom';
import { act } from 'react-dom/test-utils';
import BpmnViewer from 'bpmn-js/lib/Viewer';
import { NacBffWorkspace } from '../services/NacBffClient';
import { NacBpmnViewer } from './NacBpmnViewer';

const bpmnXml = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">',
  '<bpmn:process id="Process_immobilienkaufvertrag" isExecutable="false"/>',
  '</bpmn:definitions>'
].join('');

const workspace: NacBffWorkspace = {
  schemaVersion: 'nac.m365-test-environment-workspace/v0.2',
  workspaceId: 'notary_team_01',
  matter: {
    matterId: 'NAC-SYN-MATTER-001',
    businessCaseTypeId: 'immobilienkaufvertrag',
    displayName: 'Synthetischer Immobilienkaufvertrag',
    status: 'Entwurf',
    deadline: '2026-08-31T16:00:00Z',
    tasks: [{
      taskId: 'NAC-SYN-TASK-001',
      title: 'Entwurf prüfen',
      stepCode: 'Task_EntwurfAbstimmen',
      status: 'Offen',
      requiresNotaryApproval: true,
      dueAt: '2026-08-31T16:00:00Z'
    }],
    bpmn: {
      modelKey: 'Process_immobilienkaufvertrag',
      mimeType: 'application/xml',
      sha256: '02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0',
      xml: bpmnXml
    },
    accessMode: 'assigned'
  }
};

describe('NaC BPMN viewer runtime boundary', () => {
  let root: HTMLDivElement;
  let importXml: jest.Mock;
  let destroy: jest.Mock;
  let elementRegistryGet: jest.Mock;
  let addMarker: jest.Mock;
  let resized: jest.Mock;
  let zoom: jest.Mock;
  let resizeObserverCallback: ResizeObserverCallback;
  let resizeObserverObserve: jest.Mock;
  let resizeObserverDisconnect: jest.Mock;
  let resizeObserverInstance: ResizeObserver;
  let getService: jest.Mock;
  const currentElement = { id: 'Task_EntwurfAbstimmen' };

  beforeEach(() => {
    root = document.createElement('div');
    document.body.appendChild(root);
    importXml = jest.fn().mockResolvedValue(undefined);
    destroy = jest.fn();
    elementRegistryGet = jest.fn().mockReturnValue(currentElement);
    addMarker = jest.fn();
    resized = jest.fn();
    zoom = jest.fn();
    resizeObserverObserve = jest.fn();
    resizeObserverDisconnect = jest.fn();
    resizeObserverInstance = {
      observe: resizeObserverObserve,
      disconnect: resizeObserverDisconnect,
      unobserve: jest.fn()
    } as unknown as ResizeObserver;
    Object.defineProperty(globalThis, 'ResizeObserver', {
      configurable: true,
      writable: true,
      value: jest.fn().mockImplementation((callback: ResizeObserverCallback) => {
        resizeObserverCallback = callback;
        return resizeObserverInstance;
      })
    });
    getService = jest.fn().mockImplementation((serviceName: string) => {
      if (serviceName === 'elementRegistry') {
        return { get: elementRegistryGet };
      }
      if (serviceName === 'canvas') {
        return { addMarker, resized, zoom };
      }
      throw new Error('Unknown viewer service: ' + serviceName);
    });
    (BpmnViewer as unknown as jest.Mock).mockImplementation(() => ({
      importXML: importXml,
      destroy,
      get: getService
    }));
  });

  afterEach(() => {
    ReactDom.unmountComponentAtNode(root);
    root.remove();
    delete (globalThis as { ResizeObserver?: typeof ResizeObserver }).ResizeObserver;
    jest.clearAllMocks();
  });

  it('shows a loading state without exposing matter data', async () => {
    await act(async () => {
      ReactDom.render(
        <NacBpmnViewer
          workspaceId="notary_team_01"
          userDisplayName="Test User"
          hostName="SharePoint"
          isDarkTheme={false}
          loadWorkspace={() => new Promise<NacBffWorkspace>(() => undefined)}
        />,
        root
      );
    });

    expect(root.textContent).toContain('Vorgangsdaten werden geladen.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(BpmnViewer).not.toHaveBeenCalled();
  });

  it.each([401, 403])('shows a neutral access denial for HTTP %i', async status => {
    await renderAndFlush(async () => {
      throw new Error(status === 401 ? 'NAC_BFF_ACCESS_DENIED' : 'NAC_BFF_ACCESS_DENIED');
    });

    expect(root.textContent).toContain('Kein Zugriff auf diesen Vorgang.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(BpmnViewer).not.toHaveBeenCalled();
  });

  it('does not call the loader for an unapproved workspace', async () => {
    const loadWorkspace = jest.fn().mockResolvedValue(workspace);
    await act(async () => {
      ReactDom.render(
        <NacBpmnViewer
          workspaceId="another_workspace"
          userDisplayName="Test User"
          hostName="SharePoint"
          isDarkTheme={false}
          loadWorkspace={loadWorkspace}
        />,
        root
      );
    });

    expect(root.textContent).toContain('Kein Zugriff auf diesen Vorgang.');
    expect(loadWorkspace).not.toHaveBeenCalled();
  });

  it('hides ready matter data synchronously when rerendered for an unapproved workspace', async () => {
    const loadWorkspace = jest.fn().mockResolvedValue(workspace);
    await renderAndFlush(loadWorkspace);
    expect(root.textContent).toContain(workspace.matter.displayName);

    await act(async () => {
      ReactDom.render(
        <NacBpmnViewer
          workspaceId="another_workspace"
          userDisplayName="Test User"
          hostName="Microsoft Teams"
          isDarkTheme={false}
          loadWorkspace={loadWorkspace}
        />,
        root
      );
    });

    expect(root.textContent).toContain('Kein Zugriff auf diesen Vorgang.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(root.textContent).not.toContain(workspace.matter.tasks[0].title);
    expect(root.textContent).not.toContain('31.08.2026');
    expect(loadWorkspace).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['network error', new TypeError('network detail')],
    ['404', new Error('NAC_BFF_UNAVAILABLE')],
    ['500', new Error('NAC_BFF_UNAVAILABLE')]
  ])('shows unavailable for %s', async (_label, failure) => {
    await renderAndFlush(async () => {
      throw failure;
    });

    expect(root.textContent).toContain('Vorgangsdaten sind derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(BpmnViewer).not.toHaveBeenCalled();
  });

  it('shows an invalid-asset state without rendering matter details', async () => {
    await renderAndFlush(async () => {
      throw new Error('NAC_BPMN_ASSET_INVALID');
    });

    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(BpmnViewer).not.toHaveBeenCalled();
  });

  it('marks the canonical current BPMN task before showing ready metadata', async () => {
    await renderAndFlush(async () => workspace);

    expect(importXml).toHaveBeenCalledWith(bpmnXml);
    expect(elementRegistryGet).toHaveBeenCalledTimes(1);
    expect(elementRegistryGet).toHaveBeenCalledWith('Task_EntwurfAbstimmen');
    expect(addMarker).toHaveBeenCalledTimes(1);
    expect(addMarker).toHaveBeenCalledWith('Task_EntwurfAbstimmen', 'nac-current-step');
    expect(addMarker.mock.invocationCallOrder[0]).toBeLessThan(zoom.mock.invocationCallOrder[0]);
    expect(root.textContent).toContain(workspace.matter.displayName);
    expect(root.textContent).toContain('Entwurf prüfen');
    expect(root.textContent).toContain('31.08.2026');
    expect(root.textContent).toContain('Entwurf');
    expect(root.textContent).toContain('Zugeordnet (assigned)');
    expect(root.textContent).toContain('Aufgaben1');
    expect(root.querySelector('main')?.hasAttribute('data-nac-current-step')).toBe(false);
    expect(root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')?.getAttribute('data-nac-current-step'))
      .toBe('Task_EntwurfAbstimmen');
    expect(resized).toHaveBeenCalledTimes(1);
    expect(zoom).toHaveBeenCalledTimes(1);
    expect(resizeObserverObserve).toHaveBeenCalledWith(
      root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')
    );
  });

  it('refits the same viewer instance after its container resizes', async () => {
    await renderAndFlush(async () => workspace);

    act(() => {
      resizeObserverCallback([], resizeObserverInstance);
    });

    expect(BpmnViewer).toHaveBeenCalledTimes(1);
    expect(importXml).toHaveBeenCalledTimes(1);
    expect(addMarker).toHaveBeenCalledTimes(1);
    expect(resized).toHaveBeenCalledTimes(2);
    expect(zoom).toHaveBeenCalledTimes(2);
  });

  it('fails closed when refitting after a resize fails', async () => {
    resized.mockImplementationOnce(() => undefined).mockImplementationOnce(() => {
      throw new Error('resize failed');
    });
    await renderAndFlush(async () => workspace);

    act(() => {
      resizeObserverCallback([], resizeObserverInstance);
    });

    expect(resizeObserverDisconnect).toHaveBeenCalled();
    expect(destroy).toHaveBeenCalledTimes(1);
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.querySelector('[data-nac-current-step]')).toBeNull();
  });

  it('fails closed and destroys the viewer for an unknown current BPMN element', async () => {
    elementRegistryGet.mockReturnValue(undefined);

    await renderAndFlush(async () => workspace);

    expect(elementRegistryGet).toHaveBeenCalledWith('Task_EntwurfAbstimmen');
    expect(addMarker).not.toHaveBeenCalled();
    expect(zoom).not.toHaveBeenCalled();
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.querySelector('[data-nac-current-step]')).toBeNull();
    expect(destroy).toHaveBeenCalledTimes(1);
  });

  it('fails closed and destroys the viewer when the matter has no current task', async () => {
    const workspaceWithoutTasks: NacBffWorkspace = {
      ...workspace,
      matter: { ...workspace.matter, tasks: [] }
    };

    await renderAndFlush(async () => workspaceWithoutTasks);

    expect(getService).not.toHaveBeenCalled();
    expect(addMarker).not.toHaveBeenCalled();
    expect(zoom).not.toHaveBeenCalled();
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.querySelector('[data-nac-current-step]')).toBeNull();
    expect(destroy).toHaveBeenCalledTimes(1);
  });

  it('fails closed and destroys the viewer when a required viewer service fails', async () => {
    getService.mockImplementation(() => {
      throw new Error('viewer service unavailable');
    });

    await renderAndFlush(async () => workspace);

    expect(addMarker).not.toHaveBeenCalled();
    expect(zoom).not.toHaveBeenCalled();
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.querySelector('[data-nac-current-step]')).toBeNull();
    expect(destroy).toHaveBeenCalledTimes(1);
  });

  it('fails closed and destroys the viewer when the marker cannot be added', async () => {
    addMarker.mockImplementation(() => {
      throw new Error('marker failed');
    });

    await renderAndFlush(async () => workspace);

    expect(addMarker).toHaveBeenCalledTimes(1);
    expect(zoom).not.toHaveBeenCalled();
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.querySelector('[data-nac-current-step]')).toBeNull();
    expect(destroy).toHaveBeenCalledTimes(1);
  });

  it('shows deputy access mode in the ready state', async () => {
    const deputyWorkspace: NacBffWorkspace = {
      ...workspace,
      matter: { ...workspace.matter, accessMode: 'deputy' }
    };
    await renderAndFlush(async () => deputyWorkspace);

    expect(root.textContent).toContain('Vertretung (deputy)');
  });

  it('fails closed and destroys the viewer when BPMN import fails', async () => {
    importXml.mockRejectedValue(new Error('invalid BPMN'));

    await renderAndFlush(async () => workspace);
    await flushPromises();

    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(destroy).toHaveBeenCalledTimes(1);
  });

  it('keeps matter hidden and fails closed when BPMN rendering times out', async () => {
    jest.useFakeTimers();
    importXml.mockReturnValue(new Promise<void>(() => undefined));

    try {
      await renderAndFlush(async () => workspace);

      expect(root.textContent).toContain('Prozessmodell wird geladen.');
      expect(root.textContent).not.toContain(workspace.matter.displayName);
      expect(root.textContent).not.toContain(workspace.matter.tasks[0].title);
      expect(root.textContent).not.toContain('31.08.2026');
      expect(root.querySelector('[data-nac-current-step]')).toBeNull();

      act(() => {
        jest.advanceTimersByTime(10_000);
      });

      expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
      expect(root.textContent).not.toContain(workspace.matter.displayName);
      expect(destroy).toHaveBeenCalledTimes(1);
    } finally {
      jest.useRealTimers();
    }
  });

  it('fails the load after ten seconds even when the loader ignores abort', async () => {
    jest.useFakeTimers();
    let observedSignal: AbortSignal | undefined;
    const loadWorkspace = (signal: AbortSignal): Promise<NacBffWorkspace> => {
      observedSignal = signal;
      return new Promise<NacBffWorkspace>(() => undefined);
    };

    try {
      await act(async () => {
        ReactDom.render(
          <NacBpmnViewer
            workspaceId="notary_team_01"
            userDisplayName="Test User"
            hostName="SharePoint"
            isDarkTheme={false}
            loadWorkspace={loadWorkspace}
          />,
          root
        );
      });
      act(() => {
        jest.advanceTimersByTime(10_000);
      });

      expect(observedSignal?.aborted).toBe(true);
      expect(root.textContent).toContain('Vorgangsdaten sind derzeit nicht verfügbar.');
    } finally {
      jest.useRealTimers();
    }
  });

  it('aborts an outstanding BFF request when the component unmounts', async () => {
    let observedSignal: AbortSignal | undefined;
    const loadWorkspace = (signal: AbortSignal): Promise<NacBffWorkspace> => {
      observedSignal = signal;
      return new Promise<NacBffWorkspace>(() => undefined);
    };

    await act(async () => {
      ReactDom.render(
        <NacBpmnViewer
          workspaceId="notary_team_01"
          userDisplayName="Test User"
          hostName="SharePoint"
          isDarkTheme={false}
          loadWorkspace={loadWorkspace}
        />,
        root
      );
    });
    await act(async () => {
      ReactDom.unmountComponentAtNode(root);
    });

    expect(observedSignal).toBeDefined();
    expect(observedSignal?.aborted).toBe(true);
  });

  it('destroys a ready viewer when the component unmounts', async () => {
    await renderAndFlush(async () => workspace);
    const resizeCallCount = resized.mock.calls.length;

    await act(async () => {
      ReactDom.unmountComponentAtNode(root);
    });

    expect(destroy).toHaveBeenCalledTimes(1);
    expect(resizeObserverDisconnect).toHaveBeenCalledTimes(1);

    act(() => {
      resizeObserverCallback([], resizeObserverInstance);
    });
    expect(resized).toHaveBeenCalledTimes(resizeCallCount);
  });

  async function renderAndFlush(
    loadWorkspace: (signal: AbortSignal) => Promise<NacBffWorkspace>
  ): Promise<void> {
    await act(async () => {
      ReactDom.render(
        <NacBpmnViewer
          workspaceId="notary_team_01"
          userDisplayName="Test User"
          hostName="Microsoft Teams"
          isDarkTheme={false}
          loadWorkspace={loadWorkspace}
        />,
        root
      );
      await Promise.resolve();
      await Promise.resolve();
    });
    await flushPromises();
  }

  async function flushPromises(): Promise<void> {
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
  }
});
