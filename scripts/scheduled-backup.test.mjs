import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, cp, symlink, writeFile, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { backupDestination } from './backup-convex-live.mjs';
const execute=promisify(execFile);

test('backup destination rejects relative paths and extra arguments',async()=>{
  await assert.rejects(backupDestination(['relative']),/absolute/);
  await assert.rejects(backupDestination([resolve('.'),resolve('.')]),/absolute/);
});

test('installed runner re-verifies archives, preserves last success on failure and withholds raw diagnostics',async()=>{
  const root=await mkdtemp(join(tmpdir(),'mvvm-scheduled-test-'));
  await mkdir(join(root,'scripts'));
  await mkdir(join(root,'backups'));
  for(const file of ['run-scheduled-backup.mjs','convex-backup.mjs','backup-convex-live.mjs'])await cp(new URL(file,import.meta.url),join(root,'scripts',file));
  await symlink(resolve('node_modules'),join(root,'node_modules'),process.platform==='win32'?'junction':'dir');
  const secretsRunner=join(root,'fake-secrets.mjs');
  await writeFile(secretsRunner,`
    import {readFile,writeFile} from 'node:fs/promises';
    import {join} from 'node:path';
    import {randomUUID} from 'node:crypto';
    import {createBackup} from './scripts/convex-backup.mjs';
    if(process.env.MVVM_S3_SECRET_KEY)throw Error('Inherited app secret');
    if(process.env.CONVEX_SELF_HOSTED_URL!=='http://100.118.78.13:13210')throw Error('Wrong endpoint');
    for(const name of ['MVVM_S3_ACCESS_KEY','MVVM_S3_SECRET_KEY','MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY'])if(!process.argv.includes('--secret='+name))throw Error('Missing live credential request');
    const root=process.cwd(), mode=await readFile(join(root,'mode'),'utf8');
    if(mode==='fail'){console.error('PRIVATE_TEST_SENTINEL');process.exit(1);}
    const directory=join(root,'backups','convex-'+randomUUID());
    const snapshot={projects:[],project_events:[],operator_sessions:[],assets:[],upload_intents:[],audio_analysis_jobs:[],transcription_jobs:[]};
    const receipt=await createBackup(snapshot,'mvvm',{},directory);
    if(mode==='corrupt')await writeFile(join(directory,'snapshot.json'),'tampered');
    console.log(JSON.stringify({...receipt,directory,completedAt:new Date().toISOString(),state:'backup_verified'}));
  `);
  await writeFile(join(root,'backup-config.json'),JSON.stringify({secretsRunner,backupRoot:join(root,'backups')}));
  const run=()=>execute(process.execPath,[join(root,'scripts','run-scheduled-backup.mjs')],{env:{...process.env,MVVM_S3_SECRET_KEY:'stale'},cwd:root,windowsHide:true});
  await writeFile(join(root,'mode'),'pass');
  const result=await run();
  const success=await readFile(join(root,'last-success.json'),'utf8');
  assert.equal(JSON.parse(result.stdout).state,'backup_verified');
  assert.equal(JSON.parse(success).objects,0);
  for(const mode of ['corrupt','fail']){
    await writeFile(join(root,'mode'),mode);
    await assert.rejects(run(),error=>{
      assert.equal(error.code,1);
      assert.ok(!error.stderr.includes('PRIVATE_TEST_SENTINEL'));
      return true;
    });
    assert.equal(await readFile(join(root,'last-success.json'),'utf8'),success);
    assert.equal(JSON.parse(await readFile(join(root,'last-failure.json'),'utf8')).state,'failed');
  }
});
