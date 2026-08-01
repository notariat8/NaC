import { AadHttpClient, AadHttpClientFactory } from '@microsoft/sp-http';
import type { HttpClientResponse } from '@microsoft/sp-http';
import { WorkbenchSnapshot } from '../../../workbench/core/WorkbenchContracts';
import { parseNacWorkbenchProjectionJson } from '../../../workbench/nac/NacWorkbenchProjection';

export const NAC_BFF_RESOURCE_URI = 'api://funktion8.de/nac-bff';
export const NAC_BFF_SCOPE = 'Matter.Read';
export const NAC_BFF_BASE_URL = 'https://func-nac-bff-test-funktion8.azurewebsites.net';
export const NAC_BFF_WORKSPACE_ID = 'notary_team_01';
export const NAC_BFF_MATTER_ID = 'NAC-SYN-MATTER-001';
export const NAC_BFF_PURPOSE = 'view_synthetic_matter_workspace';

const EXPECTED_SCHEMA_VERSION = 'nac.m365-test-environment-workspace/v0.2';
const EXPECTED_BPMN_MODEL_KEY = 'Process_immobilienkaufvertrag';
const EXPECTED_BPMN_MIME_TYPE = 'application/xml';
const EXPECTED_BPMN_SHA256 =
  '02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0';
const EXPECTED_BUSINESS_CASE_TYPE_ID = 'immobilienkaufvertrag';
const MAX_RESPONSE_BYTES = 64 * 1024;
const MAX_WORKBENCH_RESPONSE_BYTES = 131072;
const MAX_BPMN_BYTES = 48 * 1024;

const ROOT_KEYS = ['matter', 'schemaVersion', 'workspaceId'];
const MATTER_KEYS = [
  'accessMode',
  'bpmn',
  'businessCaseTypeId',
  'deadline',
  'displayName',
  'matterId',
  'status',
  'tasks'
];
const BPMN_KEYS = ['mimeType', 'modelKey', 'sha256', 'xml'];
const TASK_KEYS = [
  'dueAt',
  'requiresNotaryApproval',
  'status',
  'stepCode',
  'taskId',
  'title'
];

export interface NacBffTask {
  readonly taskId: string;
  readonly title: string;
  readonly stepCode: string;
  readonly status: string;
  readonly requiresNotaryApproval: boolean;
  // JSON null is part of the bounded BFF DTO contract.
  // eslint-disable-next-line @rushstack/no-new-null
  readonly dueAt: string | null;
}

export interface NacBffWorkspace {
  readonly schemaVersion: typeof EXPECTED_SCHEMA_VERSION;
  readonly workspaceId: typeof NAC_BFF_WORKSPACE_ID;
  readonly matter: {
    readonly matterId: typeof NAC_BFF_MATTER_ID;
    readonly businessCaseTypeId: typeof EXPECTED_BUSINESS_CASE_TYPE_ID;
    readonly displayName: string;
    readonly status: string;
    readonly deadline: string;
    readonly tasks: readonly NacBffTask[];
    readonly bpmn: {
      readonly modelKey: typeof EXPECTED_BPMN_MODEL_KEY;
      readonly mimeType: typeof EXPECTED_BPMN_MIME_TYPE;
      readonly sha256: string;
      readonly xml: string;
    };
    readonly accessMode: 'assigned' | 'deputy';
  };
}

export type NacBffFailureKind = 'accessDenied' | 'invalidAsset' | 'unavailable';

export async function loadNacBffWorkspace(
  clientFactory: AadHttpClientFactory,
  signal: AbortSignal
): Promise<NacBffWorkspace> {
  const client = await clientFactory.getClient(NAC_BFF_RESOURCE_URI);
  const workspacePath = '/v1/workspaces/' + NAC_BFF_WORKSPACE_ID + '/matters/' + NAC_BFF_MATTER_ID;
  const workspaceUrl = NAC_BFF_BASE_URL + workspacePath + '?purpose=' + encodeURIComponent(NAC_BFF_PURPOSE);
  const response = await client.get(workspaceUrl, AadHttpClient.configurations.v1, {
    signal,
    headers: {
      Accept: 'application/json',
      'X-Correlation-ID': createCorrelationId()
    }
  });
  return parseWorkspaceResponse(response);
}

