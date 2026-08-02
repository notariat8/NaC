'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const packageRoot = path.resolve(__dirname, '..');
const sourceRoot = path.join(packageRoot, 'src');
const BFF_CLIENT = 'webparts/nacBpmnViewer/services/NacBffClient.ts';
const WEB_PART = 'webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts';
const EXPECTED_PRODUCTION_SOURCE_SHA256 = new Map([
  ['webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts', '148e0633d9c0dd950819a6910fc3114b1519c419fd90aee91c0afcda5353a7fa'],
  ['webparts/nacBpmnViewer/components/DiagramJs.styles.ts', 'c4bebc30c09d05152daa641df90e26ea8ce1311c421d3d3ec6730e5d1cdfdea0'],
  ['webparts/nacBpmnViewer/components/NacBpmnViewer.styles.ts', 'ab7265b95a38764177036e59babc80c7e44bb301ba43460326ed66c4e0839838'],
  ['webparts/nacBpmnViewer/components/NacBpmnViewer.tsx', '2e5e3bd8fcc4563ddb3d9a31b8aa8e841e10e74cafe9b17f410ede3028e55eac'],
  ['webparts/nacBpmnViewer/components/NacWorkbenchHost.styles.ts', '89dc903640f55dcab69cfd92836cd9466c80a73787c8198409a6c1d79fd97983'],
  ['webparts/nacBpmnViewer/components/NacWorkbenchHost.tsx', 'ecc076bf35fabee66c807a0e6a7f14b14eb43c452f01c12116b72633274247ff'],
  ['webparts/nacBpmnViewer/components/WorkspaceViewModel.ts', '1adcdd1ab8e894c1d86760d7ff6fe02bc4a34675e88bd0fc6163b6d5d46bfc87'],
  ['webparts/nacBpmnViewer/services/BpmnViewerRequestPlan.ts', 'd5b357e7b60f4de60152908d0356fab7233c73fe9e59584ec3f8ef4c2d324f4f'],
  ['webparts/nacBpmnViewer/services/NacBffClient.ts', 'eb73d4e9b6797fb2ae473118fd1f58a1c491488d9630bbf1a54c824f4f0c1d41'],
  ['workbench/core/WorkbenchContracts.ts', '8eebbb61b8d2b173568ba3022fcec20ccaf76d5a21f3be7dbec8707271db3fba'],
  ['workbench/core/WorkbenchSelectors.ts', '3e3dcf923d999254a5d92ecfbbab17642c5635d026a52bb3a0260607143b6a5c'],
  ['workbench/core/parseWorkbenchSnapshot.ts', '2db397063395acb473ced6559328d02ee2e4eeca7b4cca20b539e3d322f8e5df'],
  ['workbench/nac/NacWorkbenchProjection.ts', 'fcdb4d90b21b19e5bb97ddd96816e14a4d6067109c4113b9c0e9fe0a1d5f92b9'],
  ['workbench/react/WorkbenchPanel.styles.ts', '96fa6de6f294373d091b96daa80c5ca92487646a12506e7fd519abdf056519ff'],
  ['workbench/react/WorkbenchPanel.tsx', '4a181e0681ac11a1a5bb8ffa107f7b76a65e7ac90f0327b9eae02ad63efeecd4']
]);
const EXPECTED_EXPORTS = new Map([
  ['NAC_BFF_RESOURCE_URI', 'api://funktion8.de/nac-bff'],
  ['NAC_BFF_SCOPE', 'Matter.Read'],
  ['NAC_BFF_BASE_URL', 'https://func-nac-bff-test-funktion8.azurewebsites.net'],
  ['NAC_BFF_WORKSPACE_ID', 'notary_team_01'],
  ['NAC_BFF_MATTER_ID', 'NAC-SYN-MATTER-001'],
  ['NAC_BFF_PURPOSE', 'view_synthetic_matter_workspace']
]);
const ALLOWED_EXTERNAL_IMPORTS = new Set([
  'react',
  'react-dom',
  '@microsoft/sp-component-base',
  '@microsoft/sp-core-library',
  '@microsoft/sp-http',
  '@microsoft/sp-webpart-base',
  'bpmn-js/lib/Viewer'
]);
const FORBIDDEN_LITERAL_PARTS = ['graph.microsoft.com', '/_api/'];
const MUTATION_METHODS = new Set(['post', 'put', 'patch', 'delete', 'saveXML']);
const FORBIDDEN_NETWORK_METHODS = new Set(['fetch', 'sendBeacon', 'request', 'open', 'send']);
const FORBIDDEN_NETWORK_GLOBALS = new Set(['XMLHttpRequest', 'WebSocket', 'EventSource']);
const FORBIDDEN_NETWORK_IDENTIFIERS = new Set([
  'fetch', 'sendBeacon', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'require'
]);
const FORBIDDEN_RUNTIME_IDENTIFIERS = new Set(['eval', 'Function', 'Reflect']);

