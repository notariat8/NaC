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
      stepCode: 'draft_review',
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

  beforeEach(() => {
    root = document.createElement('div');
    document.body.appendChild(root);
    importXml = jest.fn().mockResolvedValue(undefined);
    destroy = jest.fn();
    (BpmnViewer as unknown as jest.Mock).mockImplementation(() => ({
      importXML: importXml,
      destroy,
      get: jest.fn().mockReturnValue({ zoom: jest.fn() })
    }));
  });

  afterEach(() => {
    ReactDom.unmountComponentAtNode(root);
    root.remove();
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

  it('renders only the BPMN XML returned by the BFF and shows ready metadata', async () => {
    await renderAndFlush(async () => workspace);

    expect(importXml).toHaveBeenCalledWith(bpmnXml);
    expect(root.textContent).toContain(workspace.matter.displayName);
    expect(root.textContent).toContain('Entwurf prüfen');
    expect(root.textContent).toContain('31.08.2026');
    expect(root.textContent).toContain('Entwurf');
    expect(root.textContent).toContain('Zugeordnet (assigned)');
    expect(root.textContent).toContain('Aufgaben1');
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
