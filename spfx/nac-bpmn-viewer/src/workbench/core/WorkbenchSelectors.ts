import { WorkbenchSnapshot } from './WorkbenchContracts';

export function activeMatterAttention(snapshot: WorkbenchSnapshot): WorkbenchSnapshot['attention'] {
  return [...snapshot.attention].sort((left, right) => {
    const severity = { critical: 0, warning: 1, info: 2 };
    const difference = severity[left.severity] - severity[right.severity];
    if (difference !== 0) return difference;
    return (left.dueAt ?? '9999').localeCompare(right.dueAt ?? '9999') || left.id.localeCompare(right.id);
  });
}

export function isSnapshotFresh(snapshot: WorkbenchSnapshot, nowIso: string): boolean {
  const now = Date.parse(nowIso);
  return isSnapshotFreshAt(snapshot, now);
}

export function isSnapshotFreshAt(snapshot: WorkbenchSnapshot, now: number): boolean {
  return Number.isFinite(now) && now < Date.parse(snapshot.expiresAt) && now < Date.parse(snapshot.access.expiresAt);
}

export function snapshotEffectiveExpiry(snapshot: WorkbenchSnapshot): number {
  return Math.min(Date.parse(snapshot.expiresAt), Date.parse(snapshot.access.expiresAt));
}
