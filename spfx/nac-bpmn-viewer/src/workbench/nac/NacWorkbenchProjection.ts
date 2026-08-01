import { WorkbenchSnapshot } from '../core/WorkbenchContracts';
import { parseWorkbenchSnapshotJson } from '../core/parseWorkbenchSnapshot';

export const NAC_WORKBENCH_PRODUCER_ID = 'nac-bff';

export interface NacProjectionScope {
  readonly subjectId: string;
  readonly role: string;
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
    snapshot.access.role !== expected.role ||
    snapshot.scope.workspaceId !== expected.workspaceId ||
    snapshot.scope.matterId !== expected.matterId ||
    snapshot.scope.purpose !== expected.purpose
  ) {
    throw new Error('NAC_WORKBENCH_SCOPE_INVALID');
  }
  return snapshot;
}
