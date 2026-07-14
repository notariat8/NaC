import { AadHttpClient, AadHttpClientFactory } from '@microsoft/sp-http';
import type { HttpClientResponse } from '@microsoft/sp-http';

export const NAC_BFF_RESOURCE_URI = 'api://funktion8.de/nac-bff';
export const NAC_BFF_SCOPE = 'Matter.Read';
export const NAC_BFF_BASE_URL = 'https://func-nac-bff-test-funktion8.azurewebsites.net';
export const NAC_BFF_WORKSPACE_ID = 'notary_team_01';
export const NAC_BFF_MATTER_ID = 'NAC-SYN-MATTER-001';
export const NAC_BFF_PURPOSE = 'view_synthetic_matter_workspace';

const EXPECTED_SCHEMA_VERSION = 'nac.m365-test-environment-workspace/v0.1';
const EXPECTED_BPMN_MODEL_KEY = 'NAC_SYN_MATTER_001';
const EXPECTED_BPMN_SHA256 = '1dd7203a515d434949ef9300d5738cf7318d842119ec689aaa7ba1f9a7a6d167';
const EXPECTED_BUSINESS_CASE_TYPE_ID = 'immobilienkaufvertrag';
const MAX_RESPONSE_BYTES = 64 * 1024;

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
const BPMN_KEYS = ['modelKey', 'sha256'];
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
      readonly sha256: typeof EXPECTED_BPMN_SHA256;
    };
    readonly accessMode: 'assigned' | 'deputy';
  };
}

export async function loadNacBffWorkspace(
  clientFactory: AadHttpClientFactory,
  signal: AbortSignal
): Promise<NacBffWorkspace> {
  const client = await clientFactory.getClient(NAC_BFF_RESOURCE_URI);
  const path = '/v1/workspaces/' + NAC_BFF_WORKSPACE_ID + '/matters/' + NAC_BFF_MATTER_ID;
  const url = NAC_BFF_BASE_URL + path + '?purpose=' + encodeURIComponent(NAC_BFF_PURPOSE);
  const response = await client.get(url, AadHttpClient.configurations.v1, {
    signal,
    headers: {
      Accept: 'application/json',
      'X-Correlation-ID': createCorrelationId()
    }
  });
  return parseWorkspaceResponse(response);
}

export async function parseWorkspaceResponse(
  response: HttpClientResponse
): Promise<NacBffWorkspace> {
  if (!response.ok) {
    throw new Error('NAC_BFF_REQUEST_REJECTED');
  }
  const contentLength = response.headers.get('content-length');
  if (
    contentLength !== null &&
    (!/^\d+$/.test(contentLength) || Number(contentLength) > MAX_RESPONSE_BYTES)
  ) {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
  const text = await response.text();
  if (new TextEncoder().encode(text).byteLength > MAX_RESPONSE_BYTES) {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
  if (!isWorkspace(value)) {
    throw new Error('NAC_BFF_RESPONSE_INVALID');
  }
  return value;
}

export async function verifyBpmnAsset(
  workspace: NacBffWorkspace,
  bpmnXml: string,
  declaredSha256: string
): Promise<void> {
  if (
    declaredSha256 !== EXPECTED_BPMN_SHA256 ||
    workspace.matter.bpmn.sha256 !== declaredSha256 ||
    !globalThis.crypto?.subtle
  ) {
    throw new Error('NAC_BPMN_ASSET_INVALID');
  }
  const bytes = new TextEncoder().encode(bpmnXml);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  const actual = Array.from(new Uint8Array(digest))
    .map(value => ("0" + value.toString(16)).slice(-2))
    .join('');
  if (actual !== declaredSha256) {
    throw new Error('NAC_BPMN_ASSET_INVALID');
  }
}

function isWorkspace(value: unknown): value is NacBffWorkspace {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ROOT_KEYS) ||
    value.schemaVersion !== EXPECTED_SCHEMA_VERSION ||
    value.workspaceId !== NAC_BFF_WORKSPACE_ID
  ) {
    return false;
  }
  const matter = value.matter;
  if (
    !isRecord(matter) ||
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
    return false;
  }
  const bpmn = matter.bpmn;
  return (
    isRecord(bpmn) &&
    hasExactKeys(bpmn, BPMN_KEYS) &&
    bpmn.modelKey === EXPECTED_BPMN_MODEL_KEY &&
    bpmn.sha256 === EXPECTED_BPMN_SHA256
  );
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
