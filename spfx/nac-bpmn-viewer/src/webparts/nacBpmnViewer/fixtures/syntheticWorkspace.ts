import { sampleApprovedBpmnXml } from './sampleBpmn';

export interface SyntheticWorkspaceFixture {
  readonly schemaVersion: 'nac.spfx-synthetic-bpmn-asset/v0.2';
  readonly workspaceId: 'notary_team_01';
  readonly businessCaseType: 'Immobilienkaufvertrag';
  readonly bpmnProcessKey: 'NAC_SYN_MATTER_001';
  readonly bpmnSha256: string;
  readonly bpmnXml: string;
  readonly containsMatterData: false;
  readonly source: 'package_bpmn_fixture';
}

export const syntheticWorkspaceFixture: SyntheticWorkspaceFixture = {
  schemaVersion: 'nac.spfx-synthetic-bpmn-asset/v0.2',
  workspaceId: 'notary_team_01',
  businessCaseType: 'Immobilienkaufvertrag',
  bpmnProcessKey: 'NAC_SYN_MATTER_001',
  bpmnSha256: '1dd7203a515d434949ef9300d5738cf7318d842119ec689aaa7ba1f9a7a6d167',
  bpmnXml: sampleApprovedBpmnXml,
  containsMatterData: false,
  source: 'package_bpmn_fixture'
};
