import * as React from 'react';
import BpmnViewer from 'bpmn-js/lib/Viewer';
import { sampleApprovedBpmnXml } from '../fixtures/sampleBpmn';
import { bpmnViewerRequestPlans, assertRequestPlanOnly } from '../services/BpmnViewerRequestPlan';

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
    <section data-nac-component="spfx-bpmn-viewer-skeleton">
      <div
        id="nac-bpmn-viewer-container"
        ref={containerRef}
        data-workspace-id={props.workspaceId}
        data-bpmn-model-id={props.bpmnModelId}
        data-process-id={props.processId || ''}
        data-case-id={props.caseId || ''}
      />
    </section>
  );
}
