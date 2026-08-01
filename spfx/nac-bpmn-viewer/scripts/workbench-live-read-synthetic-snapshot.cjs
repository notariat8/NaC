'use strict';

const crypto = require('crypto');

const snapshot = {
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
    contentSha256: ''
  },
  matter: {
    id: 'NAC-SYN-MATTER-001',
    businessCaseTypeId: 'immobilienkaufvertrag',
    title: 'Synthetischer Immobilienkaufvertrag mit langer Bezeichnung für schmale Arbeitsbereiche',
    status: 'Entwurf',
    deadline: '2026-08-31T16:00:00Z',
    currentStepId: null,
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
  }, {
    id: 'NAC-SYN-TASK-002',
    title: 'Abschlussfrist überwachen',
    status: 'Offen',
    dueAt: '2026-08-31T16:00:00Z',
    stepId: 'Task_FristUeberwachen',
    requiresApproval: false
  }],
  attention: [],
  decisions: [],
  evidence: [{
    id: 'evidence:model:001',
    title: 'BPMN-Prozessmodell',
    kind: 'model_reference',
    authority: 'non_authoritative',
    sourceSystem: 'nac-git',
    sourceRef: 'Process_immobilienkaufvertrag',
    sha256: '02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0'
  }],
  capabilities: [],
  agents: []
};

function canonicalJson(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (value !== null && typeof value === 'object') {
    return '{' + Object.keys(value).sort(compareUnicodeCodePoints)
      .map(key => JSON.stringify(key) + ':' + canonicalJson(value[key]))
      .join(',') + '}';
  }
  return JSON.stringify(value);
}

function compareUnicodeCodePoints(left, right) {
  const leftPoints = Array.from(left, value => value.codePointAt(0));
  const rightPoints = Array.from(right, value => value.codePointAt(0));
  const length = Math.min(leftPoints.length, rightPoints.length);
  for (let index = 0; index < length; index += 1) {
    if (leftPoints[index] !== rightPoints[index]) return leftPoints[index] - rightPoints[index];
  }
  return leftPoints.length - rightPoints.length;
}

const { redaction: _redaction, ...content } = snapshot;
snapshot.redaction.contentSha256 = crypto.createHash('sha256')
  .update(canonicalJson(content))
  .digest('hex');

module.exports = snapshot;
