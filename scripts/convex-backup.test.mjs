import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, writeFile, readFile } from "node:fs/promises";
import { join } from "node:path";
import { createBackup, verifyBackup, restoreObjects, digest } from "./convex-backup.mjs";
await mkdir(".runtime/backups",{recursive:true});
async function fixture(){
  const directory=join(await mkdtemp(".runtime/backups/backup-test-"),"archive");
  const body=Buffer.from("original media");
  const row={id:"asset",project_id:"project",object_key:"projects/project/originals/asset",metadata:JSON.stringify({sha256:digest(body),sizeBytes:body.length})};
  const snapshot={projects:[],project_events:[],operator_sessions:[],assets:[row],upload_intents:[],audio_analysis_jobs:[],transcription_jobs:[]};
  const client={async send(){return {ContentLength:body.length,Body:{transformToByteArray:async()=>body}};}};
  return {directory,body,row,snapshot,client};
}
test("backup verifies all referenced bytes and detects subsequent object corruption",async()=>{
  const f=await fixture();
  const receipt=await createBackup(f.snapshot,"mvvm",f.client,f.directory);
  assert.deepEqual((await verifyBackup(f.directory,receipt.manifestSha256)).snapshot,f.snapshot);
  await writeFile(join(f.directory,"objects",digest(f.body)),"corrupted");
  await assert.rejects(verifyBackup(f.directory,receipt.manifestSha256),/checksum/);
});
test("manifest or snapshot modification invalidates the pinned receipt",async()=>{
  const f=await fixture();
  const receipt=await createBackup(f.snapshot,"mvvm",f.client,f.directory);
  await writeFile(join(f.directory,"snapshot.json"),"{}");
  await assert.rejects(verifyBackup(f.directory,receipt.manifestSha256),/snapshot checksum/);
  const path=join(f.directory,"manifest.json");
  await writeFile(path,(await readFile(path,"utf8"))+" ");
  await assert.rejects(verifyBackup(f.directory,receipt.manifestSha256),/manifest checksum/);
});
test("missing pending uploads are retained but missing committed media fails",async()=>{
  const f=await fixture();
  const missing={async send(){throw {$metadata:{httpStatusCode:404}};}};
  f.snapshot.upload_intents=f.snapshot.assets;f.snapshot.assets=[];
  const receipt=await createBackup(f.snapshot,"mvvm",missing,f.directory);
  assert.equal((await verifyBackup(f.directory,receipt.manifestSha256)).manifest.objects[0].state,"missing");
  const required=await fixture();
  await assert.rejects(createBackup(required.snapshot,"mvvm",missing,required.directory));
});
test("ownership and original checksums are enforced before acceptance",async()=>{
  const f=await fixture();
  f.row.project_id="other";
  await assert.rejects(createBackup(f.snapshot,"mvvm",f.client,f.directory),/ownership/);
  f.row.project_id="project";f.row.metadata=JSON.stringify({sha256:"a".repeat(64),sizeBytes:f.body.length});
  await assert.rejects(createBackup(f.snapshot,"mvvm",f.client,f.directory),/integrity/);
});

test("restore revokes sessions, quarantines queued work and preserves receipts",async()=>{
  const f=await fixture();
  f.snapshot.operator_sessions=[{id:"session",revoked_at:null}];
  f.snapshot.transcription_jobs=[{id:"job",status:"queued",receipt:"saved",result:null}];
  const backup=await createBackup(f.snapshot,"music-vending-machine",f.client,f.directory);
  const stored=new Map();
  const target={async send(command){
    const {Key,Body,IfNoneMatch}=command.input;
    if(Body){assert.equal(IfNoneMatch,"*");stored.set(Key,Buffer.from(Body));return {};}
    const bytes=stored.get(Key);return {ContentLength:bytes.length,Body:{transformToByteArray:async()=>bytes}};
  }};
  const restored=await restoreObjects(f.directory,backup.manifestSha256,target,"mvvm","2026-09-26T10:00:00Z");
  assert.equal(restored.operator_sessions[0].revoked_at,"2026-09-26T10:00:00Z");
  assert.equal(restored.transcription_jobs[0].status,"reconciliation_required");
  assert.equal(restored.transcription_jobs[0].receipt,"saved");
  assert.equal(f.snapshot.transcription_jobs[0].status,"queued");
  await assert.rejects(restoreObjects(f.directory,backup.manifestSha256,target,"music-vending-machine"),/separate/);
});

