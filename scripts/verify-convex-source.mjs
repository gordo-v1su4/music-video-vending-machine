// Compare every original record, reporting staging extras separately.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { ConvexHttpClient } from "convex/browser";
import { makeFunctionReference } from "convex/server";
import { S3Client } from "@aws-sdk/client-s3";
import { materialize } from "./migration-payloads.mjs";
const tables=["projects","project_events","assets","upload_intents","operator_sessions","audio_analysis_jobs","transcription_jobs"];
const normalize=value=>Array.isArray(value)?value.map(normalize):value&&typeof value==="object"?Object.fromEntries(Object.keys(value).sort().map(key=>[key,normalize(value[key])])):value;
const canonical=value=>JSON.stringify(normalize(value));
const identity=row=>row.id??`${row.project_id}:${row.revision}`;
function source() {
  const sql="SELECT json_build_object("+tables.map(table=>`'${table}',(SELECT COALESCE(json_agg(t),'[]'::json) FROM ${table} t)`).join(",")+")";
  const snapshot=JSON.parse(execFileSync("docker",["exec","mvm-dev-postgres","psql","-X","-v","ON_ERROR_STOP=1","-U","mvm","-d","mvm_dev","-Atc",sql],{encoding:"utf8",stdio:["ignore","pipe","pipe"],maxBuffer:16*1024*1024}));
  for(const rows of Object.values(snapshot)) for(const row of rows) for(const field of ["document","metadata","result","receipt"]) {
    if(field in row && row[field]!==null) row[field]=canonical(row[field]);
  }
  return snapshot;
}
let stage="configuration";
async function main(){
  if(process.env.CONVEX_SELF_HOSTED_URL!=="http://100.118.78.13:13210"||!process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY)throw Error("Dedicated deployment required");
  const client=new ConvexHttpClient(process.env.CONVEX_SELF_HOSTED_URL);
  client.setAdminAuth(process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY);
  const bucket=process.argv.includes("--mvvm")?"mvvm":"music-vending-machine";
  const prefix=bucket==="mvvm"?"MVVM":"MVM";
  const objects=new S3Client({endpoint:"https://s3.v1su4.dev",region:"us-east-1",forcePathStyle:true,maxAttempts:1,credentials:{accessKeyId:process.env[`${prefix}_S3_ACCESS_KEY`],secretAccessKey:process.env[`${prefix}_S3_SECRET_KEY`]}});
  const original=source(), expected=structuredClone(original);
  let relocated=0;
  for(const asset of expected.assets){
    const legacy=`music-vending-machine/${asset.project_id}/originals/${asset.id}`;
    if(asset.object_key===legacy){asset.object_key=`projects/${asset.project_id}/originals/${asset.id}`;relocated++;}
  }
  stage="read_destination";
  const stored=await client.query(makeFunctionReference("migration:exportSnapshot"),{});
  // Materialize only original records; extras are explicitly not accepted as source data.
  const selected={},extras={};
  for(const table of tables){
    const ids=new Set(expected[table].map(identity));
    selected[table]=stored[table].filter(row=>ids.has(identity(row)));
    extras[table]=stored[table].length-selected[table].length;
  }
  const actual=await materialize(selected,objects,bucket);
  stage="compare_all_original_fields";
  for(const table of tables){
    const rows=value=>[...value].sort((a,b)=>identity(a).localeCompare(identity(b)));
    if(canonical(rows(actual[table]))!==canonical(rows(expected[table])))throw Error("Source mismatch");
  }
  if(canonical(source())!==canonical(original))throw Error("Source changed during verification");
  if(canonical(await client.query(makeFunctionReference("migration:exportSnapshot"),{}))!==canonical(stored))throw Error("Destination changed during verification");
  console.log(JSON.stringify({state:"all_original_records_match",counts:Object.fromEntries(tables.map(t=>[t,expected[t].length])),intentionalLegacyKeyRelocations:relocated,stagingExtras:extras,sourceSha256:createHash("sha256").update(canonical(original)).digest("hex"),sourceUnchanged:true,destinationUnchanged:true,cutover:false}));
}
main().catch(()=>{console.error(JSON.stringify({stage,state:"failed",details:"Private records withheld; no data was modified."}));process.exitCode=1;});
