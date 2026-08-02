/// <reference types="node" />
jest.mock('@microsoft/sp-http', () => ({
  AadHttpClient: {
    configurations: {
      v1: {}
    }
  }
}));

import { createHash } from 'crypto';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { TextDecoder, TextEncoder } from 'util';
import { AadHttpClient } from '@microsoft/sp-http';
import type { AadHttpClientFactory, HttpClientResponse } from '@microsoft/sp-http';

import {
  classifyNacBffFailure,
  NacBffWorkspace,
  loadNacWorkbenchSnapshot,
  loadNacBffWorkspace,
  parseWorkbenchResponse,
  parseWorkspaceResponse,
  verifyBpmnAsset
} from './NacBffClient';
import {
  signedWorkbenchSnapshotJson,
  VALID_WORKBENCH_SNAPSHOT
} from '../../../workbench/core/parseWorkbenchSnapshot.test';

const canonicalBpmnSha256 =
  '02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0';
const bpmnXml = readFileSync(
  resolve(process.cwd(), 'test-fixtures/immobilienkaufvertrag.bpmn'),
  'utf8'
);
const noncanonicalBpmnXml = bpmnXml.replace(
  'Process_immobilienkaufvertrag',
  'Process_noncanonical'
);

const workspace: NacBffWorkspace = {
  schemaVersion: 'nac.m365-test-environment-workspace/v0.2',
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
        stepCode: 'Task_EntwurfAbstimmen',
        status: 'Offen',
        requiresNotaryApproval: true,
        dueAt: '2026-08-31T16:00:00Z'
      }
    ],
    bpmn: {
      modelKey: 'Process_immobilienkaufvertrag',
      mimeType: 'application/xml',
      sha256: canonicalBpmnSha256,
      xml: bpmnXml
    },
    accessMode: 'assigned'
  }
};

function responseFromChunks(
  chunks: readonly Uint8Array[],
  ok: boolean = true,
  contentLength?: string,
  status: number = 200,
  headers: Readonly<Record<string, string>> = {}
): HttpClientResponse {
  let index = 0;
  return {
    ok,
    status,
    headers: {
      get: (name: string): string | null => {
        const normalized = name.toLowerCase();
        if (normalized === 'content-length') return contentLength ?? null;
        return headers[normalized] ?? null;
      }
    },
    body: {
      getReader: () => ({
        read: async (): Promise<{ done: boolean; value?: Uint8Array }> => {
          if (index >= chunks.length) {
            return { done: true };
          }
          const value = chunks[index];
          index += 1;
          return { done: false, value };
        },
        cancel: async (): Promise<void> => undefined,
        releaseLock: (): void => undefined
      })
    }
  } as unknown as HttpClientResponse;
}

function response(
  body: string,
  ok: boolean = true,
  contentLength?: string,
  status: number = 200
): HttpClientResponse {
  return responseFromChunks([new TextEncoder().encode(body)], ok, contentLength, status);
}

