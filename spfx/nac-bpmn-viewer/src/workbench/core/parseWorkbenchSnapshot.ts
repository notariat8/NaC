import {
  WORKBENCH_SNAPSHOT_SCHEMA_VERSION,
  WorkbenchSnapshot
} from './WorkbenchContracts';

const MAX_SNAPSHOT_BYTES = 128 * 1024;
const MAX_ITEMS = 64;
const MAX_TEXT = 256;
const MAX_LEASE_MS = 5 * 60 * 1000;
const SHA256 = /^[a-f0-9]{64}$/;
const ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const SENSITIVE_TEXT = /(?:https?:\/\/|Bearer\s+|(?:access_token|refresh_token|id_token|client_secret|authorization_code|sig|sv|se|sp|spr)=|(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,}|eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})/i;

const ROOT_KEYS = ['access', 'agents', 'attention', 'capabilities', 'decisions', 'evidence', 'expiresAt', 'generatedAt', 'matter', 'producer', 'redaction', 'schemaVersion', 'scope', 'tasks'];
const PRODUCER_KEYS = ['id', 'version'];
const SCOPE_KEYS = ['matterId', 'purpose', 'workspaceId'];
const ACCESS_KEYS = ['decisionId', 'decisionVersion', 'expiresAt', 'issuedAt', 'matterId', 'mode', 'purpose', 'reason', 'role', 'subjectId', 'workspaceId'];
const REDACTION_KEYS = ['classifierId', 'classifierVersion', 'contentSha256', 'policyId', 'policyVersion', 'status', 'verifiedAt'];
const MATTER_KEYS = ['businessCaseTypeId', 'currentStepId', 'deadline', 'id', 'modelReference', 'status', 'title'];
const MODEL_KEYS = ['kind', 'modelKey', 'sha256'];
const TASK_KEYS = ['dueAt', 'id', 'requiresApproval', 'status', 'stepId', 'title'];
const ATTENTION_KEYS = ['dueAt', 'id', 'reason', 'severity', 'taskId', 'title'];
const DECISION_KEYS = ['capabilityId', 'dueAt', 'evidenceIds', 'id', 'riskClass', 'status', 'title'];
const EVIDENCE_KEYS = ['authority', 'id', 'kind', 'sha256', 'sourceRef', 'sourceSystem', 'title'];
const CAPABILITY_KEYS = ['decision', 'id', 'mode', 'reason'];
const AGENT_KEYS = ['detail', 'id', 'label', 'status'];

export async function parseWorkbenchSnapshotJson(text: string, nowIso: string): Promise<WorkbenchSnapshot> {
  if (utf8ByteLength(text) > MAX_SNAPSHOT_BYTES) fail();
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    fail();
  }
  const snapshot = parseWorkbenchSnapshot(value, nowIso);
  await verifyRedactionContentBinding(snapshot);
  return snapshot;
}

function utf8ByteLength(value: string): number {
  let bytes = 0;
  for (let index = 0; index < value.length; index += 1) {
    const codeUnit = value.charCodeAt(index);
    if (codeUnit <= 0x7f) bytes += 1;
    else if (codeUnit <= 0x7ff) bytes += 2;
    else if (codeUnit >= 0xd800 && codeUnit <= 0xdbff && index + 1 < value.length &&
        value.charCodeAt(index + 1) >= 0xdc00 && value.charCodeAt(index + 1) <= 0xdfff) {
      bytes += 4;
      index += 1;
    } else bytes += 3;
    if (bytes > MAX_SNAPSHOT_BYTES) return bytes;
  }
  return bytes;
}

