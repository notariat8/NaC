/* eslint-disable @rushstack/no-new-null -- The exact JSON wire contract uses explicit null values. */

export const WORKBENCH_SNAPSHOT_SCHEMA_VERSION = 'nac.workbench.snapshot/v1' as const;

export type WorkbenchViewId = 'today' | 'matter' | 'decisions';
export type WorkbenchRiskClass = 'R0' | 'R1' | 'R2' | 'R3' | 'R4';
export type WorkbenchCapabilityMode = 'read' | 'propose' | 'approve' | 'execute';
export type WorkbenchAttentionSeverity = 'info' | 'warning' | 'critical';
export type WorkbenchEvidenceKind = 'model_reference' | 'supporting' | 'audit' | 'immutable';

export interface WorkbenchProducer {
  readonly id: string;
  readonly version: string;
}

export interface WorkbenchScope {
  readonly workspaceId: string;
  readonly matterId: string;
  readonly purpose: string;
}

export interface WorkbenchAccessDecision {
  readonly mode: 'assigned' | 'deputy';
  readonly decisionId: string;
  readonly decisionVersion: string;
  readonly subjectId: string;
  readonly role: string;
  readonly workspaceId: string;
  readonly matterId: string;
  readonly purpose: string;
  readonly issuedAt: string;
  readonly expiresAt: string;
  readonly reason: string | null;
}

export interface WorkbenchRedactionAttestation {
  readonly status: 'verified';
  readonly policyId: string;
  readonly policyVersion: string;
  readonly classifierId: string;
  readonly classifierVersion: string;
  readonly verifiedAt: string;
  readonly contentSha256: string;
}

export interface WorkbenchModelReference {
  readonly kind: 'bpmn';
  readonly modelKey: string;
  readonly sha256: string;
}

export interface WorkbenchMatter {
  readonly id: string;
  readonly businessCaseTypeId: string;
  readonly title: string;
  readonly status: string;
  readonly deadline: string | null;
  readonly currentStepId: string | null;
  readonly modelReference: WorkbenchModelReference;
}

export interface WorkbenchTask {
  readonly id: string;
  readonly title: string;
  readonly status: string;
  readonly dueAt: string | null;
  readonly stepId: string;
  readonly requiresApproval: boolean;
}

export interface WorkbenchAttentionItem {
  readonly id: string;
  readonly title: string;
  readonly reason: string;
  readonly severity: WorkbenchAttentionSeverity;
  readonly dueAt: string | null;
  readonly taskId: string | null;
}

export interface WorkbenchEvidenceRef {
  readonly id: string;
  readonly title: string;
  readonly kind: WorkbenchEvidenceKind;
  readonly authority: 'non_authoritative' | 'authoritative';
  readonly sourceSystem: string;
  readonly sourceRef: string;
  readonly sha256: string | null;
}

export interface WorkbenchDecision {
  readonly id: string;
  readonly title: string;
  readonly status: 'pending' | 'approved' | 'rejected' | 'expired';
  readonly riskClass: WorkbenchRiskClass;
  readonly dueAt: string | null;
  readonly evidenceIds: readonly string[];
  readonly capabilityId: string;
}

export interface WorkbenchCapability {
  readonly id: string;
  readonly mode: WorkbenchCapabilityMode;
  readonly decision: 'deny';
  readonly reason: string;
}

export interface WorkbenchAgentStatus {
  readonly id: string;
  readonly label: string;
  readonly status: 'idle' | 'working' | 'waiting' | 'blocked';
  readonly detail: string;
}

export interface WorkbenchSnapshot {
  readonly schemaVersion: typeof WORKBENCH_SNAPSHOT_SCHEMA_VERSION;
  readonly generatedAt: string;
  readonly expiresAt: string;
  readonly producer: WorkbenchProducer;
  readonly scope: WorkbenchScope;
  readonly access: WorkbenchAccessDecision;
  readonly redaction: WorkbenchRedactionAttestation;
  readonly matter: WorkbenchMatter;
  readonly tasks: readonly WorkbenchTask[];
  readonly attention: readonly WorkbenchAttentionItem[];
  readonly decisions: readonly WorkbenchDecision[];
  readonly evidence: readonly WorkbenchEvidenceRef[];
  readonly capabilities: readonly WorkbenchCapability[];
  readonly agents: readonly WorkbenchAgentStatus[];
}
