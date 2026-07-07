export type GraphMethod = 'GET';

export interface BpmnViewerRequestPlan {
  tool: 'bpmn_model_get' | 'process_register_list' | 'bpmn_viewer_overlay_get';
  method: GraphMethod;
  listName: 'BPMN Models' | 'Prozessregister' | 'AufgabenFristen';
  requiredInputs: string[];
  executesGraphRequestsNow: false;
  readsFiles: false;
  writesItems: false;
}

export const bpmnViewerRequestPlans: BpmnViewerRequestPlan[] = [
  {
    tool: 'bpmn_model_get',
    method: 'GET',
    listName: 'BPMN Models',
    requiredInputs: ['bpmn_model_id'],
    executesGraphRequestsNow: false,
    readsFiles: false,
    writesItems: false
  },
  {
    tool: 'process_register_list',
    method: 'GET',
    listName: 'Prozessregister',
    requiredInputs: [],
    executesGraphRequestsNow: false,
    readsFiles: false,
    writesItems: false
  },
  {
    tool: 'bpmn_viewer_overlay_get',
    method: 'GET',
    listName: 'AufgabenFristen',
    requiredInputs: ['case_id'],
    executesGraphRequestsNow: false,
    readsFiles: false,
    writesItems: false
  }
];

export function assertRequestPlanOnly(plan: BpmnViewerRequestPlan): void {
  if (plan.executesGraphRequestsNow || plan.readsFiles || plan.writesItems) {
    throw new Error('NaC BPMN Viewer skeleton is request-plan-only in this slice.');
  }
}