test("restore refuses conflicting destination bytes",async()=>{
  const f=await fixture();
  const backup=await createBackup(f.snapshot,"music-vending-machine",f.client,f.directory);
  const target={async send(command){
    if(command.input.Body)throw {$metadata:{httpStatusCode:412}};
    return {ContentLength:1,Body:{transformToByteArray:async()=>Buffer.from("x")}};
  }};
  await assert.rejects(restoreObjects(f.directory,backup.manifestSha256,target,"mvvm"),/differs/);
});

test("same-bucket recovery is explicit, fills missing objects and retries without overwriting",async()=>{
  const f=await fixture();
  f.snapshot.operator_sessions=[{id:"session",revoked_at:null}];
  f.snapshot.audio_analysis_jobs=[{id:"job",status:"submitting",receipt:"retained",result:null}];
  const backup=await createBackup(f.snapshot,"mvvm",f.client,f.directory);
  const stored=new Map();let calls=0,writes=0;
  const target={async send(command){
    calls++;
    const {Bucket,Key,Body,IfNoneMatch}=command.input;
    assert.equal(Bucket,"mvvm");
    if(Body!==undefined){
      assert.equal(IfNoneMatch,"*");
      if(stored.has(Key))throw {$metadata:{httpStatusCode:412}};
      stored.set(Key,Buffer.from(Body));writes++;return {};
    }
    const bytes=stored.get(Key);
    return {ContentLength:bytes.length,Body:{transformToByteArray:async()=>bytes}};
  }};
  await assert.rejects(restoreObjects(f.directory,backup.manifestSha256,target,"mvvm"),/explicit/);
  assert.equal(calls,0);
  const now="2026-09-26T12:00:00Z";
  const restored=await restoreObjects(f.directory,backup.manifestSha256,target,"mvvm",now,{allowSameBucket:true});
  assert.deepEqual(stored.get(f.row.object_key),f.body);
  assert.equal(restored.operator_sessions[0].revoked_at,now);
  assert.equal(restored.audio_analysis_jobs[0].status,"reconciliation_required");
  assert.equal(restored.audio_analysis_jobs[0].receipt,"retained");
  assert.deepEqual(await restoreObjects(f.directory,backup.manifestSha256,target,"mvvm",now,{allowSameBucket:true}),restored);
  assert.equal(writes,1);
  stored.set(f.row.object_key,Buffer.from("newer conflicting bytes"));
  await assert.rejects(restoreObjects(f.directory,backup.manifestSha256,target,"mvvm",now,{allowSameBucket:true}),/differs/);
  assert.equal(stored.get(f.row.object_key).toString(),"newer conflicting bytes");
  assert.equal(writes,1);
  assert.deepEqual((await verifyBackup(f.directory,backup.manifestSha256)).snapshot,f.snapshot);
});

test("same-bucket restore retains missing and incomplete upload state without promotion",async()=>{
  const f=await fixture();
  const incomplete=Buffer.from("partial");
  f.snapshot.assets=[];
  f.snapshot.upload_intents=[f.row,{...f.row,id:"missing",object_key:"projects/project/originals/missing"}];
  const source={async send(command){
    if(command.input.Key.endsWith("missing"))throw {$metadata:{httpStatusCode:404}};
    return {ContentLength:incomplete.length,Body:{transformToByteArray:async()=>incomplete}};
  }};
  const backup=await createBackup(f.snapshot,"mvvm",source,f.directory);
  const written=[];
  const target={async send(command){
    assert.equal(command.input.Key,f.row.object_key);
    if(command.input.Body!==undefined){written.push(Buffer.from(command.input.Body));return {};}
    return {ContentLength:incomplete.length,Body:{transformToByteArray:async()=>incomplete}};
  }};
  const restored=await restoreObjects(f.directory,backup.manifestSha256,target,"mvvm",undefined,{allowSameBucket:true});
  assert.deepEqual(written,[incomplete]);
  assert.deepEqual(restored.upload_intents,f.snapshot.upload_intents);
  assert.deepEqual(restored.assets,[]);
});