function parseWorkbenchSnapshot(value: unknown, nowIso: string): WorkbenchSnapshot {
  const now = timestamp(nowIso);
  if (!record(value) || !exact(value, ROOT_KEYS) || value.schemaVersion !== WORKBENCH_SNAPSHOT_SCHEMA_VERSION) fail();
  const generatedAt = timestamp(value.generatedAt);
  const expiresAt = timestamp(value.expiresAt);
  if (generatedAt > now || expiresAt <= now || expiresAt <= generatedAt || expiresAt - generatedAt > MAX_LEASE_MS) fail();
  if (!record(value.producer) || !exact(value.producer, PRODUCER_KEYS) || !id(value.producer.id) || !id(value.producer.version)) fail();
  if (!record(value.scope) || !exact(value.scope, SCOPE_KEYS) || !id(value.scope.workspaceId) || !id(value.scope.matterId) || !id(value.scope.purpose)) fail();
  validateAccess(value.access, value.scope, now, generatedAt, expiresAt);
  validateRedaction(value.redaction, generatedAt, now);
  validateMatter(value.matter, value.scope.matterId);
  const tasks = array(value.tasks, validateTask);
  const attention = array(value.attention, validateAttention);
  const decisions = array(value.decisions, validateDecision);
  const evidence = array(value.evidence, validateEvidence);
  const capabilities = array(value.capabilities, validateCapability);
  const agents = array(value.agents, validateAgent);
  unique(tasks, 'task');
  unique(attention, 'attention');
  unique(decisions, 'decision');
  unique(evidence, 'evidence');
  unique(capabilities, 'capability');
  unique(agents, 'agent');
  const taskIds = new Set(tasks.map(item => item.id));
  const stepIds = new Set(tasks.map(item => item.stepId));
  if (stepIds.size !== tasks.length) fail();
  const evidenceIds = new Set(evidence.map(item => item.id));
  const capabilityIds = new Set(capabilities.map(item => item.id));
  const matter = value.matter as Record<string, unknown>;
  if (matter.currentStepId !== null && !stepIds.has(String(matter.currentStepId))) fail();
  attention.forEach(item => { if (item.taskId !== null && !taskIds.has(String(item.taskId))) fail(); });
  decisions.forEach(item => {
    if (!capabilityIds.has(String(item.capabilityId))) fail();
    const decisionEvidenceIds = item.evidenceIds as unknown[];
    decisionEvidenceIds.forEach(evidenceId => { if (!evidenceIds.has(String(evidenceId))) fail(); });
  });
  const model = matter.modelReference as Record<string, unknown>;
  if (evidence.some(item => item.kind === 'model_reference' && item.authority !== 'non_authoritative')) fail();
  if (!evidence.some(item => item.kind === 'model_reference' && item.sha256 === model.sha256)) fail();
  return value as unknown as WorkbenchSnapshot;
}

function validateRedaction(value: unknown, generatedAt: number, now: number): void {
  if (!record(value) || !exact(value, REDACTION_KEYS) || value.status !== 'verified' ||
      !id(value.policyId) || !id(value.policyVersion) || !id(value.classifierId) ||
      !id(value.classifierVersion) || typeof value.contentSha256 !== 'string' ||
      !SHA256.test(value.contentSha256)) fail();
  const verifiedAt = timestamp(value.verifiedAt);
  if (verifiedAt < generatedAt || verifiedAt > now) fail();
}

async function verifyRedactionContentBinding(snapshot: WorkbenchSnapshot): Promise<void> {
  if (!globalThis.crypto?.subtle) fail();
  const content: Record<string, unknown> = { ...snapshot };
  delete content.redaction;
  const bytes = new TextEncoder().encode(canonicalJson(content));
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  const actual = Array.from(new Uint8Array(digest))
    .map(value => value.toString(16).padStart(2, '0'))
    .join('');
  if (actual !== snapshot.redaction.contentSha256) fail();
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (record(value)) {
    return '{' + Object.keys(value).sort()
      .map(key => JSON.stringify(key) + ':' + canonicalJson(value[key]))
      .join(',') + '}';
  }
  const encoded = JSON.stringify(value);
  if (encoded === undefined) fail();
  return encoded;
}

function validateAccess(value: unknown, scope: unknown, now: number, generatedAt: number, projectionExpiresAt: number): void {
  if (!record(value) || !record(scope) || !exact(value, ACCESS_KEYS) ||
      !['assigned', 'deputy'].includes(String(value.mode)) || !id(value.decisionId) ||
      !id(value.decisionVersion) || !id(value.subjectId) || !id(value.role) ||
      !id(value.workspaceId) || !id(value.matterId) || !id(value.purpose) ||
      value.workspaceId !== scope.workspaceId || value.matterId !== scope.matterId ||
      value.purpose !== scope.purpose) fail();
  const issuedAt = timestamp(value.issuedAt);
  const expiresAt = timestamp(value.expiresAt);
  if (
    issuedAt > now ||
    issuedAt > generatedAt ||
    expiresAt <= issuedAt ||
    expiresAt <= now ||
    expiresAt > projectionExpiresAt ||
    expiresAt - issuedAt > MAX_LEASE_MS
  ) fail();
  if (value.mode === 'deputy' ? !displayText(value.reason) : value.reason !== null) fail();
}

