export type GraphMethod = 'GET';
export type BpmnViewerRenderState =
  | 'approved_renderable'
  | 'approval_missing_or_review_required'
  | 'viewer_disabled'
  | 'contains_matter_data'
  | 'invalid_mime_or_hash_missing';
export type BpmnViewerContentSource = 'approved_bpmn_xml_fixture' | 'blocked_metadata_only';
export type BpmnViewerMetadataOverlay = 'redacted_metadata_only';

export interface BpmnViewerRequestPlan {
  tool: 'bpmn_model_get' | 'process_register_list' | 'bpmn_viewer_overlay_get';
  method: GraphMethod;
  listName: 'BPMN Models' | 'Prozessregister' | 'AufgabenFristen';
  requiredInputs: string[];
  executesGraphRequestsNow: false;
  readsFiles: false;
  writesItems: false;
}

export interface BpmnViewerModelMetadata {
  approvalStatus?: string;
  viewerEnabled?: boolean;
  containsMatterData?: boolean;
  bpmnXmlMimeType?: string;
  bpmnXmlSha256?: string;
}

export interface BpmnViewerRenderDecision {
  renderState: BpmnViewerRenderState;
  contentSource: BpmnViewerContentSource;
  metadataOverlay: BpmnViewerMetadataOverlay;
  renderAllowed: boolean;
  liveTenantAccess: false;
  appCatalogDeploy: false;
  requestPlanCount: number;
}

export const bpmnViewerDomMarkers = {
  renderState: 'data-nac-render-state',
  contentSource: 'data-nac-content-source',
  metadataOverlay: 'data-nac-metadata-overlay'
};

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

const allowedBpmnXmlMimeTypes = ['application/xml', 'text/xml'];

export const approvedFixtureBpmnMetadata: BpmnViewerModelMetadata = {
  approvalStatus: 'Approved',
  viewerEnabled: true,
  containsMatterData: false,
  bpmnXmlMimeType: 'application/xml',
  bpmnXmlSha256: 'fixture-only-not-a-live-content-hash'
};

export function assertRequestPlanOnly(plan: BpmnViewerRequestPlan): void {
  if (plan.executesGraphRequestsNow || plan.readsFiles || plan.writesItems) {
    throw new Error('NaC BPMN Viewer skeleton is request-plan-only in this slice.');
  }
}

export function evaluateBpmnViewerRenderContract(metadata: BpmnViewerModelMetadata): BpmnViewerRenderDecision {
  let renderState: BpmnViewerRenderState = 'approved_renderable';
  if (metadata.approvalStatus !== 'Approved') {
    renderState = 'approval_missing_or_review_required';
  } else if (metadata.viewerEnabled !== true) {
    renderState = 'viewer_disabled';
  } else if (metadata.containsMatterData !== false) {
    renderState = 'contains_matter_data';
  } else if (!isValidBpmnXmlReference(metadata)) {
    renderState = 'invalid_mime_or_hash_missing';
  }

  const renderAllowed = renderState === 'approved_renderable';
  return {
    renderState,
    contentSource: renderAllowed ? 'approved_bpmn_xml_fixture' : 'blocked_metadata_only',
    metadataOverlay: 'redacted_metadata_only',
    renderAllowed,
    liveTenantAccess: false,
    appCatalogDeploy: false,
    requestPlanCount: bpmnViewerRequestPlans.length
  };
}

export const approvedFixtureRenderDecision = evaluateBpmnViewerRenderContract(approvedFixtureBpmnMetadata);

function isValidBpmnXmlReference(metadata: BpmnViewerModelMetadata): boolean {
  return (
    typeof metadata.bpmnXmlSha256 === 'string' &&
    metadata.bpmnXmlSha256.length > 0 &&
    typeof metadata.bpmnXmlMimeType === 'string' &&
    allowedBpmnXmlMimeTypes.indexOf(metadata.bpmnXmlMimeType) >= 0
  );
}