describe('NaC BFF client boundary', () => {
  beforeAll(() => {
    const digest = jest.fn(async (
      _algorithm: AlgorithmIdentifier,
      data: BufferSource
    ): Promise<ArrayBuffer> => {
      const bytes = data instanceof ArrayBuffer
        ? new Uint8Array(data)
        : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
      const digestHex = createHash('sha256').update(bytes).digest('hex');
      return Uint8Array.from(Buffer.from(digestHex, 'hex')).buffer;
    });
    Object.defineProperty(globalThis, 'crypto', {
      configurable: true,
      value: {
        randomUUID: (): string => '00000000-0000-4000-8000-000000000000',
        subtle: { digest }
      }
    });
    Object.defineProperty(globalThis, 'TextEncoder', {
      configurable: true,
      value: TextEncoder
    });
    Object.defineProperty(globalThis, 'TextDecoder', {
      configurable: true,
      value: TextDecoder
    });
  });

  it('accepts the exact v0.2 workspace DTO and canonical BPMN digest', async () => {
    await expect(parseWorkspaceResponse(response(JSON.stringify(workspace))))
      .resolves.toEqual(workspace);
  });

  it('uses the fixed AadHttpClient resource, route, purpose and correlation boundary', async () => {
    const get = jest.fn().mockResolvedValue(response(JSON.stringify(workspace)));
    const getClient = jest.fn().mockResolvedValue({ get });
    const factory = { getClient } as unknown as AadHttpClientFactory;
    const controller = new AbortController();

    await expect(loadNacBffWorkspace(factory, controller.signal)).resolves.toEqual(workspace);

    expect(getClient).toHaveBeenCalledWith('api://funktion8.de/nac-bff');
    expect(get).toHaveBeenCalledWith(
      'https://func-nac-bff-test-funktion8.azurewebsites.net' +
        '/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001' +
        '?purpose=view_synthetic_matter_workspace',
      AadHttpClient.configurations.v1,
      expect.objectContaining({
        signal: controller.signal,
        headers: expect.objectContaining({
          Accept: 'application/json',
          'X-Correlation-ID': expect.stringMatching(/^spfx-/)
        })
      })
    );
  });

  it('uses the dedicated workbench route and validates the authenticated subject', async () => {
    const body = signedWorkbenchSnapshotJson();
    const get = jest.fn().mockResolvedValue(responseFromChunks(
      [new TextEncoder().encode(body)],
      true,
      undefined,
      200,
      {
        'content-type': 'application/json; charset=utf-8',
        'cache-control': 'no-store',
        pragma: 'no-cache'
      }
    ));
    const getClient = jest.fn().mockResolvedValue({ get });
    const factory = { getClient } as unknown as AadHttpClientFactory;
    const controller = new AbortController();

    await expect(loadNacWorkbenchSnapshot(
      factory,
      VALID_WORKBENCH_SNAPSHOT.access.subjectId,
      controller.signal,
      '2026-08-01T09:01:00Z'
    )).resolves.toEqual(expect.objectContaining({ schemaVersion: 'nac.workbench.snapshot/v1' }));

    expect(getClient).toHaveBeenCalledWith('api://funktion8.de/nac-bff');
    expect(get).toHaveBeenCalledWith(
      'https://func-nac-bff-test-funktion8.azurewebsites.net' +
        '/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001/workbench-snapshot' +
        '?purpose=view_synthetic_matter_workspace',
      AadHttpClient.configurations.v1,
      expect.objectContaining({
        signal: controller.signal,
        headers: expect.objectContaining({ Accept: 'application/json' })
      })
    );
  });

  it('normalizes the default workbench validation time to whole-second RFC3339', async () => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-08-01T09:01:00.789Z'));
    try {
      const get = jest.fn().mockResolvedValue(responseFromChunks(
        [new TextEncoder().encode(signedWorkbenchSnapshotJson())],
        true,
        undefined,
        200,
        {
          'content-type': 'application/json; charset=utf-8',
          'cache-control': 'no-store',
          pragma: 'no-cache'
        }
      ));
      const factory = {
        getClient: jest.fn().mockResolvedValue({ get })
      } as unknown as AadHttpClientFactory;

      await expect(loadNacWorkbenchSnapshot(
        factory,
        VALID_WORKBENCH_SNAPSHOT.access.subjectId,
        new AbortController().signal
      )).resolves.toEqual(expect.objectContaining({ schemaVersion: 'nac.workbench.snapshot/v1' }));
    } finally {
      jest.useRealTimers();
    }
  });

  it('captures default validation time after the BFF response arrives', async () => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-08-01T09:01:00.900Z'));
    try {
      const laterSnapshot = {
        ...VALID_WORKBENCH_SNAPSHOT,
        generatedAt: '2026-08-01T09:01:01Z',
        access: {
          ...VALID_WORKBENCH_SNAPSHOT.access,
          issuedAt: '2026-08-01T09:01:01Z'
        },
        redaction: {
          ...VALID_WORKBENCH_SNAPSHOT.redaction,
          verifiedAt: '2026-08-01T09:01:01Z'
        }
      };
      const get = jest.fn().mockImplementation(async () => {
        jest.setSystemTime(new Date('2026-08-01T09:01:01.100Z'));
        return responseFromChunks(
          [new TextEncoder().encode(signedWorkbenchSnapshotJson(laterSnapshot))],
          true,
          undefined,
          200,
          {
            'content-type': 'application/json; charset=utf-8',
            'cache-control': 'no-store',
            pragma: 'no-cache'
          }
        );
      });
      const factory = {
        getClient: jest.fn().mockResolvedValue({ get })
      } as unknown as AadHttpClientFactory;

      await expect(loadNacWorkbenchSnapshot(
        factory,
        VALID_WORKBENCH_SNAPSHOT.access.subjectId,
        new AbortController().signal
      )).resolves.toEqual(expect.objectContaining({ generatedAt: '2026-08-01T09:01:01Z' }));
    } finally {
      jest.useRealTimers();
    }
  });

  it.each([
    ['subject', { subjectId: 'actor:synthetic:other' }],
    ['role', { role: 'runtime_service' }],
    ['workspace', { workspaceId: 'notary_team_02' }],
    ['matter', { matterId: 'NAC-SYN-MATTER-OTHER' }],
    ['purpose', { purpose: 'view_other_matter' }]
  ])('rejects workbench %s drift after hash verification', async (
    _label,
    accessOverride: Partial<typeof VALID_WORKBENCH_SNAPSHOT.access>
  ) => {
    const changed = {
      ...VALID_WORKBENCH_SNAPSHOT,
      access: { ...VALID_WORKBENCH_SNAPSHOT.access, ...accessOverride },
      scope: {
        ...VALID_WORKBENCH_SNAPSHOT.scope,
        ...(accessOverride.workspaceId ? { workspaceId: accessOverride.workspaceId } : {}),
        ...(accessOverride.matterId ? { matterId: accessOverride.matterId } : {}),
        ...(accessOverride.purpose ? { purpose: accessOverride.purpose } : {})
      },
      matter: accessOverride.matterId
        ? { ...VALID_WORKBENCH_SNAPSHOT.matter, id: accessOverride.matterId }
        : VALID_WORKBENCH_SNAPSHOT.matter
    };
    const workbenchResponse = responseFromChunks(
      [new TextEncoder().encode(signedWorkbenchSnapshotJson(changed))],
      true,
      undefined,
      200,
      {
        'content-type': 'application/json; charset=utf-8',
        'cache-control': 'no-store',
        pragma: 'no-cache'
      }
    );
    await expect(parseWorkbenchResponse(
      workbenchResponse,
      VALID_WORKBENCH_SNAPSHOT.access.subjectId,
      '2026-08-01T09:01:00Z'
    )).rejects.toThrow('NAC_WORKBENCH_SCOPE_INVALID');
  });

  it('bounds chunked workbench responses at exactly 128 KiB', async () => {
    const headers = {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
      pragma: 'no-cache'
    };
    await expect(parseWorkbenchResponse(
      responseFromChunks([new Uint8Array(80 * 1024), new Uint8Array((48 * 1024) + 1)], true, undefined, 200, headers),
      VALID_WORKBENCH_SNAPSHOT.access.subjectId,
      '2026-08-01T09:01:00Z'
    )).rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
  });

  it.each([401, 403])('maps workbench HTTP %i to the neutral access denial', async status => {
    await expect(parseWorkbenchResponse(
      response('{}', false, undefined, status),
      VALID_WORKBENCH_SNAPSHOT.access.subjectId,
      '2026-08-01T09:01:00Z'
    )).rejects.toThrow('NAC_BFF_ACCESS_DENIED');
  });

  it.each([
    ['content type', { 'content-type': 'text/plain', 'cache-control': 'no-store', pragma: 'no-cache' }],
    ['cache policy', { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'public', pragma: 'no-cache' }],
    ['pragma', { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', pragma: 'cache' }]
  ])('rejects invalid workbench %s headers', async (_label, headers) => {
    await expect(parseWorkbenchResponse(
      responseFromChunks([new TextEncoder().encode(signedWorkbenchSnapshotJson())], true, undefined, 200, headers),
      VALID_WORKBENCH_SNAPSHOT.access.subjectId,
      '2026-08-01T09:01:00Z'
    )).rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
  });

  it.each([
    ['root', { ...workspace, unexpected: 'document-content' }],
    ['matter', { ...workspace, matter: { ...workspace.matter, unexpected: true } }],
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
  ])('rejects extra %s fields as an unavailable response', async (_label, value) => {
    const failure = parseWorkspaceResponse(response(JSON.stringify(value)));
    await expect(failure).rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
    await expect(failure.catch(error => classifyNacBffFailure(error)))
      .resolves.toBe('unavailable');
  });

  it('rejects wrong identifiers, timestamps and malformed bodies', async () => {
    const wrongSchema = { ...workspace, schemaVersion: 'nac.m365-test-environment-workspace/v0.1' };
    const wrongTimestamp = {
      ...workspace,
      matter: { ...workspace.matter, deadline: '31.08.2026' }
    };
    const impossibleTimestamp = {
      ...workspace,
      matter: { ...workspace.matter, deadline: '2026-02-30T25:00:00Z' }
    };
    await expect(parseWorkspaceResponse(response(JSON.stringify(wrongSchema))))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
    await expect(parseWorkspaceResponse(response(JSON.stringify(wrongTimestamp))))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
    await expect(parseWorkspaceResponse(response(JSON.stringify(impossibleTimestamp))))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
    await expect(parseWorkspaceResponse(response('{not-json')))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
  });

  it.each([
    ['missing BPMN object', undefined],
    ['null BPMN object', null],
    ['array BPMN object', []],
    [
      'missing XML key',
      {
        modelKey: workspace.matter.bpmn.modelKey,
        mimeType: workspace.matter.bpmn.mimeType,
        sha256: workspace.matter.bpmn.sha256
      }
    ],
    ['extra BPMN key', { ...workspace.matter.bpmn, unexpected: true }],
    ['non-string XML', { ...workspace.matter.bpmn, xml: 42 }]
  ])('classifies BPMN shape failure %s as invalidAsset', async (_label, bpmn) => {
    const value = { ...workspace, matter: { ...workspace.matter, bpmn } };
    const failure = parseWorkspaceResponse(response(JSON.stringify(value)));
    await expect(failure).rejects.toThrow('NAC_BPMN_ASSET_INVALID');
    await expect(failure.catch(error => classifyNacBffFailure(error)))
      .resolves.toBe('invalidAsset');
  });

  it.each([
    ['model key', { ...workspace.matter.bpmn, modelKey: 'NAC_SYN_MATTER_001' }],
    ['MIME type', { ...workspace.matter.bpmn, mimeType: 'text/xml' }],
    ['SHA-256 format', { ...workspace.matter.bpmn, sha256: 'not-a-hash' }],
    [
      'self-consistent noncanonical SHA-256',
      {
        ...workspace.matter.bpmn,
        sha256: createHash('sha256').update(noncanonicalBpmnXml, 'utf8').digest('hex'),
        xml: noncanonicalBpmnXml
      }
    ],
    ['XML digest', { ...workspace.matter.bpmn, xml: bpmnXml + '<!-- changed -->' }],
    ['empty XML', { ...workspace.matter.bpmn, xml: '' }],
    ['oversized XML', { ...workspace.matter.bpmn, xml: 'x'.repeat((48 * 1024) + 1) }]
  ])('classifies invalid BPMN %s as invalidAsset', async (_label, bpmn) => {
    const value = { ...workspace, matter: { ...workspace.matter, bpmn } };
    const failure = parseWorkspaceResponse(response(JSON.stringify(value)));
    await expect(failure).rejects.toThrow('NAC_BPMN_ASSET_INVALID');
    await expect(failure.catch(error => classifyNacBffFailure(error)))
      .resolves.toBe('invalidAsset');
  });

  it('enforces the 48 KiB BPMN limit by UTF-8 byte length', async () => {
    const value = {
      ...workspace,
      matter: {
        ...workspace.matter,
        bpmn: { ...workspace.matter.bpmn, xml: '€'.repeat(17_000) }
      }
    };
    const failure = parseWorkspaceResponse(response(JSON.stringify(value)));
    await expect(failure).rejects.toThrow('NAC_BPMN_ASSET_INVALID');
    await expect(failure.catch(error => classifyNacBffFailure(error)))
      .resolves.toBe('invalidAsset');
  });

  it.each([401, 403])('classifies HTTP %i as neutral access denial', async status => {
    const failure = parseWorkspaceResponse(response('{}', false, undefined, status));
    await expect(failure).rejects.toThrow('NAC_BFF_ACCESS_DENIED');
    await expect(failure.catch(error => classifyNacBffFailure(error)))
      .resolves.toBe('accessDenied');
  });

  it.each([404, 500, 503])('classifies HTTP %i as unavailable', async status => {
    const failure = parseWorkspaceResponse(response('{}', false, undefined, status));
    await expect(failure).rejects.toThrow('NAC_BFF_UNAVAILABLE');
    await expect(failure.catch(error => classifyNacBffFailure(error)))
      .resolves.toBe('unavailable');
  });

  it('classifies browser network failures without leaking details', () => {
    expect(classifyNacBffFailure(new TypeError('network detail'))).toBe('unavailable');
  });

  it('rejects oversized or invalid response lengths', async () => {
    await expect(parseWorkspaceResponse(response('x'.repeat(65537))))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
    await expect(parseWorkspaceResponse(response('€'.repeat(22000))))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
    await expect(parseWorkspaceResponse(response('{}', true, 'not-a-number')))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
  });

  it('stops a chunked response before buffering more than 64 KiB', async () => {
    const chunks = [
      new Uint8Array(40 * 1024),
      new Uint8Array(25 * 1024)
    ];
    await expect(parseWorkspaceResponse(responseFromChunks(chunks)))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
  });

  it('rejects a response without a readable body stream', async () => {
    const missingBody = {
      ok: true,
      status: 200,
      headers: { get: (): null => null }
    } as unknown as HttpClientResponse;
    await expect(parseWorkspaceResponse(missingBody))
      .rejects.toThrow('NAC_BFF_RESPONSE_INVALID');
  });

  it('cryptographically binds the BFF XML to the canonical declared digest', async () => {
    await expect(verifyBpmnAsset(workspace)).resolves.toBeUndefined();
    const changed = {
      ...workspace,
      matter: {
        ...workspace.matter,
        bpmn: { ...workspace.matter.bpmn, xml: bpmnXml + '<!-- changed -->' }
      }
    };
    await expect(verifyBpmnAsset(changed)).rejects.toThrow('NAC_BPMN_ASSET_INVALID');
  });
});
