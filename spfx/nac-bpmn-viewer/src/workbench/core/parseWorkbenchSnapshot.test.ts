import * as fs from 'fs';
import * as path from 'path';
import { createHash, webcrypto } from 'crypto';
import { TextEncoder as NodeTextEncoder } from 'util';

import { parseWorkbenchSnapshotJson } from './parseWorkbenchSnapshot';

const CONFORMANCE = JSON.parse(fs.readFileSync(
  path.resolve(process.cwd(), '..', '..', 'workflows', 'fixtures', 'generic-workbench-conformance.json'),
  'utf8'
));

if (!globalThis.crypto?.subtle) {
  Object.defineProperty(globalThis, 'crypto', { configurable: true, value: webcrypto });
}
if (typeof globalThis.TextEncoder === 'undefined') {
  Object.defineProperty(globalThis, 'TextEncoder', { configurable: true, value: NodeTextEncoder });
}

export const VALID_WORKBENCH_SNAPSHOT = {
  schemaVersion: 'nac.workbench.snapshot/v1',
  generatedAt: '2026-08-01T09:00:00Z',
  expiresAt: '2026-08-01T09:04:00Z',
  producer: { id: 'nac-bff', version: '1.0.0' },
  scope: {
    workspaceId: 'notary_team_01',
    matterId: 'NAC-SYN-MATTER-001',
    purpose: 'view_synthetic_matter_workspace'
  },
  access: {
    mode: 'assigned',
    decisionId: 'access:NAC-SYN-MATTER-001:1',
    decisionVersion: 'policy-v1',
    subjectId: 'actor:synthetic:001',
    role: 'notary',
    workspaceId: 'notary_team_01',
    matterId: 'NAC-SYN-MATTER-001',
    purpose: 'view_synthetic_matter_workspace',
    issuedAt: '2026-08-01T09:00:00Z',
    expiresAt: '2026-08-01T09:04:00Z',
    reason: null
  },
  redaction: {
    status: 'verified',
    policyId: 'nac-redaction',
    policyVersion: 'v1',
    classifierId: 'synthetic-redaction-verifier',
    classifierVersion: 'v1',
    verifiedAt: '2026-08-01T09:00:30Z',
    contentSha256: '1111111111111111111111111111111111111111111111111111111111111111'
  },
  matter: {
    id: 'NAC-SYN-MATTER-001',
    businessCaseTypeId: 'immobilienkaufvertrag',
    title: 'Synthetischer Immobilienkaufvertrag',
    status: 'Entwurf',
    deadline: '2026-08-31T16:00:00Z',
    currentStepId: 'Task_EntwurfAbstimmen',
    modelReference: {
      kind: 'bpmn',
      modelKey: 'Process_immobilienkaufvertrag',
      sha256: '02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0'
    }
  },
  tasks: [{
    id: 'NAC-SYN-TASK-001',
    title: 'Entwurf prüfen',
    status: 'Offen',
    dueAt: null,
    stepId: 'Task_EntwurfAbstimmen',
    requiresApproval: true
  }],
  attention: [{
    id: 'attention:NAC-SYN-TASK-001',
    title: 'Entwurf prüfen',
    reason: 'Notarielle Prüfung erforderlich',
    severity: 'warning',
    dueAt: null,
    taskId: 'NAC-SYN-TASK-001'
  }],
  decisions: [{
    id: 'decision:NAC-SYN-TASK-001',
    title: 'Entwurf notariell prüfen',
    status: 'pending',
    riskClass: 'R4',
    dueAt: null,
    evidenceIds: ['evidence:audit:001'],
    capabilityId: 'matter.decision.review'
  }],
  evidence: [{
    id: 'evidence:model:001',
    title: 'BPMN-Prozessmodell',
    kind: 'model_reference',
    authority: 'non_authoritative',
    sourceSystem: 'nac-git',
    sourceRef: 'Process_immobilienkaufvertrag',
    sha256: '02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0'
  }, {
    id: 'evidence:audit:001',
    title: 'Redigierter Prüfauftrag',
    kind: 'audit',
    authority: 'authoritative',
    sourceSystem: 'nac-bff',
    sourceRef: 'audit:synthetic:001',
    sha256: null
  }],
  capabilities: [{
    id: 'matter.decision.review',
    mode: 'approve',
    decision: 'deny',
    reason: 'Foundation-Slice ist read-only.'
  }],
  agents: [{
    id: 'personal-assistance',
    label: 'Persönliche Assistenz',
    status: 'idle',
    detail: 'Keine Agentenaktion angefordert.'
  }]
};

