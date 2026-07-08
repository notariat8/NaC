import * as React from 'react';
import BpmnViewer from 'bpmn-js/lib/Viewer';
import { sampleApprovedBpmnXml } from '../fixtures/sampleBpmn';
import {
  approvedFixtureRenderDecision,
  bpmnViewerRequestPlans,
  assertRequestPlanOnly
} from '../services/BpmnViewerRequestPlan';

export interface NacBpmnViewerProps {
  workspaceId: string;
  bpmnModelId: string;
  processId?: string;
  caseId?: string;
}

export function NacBpmnViewer(props: NacBpmnViewerProps): JSX.Element {
  const containerRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    bpmnViewerRequestPlans.forEach(assertRequestPlanOnly);
    if (!containerRef.current) {
      return;
    }
    if (!approvedFixtureRenderDecision.renderAllowed) {
      return;
    }

    const viewer = new BpmnViewer({
      container: containerRef.current
    });

    let disposed = false;
    viewer.importXML(sampleApprovedBpmnXml).then(() => {
      if (!disposed) {
        const canvas = viewer.get('canvas') as { zoom: (mode: string) => void };
        canvas.zoom('fit-viewport');
      }
    });

    return () => {
      disposed = true;
      viewer.destroy();
    };
  }, [props.workspaceId, props.bpmnModelId, props.processId, props.caseId]);

  return (
    <section
      data-nac-component="spfx-bpmn-viewer-skeleton"
      data-nac-render-state={approvedFixtureRenderDecision.renderState}
      data-nac-content-source={approvedFixtureRenderDecision.contentSource}
      data-nac-metadata-overlay={approvedFixtureRenderDecision.metadataOverlay}
    >
      <div
        id="nac-bpmn-viewer-container"
        ref={containerRef}
        data-workspace-id={props.workspaceId}
        data-bpmn-model-id={props.bpmnModelId}
        data-process-id={props.processId || ''}
        data-case-context={props.caseId ? 'redacted' : ''}
      />
      <aside
        className="nac-bpmn-viewer-overlay"
        data-nac-metadata-overlay={approvedFixtureRenderDecision.metadataOverlay}
        data-nac-overlay-redaction="metadata_only_no_private_payload_or_credentials"
      >
        <span data-nac-overlay-field="render-state">{approvedFixtureRenderDecision.renderState}</span>
        <span data-nac-overlay-field="content-source">{approvedFixtureRenderDecision.contentSource}</span>
      </aside>
    </section>
  );
}
