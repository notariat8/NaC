'use strict';

const fs = require('fs');
const crypto = require('crypto');
const path = require('path');
const ts = require('typescript');

const root = path.resolve(__dirname, '..');
const paths = {
  viewer: path.join(root, 'src/webparts/nacBpmnViewer/components/NacBpmnViewer.tsx'),
  tests: path.join(root, 'src/webparts/nacBpmnViewer/components/NacBpmnViewer.test.tsx'),
  styles: path.join(root, 'src/webparts/nacBpmnViewer/components/NacBpmnViewer.styles.ts')
};
const TITLES = {
  current: 'marks the canonical current BPMN task before showing ready metadata',
  resize: 'refits the same viewer instance after its container resizes',
  resizeFailure: 'fails closed when refitting after a resize fails',
  missingElement: 'fails closed and destroys the viewer for an unknown current BPMN element',
  missingTask: 'fails closed and destroys the viewer when the matter has no current task',
  unmount: 'destroys a ready viewer when the component unmounts',
  pointer: 'selects another task by pointer without moving the current marker',
  enter: 'exposes native button semantics used by Enter activation',
  space: 'exposes native button semantics used by Space activation',
  instanceIds: 'assigns stable unique task detail ids to each component instance',
  duplicateTaskId: 'fails closed before metadata for duplicate task ids',
  duplicateStepCode: 'fails closed before metadata for duplicate step codes',
  unknownBinding: 'fails closed before metadata for an unknown non-current task binding',
  fakeTaskType: 'fails closed before metadata for a fake task type without bpmn:Task inheritance',
  initialSelectionFailure: 'fails closed when the initial selection marker cannot be added',
  removeSelectionFailure: 'fails closed when removing the previous selection marker fails',
  addSelectionFailure: 'fails closed when adding the next selection marker fails'
};
const EXPECTED_SELF_TEST_NAMES = new Set([
  'regex-decoy',
  'unreachable-marker',
  'skipped-test',
  'helper-test',
  'unreachable-only-marker',
  'return-before-marker',
  'wrapped-suite',
  'skipped-suite',
  'early-return',
  'nested-assertion',
  'unreachable-assertion',
  'missing-css',
  'commented-css-decoy',
  'task-supertype-substitution',
  'task-id-check-removal',
  'skipped-fake-task-test',
  'selected-marker-binding',
  'transition-marker-binding',
  'selected-step-attribute-binding',
  'task-id-attribute-binding',
  'duplicate-task-id-guard',
  'manual-key-handler',
  'skipped-pointer-test',
  'missing-pointer-marker-assertion',
  'missing-selected-css',
  'non-current-loop-false-guard',
  'non-current-loop-missing-guard',
  'conditional-return-before-test',
  'numeric-truthy-return-before-test',
  'jest-registration-reassignment',
  'jest-registration-shadow',
  'dynamic-jest-registration-property',
  'eager-jest-registration-argument',
  'eager-describe-title',
  'top-level-jest-registration-mutation',
  'suite-suffix-mutation',
  'conditional-throw-before-test',
  'skipped-instance-id-test',
  'details-id-binding',
  'keyboard-test-click'
]);
const MINIMUM_SELF_TEST_COUNT = 40;
const executedSelfTestNames = new Set();
const EXPECTED_TEST_SOURCE_SHA256 =
  '8fd6fedf219e3f245073120f034b285f9b3c8d09b49ac8f5bd7fd8f40b11999f';

const CURRENT_STEP_SELECTOR =
  '.nacBpmnViewer__workspace .djs-element.nac-current-step .djs-visual > :first-child';
const SELECTED_STEP_SELECTOR =
  '.nacBpmnViewer__workspace .djs-element.nac-selected-step .djs-visual > :first-child';
const SELECTED_ONLY_SELECTOR =
  '.nacBpmnViewer__workspace .djs-element.nac-selected-step:not(.nac-current-step) .djs-visual > :first-child';

const parse = (source, file, kind) =>
  ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, kind);
const nodeText = (node, sourceFile) => node.getText(sourceFile).replace(/\s+/g, '');

function calls(rootNode, sourceFile, predicate) {
  const result = [];
  const visit = node => {
    if (ts.isCallExpression(node) && predicate(node, sourceFile)) result.push(node);
    ts.forEachChild(node, visit);
  };
  visit(rootNode);
  return result;
}

function propertyCall(objectName, methodName, argumentTexts) {
  return (node, sourceFile) =>
    ts.isPropertyAccessExpression(node.expression) &&
    nodeText(node.expression.expression, sourceFile) === objectName &&
    node.expression.name.text === methodName &&
    node.arguments.length === argumentTexts.length &&
    node.arguments.every((argument, index) =>
      nodeText(argument, sourceFile) === argumentTexts[index]);
}

function matcher(expectTarget, matcherName, argumentTexts) {
  return (node, sourceFile) => {
    if (!ts.isPropertyAccessExpression(node.expression) ||
        node.expression.name.text !== matcherName) return false;
    const expectation = node.expression.expression;
    return ts.isCallExpression(expectation) &&
      ts.isIdentifier(expectation.expression) &&
      expectation.expression.text === 'expect' &&
      expectation.arguments.length === 1 &&
      nodeText(expectation.arguments[0], sourceFile) === expectTarget &&
      node.arguments.length === argumentTexts.length &&
      node.arguments.every((argument, index) =>
        nodeText(argument, sourceFile) === argumentTexts[index]);
  };
}

function isSuccessfulImportPath(node, sourceFile) {
  const statement = node.parent;
  const successBlock = statement?.parent;
  const successIf = successBlock?.parent;
  const callbackBlock = successIf?.parent;
  const callback = callbackBlock?.parent;
  const thenCall = callback?.parent;
  if (!ts.isExpressionStatement(statement) ||
      !ts.isBlock(successBlock) ||
      !ts.isIfStatement(successIf) ||
      nodeText(successIf.expression, sourceFile) !== '!disposed&&!finished' ||
      !ts.isBlock(callbackBlock) ||
      (!ts.isArrowFunction(callback) && !ts.isFunctionExpression(callback)) ||
      !ts.isCallExpression(thenCall) ||
      !thenCall.arguments.includes(callback) ||
      !ts.isPropertyAccessExpression(thenCall.expression) ||
      thenCall.expression.name.text !== 'then' ||
      nodeText(thenCall.expression.expression, sourceFile) !== 'viewer.importXML(bpmnXml)') {
    return false;
  }
  const markerIndex = successBlock.statements.indexOf(statement);
  if (markerIndex !== 10) return false;
  const preceding = successBlock.statements.slice(0, markerIndex);
  const expectedShape = [
    ts.isVariableStatement,
    ts.isIfStatement,
    ts.isVariableStatement,
    ts.isVariableStatement,
    ts.isForOfStatement,
    ts.isVariableStatement,
    ts.isVariableStatement,
    ts.isVariableStatement,
    ts.isIfStatement,
    ts.isForOfStatement
  ];
  if (preceding.length !== expectedShape.length ||
      !preceding.every((item, index) => expectedShape[index](item))) return false;
  const guards = preceding
    .filter(item => ts.isIfStatement(item))
    .map(item => nodeText(item.expression, sourceFile));
  return guards.join('|') ===
    'currentTask===undefined|!isCanonicalBpmnTask(currentElement,currentTask.stepCode)';
}

