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
      dueAt: null
    }, {
      taskId: 'NAC-SYN-DEADLINE-001',
      title: 'Abschlussfrist überwachen',
      stepCode: 'Task_NachweiseNachhalten',
      status: 'Offen',
      requiresNotaryApproval: false,
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

function createBpmnUserTaskElement(elementId: string): {
  readonly id: string;
  readonly type: 'bpmn:UserTask';
  readonly businessObject: { readonly $instanceOf: jest.Mock };
} {
  return {
    id: elementId,
    type: 'bpmn:UserTask',
    businessObject: {
      $instanceOf: jest.fn((bpmnType: string) =>
        bpmnType === 'bpmn:Task' || bpmnType === 'bpmn:UserTask'
      )
    }
  };
}

describe('NaC BPMN viewer runtime boundary', () => {
  let root: HTMLDivElement;
  let importXml: jest.Mock;
  let destroy: jest.Mock;
  let elementRegistryGet: jest.Mock;
  let addMarker: jest.Mock;
  let removeMarker: jest.Mock;
  let resized: jest.Mock;
  let zoom: jest.Mock;
  let resizeObserverCallback: ResizeObserverCallback;
  let resizeObserverObserve: jest.Mock;
  let resizeObserverDisconnect: jest.Mock;
  let resizeObserverInstance: ResizeObserver;
  let getService: jest.Mock;
  const currentElement = createBpmnUserTaskElement('Task_EntwurfAbstimmen');
  const deadlineElement = createBpmnUserTaskElement(
    'Task_NachweiseNachhalten'
  );

  beforeEach(() => {
    root = document.createElement('div');
    document.body.appendChild(root);
    importXml = jest.fn().mockResolvedValue(undefined);
    destroy = jest.fn();
    elementRegistryGet = jest.fn().mockImplementation((stepCode: string) => {
      if (stepCode === currentElement.id) return currentElement;
      if (stepCode === deadlineElement.id) return deadlineElement;
      return undefined;
    });
    addMarker = jest.fn();
    removeMarker = jest.fn();
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
        return { addMarker, removeMarker, resized, zoom };
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
          evaluationTimestamp="2026-08-25T16:00:00Z"
          loadWorkspace={() => new Promise<NacBffWorkspace>(() => undefined)}
        />,
        root
      );
    });

    expect(root.textContent).toContain('Vorgangsdaten werden geladen.');
    const loadingStatus = root.querySelector('[role="status"]');
    expect(loadingStatus?.textContent).toContain('Vorgangsdaten werden geladen.');
    expect(loadingStatus?.classList.contains('nacBpmnViewer__message')).toBe(true);
    expect(loadingStatus?.classList.contains('nacBpmnViewer__error')).toBe(false);
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
          evaluationTimestamp="2026-08-25T16:00:00Z"
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
          evaluationTimestamp="2026-08-25T16:00:00Z"
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
    expect(root.querySelector('[role="alert"]')?.textContent)
      .toContain('Vorgangsdaten sind derzeit nicht verfügbar.');
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
    expect(elementRegistryGet).toHaveBeenCalledTimes(2);
    expect(elementRegistryGet).toHaveBeenCalledWith('Task_EntwurfAbstimmen');
    expect(elementRegistryGet).toHaveBeenCalledWith('Task_NachweiseNachhalten');
    expect(currentElement.businessObject.$instanceOf).toHaveBeenCalledWith('bpmn:Task');
    expect(deadlineElement.businessObject.$instanceOf).toHaveBeenCalledWith('bpmn:Task');
    expect(addMarker).toHaveBeenCalledTimes(2);
    expect(addMarker).toHaveBeenNthCalledWith(1, 'Task_EntwurfAbstimmen', 'nac-current-step');
    expect(addMarker).toHaveBeenNthCalledWith(2, 'Task_EntwurfAbstimmen', 'nac-selected-step');
    expect(addMarker.mock.invocationCallOrder[1]).toBeLessThan(zoom.mock.invocationCallOrder[0]);
    expect(root.textContent).toContain(workspace.matter.displayName);
    expect(root.textContent).toContain('Entwurf prüfen');
    expect(root.textContent).toContain('31.08.2026');
    expect(root.textContent).toContain('Keine eigene Frist');
    expect(root.textContent).toContain('Entwurf');
    expect(root.textContent).toContain('Notarielle Freigabe erforderlich');
    expect(root.textContent).toContain('Zugeordnetes Team (assigned)');
    expect(root.textContent).toContain('Aufgaben2');
    expect(root.querySelector('main')?.hasAttribute('data-nac-current-step')).toBe(false);
    const diagram = root.querySelector('[aria-label="BPMN-Prozessdiagramm"]');
    expect(diagram?.getAttribute('role')).toBe('img');
    const diagramStatusId = diagram?.getAttribute('aria-describedby');
    expect(diagramStatusId).toMatch(/^nac-selected-task-details-[0-9]+-diagram-status$/);
    expect(root.querySelector('[id="' + diagramStatusId + '"]')?.textContent)
      .toContain('Aktueller Prozessschritt: Entwurf prüfen');
    expect(root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')?.getAttribute('data-nac-current-step'))
      .toBe('Task_EntwurfAbstimmen');
    expect(root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')?.getAttribute('data-nac-selected-step'))
      .toBe('Task_EntwurfAbstimmen');
    const currentButton = root.querySelector('[data-nac-task-id="NAC-SYN-TASK-001"]');
    expect(currentButton?.tagName).toBe('BUTTON');
    expect(currentButton?.getAttribute('type')).toBe('button');
    expect(currentButton?.getAttribute('aria-pressed')).toBe('true');
    const taskDetailsId = currentButton?.getAttribute('aria-controls');
    expect(taskDetailsId).toMatch(/^nac-selected-task-details-[0-9]+$/);
    expect(root.querySelector('[id="' + taskDetailsId + '"]')).not.toBeNull();
    expect(resized).toHaveBeenCalledTimes(1);
    expect(zoom).toHaveBeenCalledTimes(1);
    expect(resizeObserverObserve).toHaveBeenCalledWith(
      root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')
    );
  });

  it('assigns stable unique task detail ids to each component instance', async () => {
    const loadWorkspace = jest.fn().mockResolvedValue(workspace);
    let userDisplayName = 'Test User';
    const renderPair = async (): Promise<void> => {
      await act(async () => {
        ReactDom.render(
          <>
            <NacBpmnViewer
              key="first"
              workspaceId="notary_team_01"
              userDisplayName={userDisplayName}
              hostName="SharePoint"
              isDarkTheme={false}
              evaluationTimestamp="2026-08-25T16:00:00Z"
              loadWorkspace={loadWorkspace}
            />
            <NacBpmnViewer
              key="second"
              workspaceId="notary_team_01"
              userDisplayName={userDisplayName}
              hostName="SharePoint"
              isDarkTheme={false}
              evaluationTimestamp="2026-08-25T16:00:00Z"
              loadWorkspace={loadWorkspace}
            />
          </>,
          root
        );
      });
      await flushPromises();
    };

    await renderPair();

    const viewers = root.querySelectorAll<HTMLElement>('[data-nac-component="test-workspace"]');
    expect(viewers).toHaveLength(2);
    const firstDetails = viewers[0].querySelector<HTMLElement>(
      '[id^="nac-selected-task-details-"][aria-labelledby]'
    ) as HTMLElement;
    const secondDetails = viewers[1].querySelector<HTMLElement>(
      '[id^="nac-selected-task-details-"][aria-labelledby]'
    ) as HTMLElement;
    const firstId = firstDetails.id;
    const secondId = secondDetails.id;
    expect(new Set([firstId, secondId]).size).toBe(2);
    const firstControls = Array.from(viewers[0].querySelectorAll('[data-nac-task-id]'))
      .map(button => button.getAttribute('aria-controls'));
    const secondControls = Array.from(viewers[1].querySelectorAll('[data-nac-task-id]'))
      .map(button => button.getAttribute('aria-controls'));
    expect(firstControls).toEqual([firstId, firstId]);
    expect(secondControls).toEqual([secondId, secondId]);

    userDisplayName = 'Updated User';
    await renderPair();

    const rerenderedIds = Array.from(root.querySelectorAll<HTMLElement>(
      '[id^="nac-selected-task-details-"][aria-labelledby]'
    )).map(details => details.id);
    expect(rerenderedIds).toEqual([firstId, secondId]);
  });

  it('selects another task by pointer without moving the current marker', async () => {
    await renderAndFlush(async () => workspace);

    const deadlineButton = root.querySelector('[data-nac-task-id="NAC-SYN-DEADLINE-001"]') as HTMLButtonElement;
    expect(deadlineButton).not.toBeNull();

    act(() => {
      deadlineButton.click();
    });

    expect(removeMarker).toHaveBeenCalledWith('Task_EntwurfAbstimmen', 'nac-selected-step');
    expect(addMarker).toHaveBeenCalledWith('Task_NachweiseNachhalten', 'nac-selected-step');
    expect(addMarker.mock.calls.filter(call => call[1] === 'nac-current-step')).toHaveLength(1);
    expect(root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')?.getAttribute('data-nac-current-step'))
      .toBe('Task_EntwurfAbstimmen');
    expect(root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')?.getAttribute('data-nac-selected-step'))
      .toBe('Task_NachweiseNachhalten');
    expect(root.querySelector('[data-nac-task-id="NAC-SYN-TASK-001"]')?.getAttribute('aria-pressed')).toBe('false');
    expect(deadlineButton.getAttribute('aria-pressed')).toBe('true');
    expect(root.textContent).toContain('Abschlussfrist überwachen');
    expect(root.textContent).toContain('31.08.2026');
    expect(root.textContent).toContain('Keine notarielle Freigabe erforderlich');
  });

  it('exposes native button semantics used by Enter activation', async () => {
    await renderAndFlush(async () => workspace);

    const deadlineButton = root.querySelector('[data-nac-task-id="NAC-SYN-DEADLINE-001"]') as HTMLButtonElement;

    expect(deadlineButton.tagName).toBe('BUTTON');
    expect(deadlineButton.getAttribute('type')).toBe('button');
    expect(deadlineButton.onkeydown).toBeNull();
  });

  it('exposes native button semantics used by Space activation', async () => {
    await renderAndFlush(async () => workspace);

    const deadlineButton = root.querySelector('[data-nac-task-id="NAC-SYN-DEADLINE-001"]') as HTMLButtonElement;

    expect(deadlineButton.tagName).toBe('BUTTON');
    expect(deadlineButton.getAttribute('type')).toBe('button');
    expect(deadlineButton.onkeydown).toBeNull();
  });

  it('refits the same viewer instance after its container resizes', async () => {
    await renderAndFlush(async () => workspace);

    act(() => {
      resizeObserverCallback([], resizeObserverInstance);
    });

    expect(BpmnViewer).toHaveBeenCalledTimes(1);
    expect(importXml).toHaveBeenCalledTimes(1);
    expect(addMarker).toHaveBeenCalledTimes(2);
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

  it('fails closed before metadata for duplicate task ids', async () => {
    const duplicateTaskIdWorkspace: NacBffWorkspace = {
      ...workspace,
      matter: {
        ...workspace.matter,
        tasks: [
          workspace.matter.tasks[0],
          { ...workspace.matter.tasks[1], taskId: workspace.matter.tasks[0].taskId }
        ]
      }
    };

    await renderAndFlush(async () => duplicateTaskIdWorkspace);

    expect(getService).not.toHaveBeenCalled();
    expect(addMarker).not.toHaveBeenCalled();
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(destroy).toHaveBeenCalledTimes(1);
  });
  it('fails closed before metadata for duplicate step codes', async () => {
    const duplicateStepCodeWorkspace: NacBffWorkspace = {
      ...workspace,
      matter: {
        ...workspace.matter,
        tasks: [
          workspace.matter.tasks[0],
          { ...workspace.matter.tasks[1], stepCode: workspace.matter.tasks[0].stepCode }
        ]
      }
    };

    await renderAndFlush(async () => duplicateStepCodeWorkspace);

    expect(getService).not.toHaveBeenCalled();
    expect(addMarker).not.toHaveBeenCalled();
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(destroy).toHaveBeenCalledTimes(1);
  });
  it('fails closed before metadata for an unknown non-current task binding', async () => {
    elementRegistryGet.mockImplementation((stepCode: string) =>
      stepCode === currentElement.id ? currentElement : undefined
    );

    await renderAndFlush(async () => workspace);

    expect(elementRegistryGet).toHaveBeenCalledTimes(2);
    expect(elementRegistryGet).toHaveBeenCalledWith('Task_NachweiseNachhalten');
    expect(addMarker).not.toHaveBeenCalled();
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(destroy).toHaveBeenCalledTimes(1);
  });

  it('fails closed before metadata for a fake task type without bpmn:Task inheritance', async () => {
    const fakeTaskElement = {
      id: deadlineElement.id,
      type: 'bpmn:AnythingTask',
      businessObject: {
        $instanceOf: jest.fn().mockReturnValue(false)
      }
    };
    elementRegistryGet.mockImplementation((stepCode: string) =>
      stepCode === currentElement.id ? currentElement : fakeTaskElement
    );

    await renderAndFlush(async () => workspace);

    expect(fakeTaskElement.businessObject.$instanceOf).toHaveBeenCalledWith('bpmn:Task');
    expect(addMarker).not.toHaveBeenCalled();
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(destroy).toHaveBeenCalledTimes(1);
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

  it('fails closed when the initial selection marker cannot be added', async () => {
    addMarker.mockImplementationOnce(() => undefined).mockImplementationOnce(() => {
      throw new Error('selection marker failed');
    });

    await renderAndFlush(async () => workspace);

    expect(addMarker).toHaveBeenCalledTimes(2);
    expect(zoom).not.toHaveBeenCalled();
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(destroy).toHaveBeenCalledTimes(1);
  });
  it('fails closed when removing the previous selection marker fails', async () => {
    await renderAndFlush(async () => workspace);
    removeMarker.mockImplementation(() => {
      throw new Error('remove marker failed');
    });

    const deadlineButton = root.querySelector('[data-nac-task-id="NAC-SYN-DEADLINE-001"]') as HTMLButtonElement;
    act(() => {
      deadlineButton.click();
    });

    expect(removeMarker).toHaveBeenCalledTimes(1);
    expect(addMarker).toHaveBeenCalledTimes(2);
    expect(resizeObserverDisconnect).toHaveBeenCalledTimes(1);
    expect(destroy).toHaveBeenCalledTimes(1);
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
  });
  it('fails closed when adding the next selection marker fails', async () => {
    await renderAndFlush(async () => workspace);
    addMarker.mockImplementation((stepCode: string, marker: string) => {
      if (stepCode === deadlineElement.id && marker === 'nac-selected-step') {
        throw new Error('add marker failed');
      }
    });

    const deadlineButton = root.querySelector('[data-nac-task-id="NAC-SYN-DEADLINE-001"]') as HTMLButtonElement;
    act(() => {
      deadlineButton.click();
    });

    expect(removeMarker).toHaveBeenCalledTimes(1);
    expect(addMarker).toHaveBeenCalledTimes(3);
    expect(resizeObserverDisconnect).toHaveBeenCalledTimes(1);
    expect(destroy).toHaveBeenCalledTimes(1);
    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
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

  it('filters deadline tasks and keeps current and selected BPMN markers distinct', async () => {
    await renderAndFlush(async () => workspace);

    const deadlineFilter = Array.from(root.querySelectorAll<HTMLButtonElement>(
      '[aria-label="Aufgaben filtern"] button'
    )).find(button => button.textContent === 'Aufgaben mit Frist');
    expect(deadlineFilter).toBeDefined();

    act(() => {
      deadlineFilter?.click();
    });

    expect(root.querySelector('[data-nac-task-id="NAC-SYN-TASK-001"]')).toBeNull();
    expect(root.querySelector('[data-nac-task-id="NAC-SYN-DEADLINE-001"]')).not.toBeNull();
    expect(root.textContent).toContain('1/2');
    expect(root.textContent).toContain('Abschlussfrist überwachen');
    expect(removeMarker).toHaveBeenCalledWith('Task_EntwurfAbstimmen', 'nac-selected-step');
    expect(addMarker).toHaveBeenCalledWith('Task_NachweiseNachhalten', 'nac-selected-step');
    expect(root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')?.getAttribute('data-nac-current-step'))
      .toBe('Task_EntwurfAbstimmen');
    expect(root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')?.getAttribute('data-nac-selected-step'))
      .toBe('Task_NachweiseNachhalten');
    const liveSelection = root.querySelector('[id$="-diagram-status"]');
    expect(liveSelection?.getAttribute('aria-live')).toBe('polite');
    expect(liveSelection?.getAttribute('aria-atomic')).toBe('true');
    expect(liveSelection?.textContent).toContain('Ausgewählte Aufgabe: Abschlussfrist überwachen');
  });

  it('shows an explicit empty state for a task filter without matches', async () => {
    const noNotaryWorkspace: NacBffWorkspace = {
      ...workspace,
      matter: {
        ...workspace.matter,
        tasks: workspace.matter.tasks.map(task => ({
          ...task,
          requiresNotaryApproval: false
        }))
      }
    };
    await renderAndFlush(async () => noNotaryWorkspace);

    const notaryFilter = Array.from(root.querySelectorAll<HTMLButtonElement>(
      '[aria-label="Aufgaben filtern"] button'
    )).find(button => button.textContent === 'Aufgaben mit Notarfreigabe');

    act(() => {
      notaryFilter?.click();
    });

    expect(root.textContent).toContain('Keine passenden Aufgaben');
    expect(root.textContent).toContain('Wählen Sie einen anderen Filter.');
    expect(root.querySelector('[role="status"]')?.textContent)
      .toContain('Keine passenden Aufgaben');
    expect(root.querySelectorAll('[data-nac-task-id]')).toHaveLength(0);
    expect(root.querySelector('[id^="nac-selected-task-details-"][aria-labelledby]')).toBeNull();
    expect(removeMarker).toHaveBeenCalledWith('Task_EntwurfAbstimmen', 'nac-selected-step');
    expect(root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')?.getAttribute('data-nac-current-step'))
      .toBe('Task_EntwurfAbstimmen');
    expect(root.querySelector('[aria-label="BPMN-Prozessdiagramm"]')?.hasAttribute('data-nac-selected-step'))
      .toBe(false);
  });

  it('fails closed permanently when the bound deadline evaluation timestamp is invalid', async () => {
    jest.useFakeTimers();
    const loadWorkspace = jest.fn().mockResolvedValue(workspace);
    try {
      await act(async () => {
        ReactDom.render(
          <NacBpmnViewer
            workspaceId="notary_team_01"
            userDisplayName="Test User"
            hostName="Microsoft Teams"
            isDarkTheme={false}
            evaluationTimestamp="not-a-timestamp"
            loadWorkspace={loadWorkspace}
          />,
          root
        );
        await Promise.resolve();
        await Promise.resolve();
      });
      await flushPromises();

      expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
      expect(root.textContent).not.toContain(workspace.matter.displayName);
      expect(root.querySelector('[data-nac-current-step]')).toBeNull();
      expect(destroy).toHaveBeenCalledTimes(1);

      act(() => {
        jest.advanceTimersByTime(60_000);
      });

      expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
      expect(root.textContent).not.toContain(workspace.matter.displayName);
      expect(loadWorkspace).toHaveBeenCalledTimes(1);
      expect(BpmnViewer).toHaveBeenCalledTimes(1);
      expect(destroy).toHaveBeenCalledTimes(1);
    } finally {
      jest.useRealTimers();
    }
  });

  it('refreshes and visibly dates the deadline evaluation clock every minute', async () => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-09-01T16:00:00Z'));
    try {
      await renderAndFlush(async () => workspace);

      expect(root.textContent).toContain('Frist innerhalb von sieben Tagen');
      expect(root.textContent).toContain('Stand: 25.08.2026');

      act(() => {
        jest.advanceTimersByTime(60_000);
      });

      expect(root.textContent).toContain('Frist überschritten');
      expect(root.textContent).toContain('Stand: 01.09.2026');
    } finally {
      jest.useRealTimers();
    }
  });

  it('retries once after BPMN import failure and destroys the failed viewer', async () => {
    const loadWorkspace = jest.fn().mockResolvedValue(workspace);
    importXml.mockRejectedValueOnce(new Error('invalid BPMN')).mockResolvedValueOnce(undefined);
    await renderAndFlush(loadWorkspace);

    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    const retryButton = Array.from(root.querySelectorAll<HTMLButtonElement>('button'))
      .find(button => button.textContent === 'Erneut laden');
    expect(retryButton).toBeDefined();

    await act(async () => {
      retryButton?.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    await flushPromises();

    expect(loadWorkspace).toHaveBeenCalledTimes(2);
    expect(BpmnViewer).toHaveBeenCalledTimes(2);
    expect(destroy).toHaveBeenCalledTimes(1);
    expect(root.textContent).toContain(workspace.matter.displayName);
  });

  it('announces an unavailable state with the dark host theme', async () => {
    await act(async () => {
      ReactDom.render(
        <NacBpmnViewer
          workspaceId="notary_team_01"
          userDisplayName="Test User"
          hostName="Microsoft Teams"
          isDarkTheme={true}
          evaluationTimestamp="2026-08-25T16:00:00Z"
          loadWorkspace={async () => { throw new Error('NAC_BFF_UNAVAILABLE'); }}
        />,
        root
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(root.querySelector('.nacBpmnViewer__messageHost')?.classList.contains('nacBpmnViewer__dark'))
      .toBe(true);
    expect(root.querySelector('[role="alert"]')?.textContent)
      .toContain('Vorgangsdaten sind derzeit nicht verfügbar.');
  });

  it('renders the deputy role and dark host state without changing the read boundary', async () => {
    const deputyWorkspace: NacBffWorkspace = {
      ...workspace,
      matter: { ...workspace.matter, accessMode: 'deputy' }
    };
    await act(async () => {
      ReactDom.render(
        <NacBpmnViewer
          workspaceId="notary_team_01"
          userDisplayName="Vertretung Test"
          hostName="Microsoft Teams"
          isDarkTheme={true}
          evaluationTimestamp="2026-08-25T16:00:00Z"
          loadWorkspace={async () => deputyWorkspace}
        />,
        root
      );
      await Promise.resolve();
      await Promise.resolve();
    });
    await flushPromises();

    expect(root.querySelector('main')?.classList.contains('nacBpmnViewer__dark')).toBe(true);
    expect(root.textContent).toContain('Aktive Vertretung');
    expect(root.textContent).toContain('Vertretung Test');
    expect(root.textContent).toContain('1 notarielle Freigabe');
  });

  it('retries an unavailable BFF load without changing workspace scope', async () => {
    const loadWorkspace = jest.fn()
      .mockRejectedValueOnce(new Error('NAC_BFF_UNAVAILABLE'))
      .mockResolvedValueOnce(workspace);
    await renderAndFlush(loadWorkspace);

    const retryButton = Array.from(root.querySelectorAll<HTMLButtonElement>('button'))
      .find(button => button.textContent === 'Erneut laden');
    expect(retryButton).toBeDefined();

    await act(async () => {
      retryButton?.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    await flushPromises();

    expect(loadWorkspace).toHaveBeenCalledTimes(2);
    expect(root.textContent).toContain(workspace.matter.displayName);
    expect(root.textContent).not.toContain('Vorgangsdaten sind derzeit nicht verfügbar.');
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
          evaluationTimestamp="2026-08-25T16:00:00Z"
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
          evaluationTimestamp="2026-08-25T16:00:00Z"
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
          evaluationTimestamp="2026-08-25T16:00:00Z"
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
