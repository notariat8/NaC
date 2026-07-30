import type { NacBffTask } from '../services/NacBffClient';
import {
  DEADLINE_STATUS_LABELS,
  TASK_FILTERS,
  classifyDeadline,
  filterTasks,
  getAccessModeLabel,
  getDeadlineStatus
} from './WorkspaceViewModel';

const referenceIso = '2026-08-01T12:00:00.000Z';

function task(
  taskId: string,
  status: string,
  dueAt: NacBffTask['dueAt'],
  requiresNotaryApproval: boolean = false
): NacBffTask {
  return {
    taskId,
    title: 'Synthetische Aufgabe ' + taskId,
    stepCode: 'Task_' + taskId,
    status,
    requiresNotaryApproval,
    dueAt
  };
}

describe('Workspace view model', () => {
  const tasks: readonly NacBffTask[] = [
    task('open-deadline', '  OFFEN ', '2026-08-02T12:00:00Z'),
    task('open-notary', 'Open', null, true),
    task('closed-deadline-notary', 'Erledigt', '2026-08-20T12:00:00Z', true),
    task('closed', 'Geschlossen', null)
  ];

  it('provides accessible German labels for every task filter', () => {
    expect(TASK_FILTERS).toEqual([
      { id: 'all', label: 'Alle Aufgaben' },
      { id: 'open', label: 'Offene Aufgaben' },
      { id: 'deadline', label: 'Aufgaben mit Frist' },
      { id: 'notary', label: 'Aufgaben mit Notarfreigabe' }
    ]);
  });

  it.each([
    ['all', ['open-deadline', 'open-notary', 'closed-deadline-notary', 'closed']],
    ['open', ['open-deadline', 'open-notary']],
    ['deadline', ['open-deadline', 'closed-deadline-notary']],
    ['notary', ['open-notary', 'closed-deadline-notary']]
  ] as const)('applies the %s task filter', (filter, expectedTaskIds) => {
    expect(filterTasks(tasks, filter).map(item => item.taskId)).toEqual(expectedTaskIds);
  });

  it('classifies deadline boundaries from the explicit reference timestamp', () => {
    expect(getDeadlineStatus('2026-08-01T11:59:59.999Z', referenceIso))
      .toBe('overdue');
    expect(getDeadlineStatus('2026-08-01T12:00:00.000Z', referenceIso))
      .toBe('urgent');
    expect(getDeadlineStatus('2026-08-08T12:00:00.000Z', referenceIso))
      .toBe('urgent');
    expect(getDeadlineStatus('2026-08-08T12:00:00.001Z', referenceIso))
      .toBe('scheduled');
  });

  it('uses none for a null deadline', () => {
    expect(getDeadlineStatus(null, referenceIso)).toBe('none');
  });

  it('fails closed for an invalid reference timestamp', () => {
    expect(() => getDeadlineStatus(
      '2026-08-02T12:00:00Z',
      'not-an-iso-timestamp'
    )).toThrow('NAC_DEADLINE_REFERENCE_INVALID');
  });

  it('fails closed for an invalid non-null task deadline', () => {
    expect(() => getDeadlineStatus(
      '2026-02-30T12:00:00Z',
      referenceIso
    )).toThrow('NAC_TASK_DEADLINE_INVALID');
  });

  it('provides accessible German labels for every deadline status', () => {
    expect(DEADLINE_STATUS_LABELS).toEqual({
      none: 'Keine Frist',
      overdue: 'Frist überschritten',
      urgent: 'Frist innerhalb von sieben Tagen',
      scheduled: 'Frist geplant'
    });
    expect(classifyDeadline('2026-08-01T11:59:59.999Z', referenceIso)).toEqual({
      kind: 'overdue',
      label: 'Frist überschritten'
    });
  });

  it('derives the assigned and deputy role labels from accessMode', () => {
    expect(getAccessModeLabel('assigned')).toBe('Zugeordnetes Team (assigned)');
    expect(getAccessModeLabel('deputy')).toBe('Aktive Vertretung (deputy)');
  });
});