function isCanonicalNonCurrentTaskLoop(markerCall, sourceFile) {
  const markerStatement = markerCall.parent;
  const successBlock = markerStatement?.parent;
  if (!ts.isExpressionStatement(markerStatement) || !ts.isBlock(successBlock)) return false;
  const markerIndex = successBlock.statements.indexOf(markerStatement);
  const loop = successBlock.statements[markerIndex - 1];
  if (!loop || !ts.isForOfStatement(loop) ||
      !ts.isVariableDeclarationList(loop.initializer) ||
      loop.initializer.declarations.length !== 1 ||
      nodeText(loop.initializer.declarations[0].name, sourceFile) !== 'task' ||
      loop.initializer.declarations[0].initializer !== undefined ||
      nodeText(loop.expression, sourceFile) !== 'workspace.matter.tasks.slice(1)' ||
      !ts.isBlock(loop.statement) ||
      loop.statement.statements.length !== 2) {
    return false;
  }

  const taskElementStatement = loop.statement.statements[0];
  if (!ts.isVariableStatement(taskElementStatement) ||
      !(taskElementStatement.declarationList.flags & ts.NodeFlags.Const) ||
      taskElementStatement.declarationList.declarations.length !== 1) {
    return false;
  }
  const taskElement = taskElementStatement.declarationList.declarations[0];
  if (nodeText(taskElement.name, sourceFile) !== 'taskElement' ||
      !taskElement.initializer ||
      nodeText(taskElement.initializer, sourceFile) !== 'elementRegistry.get(task.stepCode)') {
    return false;
  }

  const guard = loop.statement.statements[1];
  if (!ts.isIfStatement(guard) || guard.elseStatement !== undefined ||
      nodeText(guard.expression, sourceFile) !==
        '!isCanonicalBpmnTask(taskElement,task.stepCode)' ||
      !ts.isBlock(guard.thenStatement) || guard.thenStatement.statements.length !== 1) {
    return false;
  }
  const rejection = guard.thenStatement.statements[0];
  return ts.isThrowStatement(rejection) && rejection.expression !== undefined &&
    nodeText(rejection.expression, sourceFile) ===
      "newError('TaskBPMNelementismissing.')";
}

function statementCanExitSuite(statement) {
  let found = false;
  const visit = node => {
    if (node !== statement && ts.isFunctionLike(node)) return;
    if (ts.isReturnStatement(node) || ts.isThrowStatement(node)) {
      found = true;
      return;
    }
    ts.forEachChild(node, visit);
  };
  visit(statement);
  return found;
}

function directTestStatements(callback) {
  if (!ts.isBlock(callback.body)) return [];
  return callback.body.statements
    .filter(statement => ts.isExpressionStatement(statement))
    .map(statement => statement.expression)
    .filter(expression => ts.isCallExpression(expression));
}

function isSafeEagerExpression(node) {
  while (ts.isParenthesizedExpression(node) || ts.isAsExpression(node) ||
      ts.isTypeAssertionExpression(node) || ts.isNonNullExpression(node)) {
    node = node.expression;
  }
  if (ts.isFunctionLike(node) || ts.isIdentifier(node) ||
      ts.isStringLiteral(node) || ts.isNumericLiteral(node) ||
      ts.isNoSubstitutionTemplateLiteral(node) ||
      node.kind === ts.SyntaxKind.TrueKeyword ||
      node.kind === ts.SyntaxKind.FalseKeyword ||
      node.kind === ts.SyntaxKind.NullKeyword) {
    return true;
  }
  if (ts.isPrefixUnaryExpression(node)) {
    return isSafeEagerExpression(node.operand);
  }
  if (ts.isArrayLiteralExpression(node)) {
    return node.elements.every(element =>
      ts.isOmittedExpression(element) ||
      (!ts.isSpreadElement(element) && isSafeEagerExpression(element))
    );
  }
  if (ts.isNewExpression(node) && ts.isIdentifier(node.expression) &&
      ["Error", "TypeError"].includes(node.expression.text)) {
    return (node.arguments || []).every(isSafeEagerExpression);
  }
  return false;
}

function isAllowedSuiteRegistrationCall(expression) {
  if (!ts.isCallExpression(expression)) return false;
  if (ts.isIdentifier(expression.expression)) {
    return ["beforeEach", "afterEach", "it"].includes(expression.expression.text) &&
      expression.arguments.every(isSafeEagerExpression);
  }
  const factoryCall = expression.expression;
  return ts.isCallExpression(factoryCall) &&
    ts.isPropertyAccessExpression(factoryCall.expression) &&
    ts.isIdentifier(factoryCall.expression.expression) &&
    factoryCall.expression.expression.text === "it" &&
    factoryCall.expression.name.text === "each" &&
    factoryCall.arguments.every(isSafeEagerExpression) &&
    expression.arguments.every(isSafeEagerExpression);
}

function isAllowedSuiteStatement(statement) {
  if (ts.isVariableStatement(statement)) {
    return statement.declarationList.declarations.every(declaration =>
      ts.isIdentifier(declaration.name) &&
      (declaration.initializer === undefined ||
        (ts.isCallExpression(declaration.initializer) &&
          ts.isIdentifier(declaration.initializer.expression) &&
          declaration.initializer.expression.text === "createBpmnUserTaskElement" &&
          declaration.initializer.arguments.every(isSafeEagerExpression)))
    );
  }
  return ts.isExpressionStatement(statement) &&
    isAllowedSuiteRegistrationCall(statement.expression);
}

function hasCanonicalSuiteBody(callback, sourceFile) {
  if (!ts.isBlock(callback.body)) return false;
  const helpers = new Set();
  let helperCount = 0;
  for (const statement of callback.body.statements) {
    if (ts.isFunctionDeclaration(statement)) {
      const text = nodeText(statement, sourceFile);
      if (!EXPECTED_SUITE_HELPERS.has(text)) return false;
      helpers.add(text);
      helperCount += 1;
      continue;
    }
    if (!isAllowedSuiteStatement(statement)) return false;
  }
  return helperCount === EXPECTED_SUITE_HELPERS.size &&
    helpers.size === EXPECTED_SUITE_HELPERS.size;
}

