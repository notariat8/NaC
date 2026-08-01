import { WorkbenchSnapshot } from '../core/WorkbenchContracts';
import { parseWorkbenchSnapshotJson } from '../core/parseWorkbenchSnapshot';

export const NAC_WORKBENCH_PRODUCER_ID = 'nac-bff';
export const NAC_WORKBENCH_SUPPORTED_ROLES = [
  'notary',
  'notary_clerk',
  'deputy_notary',
  'deputy_clerk'
] as const;

const supportedRoles = new Set<string>(NAC_WORKBENCH_SUPPORTED_ROLES);

export interface NacProjectionScope {
  readonly subjectId: string;
  readonly workspaceId: string;
  readonly matterId: string;
  readonly purpose: string;
}

export async function parseNacWorkbenchProjectionJson(
  text: string,
  nowIso: string,
  expected: NacProjectionScope
): Promise<WorkbenchSnapshot> {
  const snapshot = await parseWorkbenchSnapshotJson(text, nowIso);
  if (
    snapshot.producer.id !== NAC_WORKBENCH_PRODUCER_ID ||
    snapshot.access.subjectId !== expected.subjectId ||
    !supportedRoles.has(snapshot.access.role) ||
    snapshot.scope.workspaceId !== expected.workspaceId ||
    snapshot.scope.matterId !== expected.matterId ||
    snapshot.scope.purpose !== expected.purpose
  ) {
    throw new Error('NAC_WORKBENCH_SCOPE_INVALID');
  }
  return snapshot;
}
