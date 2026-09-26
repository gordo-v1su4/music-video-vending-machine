// Disposable local backend: never reads project deployment configuration or credentials.
import { spawnSync } from 'node:child_process';
import { randomBytes, randomUUID } from 'node:crypto';
import { cpSync, mkdtempSync, symlinkSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const stage = mkdtempSync(join(tmpdir(), 'mvvm-convex-test-'));
const name = `mvvm-test-${randomUUID()}`;
const image = 'ghcr.io/get-convex/convex-backend@sha256:d9b46c8a7f4ed7724dc9325b7a215d6818953bf8b951c884eb916ae890e0e3c9';
const env = { ...process.env };
const privateValues = [];
for (const key of Object.keys(env)) {
  if (/^(CONVEX_|MVVM_|MVM_|DATABASE_URL$)/.test(key)) delete env[key];
}
function run(command, args, options = {}) {
  const result = spawnSync(command, args, { cwd: root, env, encoding: 'utf8', ...options });
  if (result.error || result.status !== 0) {
    let diagnostic = result.stderr || result.error?.message || '';
    for (const value of privateValues) diagnostic = diagnostic.replaceAll(value, '[redacted]');
    throw new Error(`${command} failed: ${diagnostic}`);
  }
  return result.stdout?.trim();
}
try {
  run('docker', ['run', '--detach', '--rm', '--name', name, '-p', '127.0.0.1::3210',
    '-e', 'INSTANCE_NAME=mvvm-test', '-e', `INSTANCE_SECRET=${randomBytes(32).toString('hex')}`,
    '-e', 'DISABLE_BEACON=true', image]);
  const binding = run('docker', ['port', name, '3210/tcp']);
  if (!/^127\.0\.0\.1:\d+$/.test(binding)) throw new Error('Unexpected test listener');
  const url = `http://${binding}`;
  let healthy = false;
  for (let attempt = 0; attempt < 60; attempt++) {
    try { healthy = (await fetch(`${url}/version`, { signal: AbortSignal.timeout(2000) })).ok; } catch {}
    if (healthy) break;
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  if (!healthy) throw new Error('Disposable backend did not become healthy');
  const admin = run('docker', ['exec', name, './generate_admin_key.sh']);
  privateValues.push(admin);
  if (!admin || admin.includes('\n')) throw new Error('Unexpected test admin response');
  cpSync(join(root, 'convex'), join(stage, 'convex'), { recursive: true });
  cpSync(join(root, 'scripts/fixtures/convex-testing.ts'), join(stage, 'convex/testing.ts'));
  cpSync(join(root, 'convex.json'), join(stage, 'convex.json'));
  cpSync(join(root, 'package.json'), join(stage, 'package.json'));
  symlinkSync(join(root, 'node_modules'), join(stage, 'node_modules'), process.platform === 'win32' ? 'junction' : 'dir');
  writeFileSync(join(stage, '.env.local'), `CONVEX_SELF_HOSTED_URL=${url}\nCONVEX_SELF_HOSTED_ADMIN_KEY=${admin}\n`, { mode: 0o600 });
  run('node', [join(root, 'node_modules/convex/bin/main.js'), 'dev', '--once', '--typecheck', 'enable'], { cwd: stage });
  console.log('Disposable Convex schema deployed; running HTTP acceptance with fake providers.');
  run('cargo', ['test', '-p', 'mvm-coordinator', '--locked', '--test', 'sessions', '--test', 'persistence', '--test', 'analysis_jobs', '--test', 'transcription',
    'convex_', '--', '--ignored', '--test-threads=1'], {
    env: { ...env, MVVM_TEST_CONVEX_URL: url, MVVM_TEST_CONVEX_ADMIN_KEY: admin }, stdio: 'inherit',
  });
} finally {
  spawnSync('docker', ['rm', '--force', name], { stdio: 'ignore' });
  // Only this invocation's mkdtemp directory is removed, including its junction itself.
  rmSync(stage, { recursive: true, force: true });
}
