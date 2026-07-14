/// <reference types="node" />
jest.mock('@microsoft/sp-http', () => ({
  AadHttpClient: {
    configurations: {
      v1: {}
    }
  }
}));

import { webcrypto } from 'crypto';
import { TextEncoder } from 'util';
import type { HttpClientResponse } from '@microsoft/sp-http';
import { syntheticWorkspaceFixture } from '../fixtures/syntheticWorkspace';


import {
  NacBffWorkspace,
  parseWorkspaceResponse,
  verifyBpmnAsset
} from './NacBffClient';

const workspace: NacBffWorkspace = {
  schemaVersion: 'nac.m365-test-environment-workspace/v0.1',
  workspaceId: 'notary_team_01',
  matter: {
    matterId: 'NAC-SYN-MATTER-001',
    businessCaseTypeId: 'immobilienkaufvertrag',
    displayName: 'Synthetischer Immobilienkaufvertrag',
    status: 'Entwurf',
    deadline: '2026-08-31T16:00:00Z',
    tasks: [
      {
        taskId: 'NAC-SYN-TASK-001',
        title: 'Entwurf prüfen',
        stepCode: 'draft_review',
        status: 'Offen',
        requiresNotaryApproval: true,
        dueAt: '2026-08-31T16:00:00Z'
      }
    ],
    bpmn: {
      modelKey: 'NAC_SYN_MATTER_001',
      sha256: '1dd7203a515d434949ef9300d5738cf7318d842119ec689aaa7ba1f9a7a6d167'
    },
    accessMode: 'assigned'
  }
};

function response(body: string, ok: boolean = true, contentLength?: string): HttpClientResponse {
  return {
    ok,
    headers: {
      get: (name: string): string | null =>
        name.toLowerCase() === 'content-length' ? contentLength ?? null : null
    },
    text: async (): Promise<string> => body
  } as unknown as HttpClientResponse;
}

describe('NaC BFF client boundary', () => {
  beforeAll(() => {
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: webcrypto
    });
    Object.defineProperty(globalThis, 'TextEncoder', {
      configurable: true,
      value: TextEncoder
    });
  });

  it('accepts the exact bounded workspace DTO', async () => {
    await expect(parseWorkspaceResponse(response(JSON.stringify(workspace))))
      .resolves.toEqual(workspace);
  });

  it.each([
    ['root', { ...workspace, unexpected: 'document-content' }],
    ['matter', { ...workspace, matter: { ...workspace.matter, unexpected: true } }],
    [
      'bpmn',
      {
        ...workspace,
        matter: {
          ...workspace.matter,
          bpmn: { ...workspace.matter.bpmn, unexpected: true }
        }
      }
    ],
    [
      'task',
      {
        ...workspace,
        matter: {
          ...workspace.matter,
          tasks: [{ ...workspace.matter.tasks[0], unexpected: true }]
        }
      }
    ]
  ])('rejects extra %s fields', async (_label, value) => {
    await expect(parseWorkspaceResponse(response(JSON.stringify(value))))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
  });

  it('rejects wrong identifiers, hashes, timestamps and malformed bodies', async () => {
    const wrongHash = {
      ...workspace,
      matter: {
        ...workspace.matter,
        bpmn: { ...workspace.matter.bpmn, sha256: '0'.repeat(64) }
      }
    };
    const wrongTimestamp = {
      ...workspace,
      matter: { ...workspace.matter, deadline: '31.08.2026' }
    };
    await expect(parseWorkspaceResponse(response(JSON.stringify(wrongHash))))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
    await expect(parseWorkspaceResponse(response(JSON.stringify(wrongTimestamp))))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
    await expect(parseWorkspaceResponse(response('{not-json')))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
  });

  it('rejects authorization failures and oversized or invalid lengths', async () => {
    await expect(parseWorkspaceResponse(response('{}', false)))
      .rejects.toThrow('NAC_BFF_REQUEST_REJECTED');
    await expect(parseWorkspaceResponse(response('x'.repeat(65537))))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
    await expect(parseWorkspaceResponse(response('{}', true, 'not-a-number')))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
  });

  it('cryptographically binds packaged BPMN XML to fixture and BFF DTO', async () => {
    await expect(
      verifyBpmnAsset(
        workspace,
        syntheticWorkspaceFixture.bpmnXml,
        syntheticWorkspaceFixture.bpmnSha256
      )
    ).resolves.toBeUndefined();
    await expect(
      verifyBpmnAsset(
        workspace,
        syntheticWorkspaceFixture.bpmnXml + '<!-- changed -->',
        syntheticWorkspaceFixture.bpmnSha256
      )
    ).rejects.toThrow('NAC_BPMN_ASSET_INVALID');
  });
});
