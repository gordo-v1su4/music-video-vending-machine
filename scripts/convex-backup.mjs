import { createHash } from "node:crypto";
import { GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
export const digest=bytes=>createHash("sha256").update(bytes).digest("hex");

export function inventory(snapshot,bucket){
  if(!["mvvm","music-vending-machine"].includes(bucket))throw Error("Invalid backup bucket");
  const result=[];
  for(const table of ["assets","upload_intents"]){
    for(const row of snapshot[table]){
      const meta=JSON.parse(row.metadata);
      if(!row.object_key.startsWith(`projects/${row.project_id}/`) || row.object_key.split("/").some(part=>part===".."||part==="."))throw Error("Invalid asset ownership");
      result.push({table,id:row.id,bucket,key:row.object_key,sha256:meta.sha256,bytes:meta.sizeBytes,optional:table==="upload_intents"});
    }
  }
  for(const table of ["audio_analysis_jobs","transcription_jobs"]){
    for(const row of snapshot[table])for(const field of ["result","receipt"]){
      const ref=row[field];
      if(!ref||typeof ref==="string")continue;
      if(ref.kind!=="rustfs-json-v1"||ref.bucket!==bucket||ref.key!==`projects/${row.project_id}/mvvm/payloads/${ref.sha256}.json`||ref.bytes>8*1024*1024)throw Error("Invalid payload ownership");
      result.push({table,id:row.id,field,bucket,key:ref.key,sha256:ref.sha256,bytes:ref.bytes,optional:false});
    }
  }
  for(const item of result)if(!/^[a-f0-9]{64}$/.test(item.sha256)||!Number.isSafeInteger(item.bytes)||item.bytes<0||item.bytes>128*1024*1024)throw Error("Invalid object integrity metadata");
  return result;
}

export async function createBackup(snapshot,bucket,client,directory){
  const items=inventory(snapshot,bucket);
  await mkdir(directory,{recursive:false});
  await mkdir(join(directory,"objects"));
  const snapshotBytes=Buffer.from(JSON.stringify(snapshot));
  await writeFile(join(directory,"snapshot.json"),snapshotBytes,{flag:"wx"});
  const objects=[];
  for(const item of items){
    let response;
    try{response=await client.send(new GetObjectCommand({Bucket:item.bucket,Key:item.key}));}
    catch(error){
      if(item.optional&&error.$metadata?.httpStatusCode===404){objects.push({...item,state:"missing"});continue;}
      throw error;
    }
    if(!Number.isSafeInteger(response.ContentLength)||response.ContentLength>128*1024*1024)throw Error("Invalid stored object length");
    const bytes=Buffer.from(await response.Body.transformToByteArray());
    const storedSha256=digest(bytes);
    if(!item.optional&&(bytes.length!==item.bytes||storedSha256!==item.sha256))throw Error("Required object integrity failure");
    const filename=join(directory,"objects",storedSha256);
    try{await writeFile(filename,bytes,{flag:"wx"});}
    catch(error){if(error.code!=="EEXIST")throw error;}
    if(digest(await readFile(filename))!==storedSha256)throw Error("Backup object readback failure");
    objects.push({...item,state:bytes.length===item.bytes&&storedSha256===item.sha256?"verified":"incomplete",storedSha256,storedBytes:bytes.length});
  }
  const manifest={version:1,bucket,snapshotSha256:digest(snapshotBytes),objects};
  const text=JSON.stringify(manifest);
  await writeFile(join(directory,"manifest.json"),text,{flag:"wx"});
  const manifestSha256=digest(text);
  await verifyBackup(directory,manifestSha256);
  return {manifestSha256,objects:objects.length,bytes:objects.reduce((sum,item)=>sum+(item.storedBytes??0),0)};
}

export async function verifyBackup(directory,manifestSha256){
  const raw=await readFile(join(directory,"manifest.json"));
  if(!/^[a-f0-9]{64}$/.test(manifestSha256)||digest(raw)!==manifestSha256)throw Error("Backup manifest checksum mismatch");
  const manifest=JSON.parse(raw);
  if(manifest.version!==1)throw Error("Unsupported backup version");
  const snapshotBytes=await readFile(join(directory,"snapshot.json"));
  if(digest(snapshotBytes)!==manifest.snapshotSha256)throw Error("Backup snapshot checksum mismatch");
  const snapshot=JSON.parse(snapshotBytes);
  const expected=inventory(snapshot,manifest.bucket);
  if(expected.length!==manifest.objects.length)throw Error("Incomplete backup inventory");
  for(let i=0;i<expected.length;i++){
    const wanted=expected[i],item=manifest.objects[i];
    for(const [key,value] of Object.entries(wanted))if(item[key]!==value)throw Error("Backup inventory mismatch");
    if(item.state==="missing"&&wanted.optional)continue;
    if(!["verified","incomplete"].includes(item.state)||(!wanted.optional&&item.state!=="verified")||!/^[a-f0-9]{64}$/.test(item.storedSha256))throw Error("Invalid backup object state");
    const bytes=await readFile(join(directory,"objects",item.storedSha256));
    if(bytes.length!==item.storedBytes||digest(bytes)!==item.storedSha256)throw Error("Backup object checksum mismatch");
    if(item.state==="verified"&&(bytes.length!==wanted.bytes||item.storedSha256!==wanted.sha256))throw Error("Backup integrity mismatch");
  }
  return {snapshot,manifest};
}

export async function restoreObjects(directory,manifestSha256,client,targetBucket,now=new Date().toISOString()){
  const {snapshot,manifest}=await verifyBackup(directory,manifestSha256);
  if(!["mvvm","music-vending-machine"].includes(targetBucket)||targetBucket===manifest.bucket)throw Error("Restore requires a separate approved bucket");
  for(const item of manifest.objects){
    if(item.state==="missing")continue;
    const bytes=await readFile(join(directory,"objects",item.storedSha256));
    try{await client.send(new PutObjectCommand({Bucket:targetBucket,Key:item.key,Body:bytes,IfNoneMatch:"*"}));}
    catch(error){if(error.$metadata?.httpStatusCode!==412)throw error;}
    const response=await client.send(new GetObjectCommand({Bucket:targetBucket,Key:item.key}));
    if(response.ContentLength!==bytes.length || digest(await response.Body.transformToByteArray())!==item.storedSha256)throw Error("Restored object differs; never overwrite an existing object");
  }
  for(const row of snapshot.operator_sessions)if(row.revoked_at===null)row.revoked_at=now;
  for(const table of ["audio_analysis_jobs","transcription_jobs"]){
    for(const row of snapshot[table]){
      for(const field of ["result","receipt"])if(row[field]&&typeof row[field]==="object")row[field].bucket=targetBucket;
      // An old backup cannot prove that queued work was never submitted later.
      // Restore must never automatically replay a potentially paid request.
      if(["queued","running","submitting"].includes(row.status)){
        row.status="reconciliation_required";
        if(table==="audio_analysis_jobs")row.stage="reconciliation_required";
        row.message="Restored from backup; reconcile provider state before any further submission.";
        row.updated_at=now;
      }
    }
  }
  return snapshot;
}