export async function loadNacWorkbenchSnapshot(
  clientFactory: AadHttpClientFactory,
  expectedSubjectId: string,
  signal: AbortSignal,
  nowIso: string = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z')
): Promise<WorkbenchSnapshot> {
  if (expectedSubjectId.trim().length === 0) {
    throw new Error('NAC_BFF_ACCESS_DENIED');
  }
  const client = await clientFactory.getClient(NAC_BFF_RESOURCE_URI);
  const workbenchPath = '/v1/workspaces/' + NAC_BFF_WORKSPACE_ID + '/matters/' +
    NAC_BFF_MATTER_ID + '/workbench-snapshot';
  const workbenchUrl = NAC_BFF_BASE_URL + workbenchPath + '?purpose=' +
    encodeURIComponent(NAC_BFF_PURPOSE);
  const response = await client.get(workbenchUrl, AadHttpClient.configurations.v1, {
    signal,
    headers: {
      Accept: 'application/json',
      'X-Correlation-ID': createCorrelationId()
    }
  });
  return parseWorkbenchResponse(response, expectedSubjectId, nowIso);
}

export async function parseWorkbenchResponse(
  response: HttpClientResponse,
  expectedSubjectId: string,
  nowIso: string
): Promise<WorkbenchSnapshot> {
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error('NAC_BFF_ACCESS_DENIED');
    }
    throw new Error('NAC_BFF_UNAVAILABLE');
  }
  if (
    response.headers.get('content-type') !== 'application/json; charset=utf-8' ||
    response.headers.get('cache-control') !== 'no-store' ||
    response.headers.get('pragma') !== 'no-cache'
  ) {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
  validateContentLength(response, MAX_WORKBENCH_RESPONSE_BYTES);
  const text = await readBoundedResponseText(response, MAX_WORKBENCH_RESPONSE_BYTES);
  return parseNacWorkbenchProjectionJson(text, nowIso, {
    subjectId: expectedSubjectId,
    workspaceId: NAC_BFF_WORKSPACE_ID,
    matterId: NAC_BFF_MATTER_ID,
    purpose: NAC_BFF_PURPOSE
  });
}

export async function parseWorkspaceResponse(
  response: HttpClientResponse
): Promise<NacBffWorkspace> {
  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error('NAC_BFF_ACCESS_DENIED');
    }
    throw new Error('NAC_BFF_UNAVAILABLE');
  }
  validateContentLength(response, MAX_RESPONSE_BYTES);
  const text = await readBoundedResponseText(response, MAX_RESPONSE_BYTES);
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
  const workspace = parseWorkspaceValue(value);
  await verifyBpmnAsset(workspace);
  return workspace;
}

