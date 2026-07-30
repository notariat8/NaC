import * as React from 'react';
import * as ReactDom from 'react-dom';
import { IReadonlyTheme } from '@microsoft/sp-component-base';
import { Version } from '@microsoft/sp-core-library';
import { BaseClientSideWebPart } from '@microsoft/sp-webpart-base';
import { NacBpmnViewer, NacBpmnViewerProps } from './components/NacBpmnViewer';
import { loadNacBffWorkspace } from './services/NacBffClient';

export interface NacBpmnViewerWebPartProps {
  workspaceId: string;
}

export default class NacBpmnViewerWebPart extends BaseClientSideWebPart<NacBpmnViewerWebPartProps> {
  private isDarkTheme = false;
  private readonly evaluationTimestamp = new Date().toISOString();

  public render(): void {
    const element = React.createElement<NacBpmnViewerProps>(NacBpmnViewer, {
      workspaceId: 'notary_team_01',
      userDisplayName: this.context.pageContext.user.displayName,
      hostName: this.context.sdks.microsoftTeams ? 'Microsoft Teams' : 'SharePoint',
      isDarkTheme: this.isDarkTheme,
      evaluationTimestamp: this.evaluationTimestamp,
      loadWorkspace: (signal: AbortSignal) => loadNacBffWorkspace(this.context.aadHttpClientFactory, signal)
    });

    ReactDom.render(element, this.domElement);
  }

  protected onThemeChanged(currentTheme: IReadonlyTheme | undefined): void {
    this.isDarkTheme = currentTheme?.isInverted === true;
    this.render();
  }

  protected onDispose(): void {
    ReactDom.unmountComponentAtNode(this.domElement);
  }

  protected get dataVersion(): Version {
    return Version.parse('1.0');
  }
}
