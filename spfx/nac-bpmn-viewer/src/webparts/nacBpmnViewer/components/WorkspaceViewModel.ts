import type {
  NacBffTask,
  NacBffWorkspace
} from '../services/NacBffClient';

export type TaskFilter = 'all' | 'open' | 'deadline' | 'notary';
export type DeadlineStatus = 'none' | 'overdue' | 'urgent' | 'scheduled';

export interface TaskFilterDefinition {
  readonly id: TaskFilter;
  readonly label: string;
}

export interface DeadlineViewModel {
  readonly kind: DeadlineStatus;
  readonly label: string;
}

export const TASK_FILTERS: readonly TaskFilterDefinition[] = [
  { id: 'all', label: 'Alle Aufgaben' },
  { id: 'open', label: 'Offene Aufgaben' },
  { id: 'deadline', label: 'Aufgaben mit Frist' },
  { id: 'notary', label: 'Aufgaben mit Notarfreigabe' }
];

export const DEADLINE_STATUS_LABELS: Readonly<Record<DeadlineStatus, string>> = {
  none: 'Keine Frist',
  overdue: 'Frist überschritten',
  urgent: 'Frist innerhalb von sieben Tagen',
  scheduled: 'Frist geplant'
};

const URGENT_WINDOW_MS = 7 * 24 * 60 * 60 * 1000;
const ISO_TIMESTAMP_PATTERN =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/;

type AccessMode = NacBffWorkspace['matter']['accessMode'];

export function filterTasks(
  tasks: readonly NacBffTask[],
  filter: TaskFilter
): readonly NacBffTask[] {
  switch (filter) {
    case 'all':
      return tasks.slice();
    case 'open':
      return tasks.filter(task => normalizeTaskStatus(task.status) === 'open');
    case 'deadline':
      return tasks.filter(task => task.dueAt !== null);
    case 'notary':
      return tasks.filter(task => task.requiresNotaryApproval);
  }
}

export function getDeadlineStatus(
  dueAt: NacBffTask['dueAt'],
  referenceIso: string
): DeadlineStatus {
  if (dueAt === null) {
    return 'none';
  }

  const referenceTime = parseIsoTimestamp(referenceIso);
  if (referenceTime === undefined) {
    throw new Error('NAC_DEADLINE_REFERENCE_INVALID');
  }

  const dueTime = parseIsoTimestamp(dueAt);
  if (dueTime === undefined) {
    throw new Error('NAC_TASK_DEADLINE_INVALID');
  }

  const remainingMs = dueTime - referenceTime;
  if (remainingMs < 0) {
    return 'overdue';
  }
  if (remainingMs <= URGENT_WINDOW_MS) {
    return 'urgent';
  }
  return 'scheduled';
}

export function classifyDeadline(
  dueAt: NacBffTask['dueAt'],
  referenceIso: string
): DeadlineViewModel {
  const kind = getDeadlineStatus(dueAt, referenceIso);
  return {
    kind,
    label: DEADLINE_STATUS_LABELS[kind]
  };
}

export function getAccessModeLabel(accessMode: AccessMode): string {
  return accessMode === 'deputy'
    ? 'Aktive Vertretung (deputy)'
    : 'Zugeordnetes Team (assigned)';
}

function normalizeTaskStatus(status: string): 'open' | 'other' {
  const normalized = status.trim().toLowerCase();
  return normalized === 'offen' || normalized === 'open' ? 'open' : 'other';
}

function parseIsoTimestamp(value: string): number | undefined {
  if (!ISO_TIMESTAMP_PATTERN.test(value)) {
    return undefined;
  }

  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) {
    return undefined;
  }

  const normalizedInput = value.includes('.')
    ? value
    : value.slice(0, -1) + '.000Z';
  return new Date(parsed).toISOString() === normalizedInput ? parsed : undefined;
}
