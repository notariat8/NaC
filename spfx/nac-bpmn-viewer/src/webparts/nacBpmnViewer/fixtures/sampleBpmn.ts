export const sampleApprovedBpmnXml = `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
  id="Definitions_NacSyntheticMatter"
  targetNamespace="https://notariat8.de/nac/synthetic">
  <bpmn:process id="NAC_SYN_MATTER_001" isExecutable="false">
    <bpmn:startEvent id="StartEvent_Synthetic"/>
    <bpmn:userTask id="synthetic_contract_review" name="Vertragsentwurf prüfen"/>
    <bpmn:userTask id="synthetic_completion_deadline" name="Abschlussfrist überwachen"/>
    <bpmn:endEvent id="EndEvent_Synthetic"/>
    <bpmn:sequenceFlow id="Flow_Start_Review" sourceRef="StartEvent_Synthetic" targetRef="synthetic_contract_review"/>
    <bpmn:sequenceFlow id="Flow_Review_Deadline" sourceRef="synthetic_contract_review" targetRef="synthetic_completion_deadline"/>
    <bpmn:sequenceFlow id="Flow_Deadline_End" sourceRef="synthetic_completion_deadline" targetRef="EndEvent_Synthetic"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_NacSyntheticMatter">
    <bpmndi:BPMNPlane id="BPMNPlane_NacSyntheticMatter" bpmnElement="NAC_SYN_MATTER_001">
      <bpmndi:BPMNShape id="StartEvent_Synthetic_di" bpmnElement="StartEvent_Synthetic">
        <dc:Bounds x="120" y="122" width="36" height="36"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="synthetic_contract_review_di" bpmnElement="synthetic_contract_review">
        <dc:Bounds x="220" y="100" width="140" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="synthetic_completion_deadline_di" bpmnElement="synthetic_completion_deadline">
        <dc:Bounds x="430" y="100" width="150" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_Synthetic_di" bpmnElement="EndEvent_Synthetic">
        <dc:Bounds x="650" y="122" width="36" height="36"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_Start_Review_di" bpmnElement="Flow_Start_Review">
        <di:waypoint x="156" y="140"/>
        <di:waypoint x="220" y="140"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Review_Deadline_di" bpmnElement="Flow_Review_Deadline">
        <di:waypoint x="360" y="140"/>
        <di:waypoint x="430" y="140"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Deadline_End_di" bpmnElement="Flow_Deadline_End">
        <di:waypoint x="580" y="140"/>
        <di:waypoint x="650" y="140"/>
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`;
