'use strict';

const fs = require('fs');
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
  unmount: 'destroys a ready viewer when the component unmounts'
};
const CURRENT_STEP_SELECTOR =
  '.nacBpmnViewer__workspace .djs-element.nac-current-step .djs-visual > :first-child';

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
  if (markerIndex !== 6) return false;
  const preceding = successBlock.statements.slice(0, markerIndex);
  const expectedShape = [
    ts.isVariableStatement,
    ts.isIfStatement,
    ts.isVariableStatement,
    ts.isVariableStatement,
    ts.isVariableStatement,
    ts.isIfStatement
  ];
  if (!preceding.every((item, index) => expectedShape[index](item))) return false;
  const guards = preceding
    .filter(item => ts.isIfStatement(item))
    .map(item => nodeText(item.expression, sourceFile));
  return guards.join('|') ===
    'currentTask===undefined|currentElement===undefined||currentElement===null';
}

function directTestStatements(callback) {
  if (!ts.isBlock(callback.body)) return [];
  return callback.body.statements
    .filter(statement => ts.isExpressionStatement(statement))
    .map(statement => statement.expression)
    .filter(expression => ts.isCallExpression(expression));
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
      !suiteCall.arguments.includes(suiteCallback) ||
      !ts.isIdentifier(suiteCall.expression) ||
      suiteCall.expression.text !== 'describe' ||
      !ts.isExpressionStatement(suiteStatement) ||
      !ts.isSourceFile(suiteStatement.parent)) {
    return false;
  }
  const testIndex = suiteBlock.statements.indexOf(testStatement);
  return !suiteBlock.statements.slice(0, testIndex).some(statement =>
    ts.isReturnStatement(statement) || ts.isThrowStatement(statement)
  );
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

function validateViewer(source) {
  const errors = [];
  const sf = parse(source, 'NacBpmnViewer.tsx', ts.ScriptKind.TSX);
  const markerCalls = calls(sf, sf, node =>
    ts.isPropertyAccessExpression(node.expression) &&
    nodeText(node.expression.expression, sf) === 'canvas' &&
    node.expression.name.text === 'addMarker'
  );
  const canonicalMarkerPredicate = propertyCall(
    'canvas', 'addMarker', ['currentTask.stepCode', "'nac-current-step'"]
  );
  const canonicalMarkerCalls = markerCalls.filter(node => canonicalMarkerPredicate(node, sf));
  if (markerCalls.length !== 1 || canonicalMarkerCalls.length !== 1) {
    errors.push('viewer must contain exactly one addMarker call with the canonical binding');
  } else if (!isSuccessfulImportPath(canonicalMarkerCalls[0], sf)) {
    errors.push('canonical marker call must be inside the successful importXML callback');
  }
  if (calls(sf, sf, propertyCall(
    'elementRegistry', 'get', ['currentTask.stepCode']
  )).length !== 1) {
    errors.push('viewer must resolve currentTask.stepCode exactly once');
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
  const thrown = [];
  const visit = node => {
    if (ts.isJsxAttribute(node) && node.name.text === 'data-nac-current-step') {
      attributeCount += 1;
      const expression = node.initializer && ts.isJsxExpression(node.initializer)
        ? node.initializer.expression : undefined;
      if (!expression || nodeText(expression, sf) !== 'currentTask?.stepCode') {
        errors.push('data-nac-current-step must bind exactly to currentTask?.stepCode');
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
  if (attributeCount !== 1) errors.push('viewer must declare data-nac-current-step exactly once');
  for (const message of [
    'Current BPMN task is missing.',
    'Current BPMN element is missing.'
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
  requireMatcher('current', matcher('addMarker', 'toHaveBeenCalledTimes', ['1']), 'one marker call');
  requireMatcher('current', matcher(
    'addMarker', 'toHaveBeenCalledWith',
    ["'Task_EntwurfAbstimmen'", "'nac-current-step'"]
  ), 'the canonical marker binding');
  requireMatcher('resize', matcher('resized', 'toHaveBeenCalledTimes', ['2']), 'two resize notifications');
  requireMatcher('resizeFailure', matcher('destroy', 'toHaveBeenCalledTimes', ['1']), 'fail-closed destruction');
  requireMatcher('missingElement', matcher('destroy', 'toHaveBeenCalledTimes', ['1']), 'unknown-element destruction');
  requireMatcher('missingTask', matcher('destroy', 'toHaveBeenCalledTimes', ['1']), 'missing-task destruction');
  requireMatcher('unmount', matcher(
    'resizeObserverDisconnect', 'toHaveBeenCalledTimes', ['1']
  ), 'observer disconnect');
  requireMatcher('unmount', matcher('destroy', 'toHaveBeenCalledTimes', ['1']), 'viewer destruction');
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
  return errors;
}

function assertRejected(name, validator, source, mutate) {
  const changed = mutate(source);
  if (changed === source) throw new Error(`self-test ${name} changed nothing`);
  if (validator(changed).length === 0) throw new Error(`self-test ${name} was accepted`);
}

function run() {
  const viewer = fs.readFileSync(paths.viewer, 'utf8');
  const tests = fs.readFileSync(paths.tests, 'utf8');
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
      'expect(addMarker).toHaveBeenCalledTimes(1);',
      'const neverCalled = (): void => { expect(addMarker).toHaveBeenCalledTimes(1); };'
    ));
  assertRejected('unreachable-assertion', validateTests, tests, source =>
    source.replace(
      'expect(addMarker).toHaveBeenCalledTimes(1);',
      'if (false) { expect(addMarker).toHaveBeenCalledTimes(1); }'
    ));
  assertRejected('missing-css', validateStyles, styles, source =>
    source.replace('stroke-width: 4px !important;', 'stroke-width: 2px !important;'));
  assertRejected('commented-css-decoy', validateStyles, styles, source => {
    const rule = currentStepCssRule('4px');
    return source.replace(rule, `/* ${rule} */\n${currentStepCssRule('0')}`);
  });

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