function staticPropertyName(node) {
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
  if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.PlusToken) {
    const left = staticPropertyName(node.left);
    const right = staticPropertyName(node.right);
    return left === undefined || right === undefined ? undefined : left + right;
  }
  return undefined;
}

const compact = (node, sourceFile) => node.getText(sourceFile).replace(/\s+/g, '');

function sourceFiles() {
  const result = new Map();
  const walk = directory => {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        walk(absolute);
      } else if (
        (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx')) &&
        !entry.name.endsWith('.test.ts') &&
        !entry.name.endsWith('.test.tsx')
      ) {
        result.set(path.relative(sourceRoot, absolute).replaceAll(path.sep, '/'), fs.readFileSync(absolute, 'utf8'));
      }
    }
  };
  walk(sourceRoot);
  return result;
}

function validateSource(relativePath, source) {
  const errors = [];
  const sourceFile = ts.createSourceFile(
    relativePath,
    source,
    ts.ScriptTarget.Latest,
    true,
    relativePath.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  );
  const getClientCalls = [];
  const bffGetCalls = [];
  const spHttpImportNames = [];

  const visit = node => {
    if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) {
      const moduleName = node.moduleSpecifier.text;
      if (!moduleName.startsWith('.') && !ALLOWED_EXTERNAL_IMPORTS.has(moduleName)) {
        errors.push(`${relativePath}: external import is not allowlisted: ${moduleName}`);
      }
      if (moduleName === '@microsoft/sp-http') {
        if (relativePath !== BFF_CLIENT) {
          errors.push(`${relativePath}: @microsoft/sp-http is allowed only in NacBffClient.ts`);
        }
        const bindings = node.importClause && node.importClause.namedBindings;
        if (!bindings || !ts.isNamedImports(bindings) || node.importClause.name) {
          errors.push(`${relativePath}: @microsoft/sp-http requires named imports`);
        } else {
          for (const specifier of bindings.elements) {
            if (specifier.propertyName) errors.push(`${relativePath}: aliased SP HTTP imports are forbidden`);
            spHttpImportNames.push(specifier.name.text);
          }
        }
      }
    }
    if (ts.isImportEqualsDeclaration(node)) {
      errors.push(`${relativePath}: import-equals declarations are forbidden`);
    }
    if (ts.isExportDeclaration(node) && node.moduleSpecifier) {
      errors.push(`${relativePath}: module re-exports are forbidden`);
    }
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      if (FORBIDDEN_LITERAL_PARTS.some(part => node.text.includes(part))) {
        errors.push(`${relativePath}: forbidden network literal ${node.text}`);
      }
    }
    if (ts.isNewExpression(node) && ts.isIdentifier(node.expression) &&
        FORBIDDEN_NETWORK_GLOBALS.has(node.expression.text)) {
      errors.push(`${relativePath}: network constructor ${node.expression.text} is forbidden`);
    }
    if (ts.isCallExpression(node)) {
      if (node.expression.kind === ts.SyntaxKind.ImportKeyword) {
        errors.push(`${relativePath}: dynamic import is forbidden`);
      }
      if (ts.isIdentifier(node.expression) && FORBIDDEN_NETWORK_METHODS.has(node.expression.text)) {
        errors.push(`${relativePath}: network call ${node.expression.text} is forbidden`);
      }
      if (ts.isPropertyAccessExpression(node.expression)) {
        const method = node.expression.name.text;
        if (MUTATION_METHODS.has(method) || FORBIDDEN_NETWORK_METHODS.has(method)) {
          errors.push(`${relativePath}: network or mutation method ${method} is forbidden`);
        }
        if (method === 'getClient') getClientCalls.push(node);
        if (method === 'get' && compact(node.expression.expression, sourceFile) === 'client') {
          bffGetCalls.push(node);
        }
      }
      if (ts.isElementAccessExpression(node.expression)) {
        const method = staticPropertyName(node.expression.argumentExpression);
        if (method !== undefined &&
            (MUTATION_METHODS.has(method) || FORBIDDEN_NETWORK_METHODS.has(method) ||
             FORBIDDEN_NETWORK_GLOBALS.has(method) || method === 'get')) {
          errors.push(`${relativePath}: computed network or HTTP method ${method} is forbidden`);
        }
      }
    }
    if (ts.isIdentifier(node) && ['MSGraphClient', 'GraphClient'].includes(node.text)) {
      errors.push(`${relativePath}: Graph client identifier ${node.text} is forbidden`);
    }
    if (ts.isIdentifier(node) && FORBIDDEN_NETWORK_IDENTIFIERS.has(node.text)) {
      errors.push(`${relativePath}: network identifier ${node.text} is forbidden`);
    }
    if (ts.isIdentifier(node) && FORBIDDEN_RUNTIME_IDENTIFIERS.has(node.text)) {
      errors.push(`${relativePath}: runtime reflection or compilation identifier ${node.text} is forbidden`);
    }
    if (ts.isPropertyAccessExpression(node) &&
        node.name.text === 'get' &&
        compact(node.expression, sourceFile) === 'client' &&
        (!ts.isCallExpression(node.parent) || node.parent.expression !== node)) {
      errors.push(`${relativePath}: client.get may only be referenced by the canonical call`);
    }
    if (ts.isElementAccessExpression(node)) {
      const propertyName = staticPropertyName(node.argumentExpression);
      if (propertyName !== undefined &&
          (FORBIDDEN_NETWORK_IDENTIFIERS.has(propertyName) ||
           FORBIDDEN_NETWORK_METHODS.has(propertyName) ||
           FORBIDDEN_NETWORK_GLOBALS.has(propertyName))) {
        errors.push(`${relativePath}: computed network property ${propertyName} is forbidden`);
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sourceFile);

  if (relativePath === BFF_CLIENT) {
    const expectedSpHttpImports = ['AadHttpClient', 'AadHttpClientFactory', 'HttpClientResponse'];
    if (JSON.stringify(spHttpImportNames.sort()) !== JSON.stringify(expectedSpHttpImports.sort())) {
      errors.push(`${relativePath}: SP HTTP imports must be exactly AadHttpClient, AadHttpClientFactory, and HttpClientResponse`);
    }
    for (const [name, expected] of EXPECTED_EXPORTS) {
      const matches = [];
      const findExport = node => {
        if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) &&
            node.name.text === name && node.initializer &&
            ts.isStringLiteral(node.initializer)) {
          matches.push(node.initializer.text);
        }
        ts.forEachChild(node, findExport);
      };
      findExport(sourceFile);
      if (matches.length !== 1 || matches[0] !== expected) {
        errors.push(`${relativePath}: ${name} must equal ${expected}`);
      }
    }
    if (getClientCalls.length !== 2 || getClientCalls.some(call =>
      compact(call, sourceFile) !== 'clientFactory.getClient(NAC_BFF_RESOURCE_URI)')) {
      errors.push(`${relativePath}: exactly two canonical BFF getClient calls are required`);
    }
    const expectedGets = [
      "client.get(workspaceUrl,AadHttpClient.configurations.v1,{signal,headers:{Accept:'application/json','X-Correlation-ID':createCorrelationId()}})",
      "client.get(workbenchUrl,AadHttpClient.configurations.v1,{signal,headers:{Accept:'application/json','X-Correlation-ID':createCorrelationId()}})"
    ].sort();
    if (bffGetCalls.length !== 2 ||
        JSON.stringify(bffGetCalls.map(call => compact(call, sourceFile)).sort()) !==
          JSON.stringify(expectedGets)) {
      errors.push(`${relativePath}: exactly two canonical AadHttpClient GETs are required`);
    }
    for (const [name, expectedInitializer] of [
      ['workspacePath', "'/v1/workspaces/'+NAC_BFF_WORKSPACE_ID+'/matters/'+NAC_BFF_MATTER_ID"],
      ['workspaceUrl', "NAC_BFF_BASE_URL+workspacePath+'?purpose='+encodeURIComponent(NAC_BFF_PURPOSE)"],
      ['workbenchPath', "'/v1/workspaces/'+NAC_BFF_WORKSPACE_ID+'/matters/'+NAC_BFF_MATTER_ID+'/workbench-snapshot'"],
      ['workbenchUrl', "NAC_BFF_BASE_URL+workbenchPath+'?purpose='+encodeURIComponent(NAC_BFF_PURPOSE)"]
    ]) {
      const matches = [];
      const findVariable = node => {
        if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) &&
            node.name.text === name && node.initializer) {
          matches.push(compact(node.initializer, sourceFile));
        }
        ts.forEachChild(node, findVariable);
      };
      findVariable(sourceFile);
      if (matches.length !== 1 || matches[0] !== expectedInitializer) {
        errors.push(`${relativePath}: ${name} must use the canonical bounded route`);
      }
    }
  } else {
    if (getClientCalls.length !== 0) {
      errors.push(`${relativePath}: getClient is allowed only in NacBffClient.ts`);
    }
    if (bffGetCalls.length !== 0) {
      errors.push(`${relativePath}: client.get is allowed only in NacBffClient.ts`);
    }
  }

  if (relativePath === WEB_PART) {
    const requiredDetail =
      'loadWorkspace:(signal:AbortSignal)=>loadNacBffWorkspace(this.context.aadHttpClientFactory,signal)';
    const requiredWorkbench =
      "loadSnapshot:(signal:AbortSignal)=>loadNacWorkbenchSnapshot(this.context.aadHttpClientFactory,expectedSubjectId??'',signal)";
    const requiredSubject =
      'expectedSubjectId=this.context.pageContext.aadInfo?.userId.toString()';
    const compactSource = compact(sourceFile, sourceFile);
    if (!compactSource.includes(requiredDetail)) {
      errors.push(`${relativePath}: web part must bind the canonical BPMN detail loader`);
    }
    if (!compactSource.includes(requiredWorkbench)) {
      errors.push(`${relativePath}: web part must bind the canonical workbench loader`);
    }
    if (!compactSource.includes(requiredSubject)) {
      errors.push(`${relativePath}: expected subject must come from authenticated AAD page context`);
    }
  }
  return errors;
}

