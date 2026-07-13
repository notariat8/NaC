import { sampleApprovedBpmnXml } from './sampleBpmn';

export interface SyntheticTask {
  readonly id: string;
  readonly title: string;
  readonly stepCode: string;
  readonly status: 'Offen';
  readonly dueAt: string | undefined;
  readonly dueLabel: string;
}

export interface SyntheticWorkspaceFixture {
  readonly schemaVersion: 'nac.spfx-synthetic-workspace/v0.1';
  readonly workspaceId: 'notary_team_01';
  readonly matterId: 'NAC-SYN-MATTER-001';
  readonly matterLabel: string;
  readonly businessCaseType: string;
  readonly lifecycleStatus: string;
  readonly stageLabel: string;
  readonly deadlineLabel: string;
  readonly assignedRole: string;
  readonly tasks: readonly SyntheticTask[];
  readonly bpmnProcessKey: 'NAC_SYN_MATTER_001';
  readonly bpmnSha256: string;
  readonly bpmnXml: string;
  readonly containsMatterData: false;
  readonly source: 'package_fixture';
}

export const syntheticWorkspaceFixture: SyntheticWorkspaceFixture = {
  schemaVersion: 'nac.spfx-synthetic-workspace/v0.1',
  workspaceId: 'notary_team_01',
  matterId: 'NAC-SYN-MATTER-001',
  matterLabel: 'Synthetische Testakte NAC-SYN-MATTER-001',
  businessCaseType: 'Immobilienkaufvertrag',
  lifecycleStatus: 'Entwurf',
  stageLabel: 'Vertragsentwurf prüfen',
  deadlineLabel: '31.08.2026, 18:00 Uhr (2026-08-31T16:00:00Z)',
  assignedRole: 'Zugeordnete Fachkraft (synthetisch)',
  tasks: [
    {
      id: 'NAC-SYN-TASK-001',
      title: 'Vertragsentwurf prüfen',
      stepCode: 'synthetic_contract_review',
      status: 'Offen',
      dueAt: undefined,
      dueLabel: 'Vor Fristablauf'
    },
    {
      id: 'NAC-SYN-DEADLINE-001',
      title: 'Abschlussfrist überwachen',
      stepCode: 'synthetic_completion_deadline',
      status: 'Offen',
      dueAt: '2026-08-31T16:00:00Z',
      dueLabel: '31.08.2026, 18:00 Uhr (2026-08-31T16:00:00Z)'
    }
  ],
  bpmnProcessKey: 'NAC_SYN_MATTER_001',
  bpmnSha256: '1dd7203a515d434949ef9300d5738cf7318d842119ec689aaa7ba1f9a7a6d167',
  bpmnXml: sampleApprovedBpmnXml,
  containsMatterData: false,
  source: 'package_fixture'
};
