export const sampleApprovedBpmnXml = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
  id="Definitions_NaC_Bpmn_Viewer_Fixture"
  targetNamespace="https://notariat8.de/nac/bpmn-viewer-fixture">
  <bpmn:process id="Process_NaC_Bpmn_Viewer_Fixture" isExecutable="false">
    <bpmn:startEvent id="StartEvent_Template"/>
    <bpmn:task id="Task_Review_Template" name="Template pruefen"/>
    <bpmn:endEvent id="EndEvent_Template"/>
    <bpmn:sequenceFlow id="Flow_Start_Review" sourceRef="StartEvent_Template" targetRef="Task_Review_Template"/>
    <bpmn:sequenceFlow id="Flow_Review_End" sourceRef="Task_Review_Template" targetRef="EndEvent_Template"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_NaC_Bpmn_Viewer_Fixture">
    <bpmndi:BPMNPlane id="BPMNPlane_NaC_Bpmn_Viewer_Fixture" bpmnElement="Process_NaC_Bpmn_Viewer_Fixture">
      <bpmndi:BPMNShape id="StartEvent_Template_di" bpmnElement="StartEvent_Template">
        <dc:Bounds x="160" y="120" width="36" height="36"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_Review_Template_di" bpmnElement="Task_Review_Template">
        <dc:Bounds x="260" y="98" width="120" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_Template_di" bpmnElement="EndEvent_Template">
        <dc:Bounds x="450" y="120" width="36" height="36"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_Start_Review_di" bpmnElement="Flow_Start_Review">
        <di:waypoint x="196" y="138"/>
        <di:waypoint x="260" y="138"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Review_End_di" bpmnElement="Flow_Review_End">
        <di:waypoint x="380" y="138"/>
        <di:waypoint x="450" y="138"/>
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`;