function isDirectActiveTest(testCall) {
  const testStatement = testCall.parent;
  const suiteBlock = testStatement?.parent;
  const suiteCallback = suiteBlock?.parent;
  const suiteCall = suiteCallback?.parent;
  const suiteStatement = suiteCall?.parent;
  if (!ts.isExpressionStatement(testStatement) ||
      !ts.isBlock(suiteBlock) ||
      (!ts.isArrowFunction(suiteCallback) && !ts.isFunctionExpression(suiteCallback)) ||
      !ts.isCallExpression(suiteCall) ||
      suiteCall.arguments.length !== 2 ||
      !ts.isStringLiteral(suiteCall.arguments[0]) ||
      suiteCall.arguments[0].text !== "NaC BPMN viewer runtime boundary" ||
      suiteCall.arguments[1] !== suiteCallback ||
      !ts.isIdentifier(suiteCall.expression) ||
      suiteCall.expression.text !== 'describe' ||
      !ts.isExpressionStatement(suiteStatement) ||
      !ts.isSourceFile(suiteStatement.parent)) {
    return false;
  }
  const testIndex = suiteBlock.statements.indexOf(testStatement);
  const precedingStatements = suiteBlock.statements.slice(0, testIndex);
  return !precedingStatements.some(statementCanExitSuite) &&
    precedingStatements.every(isAllowedSuiteStatement);
}

function hasEarlyExit(callback) {
  let found = false;
  const visit = node => {
    if (node !== callback.body && ts.isFunctionLike(node)) return;
    if (ts.isReturnStatement(node) || ts.isThrowStatement(node)) {
      found = true;
      return;
    }
    ts.forEachChild(node, visit);
  };
  visit(callback.body);
  return found;
}

function hasForbiddenNativeButtonTestAction(callback, sourceFile) {
  let found = false;
  const visit = node => {
    if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression) &&
        (node.expression.name.text === 'click' ||
          node.expression.name.text === 'dispatchEvent')) {
      found = true;
      return;
    }
    if (ts.isNewExpression(node) && ts.isIdentifier(node.expression) &&
        node.expression.text === 'KeyboardEvent') {
      found = true;
      return;
    }
    ts.forEachChild(node, visit);
  };
  visit(callback.body);
  return found;
}

const EXPECTED_TEST_IMPORTS = new Set([
  "react",
  "react-dom",
  "react-dom/test-utils",
  "bpmn-js/lib/Viewer",
  "../services/NacBffClient",
  "./NacBpmnViewer"
]);
const EXPECTED_TOP_LEVEL_MOCKS = new Set([
  "jest.mock('" + String.fromCharCode(64) +
    "microsoft/sp-http',()=>({AadHttpClient:{configurations:{v1:{}}}}));",
  "jest.mock('bpmn-js/lib/Viewer',()=>({__esModule:true,default:jest.fn()}));"
]);
const EXPECTED_TASK_HELPER =
  "functioncreateBpmnUserTaskElement(elementId:string):{readonlyid:string;" +
  "readonlytype:'bpmn:UserTask';readonlybusinessObject:{readonly" +
  String.fromCharCode(36) + "instanceOf:jest.Mock};}" +
  "{return{id:elementId,type:'bpmn:UserTask',businessObject:{" +
  String.fromCharCode(36) +
  "instanceOf:jest.fn((bpmnType:string)=>bpmnType==='bpmn:Task'||" +
  "bpmnType==='bpmn:UserTask')}};}";

const EXPECTED_SUITE_HELPERS = new Set([
  `asyncfunctionrenderAndFlush(loadWorkspace:(signal:AbortSignal)=>Promise<NacBffWorkspace>):Promise<void>{awaitact(async()=>{ReactDom.render(<NacBpmnViewerworkspaceId="notary_team_01"userDisplayName="TestUser"hostName="MicrosoftTeams"isDarkTheme={false}loadWorkspace={loadWorkspace}/>,root);awaitPromise.resolve();awaitPromise.resolve();});awaitflushPromises();}`,
  `asyncfunctionflushPromises():Promise<void>{awaitact(async()=>{awaitPromise.resolve();awaitPromise.resolve();});}`
]);

function isSafeTopLevelDataExpression(node) {
  while (ts.isParenthesizedExpression(node) || ts.isAsExpression(node) ||
      ts.isTypeAssertionExpression(node) || ts.isNonNullExpression(node)) {
    node = node.expression;
  }
  if (ts.isIdentifier(node) || ts.isStringLiteral(node) ||
      ts.isNumericLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node) ||
      node.kind === ts.SyntaxKind.TrueKeyword ||
      node.kind === ts.SyntaxKind.FalseKeyword ||
      node.kind === ts.SyntaxKind.NullKeyword) {
    return true;
  }
  if (ts.isArrayLiteralExpression(node)) {
    return node.elements.every(element =>
      ts.isOmittedExpression(element) ||
      (!ts.isSpreadElement(element) && isSafeTopLevelDataExpression(element))
    );
  }
  if (ts.isObjectLiteralExpression(node)) {
    return node.properties.every(property =>
      ts.isPropertyAssignment(property) &&
      !ts.isComputedPropertyName(property.name) &&
      isSafeTopLevelDataExpression(property.initializer)
    );
  }
  return ts.isCallExpression(node) &&
    ts.isPropertyAccessExpression(node.expression) &&
    node.expression.name.text === "join" &&
    ts.isArrayLiteralExpression(node.expression.expression) &&
    isSafeTopLevelDataExpression(node.expression.expression) &&
    node.arguments.every(isSafeTopLevelDataExpression);
}

function isCanonicalSuiteExpression(expression, sourceFile) {
  return ts.isCallExpression(expression) &&
    ts.isIdentifier(expression.expression) && expression.expression.text === "describe" &&
    expression.arguments.length === 2 &&
    ts.isStringLiteral(expression.arguments[0]) &&
    expression.arguments[0].text === "NaC BPMN viewer runtime boundary" &&
    (ts.isArrowFunction(expression.arguments[1]) ||
      ts.isFunctionExpression(expression.arguments[1])) &&
    hasCanonicalSuiteBody(expression.arguments[1], sourceFile);
}

function hasCanonicalSourceFileEnvelope(sourceFile) {
  const imports = new Set();
  const mocks = new Set();
  const variables = new Set();
  let helperCount = 0;
  let suiteCount = 0;
  for (const statement of sourceFile.statements) {
    if (ts.isImportDeclaration(statement) && statement.importClause &&
        ts.isStringLiteral(statement.moduleSpecifier)) {
      imports.add(statement.moduleSpecifier.text);
      continue;
    }
    if (ts.isVariableStatement(statement) &&
        (statement.declarationList.flags & ts.NodeFlags.Const) &&
        statement.declarationList.declarations.length === 1) {
      const declaration = statement.declarationList.declarations[0];
      if (!ts.isIdentifier(declaration.name) ||
          !["bpmnXml", "workspace"].includes(declaration.name.text) ||
          !declaration.initializer ||
          !isSafeTopLevelDataExpression(declaration.initializer)) return false;
      variables.add(declaration.name.text);
      continue;
    }
    if (ts.isFunctionDeclaration(statement) &&
        nodeText(statement, sourceFile) === EXPECTED_TASK_HELPER) {
      helperCount += 1;
      continue;
    }
    if (ts.isExpressionStatement(statement)) {
      const text = nodeText(statement, sourceFile);
      if (EXPECTED_TOP_LEVEL_MOCKS.has(text)) {
        mocks.add(text);
        continue;
      }
      if (isCanonicalSuiteExpression(statement.expression, sourceFile)) {
        suiteCount += 1;
        continue;
      }
    }
    return false;
  }
  return imports.size === EXPECTED_TEST_IMPORTS.size &&
    [...EXPECTED_TEST_IMPORTS].every(item => imports.has(item)) &&
    mocks.size === EXPECTED_TOP_LEVEL_MOCKS.size &&
    variables.size === 2 && helperCount === 1 && suiteCount === 1;
}