function validateAll(files) {
  const errors = [];
  if (!files.has(BFF_CLIENT) || !files.has(WEB_PART)) {
    errors.push('canonical BFF client and web part sources are required');
  }
  if (JSON.stringify([...files.keys()].sort()) !==
      JSON.stringify([...EXPECTED_PRODUCTION_SOURCE_SHA256.keys()].sort())) {
    errors.push('production TS/TSX file set must match the positive capability manifest');
  }
  for (const [relativePath, source] of files) {
    const expectedDigest = EXPECTED_PRODUCTION_SOURCE_SHA256.get(relativePath);
    const actualDigest = crypto.createHash('sha256').update(source).digest('hex');
    if (expectedDigest !== actualDigest) {
      errors.push(relativePath + ': production source SHA-256 is not approved');
    }
    errors.push(...validateSource(relativePath, source));
  }
  return errors;
}

function assertRejected(name, files, relativePath, mutate) {
  const source = files.get(relativePath);
  if (source === undefined) throw new Error(`${name}: missing mutation source`);
  const mutated = mutate(source);
  if (mutated === source) throw new Error(`${name}: mutation changed nothing`);
  if (validateSource(relativePath, mutated).length === 0) {
    throw new Error(`${name}: mutation was accepted`);
  }
}

function run() {
  const files = sourceFiles();
  const bff = files.get(BFF_CLIENT);
  const webPart = files.get(WEB_PART);
  if (bff === undefined || webPart === undefined) {
    return ['canonical runtime sources are missing'];
  }
  assertRejected('resource-drift', files, BFF_CLIENT, source =>
    source.replace('api://funktion8.de/nac-bff', 'api://example.invalid/other'));
  assertRejected('scope-drift', files, BFF_CLIENT, source =>
    source.replace("'Matter.Read'", "'Matter.Write'"));
  assertRejected('base-url-drift', files, BFF_CLIENT, source =>
    source.replace('func-nac-bff-test-funktion8.azurewebsites.net', 'graph.microsoft.com'));
  assertRejected('mutation-method', files, BFF_CLIENT, source =>
    source.replace('client.get(workspaceUrl,', 'client.post(workspaceUrl,'));
  assertRejected('computed-method', files, BFF_CLIENT, source =>
    source.replace('client.get(workspaceUrl,', "client['get'](workspaceUrl,"));
  assertRejected('direct-fetch', files, BFF_CLIENT, source =>
    source + '\nvoid fetch(\"https://example.invalid\");\n');
  assertRejected('graph-import', files, BFF_CLIENT, source =>
    "import { Client } from '@microsoft/microsoft-graph-client';\n" + source);
  assertRejected('send-beacon', files, BFF_CLIENT, source =>
    source + '\nnavigator.sendBeacon("https://example.invalid", "x");\n');
  assertRejected('websocket', files, BFF_CLIENT, source =>
    source + '\nnew WebSocket("wss://example.invalid");\n');
  assertRejected('window-fetch', files, BFF_CLIENT, source =>
    source + '\nvoid window.fetch("https://example.invalid");\n');
  assertRejected('dynamic-import', files, BFF_CLIENT, source =>
    source + '\nvoid import("axios");\n');
  assertRejected('sp-http-client-import', files, BFF_CLIENT, source =>
    "import { SPHttpClient } from '@microsoft/sp-http';\n" + source);
  assertRejected('alternate-http-import', files, BFF_CLIENT, source =>
    "import axios from 'axios';\n" + source);
  assertRejected('send-beacon-alias', files, BFF_CLIENT, source =>
    source + '\nconst transmit = navigator.sendBeacon.bind(navigator);\nvoid transmit;\n');
  assertRejected('qualified-websocket', files, BFF_CLIENT, source =>
    source + '\nnew globalThis.WebSocket("wss://example.invalid");\n');
  assertRejected('computed-fetch', files, BFF_CLIENT, source =>
    source + '\nvoid window["fe" + "tch"]("https://example.invalid");\n');
  assertRejected('require-client', files, BFF_CLIENT, source =>
    source + '\nvoid require("axios");\n');
  assertRejected('aliased-canonical-get', files, BFF_CLIENT, source =>
    source.replace('const response = await client.get(workspaceUrl,', 'const alias = client.get.bind(client);\n  void alias;\n  const response = await client.get(workspaceUrl,'));
  assertRejected('reflection-client', files, BFF_CLIENT, source =>
    source + '\nvoid Reflect.get(window, "fe" + "tch");\n');
  assertRejected('runtime-compilation', files, BFF_CLIENT, source =>
    source + '\nvoid Function("return import(\\\"axios\\\")")();\n');
  assertRejected('export-from-client', files, BFF_CLIENT, source =>
    source + '\nexport * from "@microsoft/microsoft-graph-client";\n');
  assertRejected('import-equals-client', files, BFF_CLIENT, source =>
    'import Graph = require("@microsoft/microsoft-graph-client");\n' + source);
  assertRejected('webpart-loader-drift', files, WEB_PART, source =>
    source.replace(
      'loadNacBffWorkspace(this.context.aadHttpClientFactory, signal)',
      'loadNacBffWorkspace(otherFactory, signal)'
    ));
  assertRejected('webpart-workbench-loader-drift', files, WEB_PART, source =>
    source.replace(
      'loadNacWorkbenchSnapshot(\n        this.context.aadHttpClientFactory,',
      'loadNacWorkbenchSnapshot(\n        otherFactory,'
    ));
  assertRejected('workbench-route-drift', files, BFF_CLIENT, source =>
    source.replace(" + '/workbench-snapshot';", " + '/other-snapshot';"));
  return validateAll(files);
}

try {
  const errors = run();
  if (errors.length !== 0) {
    console.error('STATUS: FAILED');
    errors.forEach(error => console.error(`ERROR: ${error}`));
    process.exitCode = 1;
  } else {
    console.log('STATUS: PASSED');
    console.log('OK: production sources are SHA-bound to exactly two delegated read-only BFF GET capabilities.');
  }
} catch (error) {
  console.error('STATUS: FAILED');
  console.error(`ERROR: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
