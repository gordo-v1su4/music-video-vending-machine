import { ConvexHttpClient } from "convex/browser";
import { makeFunctionReference } from "convex/server";
import { S3Client } from "@aws-sdk/client-s3";
import { mkdir, writeFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { readPayload } from "./migration-payloads.mjs";
let stage="configuration";
async function main(){
  if(!process.argv.includes("--apply")||process.env.CONVEX_SELF_HOSTED_URL!=="http://100.118.78.13:13210"||!process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY)throw Error("Explicit primary cutover required");
  const client=new ConvexHttpClient(process.env.CONVEX_SELF_HOSTED_URL);
  client.setAdminAuth(process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY);
  const objects=new S3Client({endpoint:"https://s3.v1su4.dev",region:"us-east-1",forcePathStyle:true,maxAttempts:1,credentials:{accessKeyId:process.env.MVVM_S3_ACCESS_KEY,secretAccessKey:process.env.MVVM_S3_SECRET_KEY}});
  const snapshot=await client.query(makeFunctionReference("migration:exportSnapshot"),{});
  const expected={audio_analysis_jobs:snapshot.audio_analysis_jobs,transcription_jobs:snapshot.transcription_jobs};
  const folder=new URL(`../.runtime/backups/bucket-cutover-${randomUUID()}/`,import.meta.url);
  await mkdir(folder,{recursive:true});
  await writeFile(new URL("before.json",folder),JSON.stringify(snapshot),{flag:"wx"});
  stage="verify_destination_payloads";
  const after=structuredClone(snapshot);
  for(const table of ["audio_analysis_jobs","transcription_jobs"]){
    for(const row of after[table])for(const field of ["result","receipt"]){
      if(!row[field]||typeof row[field]!=="object")continue;
      if(row[field].bucket!=="music-vending-machine")throw Error("Unexpected source bucket; inspect before retrying");
      row[field].bucket="mvvm";
      await readPayload(row[field],objects,row.project_id,"mvvm");
    }
  }
  stage="atomic_switch";
  const switched=await client.mutation(makeFunctionReference("migration:relocatePayloadBucket"),expected);
  stage="readback";
  const canonical=value=>JSON.stringify(value,(_,v)=>v&&typeof v==="object"&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v);
  if(canonical(await client.query(makeFunctionReference("migration:exportSnapshot"),{}))!==canonical(after))throw Error("Readback differs; inspect retained checkpoint");
  console.log(JSON.stringify({state:"primary_payload_bucket_switched",...switched,bucket:"mvvm",checkpoint:folder.pathname}));
}
main().catch(()=>{console.error(JSON.stringify({stage,state:"failed",details:"Private data withheld; inspect cutover checkpoint before retrying."}));process.exitCode=1;});