const JEST_REGISTRATION_NAMES = new Set(["it", "test", "describe"]);

function hasForbiddenJestRegistrationMutation(sourceFile) {
  let found = false;
  const visit = node => {
    if (ts.isIdentifier(node) && JEST_REGISTRATION_NAMES.has(node.text)) {
      const parent = node.parent;
      const isDirectRegistrationCall =
        ts.isCallExpression(parent) && parent.expression === node;
      const isEachRegistrationCall =
        ts.isPropertyAccessExpression(parent) && parent.expression === node &&
        parent.name.text === "each" && ts.isCallExpression(parent.parent) &&
        parent.parent.expression === parent;
      if (!isDirectRegistrationCall && !isEachRegistrationCall) {
        found = true;
        return;
      }
    }
    if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) &&
        JEST_REGISTRATION_NAMES.has(node.text)) {
      found = true;
      return;
    }
    ts.forEachChild(node, visit);
  };
  visit(sourceFile);
  return found;
}

function validateViewer(source) {
  const errors = [];
  const sf = parse(source, 'NacBpmnViewer.tsx', ts.ScriptKind.TSX);
  const componentFunctions = sf.statements.filter(statement =>
    ts.isFunctionDeclaration(statement) && statement.name?.text === 'NacBpmnViewer'
  );
  const counterDeclarations = sf.statements.filter(statement =>
    ts.isVariableStatement(statement) &&
    nodeText(statement, sf) === 'letnextTaskDetailsId=0;'
  );
  if (counterDeclarations.length !== 1) {
    errors.push('viewer must declare one module-scoped task details ID counter');
  }
  if (componentFunctions.length !== 1 || !componentFunctions[0].body) {
    errors.push('viewer must declare exactly one NacBpmnViewer function');
  } else {
    const componentStatements = componentFunctions[0].body.statements.map(statement =>
      nodeText(statement, sf)
    );
    for (const requiredStatement of [
      'consttaskDetailsIdRef=React.useRef<string|null>(null);',
      "if(taskDetailsIdRef.current===null){nextTaskDetailsId+=1;taskDetailsIdRef.current='nac-selected-task-details-'+nextTaskDetailsId;}",
      'consttaskDetailsId=taskDetailsIdRef.current;',
      "consttaskDetailsHeadingId=taskDetailsId+'-heading';"
    ]) {
      if (componentStatements.filter(statement => statement === requiredStatement).length !== 1) {
        errors.push('viewer missing stable per-instance details ID statement: ' + requiredStatement);
      }
    }
  }

  const markerCalls = calls(sf, sf, node =>
    ts.isPropertyAccessExpression(node.expression) &&
    nodeText(node.expression.expression, sf) === 'canvas' &&
    node.expression.name.text === 'addMarker'
  );
  const canonicalMarkerPredicate = propertyCall(
    'canvas', 'addMarker', ['currentTask.stepCode', "'nac-current-step'"]
  );
  const initialSelectionPredicate = propertyCall(
    'canvas', 'addMarker', ['currentTask.stepCode', "'nac-selected-step'"]
  );
  const canonicalMarkerCalls = markerCalls.filter(node => canonicalMarkerPredicate(node, sf));
  const initialSelectionCalls = markerCalls.filter(node => initialSelectionPredicate(node, sf));
  if (markerCalls.length !== 2 || canonicalMarkerCalls.length !== 1) {
    errors.push('viewer must contain exactly one current marker plus one initial selection marker');
  } else {
    if (!isSuccessfulImportPath(canonicalMarkerCalls[0], sf)) {
      errors.push('canonical marker call must be inside the successful importXML callback');
    }
    if (!isCanonicalNonCurrentTaskLoop(canonicalMarkerCalls[0], sf)) {
      errors.push('viewer must directly resolve and guard every non-current BPMN task');
    }
  }
  if (initialSelectionCalls.length !== 1 || canonicalMarkerCalls.length !== 1) {
    errors.push('viewer must initialize exactly one selected marker at currentTask.stepCode');
  } else {
    const currentStatement = canonicalMarkerCalls[0].parent;
    const selectedStatement = initialSelectionCalls[0].parent;
    const successBlock = currentStatement.parent;
    const currentIndex = ts.isBlock(successBlock) ? successBlock.statements.indexOf(currentStatement) : -1;
    const selectedIndex = ts.isBlock(successBlock) ? successBlock.statements.indexOf(selectedStatement) : -1;
    if (!ts.isExpressionStatement(currentStatement) || !ts.isExpressionStatement(selectedStatement) ||
        selectedStatement.parent !== successBlock || selectedIndex !== currentIndex + 1) {
      errors.push('initial selected marker must immediately follow the current marker');
    }
  }
  if (calls(sf, sf, propertyCall(
    'elementRegistry', 'get', ['currentTask.stepCode']
  )).length !== 1) {
    errors.push('viewer must resolve currentTask.stepCode exactly once');
  }
  const requiredViewerCalls = [
    [propertyCall('elementRegistry', 'get', ['task.stepCode']), 'every non-current task binding'],
    [propertyCall('taskIds', 'has', ['task.taskId']), 'duplicate taskId guard'],
    [propertyCall('taskIds', 'add', ['task.taskId']), 'taskId uniqueness registration'],
    [propertyCall('stepCodes', 'has', ['task.stepCode']), 'duplicate stepCode guard'],
    [propertyCall('stepCodes', 'add', ['task.stepCode']), 'stepCode uniqueness registration'],
    [propertyCall(
      'runtime.canvas', 'removeMarker', ['runtime.selectedStepCode', "'nac-selected-step'"]
    ), 'previous selected-marker removal'],
    [propertyCall(
      'runtime.canvas', 'addMarker', ['task.stepCode', "'nac-selected-step'"]
    ), 'next selected-marker addition'],
    [propertyCall('runtime', 'failClosed', []), 'marker-transition fail-closed path']
  ];
  for (const [predicate, label] of requiredViewerCalls) {
    if (calls(sf, sf, predicate).length !== 1) {
      errors.push(`viewer must contain exactly one ${label}`);
    }
  }
  for (const expectedCall of [
    "setState({kind:'ready',workspace,selectedTaskId:currentTask.taskId})",
    'setState({...state,selectedTaskId:task.taskId})'
  ]) {
    if (calls(sf, sf, node => nodeText(node, sf) === expectedCall).length !== 1) {
      errors.push(`viewer missing exact selected-state binding: ${expectedCall}`);
    }
  }
  const taskTypeHelpers = sf.statements.filter(statement =>
    ts.isFunctionDeclaration(statement) &&
    statement.name?.text === 'isCanonicalBpmnTask'
  );
  if (taskTypeHelpers.length !== 1) {
    errors.push('viewer must declare exactly one isCanonicalBpmnTask helper');
  } else {
    const taskTypeHelper = taskTypeHelpers[0];
    const instanceOfCalls = calls(taskTypeHelper, sf, propertyCall(
      'businessObject', '$instanceOf', ["'bpmn:Task'"]
    ));
    if (instanceOfCalls.length !== 1) {
      errors.push("task helper must call businessObject.$instanceOf('bpmn:Task') exactly once");
    } else {
      const comparison = instanceOfCalls[0].parent;
      if (!ts.isBinaryExpression(comparison) ||
          comparison.operatorToken.kind !== ts.SyntaxKind.EqualsEqualsEqualsToken ||
          comparison.right.kind !== ts.SyntaxKind.TrueKeyword) {
        errors.push("bpmn:Task $instanceOf result must be compared with === true");
      }
    }
    const returnExpressions = [];
    let elementTypeReadCount = 0;
    const visitTaskTypeHelper = node => {
      if (ts.isReturnStatement(node) && node.expression) {
        returnExpressions.push(nodeText(node.expression, sf));
      }
      if (ts.isPropertyAccessExpression(node) &&
          nodeText(node, sf) === 'element.type') {
        elementTypeReadCount += 1;
      }
      ts.forEachChild(node, visitTaskTypeHelper);
    };
    visitTaskTypeHelper(taskTypeHelper);
    const exactTaskCheck =
      "element.id===expectedStepCode&&typeofbusinessObject?.$instanceOf==='function'&&" +
      "businessObject.$instanceOf('bpmn:Task')===true";
    if (returnExpressions.filter(expression => expression === exactTaskCheck).length !== 1) {
      errors.push('task helper must bind exact element ID and exact bpmn:Task supertype');
    }
    if (elementTypeReadCount !== 0) {
      errors.push('task helper must not infer BPMN inheritance from element.type');
    }
  }
  if (calls(sf, sf, propertyCall('canvas', 'resized', [])).length !== 1) {
    errors.push('viewer must define exactly one canvas.resized call site');
  }
  const disconnectCount = calls(sf, sf, node =>
    ts.isPropertyAccessExpression(node.expression) &&
    node.expression.name.text === 'disconnect' &&
    nodeText(node.expression.expression, sf) === 'resizeObserver'
  ).length;
  if (disconnectCount < 2) errors.push('viewer must disconnect ResizeObserver on failure and cleanup');

  let attributeCount = 0;
  let selectedAttributeCount = 0;
  let taskButtonCount = 0;
  let taskDetailsSectionCount = 0;
  let taskDetailsHeadingCount = 0;
  let dueExpressionCount = 0;
  let approvalExpressionCount = 0;
  const thrown = [];
  const stringLiterals = [];
  const visit = node => {
    if (ts.isJsxAttribute(node) && node.name.text === 'data-nac-current-step') {
      attributeCount += 1;
      const expression = node.initializer && ts.isJsxExpression(node.initializer)
        ? node.initializer.expression : undefined;
      if (!expression || nodeText(expression, sf) !== 'currentTask?.stepCode') {
        errors.push('data-nac-current-step must bind exactly to currentTask?.stepCode');
      }
    }
    if (ts.isJsxAttribute(node) && node.name.text === 'data-nac-selected-step') {
      selectedAttributeCount += 1;
      const expression = node.initializer && ts.isJsxExpression(node.initializer)
        ? node.initializer.expression : undefined;
      if (!expression || nodeText(expression, sf) !== 'selectedTask?.stepCode') {
        errors.push('data-nac-selected-step must bind exactly to selectedTask?.stepCode');
      }
    }
    if (ts.isJsxOpeningElement(node) && nodeText(node.tagName, sf) === 'button') {
      taskButtonCount += 1;
      const attributes = new Map(node.attributes.properties
        .filter(property => ts.isJsxAttribute(property))
        .map(attribute => [attribute.name.text, attribute.initializer
          ? nodeText(attribute.initializer, sf) : '']));
      const expectedAttributes = new Map([
        ['type', '"button"'],
        ['data-nac-task-id', '{task.taskId}'],
        ['aria-pressed', '{task.taskId===selectedTaskId}'],
        ['aria-controls', '{taskDetailsId}'],
        ['onClick', '{()=>selectTask(task.taskId)}']
      ]);
      for (const [name, expected] of expectedAttributes) {
        if (attributes.get(name) !== expected) {
          errors.push(`native task button must bind ${name} exactly to ${expected}`);
        }
      }
      if (attributes.has('onKeyDown') || attributes.has('onKeyUp')) {
        errors.push('native task button must not duplicate keyboard activation handlers');
      }
    }
    if (ts.isJsxOpeningElement(node) && nodeText(node.tagName, sf) === 'section') {
      const attributes = new Map(node.attributes.properties
        .filter(property => ts.isJsxAttribute(property))
        .map(attribute => [attribute.name.text, attribute.initializer
          ? nodeText(attribute.initializer, sf) : '']));
      if (attributes.get('className') === '{styles.taskDetails}') {
        taskDetailsSectionCount += 1;
        if (attributes.get('id') !== '{taskDetailsId}' ||
            attributes.get('aria-labelledby') !== '{taskDetailsHeadingId}') {
          errors.push('task details section must bind per-instance IDs');
        }
      }
    }
    if (ts.isJsxOpeningElement(node) && nodeText(node.tagName, sf) === 'h3') {
      const id = node.attributes.properties.find(property =>
        ts.isJsxAttribute(property) && property.name.text === 'id'
      );
      if (id && ts.isJsxAttribute(id) && id.initializer &&
          nodeText(id.initializer, sf) === '{taskDetailsHeadingId}') {
        taskDetailsHeadingCount += 1;
      }
    }
    if (ts.isStringLiteral(node)) stringLiterals.push(node.text);
    if (ts.isJsxText(node)) {
      const text = node.text.trim();
      if (text) stringLiterals.push(text);
    }
    if (ts.isConditionalExpression(node)) {
      const expression = nodeText(node, sf);
      if (expression === "selectedTask.dueAt?formatTimestamp(selectedTask.dueAt):'KeineeigeneFrist'") {
        dueExpressionCount += 1;
      }
      if (expression === "selectedTask.requiresNotaryApproval?'NotarielleFreigabeerforderlich':'KeinenotarielleFreigabeerforderlich'") {
        approvalExpressionCount += 1;
      }
    }
    if (ts.isThrowStatement(node) && node.expression &&
        ts.isNewExpression(node.expression) &&
        ts.isIdentifier(node.expression.expression) &&
        node.expression.expression.text === 'Error' &&
        node.expression.arguments?.length === 1 &&
        ts.isStringLiteral(node.expression.arguments[0])) {
      thrown.push(node.expression.arguments[0].text);
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  if (selectedAttributeCount !== 1) {
    errors.push('viewer must declare data-nac-selected-step exactly once');
  }
  if (taskButtonCount !== 1) {
    errors.push('viewer must declare exactly one mapped native task button source');
  }
  if (taskDetailsSectionCount !== 1 || taskDetailsHeadingCount !== 1) {
    errors.push('viewer must bind one per-instance task details section and heading');
  }
  if (dueExpressionCount !== 1) {
    errors.push('viewer must render exact own-deadline or Keine eigene Frist semantics');
  }
  if (approvalExpressionCount !== 1) {
    errors.push('viewer must render exact notarial-approval semantics');
  }
  for (const requiredLiteral of [
    'Ausgewählte Aufgabe',
    'Status',
    'Eigene Frist',
    'Freigabe',
    'Zugeordnet (assigned)',
    'Vertretung (deputy)'
  ]) {
    if (!stringLiterals.includes(requiredLiteral)) {
      errors.push(`viewer missing required task-navigation literal: ${requiredLiteral}`);
    }
  }
  if (attributeCount !== 1) errors.push('viewer must declare data-nac-current-step exactly once');
  for (const message of [
    'Current BPMN task is missing.',
    'Current BPMN element is missing.',
    'Task BPMN element is missing.',
    'Duplicate taskId is not allowed.',
    'Duplicate stepCode is not allowed.'
  ]) {
    if (!thrown.includes(message)) errors.push(`viewer must fail closed with ${message}`);
  }
  return errors;
}

function activeTests(sourceFile) {
  const result = new Map();
  for (const call of calls(sourceFile, sourceFile,
    node => ts.isIdentifier(node.expression) && node.expression.text === 'it')) {
    if (!isDirectActiveTest(call)) continue;
    if (call.arguments.length < 2 || !ts.isStringLiteral(call.arguments[0])) continue;
    const callback = call.arguments[1];
    if (!ts.isArrowFunction(callback) && !ts.isFunctionExpression(callback)) continue;
    const title = call.arguments[0].text;
    result.set(title, [...(result.get(title) || []), callback]);
  }
  return result;
}

function validateTests(source) {
  const errors = [];
  const sf = parse(source, 'NacBpmnViewer.test.tsx', ts.ScriptKind.TSX);
  if (!hasCanonicalSourceFileEnvelope(sf)) {
    errors.push("test source file must match the canonical import, fixture, helper, mock, and suite envelope");
  }
  if (hasForbiddenJestRegistrationMutation(sf)) {
    errors.push("Jest registration globals must not be declared, assigned, incremented, or deleted");
  }
  const tests = activeTests(sf);
  for (const title of Object.values(TITLES)) {
    if ((tests.get(title) || []).length !== 1) {
      errors.push(`exactly one active direct it callback required: ${title}`);
    }
  }
  for (const title of Object.values(TITLES)) {
    for (const callback of tests.get(title) || []) {
      if (hasEarlyExit(callback)) {
        errors.push(`required test callback must not return or throw early: ${title}`);
      }
    }
  }
  const requireMatcher = (key, predicate, label) => {
    const callback = (tests.get(TITLES[key]) || [])[0];
    if (!callback) return;
    const found = directTestStatements(callback).filter(node => predicate(node, sf));
    if (found.length !== 1) errors.push(`${TITLES[key]} must directly assert ${label}`);
  };
  requireMatcher('current', matcher('addMarker', 'toHaveBeenCalledTimes', ['2']), 'two initial marker calls');
  requireMatcher('current', matcher(
    'addMarker', 'toHaveBeenNthCalledWith',
    ['1', "'Task_EntwurfAbstimmen'", "'nac-current-step'"]
  ), 'the canonical marker binding');
  requireMatcher('current', matcher(
    'addMarker', 'toHaveBeenNthCalledWith',
    ['2', "'Task_EntwurfAbstimmen'", "'nac-selected-step'"]
  ), 'the initial selection marker binding');
  requireMatcher('resize', matcher('resized', 'toHaveBeenCalledTimes', ['2']), 'two resize notifications');
  requireMatcher('resizeFailure', matcher('destroy', 'toHaveBeenCalledTimes', ['1']), 'fail-closed destruction');
  requireMatcher('missingElement', matcher('destroy', 'toHaveBeenCalledTimes', ['1']), 'unknown-element destruction');
  requireMatcher('missingTask', matcher('destroy', 'toHaveBeenCalledTimes', ['1']), 'missing-task destruction');
  requireMatcher('unmount', matcher(
    'resizeObserverDisconnect', 'toHaveBeenCalledTimes', ['1']
  ), 'observer disconnect');
  requireMatcher('unmount', matcher('destroy', 'toHaveBeenCalledTimes', ['1']), 'viewer destruction');
  requireMatcher('pointer', matcher(
    'removeMarker', 'toHaveBeenCalledWith',
    ["'Task_EntwurfAbstimmen'", "'nac-selected-step'"]
  ), 'previous selection-marker removal');
  requireMatcher('pointer', matcher(
    'addMarker', 'toHaveBeenCalledWith',
    ["'Task_NachweiseNachhalten'", "'nac-selected-step'"]
  ), 'deadline selection-marker addition');
  for (const key of ['enter', 'space']) {
    requireMatcher(key, matcher('deadlineButton.tagName', 'toBe', ["'BUTTON'"]),
      'native button tag semantics');
    requireMatcher(key, matcher(
      "deadlineButton.getAttribute('type')", 'toBe', ["'button'"]
    ), 'native button type semantics');
    requireMatcher(key, matcher('deadlineButton.onkeydown', 'toBeNull', []),
      'absence of a manual keydown handler');
    const callback = (tests.get(TITLES[key]) || [])[0];
    if (callback && hasForbiddenNativeButtonTestAction(callback, sf)) {
      errors.push(TITLES[key] + ' must not simulate keyboard activation with click or events');
    }
  }
  requireMatcher('instanceIds', matcher('viewers', 'toHaveLength', ['2']),
    'two rendered component instances');
  requireMatcher('instanceIds', matcher(
    'newSet([firstId,secondId]).size', 'toBe', ['2']
  ), 'two unique detail IDs');
  requireMatcher('instanceIds', matcher(
    'firstControls', 'toEqual', ['[firstId,firstId]']
  ), 'first-instance aria-controls bindings');
  requireMatcher('instanceIds', matcher(
    'secondControls', 'toEqual', ['[secondId,secondId]']
  ), 'second-instance aria-controls bindings');
  requireMatcher('instanceIds', matcher(
    'rerenderedIds', 'toEqual', ['[firstId,secondId]']
  ), 'stable detail IDs after rerender');
  for (const key of ['duplicateTaskId', 'duplicateStepCode', 'unknownBinding', 'fakeTaskType']) {
    requireMatcher(key, matcher('destroy', 'toHaveBeenCalledTimes', ['1']),
      'binding failure destruction');
  }
  requireMatcher('fakeTaskType', matcher(
    'fakeTaskElement.businessObject.$instanceOf', 'toHaveBeenCalledWith', ["'bpmn:Task'"]
  ), 'exact bpmn:Task supertype probe');
  requireMatcher('initialSelectionFailure', matcher(
    'destroy', 'toHaveBeenCalledTimes', ['1']
  ), 'initial selected-marker failure destruction');
  for (const key of ['removeSelectionFailure', 'addSelectionFailure']) {
    requireMatcher(key, matcher('resizeObserverDisconnect', 'toHaveBeenCalledTimes', ['1']),
      'marker-transition observer disconnect');
    requireMatcher(key, matcher('destroy', 'toHaveBeenCalledTimes', ['1']),
      'marker-transition viewer destruction');
  }
  return errors;
}

function currentStepCssRule(strokeWidth) {
  return `${CURRENT_STEP_SELECTOR} {
  fill: var(--current-step-fill) !important;
  stroke: var(--current-step-stroke) !important;
  stroke-width: ${strokeWidth} !important;
}`;
}

function validateStyles(source) {
  const sf = parse(source, 'NacBpmnViewer.styles.ts', ts.ScriptKind.TS);
  let css;
  const visit = node => {
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) &&
        node.name.text === 'nacBpmnViewerStyleSheet' &&
        node.initializer && ts.isNoSubstitutionTemplateLiteral(node.initializer)) {
      css = node.initializer.text;
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  if (css === undefined) return ['nacBpmnViewerStyleSheet must be a static template literal'];

  const activeCss = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const escaped = CURRENT_STEP_SELECTOR.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const rules = [...activeCss.matchAll(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`, 'g'))];
  if (rules.length !== 1) return ['exactly one active current-step CSS selector is required'];

  const errors = [];
  for (const declaration of [
    'fill: var(--current-step-fill) !important',
    'stroke: var(--current-step-stroke) !important',
    'stroke-width: 4px !important'
  ]) {
    if (!rules[0][1].includes(declaration)) {
      errors.push(`current-step CSS rule missing ${declaration}`);
    }
  }
  const selectedRules = [SELECTED_STEP_SELECTOR, SELECTED_ONLY_SELECTOR].map(selector => {
    const selectorPattern = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return [...activeCss.matchAll(new RegExp(`${selectorPattern}\\s*\\{([^}]*)\\}`, 'g'))];
  });
  if (selectedRules.some(ruleSet => ruleSet.length !== 1)) {
    errors.push('exactly one active selected-step and selected-only CSS selector are required');
  } else {
    if (!selectedRules[0][0][1].includes(
      'filter: drop-shadow(0 0 4px var(--selected-step-stroke))'
    )) {
      errors.push('selected-step CSS must preserve current styling with a separate shadow');
    }
    for (const declaration of [
      'stroke: var(--selected-step-stroke) !important',
      'stroke-width: 3px !important'
    ]) {
      if (!selectedRules[1][0][1].includes(declaration)) {
        errors.push(`selected-only CSS rule missing ${declaration}`);
      }
    }
  }
  return errors;
}

function assertRejected(name, validator, source, mutate) {
  if (!EXPECTED_SELF_TEST_NAMES.has(name)) {
    throw new Error('unexpected self-test name: ' + name);
  }
  if (executedSelfTestNames.has(name)) {
    throw new Error('duplicate self-test name: ' + name);
  }
  executedSelfTestNames.add(name);
  const changed = mutate(source);
  if (changed === source) throw new Error('self-test ' + name + ' changed nothing');
  if (validator(changed).length === 0) throw new Error('self-test ' + name + ' was accepted');
}

function run() {
  const viewer = fs.readFileSync(paths.viewer, 'utf8');
  const tests = fs.readFileSync(paths.tests, 'utf8');
  const testSourceDigest = crypto.createHash('sha256').update(tests, 'utf8').digest('hex');
  if (testSourceDigest !== EXPECTED_TEST_SOURCE_SHA256) {
    throw new Error('test source digest does not match the canonical verification contract');
  }
  const styles = fs.readFileSync(paths.styles, 'utf8');

  assertRejected('regex-decoy', validateViewer, viewer, source =>
    source.replace(
      "canvas.addMarker(currentTask.stepCode, 'nac-current-step');",
      "canvas.addMarker('wrong', 'wrong');\n        /canvas.addMarker(currentTask.stepCode, 'nac-current-step')/;"
    ));
  assertRejected('unreachable-marker', validateViewer, viewer, source =>
    source.replace(
      "canvas.addMarker(currentTask.stepCode, 'nac-current-step');",
      "if (false) { canvas.addMarker(currentTask.stepCode, 'nac-current-step'); }\n        canvas.addMarker('Task_Wrong', 'wrong-marker');"
    ));
  assertRejected('skipped-test', validateTests, tests, source =>
    source.replace(`it('${TITLES.current}'`, `it.skip('${TITLES.current}'`));
  assertRejected('helper-test', validateTests, tests, source =>
    source.replace(`it('${TITLES.current}'`, `helper.it('${TITLES.current}'`));
  assertRejected('unreachable-only-marker', validateViewer, viewer, source =>
    source.replace(
      "canvas.addMarker(currentTask.stepCode, 'nac-current-step');",
      "if (false) { canvas.addMarker(currentTask.stepCode, 'nac-current-step'); }"
    ));
  assertRejected('return-before-marker', validateViewer, viewer, source =>
    source.replace(
      "canvas.addMarker(currentTask.stepCode, 'nac-current-step');",
      "return;\n        canvas.addMarker(currentTask.stepCode, 'nac-current-step');"
    ));
  assertRejected('wrapped-suite', validateTests, tests, source =>
    `if (false) {\n${source}\n}`);
  assertRejected('skipped-suite', validateTests, tests, source =>
    source.replace(
      "describe('NaC BPMN viewer runtime boundary'",
      "describe.skip('NaC BPMN viewer runtime boundary'"
    ));
  assertRejected('early-return', validateTests, tests, source =>
    source.replace(
      `it('${TITLES.current}', async () => {`,
      `it('${TITLES.current}', async () => { return;`
    ));
  assertRejected('nested-assertion', validateTests, tests, source =>
    source.replace(
      'expect(addMarker).toHaveBeenCalledTimes(2);',
      'const neverCalled = (): void => { expect(addMarker).toHaveBeenCalledTimes(2); };'
    ));
  assertRejected('unreachable-assertion', validateTests, tests, source =>
    source.replace(
      'expect(addMarker).toHaveBeenCalledTimes(2);',
      'if (false) { expect(addMarker).toHaveBeenCalledTimes(2); }'
    ));
  assertRejected('missing-css', validateStyles, styles, source =>
    source.replace('stroke-width: 4px !important;', 'stroke-width: 2px !important;'));
  assertRejected('commented-css-decoy', validateStyles, styles, source => {
    const rule = currentStepCssRule('4px');
    return source.replace(rule, `/* ${rule} */\n${currentStepCssRule('0')}`);
  });
  assertRejected('task-supertype-substitution', validateViewer, viewer, source =>
    source.replace(
      "businessObject.$instanceOf('bpmn:Task') === true",
      "businessObject.$instanceOf('bpmn:AnythingTask') === true"
    ));
  assertRejected('task-id-check-removal', validateViewer, viewer, source =>
    source.replace('element.id === expectedStepCode &&', 'true &&'));
  assertRejected('skipped-fake-task-test', validateTests, tests, source =>
    source.replace(`it('${TITLES.fakeTaskType}'`, `it.skip('${TITLES.fakeTaskType}'`));

  assertRejected('selected-marker-binding', validateViewer, viewer, source =>
    source.replace(
      "canvas.addMarker(currentTask.stepCode, 'nac-selected-step');",
      "canvas.addMarker('Task_Wrong', 'nac-selected-step');"
    ));
  assertRejected('transition-marker-binding', validateViewer, viewer, source =>
    source.replace(
      "runtime.canvas.addMarker(task.stepCode, 'nac-selected-step');",
      "runtime.canvas.addMarker('Task_Wrong', 'nac-selected-step');"
    ));
  assertRejected('selected-step-attribute-binding', validateViewer, viewer, source =>
    source.replace(
      'data-nac-selected-step={selectedTask?.stepCode}',
      'data-nac-selected-step="Task_Wrong"'
    ));
  assertRejected('task-id-attribute-binding', validateViewer, viewer, source =>
    source.replace('data-nac-task-id={task.taskId}', 'data-nac-task-id="wrong"'));
  assertRejected('duplicate-task-id-guard', validateViewer, viewer, source =>
    source.replace('taskIds.has(task.taskId)', 'false'));
  assertRejected('manual-key-handler', validateViewer, viewer, source =>
    source.replace(
      'onClick={() => selectTask(task.taskId)}',
      'onClick={() => selectTask(task.taskId)} onKeyDown={() => selectTask(task.taskId)}'
    ));
  assertRejected('skipped-pointer-test', validateTests, tests, source =>
    source.replace(`it('${TITLES.pointer}'`, `it.skip('${TITLES.pointer}'`));
  assertRejected('missing-pointer-marker-assertion', validateTests, tests, source =>
    source.replace(
      "expect(removeMarker).toHaveBeenCalledWith('Task_EntwurfAbstimmen', 'nac-selected-step');",
      'expect(removeMarker).toBeDefined();'
    ));
  assertRejected('missing-selected-css', validateStyles, styles, source =>
    source.replace(
      'filter: drop-shadow(0 0 4px var(--selected-step-stroke));',
      'filter: none;'
    ));

  assertRejected('non-current-loop-false-guard', validateViewer, viewer, source =>
    source.replace(
      'if (!isCanonicalBpmnTask(taskElement, task.stepCode))',
      'if (false)'
    ));
  assertRejected('non-current-loop-missing-guard', validateViewer, viewer, source => {
    const guard = [
      '          if (!isCanonicalBpmnTask(taskElement, task.stepCode)) {',
      "            throw new Error('Task BPMN element is missing.');",
      '          }'
    ].join('\n');
    return source.replace(guard, '          void taskElement;');
  });
  assertRejected('conditional-return-before-test', validateTests, tests, source =>
    source.replace(
      "  it('" + TITLES.current + "'",
      "  if (true) { return; }\n  it('" + TITLES.current + "'"
    ));
  assertRejected('numeric-truthy-return-before-test', validateTests, tests, source =>
    source.replace(
      "  it('" + TITLES.current + "'",
      "  if (1) { return; }\n  it('" + TITLES.current + "'"
    ));
  assertRejected("jest-registration-reassignment", validateTests, tests, source =>
    source.replace(
      "  it('" + TITLES.current + "'",
      "  it = jest.fn() as unknown as jest.It;\n  it('" + TITLES.current + "'"
    ));
  assertRejected("jest-registration-shadow", validateTests, tests, source =>
    source.replace(
      "describe('NaC BPMN viewer runtime boundary'",
      "const describe = jest.fn() as unknown as jest.Describe;\ndescribe('NaC BPMN viewer runtime boundary'"
    ));
  assertRejected("dynamic-jest-registration-property", validateTests, tests, source =>
    source.replace(
      "  it('" + TITLES.current + "'",
      "  (globalThis as unknown as Record<string, unknown>)['i' + 't'] = jest.fn();\n  it('" + TITLES.current + "'"
    ));
  assertRejected("eager-jest-registration-argument", validateTests, tests, source =>
    source.replace(
      "  it('" + TITLES.current + "'",
      "  beforeEach(((globalThis as unknown as Record<string, unknown>)['i' + 't'] = jest.fn(), () => {}));\n  it('" + TITLES.current + "'"
    ));
  assertRejected("eager-describe-title", validateTests, tests, source =>
    source.replace(
      "describe('NaC BPMN viewer runtime boundary', () => {",
      "it('validator decoy', () => {});\ndescribe(((globalThis as unknown as Record<string, unknown>)['i' + 't'] = jest.fn(), 'NaC BPMN viewer runtime boundary'), () => {"
    ));
  assertRejected("top-level-jest-registration-mutation", validateTests, tests, source =>
    source.replace(
      "describe('NaC BPMN viewer runtime boundary'",
      "it('validator decoy', () => {});\n(globalThis as unknown as Record<string, unknown>)['i' + 't'] = jest.fn();\ndescribe('NaC BPMN viewer runtime boundary'"
    ));
  assertRejected("suite-suffix-mutation", validateTests, tests, source =>
    source.replace(
      "  async function renderAndFlush(",
      "  (globalThis as unknown as Record<string, unknown>)['i' + 't'] = jest.fn();\n  async function renderAndFlush("
    ));
  assertRejected('conditional-throw-before-test', validateTests, tests, source =>
    source.replace(
      "  it('" + TITLES.current + "'",
      "  if (!false) { throw new Error('stop'); }\n  it('" + TITLES.current + "'"
    ));
  assertRejected('skipped-instance-id-test', validateTests, tests, source =>
    source.replace(
      "it('" + TITLES.instanceIds + "'",
      "it.skip('" + TITLES.instanceIds + "'"
    ));
  assertRejected('details-id-binding', validateViewer, viewer, source =>
    source.replace('aria-controls={taskDetailsId}', 'aria-controls="shared-details"'));
  assertRejected('keyboard-test-click', validateTests, tests, source =>
    source.replace(
      "    expect(deadlineButton.tagName).toBe('BUTTON');",
      "    deadlineButton.click();\n    expect(deadlineButton.tagName).toBe('BUTTON');"
    ));

  if (EXPECTED_SELF_TEST_NAMES.size < MINIMUM_SELF_TEST_COUNT) {
    throw new Error('self-test registry is below the required minimum');
  }
  const missingSelfTests = [...EXPECTED_SELF_TEST_NAMES].filter(name =>
    !executedSelfTestNames.has(name)
  );
  if (executedSelfTestNames.size !== EXPECTED_SELF_TEST_NAMES.size ||
      missingSelfTests.length !== 0) {
    throw new Error('missing expected self-tests: ' + missingSelfTests.join(', '));
  }

  return [
    ...validateViewer(viewer),
    ...validateTests(tests),
    ...validateStyles(styles)
  ];
}

try {
  const errors = run();
  if (errors.length) {
    console.error('STATUS: FAILED');
    errors.forEach(error => console.error(`ERROR: ${error}`));
    process.exitCode = 1;
  } else {
    console.log('STATUS: PASSED');
    console.log('OK: current BPMN step source, tests, and marker CSS are AST-bound.');
  }
} catch (error) {
  console.error('STATUS: FAILED');
  console.error(`ERROR: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
