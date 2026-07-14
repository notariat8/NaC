/// <reference types="node" />
jest.mock('bpmn-js/lib/Viewer', () => ({
  __esModule: true,
  default: jest.fn()
}));
jest.mock('../services/NacBffClient', () => ({
  verifyBpmnAsset: jest.fn()
}));

import * as React from 'react';
import * as ReactDom from 'react-dom';
import { act } from 'react-dom/test-utils';
import BpmnViewer from 'bpmn-js/lib/Viewer';
import {
  NacBffWorkspace,
  verifyBpmnAsset
} from '../services/NacBffClient';
import { NacBpmnViewer } from './NacBpmnViewer';

const workspace: NacBffWorkspace = {
  schemaVersion: 'nac.m365-test-environment-workspace/v0.1',
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
      modelKey: 'NAC_SYN_MATTER_001',
      sha256: '1dd7203a515d434949ef9300d5738cf7318d842119ec689aaa7ba1f9a7a6d167'
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
    (verifyBpmnAsset as jest.Mock).mockResolvedValue(undefined);
  });

  afterEach(() => {
    ReactDom.unmountComponentAtNode(root);
    root.remove();
    jest.clearAllMocks();
  });

  it('fails closed and destroys the viewer when BPMN import fails', async () => {
    importXml.mockRejectedValue(new Error('invalid BPMN'));

    await act(async () => {
      ReactDom.render(
        <NacBpmnViewer
          workspaceId="notary_team_01"
          userDisplayName="Test User"
          hostName="Microsoft Teams"
          isDarkTheme={false}
          loadWorkspace={async () => workspace}
        />,
        root
      );
      await Promise.resolve();
      await Promise.resolve();
    });
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(root.textContent).toContain('Prozessmodell ist derzeit nicht verfügbar.');
    expect(root.textContent).not.toContain(workspace.matter.displayName);
    expect(destroy).toHaveBeenCalledTimes(1);
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
});