export function signedWorkbenchSnapshotJson(
  snapshot: Record<string, unknown> = VALID_WORKBENCH_SNAPSHOT as unknown as Record<string, unknown>
): string {
  const { redaction, ...content } = snapshot;
  const contentSha256 = createHash('sha256').update(canonicalJson(content)).digest('hex');
  return JSON.stringify({
    ...snapshot,
    redaction: { ...(redaction as Record<string, unknown>), contentSha256 }
  });
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (value !== null && typeof value === 'object') {
    const item = value as Record<string, unknown>;
    return '{' + Object.keys(item).sort()
      .map(key => JSON.stringify(key) + ':' + canonicalJson(item[key]))
      .join(',') + '}';
  }
  const encoded = JSON.stringify(value);
  if (encoded === undefined) throw new Error('TEST_CANONICAL_JSON_INVALID');
  return encoded;
}

describe('generic workbench runtime contract', () => {
  it('accepts an exact, fresh and referentially valid snapshot', async () => {
    expect(CONFORMANCE.limits.maximum_snapshot_bytes).toBe(128 * 1024);
    expect(VALID_WORKBENCH_SNAPSHOT.generatedAt).toBe(CONFORMANCE.accepted.generated_at);
    expect(VALID_WORKBENCH_SNAPSHOT.access.subjectId)
      .toBe(CONFORMANCE.accepted.access_binding.subject_id);
    const parsed = await parseWorkbenchSnapshotJson(
      signedWorkbenchSnapshotJson(),
      '2026-08-01T09:01:00Z'
    );
    expect(parsed.matter.id).toBe('NAC-SYN-MATTER-001');
  });

  it('requires a verified, current and content-bound redaction attestation', async () => {
    expect(VALID_WORKBENCH_SNAPSHOT.redaction.verifiedAt)
      .toBe(CONFORMANCE.accepted.redaction_verified_at);
    for (const redaction of [
      { ...VALID_WORKBENCH_SNAPSHOT.redaction, status: 'pending' },
      { ...VALID_WORKBENCH_SNAPSHOT.redaction, verifiedAt: '2026-08-01T08:59:59Z' },
      { ...VALID_WORKBENCH_SNAPSHOT.redaction, contentSha256: 'invalid' }
    ]) {
      const changed = { ...VALID_WORKBENCH_SNAPSHOT, redaction };
      await expect(parseWorkbenchSnapshotJson(JSON.stringify(changed), '2026-08-01T09:01:00Z'))
        .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    }
    const signed = JSON.parse(signedWorkbenchSnapshotJson());
    const mutatedContent = { ...signed, matter: { ...signed.matter, status: 'Geändert' } };
    await expect(parseWorkbenchSnapshotJson(JSON.stringify(mutatedContent), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
  });

  it('rejects sensitive display text and non-opaque evidence references', async () => {
    const tokenIdentifier = CONFORMANCE.rejected.token_shaped_identifier_parts.join('');
    const sensitiveTitle = {
      ...VALID_WORKBENCH_SNAPSHOT,
      matter: { ...VALID_WORKBENCH_SNAPSHOT.matter, title: 'Kontakt test@example.invalid' }
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(sensitiveTitle), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    const linkedEvidence = {
      ...VALID_WORKBENCH_SNAPSHOT,
      evidence: VALID_WORKBENCH_SNAPSHOT.evidence.map(item =>
        item.kind === 'model_reference' ? { ...item, sourceRef: 'https://example.invalid/model' } : item)
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(linkedEvidence), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    const tokenEvidence = {
      ...VALID_WORKBENCH_SNAPSHOT,
      evidence: VALID_WORKBENCH_SNAPSHOT.evidence.map(item =>
        item.kind === 'model_reference' ? { ...item, sourceRef: tokenIdentifier } : item)
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(tokenEvidence), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    const tokenMatter = {
      ...VALID_WORKBENCH_SNAPSHOT,
      matter: { ...VALID_WORKBENCH_SNAPSHOT.matter, businessCaseTypeId: tokenIdentifier }
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(tokenMatter), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
  });

  it('counts bounded text in shared UTF-16 code units', async () => {
    const maximum = CONFORMANCE.limits.maximum_text_utf16_code_units;
    const acceptedTitle = '\u{1F600}'.repeat(maximum / 2);
    const accepted = {
      ...VALID_WORKBENCH_SNAPSHOT,
      matter: { ...VALID_WORKBENCH_SNAPSHOT.matter, title: acceptedTitle }
    };
    expect((await parseWorkbenchSnapshotJson(
      signedWorkbenchSnapshotJson(accepted),
      '2026-08-01T09:01:00Z'
    )).matter.title).toBe(acceptedTitle);
    const rejected = {
      ...accepted,
      matter: { ...accepted.matter, title: acceptedTitle + '\u{1F600}' }
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(rejected), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
  });

  it('rejects an expired snapshot and a lease beyond five minutes', async () => {
    await expect(parseWorkbenchSnapshotJson(
      signedWorkbenchSnapshotJson(),
      '2026-08-01T09:04:00Z'
    )).rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    const changed = {
      ...VALID_WORKBENCH_SNAPSHOT,
      access: { ...VALID_WORKBENCH_SNAPSHOT.access, expiresAt: '2026-08-01T09:06:00Z' }
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(changed), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
  });

  it('rejects future generation and access issue times', async () => {
    const futureProjection = {
      ...VALID_WORKBENCH_SNAPSHOT,
      generatedAt: '2026-08-01T09:02:00Z'
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(futureProjection), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    const futureAccess = {
      ...VALID_WORKBENCH_SNAPSHOT,
      access: { ...VALID_WORKBENCH_SNAPSHOT.access, issuedAt: '2026-08-01T09:02:00Z' }
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(futureAccess), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
  });

  it('requires a bounded deputy reason and never accepts a deny snapshot', async () => {
    const deputy = {
      ...VALID_WORKBENCH_SNAPSHOT,
      access: { ...VALID_WORKBENCH_SNAPSHOT.access, mode: 'deputy', reason: 'Vertretung bis 09:04 UTC' }
    };
    expect((await parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(deputy), '2026-08-01T09:01:00Z')).access.mode)
      .toBe('deputy');
    const deny = { ...deputy, access: { ...deputy.access, mode: 'deny' } };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(deny), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
  });

  it('rejects access decisions bound to another actor scope', async () => {
    for (const accessOverride of [
      { workspaceId: 'notary_team_02' },
      { matterId: 'NAC-SYN-MATTER-OTHER' },
      { purpose: 'view_other_matter' }
    ]) {
      const changed = {
        ...VALID_WORKBENCH_SNAPSHOT,
        access: { ...VALID_WORKBENCH_SNAPSHOT.access, ...accessOverride }
      };
      await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(changed), '2026-08-01T09:01:00Z'))
        .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    }
  });

  it('rejects duplicate agent and step identifiers and millisecond timestamps', async () => {
    const duplicateAgent = {
      ...VALID_WORKBENCH_SNAPSHOT,
      agents: [VALID_WORKBENCH_SNAPSHOT.agents[0], {
        ...VALID_WORKBENCH_SNAPSHOT.agents[0], id: CONFORMANCE.rejected.duplicate_agent_id
      }]
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(duplicateAgent), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_AGENT_ID_DUPLICATE');
    const duplicateStep = {
      ...VALID_WORKBENCH_SNAPSHOT,
      tasks: [VALID_WORKBENCH_SNAPSHOT.tasks[0], {
        ...VALID_WORKBENCH_SNAPSHOT.tasks[0],
        id: 'NAC-SYN-TASK-002',
        stepId: CONFORMANCE.rejected.duplicate_step_id
      }]
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(duplicateStep), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    const milliseconds = {
      ...VALID_WORKBENCH_SNAPSHOT,
      generatedAt: CONFORMANCE.rejected.timestamp_with_milliseconds
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(milliseconds), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
  });

  it('rejects invented authority, enabled capability shapes and broken references', async () => {
    const authoritativeModel = {
      ...VALID_WORKBENCH_SNAPSHOT,
      evidence: VALID_WORKBENCH_SNAPSHOT.evidence.map(item =>
        item.kind === 'model_reference' ? { ...item, authority: 'authoritative' } : item)
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(authoritativeModel), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    const enabled = {
      ...VALID_WORKBENCH_SNAPSHOT,
      capabilities: [{ ...VALID_WORKBENCH_SNAPSHOT.capabilities[0], decision: 'allow' }]
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(enabled), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    const broken = {
      ...VALID_WORKBENCH_SNAPSHOT,
      matter: { ...VALID_WORKBENCH_SNAPSHOT.matter, currentStepId: 'missing' }
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(broken), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    const taskIdInsteadOfStepId = {
      ...VALID_WORKBENCH_SNAPSHOT,
      matter: { ...VALID_WORKBENCH_SNAPSHOT.matter, currentStepId: 'NAC-SYN-TASK-001' }
    };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(taskIdInsteadOfStepId), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
  });

  it('rejects unknown keys and oversized input before projection', async () => {
    const unknown = { ...VALID_WORKBENCH_SNAPSHOT, callbackUrl: 'https://example.invalid' };
    await expect(parseWorkbenchSnapshotJson(signedWorkbenchSnapshotJson(unknown), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
    await expect(parseWorkbenchSnapshotJson(' '.repeat(129 * 1024), '2026-08-01T09:01:00Z'))
      .rejects.toThrow('WORKBENCH_SNAPSHOT_INVALID');
  });
});
