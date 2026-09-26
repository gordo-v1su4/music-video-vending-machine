import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const runtime = resolve(root, '.runtime');
mkdirSync(runtime, { recursive: true });
const schemaFile = resolve(runtime, 'openapi.json');
const output = resolve(runtime, 'api.generated.d.ts');
const target = resolve(root, 'apps/web/src/lib/generated/api.d.ts');
const schema = execFileSync('cargo', ['run', '--locked', '--quiet', '-p', 'mvm-coordinator', '--', '--openapi'], { cwd: root, encoding: 'utf8' });
const operations = new Set();
for (const path of Object.values(JSON.parse(schema).paths)) {
  for (const [method, operation] of Object.entries(path)) {
    if (!['get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace'].includes(method)) continue;
    if (!operation.operationId || operations.has(operation.operationId)) {
      throw new Error(`Missing or duplicate OpenAPI operationId: ${operation.operationId}`);
    }
    operations.add(operation.operationId);
  }
}
writeFileSync(schemaFile, schema);
execFileSync(process.execPath, [resolve(root, 'apps/web/node_modules/openapi-typescript/bin/cli.js'), schemaFile, '-o', output], { cwd: root, stdio: 'inherit' });
const generated = readFileSync(output, 'utf8').replaceAll('\r\n', '\n');
if (process.argv.includes('--check')) {
  if (readFileSync(target, 'utf8').replaceAll('\r\n', '\n') !== generated) {
    console.error('API types differ from the Rust OpenAPI contract. Run node scripts/generate-contract.mjs.');
    process.exitCode = 1;
  } else console.log('Generated API contract matches Rust.');
} else {
  writeFileSync(target, generated);
  console.log('Updated generated API types.');
}
