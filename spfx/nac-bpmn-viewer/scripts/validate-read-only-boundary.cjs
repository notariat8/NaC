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
  ['webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts', '30e111316f4c9c0a2460b2d13b00c1042c5de4b59c6788954c3ae9302f2fc217'],
  ['webparts/nacBpmnViewer/components/NacBpmnViewer.styles.ts', 'ab7265b95a38764177036e59babc80c7e44bb301ba43460326ed66c4e0839838'],
  ['webparts/nacBpmnViewer/components/NacBpmnViewer.tsx', '1f52f331b87b9314e118ab0606b269e79b4b691632c0488a4226716a7832447a'],
  ['webparts/nacBpmnViewer/components/WorkspaceViewModel.ts', '1adcdd1ab8e894c1d86760d7ff6fe02bc4a34675e88bd0fc6163b6d5d46bfc87'],
  ['webparts/nacBpmnViewer/services/BpmnViewerRequestPlan.ts', 'd5b357e7b60f4de60152908d0356fab7233c73fe9e59584ec3f8ef4c2d324f4f'],
  ['webparts/nacBpmnViewer/services/NacBffClient.ts', '2af29f10107074f4fe0c303082fa3186b2fd8b9dfac9e8766eda44449970bfcd']
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
  'bpmn-js/lib/Viewer',
  'bpmn-js/dist/assets/diagram-js.css'
]);
const FORBIDDEN_LITERAL_PARTS = ['graph.microsoft.com', '/_api/'];
const MUTATION_METHODS = new Set(['post', 'put', 'patch', 'delete', 'saveXML']);
const FORBIDDEN_NETWORK_METHODS = new Set(['fetch', 'sendBeacon', 'request', 'open', 'send']);
const FORBIDDEN_NETWORK_GLOBALS = new Set(['XMLHttpRequest', 'WebSocket', 'EventSource']);
const FORBIDDEN_NETWORK_IDENTIFIERS = new Set([
  'fetch', 'sendBeacon', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'require'
]);

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
    if (getClientCalls.length !== 1 ||
        compact(getClientCalls[0], sourceFile) !==
          'clientFactory.getClient(NAC_BFF_RESOURCE_URI)') {
      errors.push(`${relativePath}: exactly one canonical BFF getClient call is required`);
    }
    if (bffGetCalls.length !== 1 ||
        compact(bffGetCalls[0], sourceFile) !==
          "client.get(url,AadHttpClient.configurations.v1,{signal,headers:{Accept:'application/json','X-Correlation-ID':createCorrelationId()}})") {
      errors.push(`${relativePath}: exactly one canonical AadHttpClient GET is required`);
    }
    for (const [name, expectedInitializer] of [
      ['path', "'/v1/workspaces/'+NAC_BFF_WORKSPACE_ID+'/matters/'+NAC_BFF_MATTER_ID"],
      ['url', "NAC_BFF_BASE_URL+path+'?purpose='+encodeURIComponent(NAC_BFF_PURPOSE)"]
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
    const required =
      'loadWorkspace:(signal:AbortSignal)=>loadNacBffWorkspace(this.context.aadHttpClientFactory,signal)';
    if (!compact(sourceFile, sourceFile).includes(required)) {
      errors.push(`${relativePath}: web part must bind the canonical BFF loader`);
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
  const changed = new Map(files);
  const source = changed.get(relativePath);
  if (source === undefined) throw new Error(`${name}: missing mutation source`);
  const mutated = mutate(source);
  if (mutated === source) throw new Error(`${name}: mutation changed nothing`);
  changed.set(relativePath, mutated);
  if (validateAll(changed).length === 0) {
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
    source.replace('client.get(url,', 'client.post(url,'));
  assertRejected('computed-method', files, BFF_CLIENT, source =>
    source.replace('client.get(url,', "client['get'](url,"));
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
    source.replace('const response = await client.get(url,', 'const alias = client.get.bind(client);\n  void alias;\n  const response = await client.get(url,'));
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
    console.log('OK: production sources are SHA-bound to one delegated read-only BFF GET capability.');
  }
} catch (error) {
  console.error('STATUS: FAILED');
  console.error(`ERROR: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
