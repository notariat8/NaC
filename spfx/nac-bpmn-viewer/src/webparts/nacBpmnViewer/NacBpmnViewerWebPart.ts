import * as React from 'react';
import * as ReactDom from 'react-dom';
import { BaseClientSideWebPart } from '@microsoft/sp-webpart-base';
import { IPropertyPaneConfiguration, PropertyPaneTextField } from '@microsoft/sp-property-pane';
import { NacBpmnViewer, NacBpmnViewerProps } from './components/NacBpmnViewer';

export interface NacBpmnViewerWebPartProps {
  workspaceId: string;
  bpmnModelId: string;
  processId?: string;
  caseId?: string;
}

export default class NacBpmnViewerWebPart extends BaseClientSideWebPart<NacBpmnViewerWebPartProps> {
  public render(): void {
    const element = React.createElement<NacBpmnViewerProps>(NacBpmnViewer, {
      workspaceId: this.properties.workspaceId || 'notary_team_01',
      bpmnModelId: this.properties.bpmnModelId || 'bpmn-model-immobilienkaufvertrag-v1',
      processId: this.properties.processId,
      caseId: this.properties.caseId
    });

    ReactDom.render(element, this.domElement);
  }

  protected onDispose(): void {
    ReactDom.unmountComponentAtNode(this.domElement);
  }

  protected getPropertyPaneConfiguration(): IPropertyPaneConfiguration {
    return {
      pages: [
        {
          header: {
            description: 'NaC BPMN Viewer skeleton configuration'
          },
          groups: [
            {
              groupName: 'Viewer metadata',
              groupFields: [
                PropertyPaneTextField('workspaceId', { label: 'Workspace ID' }),
                PropertyPaneTextField('bpmnModelId', { label: 'BPMN model ID' }),
                PropertyPaneTextField('processId', { label: 'Process ID' }),
                PropertyPaneTextField('caseId', { label: 'Case ID' })
              ]
            }
          ]
        }
      ]
    };
  }
}
