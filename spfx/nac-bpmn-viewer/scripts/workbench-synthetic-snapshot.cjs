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
    contentSha256: '1111111111111111111111111111111111111111111111111111111111111111'
  },
  matter: {
    id: 'NAC-SYN-MATTER-001',
    businessCaseTypeId: 'immobilienkaufvertrag',
    title: 'Synthetischer Immobilienkaufvertrag mit bewusst langer, aber begrenzter Bezeichnung für die visuelle Prüfung schmaler Arbeitsbereiche',
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
    id: 'NAC-SYN-TASK-001', title: 'Entwurf prüfen', status: 'Offen', dueAt: null,
    stepId: 'Task_EntwurfAbstimmen', requiresApproval: true
  }, {
    id: 'NAC-SYN-TASK-002', title: 'Abschlussfrist überwachen', status: 'Offen',
    dueAt: '2026-08-31T16:00:00Z', stepId: 'Task_FristUeberwachen', requiresApproval: false
  }],
  attention: [{
    id: 'attention:NAC-SYN-TASK-001', title: 'Entwurf prüfen',
    reason: 'Notarielle Prüfung erforderlich', severity: 'warning', dueAt: null,
    taskId: 'NAC-SYN-TASK-001'
  }, {
    id: 'attention:NAC-SYN-TASK-002', title: 'Abschlussfrist überwachen',
    reason: 'Frist serverseitig priorisiert', severity: 'info', dueAt: '2026-08-31T16:00:00Z',
    taskId: 'NAC-SYN-TASK-002'
  }],
  decisions: [{
    id: 'decision:NAC-SYN-TASK-001', title: 'Entwurf notariell prüfen', status: 'pending',
    riskClass: 'R4', dueAt: null, evidenceIds: ['evidence:audit:001'],
    capabilityId: 'matter.decision.review'
  }],
  evidence: [{
    id: 'evidence:model:001', title: 'BPMN-Prozessmodell', kind: 'model_reference',
    authority: 'non_authoritative', sourceSystem: 'nac-git',
    sourceRef: 'Process_immobilienkaufvertrag',
    sha256: '02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0'
  }, {
    id: 'evidence:audit:001', title: 'Redigierter Prüfauftrag', kind: 'audit',
    authority: 'authoritative', sourceSystem: 'nac-bff', sourceRef: 'audit:synthetic:001',
    sha256: null
  }],
  capabilities: [{
    id: 'matter.decision.review', mode: 'approve', decision: 'deny',
    reason: 'Foundation-Slice ist read-only und führt keine Aktion im Browser aus.'
  }],
  agents: [{
    id: 'personal-assistance', label: 'Persönliche Assistenz', status: 'idle',
    detail: 'Keine Agentenaktion angefordert; sämtliche Hinweise stammen aus der redigierten Serverprojektion.'
  }]
};

function canonicalJson(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalJson).join(',') + ']';
  if (value !== null && typeof value === 'object') {
    return '{' + Object.keys(value).sort()
      .map(key => JSON.stringify(key) + ':' + canonicalJson(value[key]))
      .join(',') + '}';
  }
  return JSON.stringify(value);
}

const { redaction: _redaction, ...content } = snapshot;
snapshot.redaction.contentSha256 = crypto.createHash('sha256')
  .update(canonicalJson(content))
  .digest('hex');

module.exports = snapshot;