function validateContentLength(response: HttpClientResponse, maximumBytes: number): void {
  const contentLength = response.headers.get('content-length');
  if (
    contentLength !== null &&
    (!/^\d+$/.test(contentLength) || Number(contentLength) > maximumBytes)
  ) {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
}

async function readBoundedResponseText(
  response: HttpClientResponse,
  maximumBytes: number
): Promise<string> {
  const streamingResponse = response as HttpClientResponse & {
    readonly body: ReadableStream<Uint8Array> | null;
  };
  const reader = streamingResponse.body?.getReader();
  if (!reader) {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }

  const chunks: Uint8Array[] = [];
  let byteLength = 0;
  try {
    while (true) {
      const result = await reader.read();
      if (result.done) {
        break;
      }
      if (!result.value) {
        continue;
      }
      byteLength += result.value.byteLength;
      if (byteLength > maximumBytes) {
        await reader.cancel();
        throw new Error('NAC_BFF_RESPONSE_INVALID');
      }
      chunks.push(result.value);
    }
  } finally {
    reader.releaseLock();
  }

  const bytes = new Uint8Array(byteLength);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
}

export async function verifyBpmnAsset(workspace: NacBffWorkspace): Promise<void> {
  const bpmn = workspace.matter.bpmn;
  const bytes = new TextEncoder().encode(bpmn.xml);
  if (
    bpmn.modelKey !== EXPECTED_BPMN_MODEL_KEY ||
    bpmn.mimeType !== EXPECTED_BPMN_MIME_TYPE ||
    bpmn.sha256 !== EXPECTED_BPMN_SHA256 ||
    bytes.byteLength === 0 ||
    bytes.byteLength > MAX_BPMN_BYTES ||
    !globalThis.crypto?.subtle
  ) {
    throw new Error('NAC_BPMN_ASSET_INVALID');
  }
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  const actual = Array.from(new Uint8Array(digest))
    .map(value => ("0" + value.toString(16)).slice(-2))
    .join('');
  if (actual !== EXPECTED_BPMN_SHA256) {
    throw new Error('NAC_BPMN_ASSET_INVALID');
  }
}

export function classifyNacBffFailure(error: unknown): NacBffFailureKind {
  if (error instanceof Error && error.message === 'NAC_BFF_ACCESS_DENIED') {
    return 'accessDenied';
  }
  if (error instanceof Error && error.message === 'NAC_BPMN_ASSET_INVALID') {
    return 'invalidAsset';
  }
  return 'unavailable';
}

function parseWorkspaceValue(value: unknown): NacBffWorkspace {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ROOT_KEYS) ||
    value.schemaVersion !== EXPECTED_SCHEMA_VERSION ||
    value.workspaceId !== NAC_BFF_WORKSPACE_ID
  ) {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
  const matter = value.matter;
  if (!isRecord(matter)) {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
  if (!Object.prototype.hasOwnProperty.call(matter, 'bpmn')) {
    throw new Error('NAC_BPMN_ASSET_INVALID');
  }
  if (
    !hasExactKeys(matter, MATTER_KEYS) ||
    matter.matterId !== NAC_BFF_MATTER_ID ||
    matter.businessCaseTypeId !== EXPECTED_BUSINESS_CASE_TYPE_ID ||
    !isBoundedText(matter.displayName, 160) ||
    !isBoundedText(matter.status, 80) ||
    !isIsoTimestamp(matter.deadline) ||
    (matter.accessMode !== 'assigned' && matter.accessMode !== 'deputy') ||
    !Array.isArray(matter.tasks) ||
    matter.tasks.length > 16 ||
    !matter.tasks.every(isTask)
  ) {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
  const bpmn = matter.bpmn;
  if (
    !isRecord(bpmn) ||
    !hasExactKeys(bpmn, BPMN_KEYS) ||
    typeof bpmn.modelKey !== 'string' ||
    typeof bpmn.mimeType !== 'string' ||
    typeof bpmn.sha256 !== 'string' ||
    typeof bpmn.xml !== 'string'
  ) {
    throw new Error('NAC_BPMN_ASSET_INVALID');
  }
  return value as unknown as NacBffWorkspace;
}

function isTask(value: unknown): value is NacBffTask {
  return (
    isRecord(value) &&
    hasExactKeys(value, TASK_KEYS) &&
    isBoundedText(value.taskId, 80) &&
    isBoundedText(value.title, 160) &&
    isBoundedText(value.stepCode, 120) &&
    isBoundedText(value.status, 80) &&
    typeof value.requiresNotaryApproval === 'boolean' &&
    (value.dueAt === null || isIsoTimestamp(value.dueAt))
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, expected: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  return actual.length === expected.length &&
    actual.every((key, index) => key === expected[index]);
}

function isBoundedText(value: unknown, maxLength: number): value is string {
  return typeof value === 'string' && value.length > 0 && value.length <= maxLength;
}

function isIsoTimestamp(value: unknown): value is string {
  if (
    typeof value !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value)
  ) {
    return false;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return false;
  }
  const canonical = /\.\d{3}Z$/.test(value)
    ? value
    : value.slice(0, -1) + '.000Z';
  return parsed.toISOString() === canonical;
}

function createCorrelationId(): string {
  const cryptoApi = globalThis.crypto;
  if (cryptoApi?.randomUUID) {
    return 'spfx-' + cryptoApi.randomUUID();
  }
  const random = Math.random().toString(16).slice(2);
  return 'spfx-' + Date.now().toString(16) + '-' + random;
}
