import {
  signedWorkbenchSnapshotJson,
  VALID_WORKBENCH_SNAPSHOT
} from '../core/parseWorkbenchSnapshot.test';
import { parseNacWorkbenchProjectionJson } from './NacWorkbenchProjection';

const expected = {
  subjectId: 'actor:synthetic:001',
  workspaceId: 'notary_team_01',
  matterId: 'NAC-SYN-MATTER-001',
  purpose: 'view_synthetic_matter_workspace'
};

describe('NaC workbench projection boundary', () => {
  it.each(['notary', 'notary_clerk', 'deputy_notary', 'deputy_clerk'])(
    'accepts the canonical UI role %s',
    async role => {
      const roleSnapshot = {
        ...VALID_WORKBENCH_SNAPSHOT,
        access: { ...VALID_WORKBENCH_SNAPSHOT.access, role }
      };
      await expect(parseNacWorkbenchProjectionJson(
        signedWorkbenchSnapshotJson(roleSnapshot),
        '2026-08-01T09:01:00Z',
        expected
      )).resolves.toEqual(expect.objectContaining({
        access: expect.objectContaining({ role })
      }));
    }
  );

  it('keeps all decisions, evidence and capabilities server-authored', async () => {
    const snapshot = await parseNacWorkbenchProjectionJson(
      signedWorkbenchSnapshotJson(),
      '2026-08-01T09:01:00Z',
      expected
    );
    expect(snapshot.decisions).toEqual(VALID_WORKBENCH_SNAPSHOT.decisions);
    expect(snapshot.evidence).toEqual(VALID_WORKBENCH_SNAPSHOT.evidence);
    expect(snapshot.capabilities.every(item => item.decision === 'deny')).toBe(true);
  });

  it('fails closed on producer or scope drift', async () => {
    const producerDrift = {
      ...VALID_WORKBENCH_SNAPSHOT,
      producer: { ...VALID_WORKBENCH_SNAPSHOT.producer, id: 'browser' }
    };
    await expect(parseNacWorkbenchProjectionJson(
      signedWorkbenchSnapshotJson(producerDrift),
      '2026-08-01T09:01:00Z',
      expected
    )).rejects.toThrow('NAC_WORKBENCH_SCOPE_INVALID');
    await expect(parseNacWorkbenchProjectionJson(
      signedWorkbenchSnapshotJson(),
      '2026-08-01T09:01:00Z',
      { ...expected, workspaceId: 'other' }
    )).rejects.toThrow('NAC_WORKBENCH_SCOPE_INVALID');
    await expect(parseNacWorkbenchProjectionJson(
      signedWorkbenchSnapshotJson(),
      '2026-08-01T09:01:00Z',
      { ...expected, subjectId: 'actor:synthetic:other' }
    )).rejects.toThrow('NAC_WORKBENCH_SCOPE_INVALID');
    const unsupportedRole = {
      ...VALID_WORKBENCH_SNAPSHOT,
      access: { ...VALID_WORKBENCH_SNAPSHOT.access, role: 'runtime_service' }
    };
    await expect(parseNacWorkbenchProjectionJson(
      signedWorkbenchSnapshotJson(unsupportedRole),
      '2026-08-01T09:01:00Z',
      expected
    )).rejects.toThrow('NAC_WORKBENCH_SCOPE_INVALID');
  });
});
