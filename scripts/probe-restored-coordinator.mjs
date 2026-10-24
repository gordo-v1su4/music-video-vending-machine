import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { digest, verifyBackup } from "./convex-backup.mjs";
const origin="http://127.0.0.1:5204/api/v1";
const canonical=value=>JSON.stringify(value,(_,v)=>v&&typeof v==="object"&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v);
let stage="archive", token;
async function request(path,options={},credential=token){
  return fetch(origin+path,{...options,headers:{...(options.body?{"Content-Type":"application/json"}:{}),...(credential?{Authorization:`Bearer ${credential}`}:{})},signal:AbortSignal.timeout(30000)});
}
async function main(){
  const [directory,manifestHash]=process.argv.slice(2);
  const {snapshot}=await verifyBackup(directory,manifestHash);
  stage="private_health";
  const health=await (await request("/health",{},null)).json();
  if(health.database!=="convex"||health.storage!=="rustfs"||!health.sessionRequired||health.development)throw Error("Wrong runtime");
  if((await request("/projects",{},null)).status!==401)throw Error("Anonymous project read allowed");
  if((await request("/projects",{},process.env.MVVM_OPERATOR_TOKEN)).status!==401)throw Error("Bootstrap accepted on data route");
  stage="operator_session";
  const login=await request("/sessions",{method:"POST",body:JSON.stringify({clientLabel:"MVVM isolated restore acceptance"})},process.env.MVVM_OPERATOR_TOKEN);
  if(!login.ok)throw Error("Session failed");
  const grant=await login.json(); token=grant.token;
  if(typeof token!=="string"||!grant.session?.id)throw Error("Invalid session grant");
  if(!(await request("/sessions/current")).ok)throw Error("Current session unavailable");
  let assets=0,bytes=0;
  stage="projects_and_media";
  for(const row of snapshot.projects){
    const response=await request(`/projects/${row.id}`);
    const actual=await response.json(),expected=JSON.parse(row.document);
    // Legacy documents predate the optional lyric-reference field; Rust's
    // backward-compatible domain deserializer exposes the absent value as null.
    if(!("lyrics" in expected))expected.lyrics=null;
    if(!response.ok||canonical(actual)!==canonical(expected)){
      console.error(JSON.stringify({projectStatus:response.status,actualKeys:Object.keys(actual),expectedKeys:Object.keys(expected)}));
      throw Error("Restored project differs");
    }
  }
  for(const row of snapshot.assets){
    const meta=JSON.parse(row.metadata);
    const response=await request(`/projects/${row.project_id}/assets/${row.id}`);
    if(!response.ok)throw Error("Restored media inaccessible");
    const body=Buffer.from(await response.arrayBuffer());
    if(body.length!==meta.sizeBytes||digest(body)!==meta.sha256)throw Error("Restored media differs");
    assets++;bytes+=body.length;
  }
  stage="analysis_and_transcripts";
  const shapes=[];
  for(const [table,route] of [["audio_analysis_jobs","analysis"],["transcription_jobs","transcription"]]){
    for(const row of snapshot[table]){
      const path=`/projects/${row.project_id}/assets/${row.asset_id}/${route}`;
      const response=await request(path);
      if(!response.ok)throw Error("Restored job inaccessible");
      const value=await response.json();
      const original=await fetch(`http://127.0.0.1:5199/api/v1${path}`,{signal:AbortSignal.timeout(30000)});
      if(!original.ok || canonical(await original.json())!==canonical(value))throw Error("Restored job API differs from original coordinator");
      shapes.push({route,keys:Object.keys(value),status:value.status});
    }
  }
  stage="session_revocation";
  if(!(await request("/sessions/current/revoke",{method:"POST",body:"{}"})).ok)throw Error("Revocation failed");
  if((await request("/projects")).status!==401)throw Error("Revoked session remained valid");
  token=null;
  console.log(JSON.stringify({state:"restore_api_readback_passed",projects:snapshot.projects.length,assets,bytes,privateSessionsVerified:true,jobResponses:shapes,paidCalls:false}));
}
main().catch(()=>{console.error(JSON.stringify({stage,state:"failed",details:"Private response details withheld."}));process.exitCode=1;}).finally(async()=>{
  if(token)await request("/sessions/current/revoke",{method:"POST",body:"{}"}).catch(()=>{});
});
