import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { ConvexHttpClient } from "convex/browser";
import { makeFunctionReference } from "convex/server";
import { digest, verifyBackup } from "./convex-backup.mjs";
const canonical=value=>JSON.stringify(value,(_,v)=>v&&typeof v==="object"&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v);
let stage="verify_archive";
async function main(){
  const [directory,manifestHash,restoredHash]=process.argv.slice(2);
  await verifyBackup(directory,manifestHash);
  const text=await readFile(join(directory,"restored-snapshot.json"),"utf8");
  if(digest(text)!==restoredHash)throw Error("Prepared restore checksum mismatch");
  const snapshot=JSON.parse(text);
  if(snapshot.operator_sessions.some(row=>row.revoked_at===null))throw Error("Restored sessions must be revoked");
  for(const table of ["audio_analysis_jobs","transcription_jobs"])if(snapshot[table].some(row=>["queued","running","submitting"].includes(row.status)))throw Error("Restored jobs must be quarantined");
  if(process.env.CONVEX_SELF_HOSTED_URL!=="http://100.118.78.13:13212"||!process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY)throw Error("Only the isolated restore endpoint is permitted");
  const client=new ConvexHttpClient(process.env.CONVEX_SELF_HOSTED_URL);
  client.setAdminAuth(process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY);
  const query=makeFunctionReference("migration:exportSnapshot"), mutation=makeFunctionReference("migration:importSnapshot");
  stage="inspect_destination";
  const before=await client.query(query,{});
  if(Object.values(before).every(rows=>rows.length===0)){
    stage="import_empty_restore_instance";
    await client.mutation(mutation,{snapshot});
  } else if(canonical(before)!==canonical(snapshot))throw Error("Existing destination differs; no overwrite attempted");
  stage="full_readback";
  if(canonical(await client.query(query,{}))!==canonical(snapshot))throw Error("Restored database differs");
  let repeatRefused=false;
  try{await client.mutation(mutation,{snapshot});}catch{repeatRefused=true;}
  if(!repeatRefused)throw Error("Populated destination accepted import");
  console.log(JSON.stringify({state:"isolated_database_restored",counts:Object.fromEntries(Object.entries(snapshot).map(([k,v])=>[k,v.length])),repeatImportRefused:true,primaryModified:false,workersMayStart:false}));
}
main().catch(()=>{console.error(JSON.stringify({stage,state:"failed",details:"Private records withheld; primary endpoint is never targeted."}));process.exitCode=1;});