function validateMatter(value: unknown, matterId: unknown): void {
  if (!record(value) || !exact(value, MATTER_KEYS) || value.id !== matterId || !id(value.id) || !id(value.businessCaseTypeId) || !displayText(value.title) || !displayText(value.status) || !nullableTimestamp(value.deadline) || (value.currentStepId !== null && !id(value.currentStepId))) fail();
  const model = value.modelReference;
  if (!record(model) || !exact(model, MODEL_KEYS) || model.kind !== 'bpmn' || !id(model.modelKey) || typeof model.sha256 !== 'string' || !SHA256.test(model.sha256)) fail();
}

function validateTask(value: unknown): asserts value is Record<string, unknown> {
  if (!record(value) || !exact(value, TASK_KEYS) || !id(value.id) || !displayText(value.title) || !displayText(value.status) || !id(value.stepId) || !nullableTimestamp(value.dueAt) || typeof value.requiresApproval !== 'boolean') fail();
}

function validateAttention(value: unknown): asserts value is Record<string, unknown> {
  if (!record(value) || !exact(value, ATTENTION_KEYS) || !id(value.id) || !displayText(value.title) || !displayText(value.reason) || !['info', 'warning', 'critical'].includes(String(value.severity)) || !nullableTimestamp(value.dueAt) || (value.taskId !== null && !id(value.taskId))) fail();
}

function validateDecision(value: unknown): asserts value is Record<string, unknown> {
  if (!record(value) || !exact(value, DECISION_KEYS) || !id(value.id) || !displayText(value.title) || !['pending', 'approved', 'rejected', 'expired'].includes(String(value.status)) || !['R0', 'R1', 'R2', 'R3', 'R4'].includes(String(value.riskClass)) || !nullableTimestamp(value.dueAt) || !id(value.capabilityId) || !Array.isArray(value.evidenceIds) || value.evidenceIds.length > MAX_ITEMS || !value.evidenceIds.every(id)) fail();
}

function validateEvidence(value: unknown): asserts value is Record<string, unknown> {
  if (!record(value) || !exact(value, EVIDENCE_KEYS) || !id(value.id) || !displayText(value.title) || !['model_reference', 'supporting', 'audit', 'immutable'].includes(String(value.kind)) || !['non_authoritative', 'authoritative'].includes(String(value.authority)) || !opaqueId(value.sourceSystem) || !opaqueId(value.sourceRef) || (value.sha256 !== null && (typeof value.sha256 !== 'string' || !SHA256.test(value.sha256)))) fail();
}

function validateCapability(value: unknown): asserts value is Record<string, unknown> {
  if (!record(value) || !exact(value, CAPABILITY_KEYS) || !id(value.id) || !['read', 'propose', 'approve', 'execute'].includes(String(value.mode)) || value.decision !== 'deny' || !displayText(value.reason)) fail();
}

function validateAgent(value: unknown): asserts value is Record<string, unknown> {
  if (!record(value) || !exact(value, AGENT_KEYS) || !id(value.id) || !displayText(value.label) || !['idle', 'working', 'waiting', 'blocked'].includes(String(value.status)) || !displayText(value.detail)) fail();
}

function array(value: unknown, validator: (item: unknown) => asserts item is Record<string, unknown>): Record<string, unknown>[] {
  if (!Array.isArray(value) || value.length > MAX_ITEMS) fail();
  value.forEach(validator);
  return value;
}

function unique(items: Record<string, unknown>[], label: string): void {
  const ids = new Set(items.map(item => item.id));
  if (ids.size !== items.length) throw new Error(`WORKBENCH_${label.toUpperCase()}_ID_DUPLICATE`);
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function exact(value: Record<string, unknown>, keys: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  return actual.length === keys.length && actual.every((key, index) => key === keys[index]);
}

function id(value: unknown): value is string {
  return typeof value === 'string' && ID.test(value) && !SENSITIVE_TEXT.test(value);
}

function opaqueId(value: unknown): value is string {
  return id(value) && !SENSITIVE_TEXT.test(value);
}

function text(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= MAX_TEXT;
}

function displayText(value: unknown): value is string {
  return text(value) && !SENSITIVE_TEXT.test(value);
}

function nullableTimestamp(value: unknown): boolean {
  return value === null || validTimestamp(value);
}

function validTimestamp(value: unknown): boolean {
  try {
    timestamp(value);
    return true;
  } catch {
    return false;
  }
}

function timestamp(value: unknown): number {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value)) fail();
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) fail();
  const canonical = value.slice(0, -1) + '.000Z';
  if (new Date(parsed).toISOString() !== canonical) fail();
  return parsed;
}

function fail(): never {
  throw new Error('WORKBENCH_SNAPSHOT_INVALID');
}
