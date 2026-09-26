import { execFileSync } from "node:child_process";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { randomUUID, createHash } from "node:crypto";
import { ConvexHttpClient } from "convex/browser";
import { makeFunctionReference } from "convex/server";
let stage="configuration";
const canonical=value=>JSON.stringify(value,(_,v)=>v&&typeof v==="object"&&!Array.isArray(v)?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b))):v);
async function main(){
  if(!process.argv.includes("--apply") || process.env.CONVEX_SELF_HOSTED_URL!=="http://100.118.78.13:13210" || !process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY)throw Error("Explicit dedicated cleanup required");
  const client=new ConvexHttpClient(process.env.CONVEX_SELF_HOSTED_URL);
  client.setAdminAuth(process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY);
  const protectedProjectIds=JSON.parse(execFileSync("docker",["exec","mvm-dev-postgres","psql","-X","-v","ON_ERROR_STOP=1","-U","mvm","-d","mvm_dev","-Atc","SELECT COALESCE(json_agg(id),'[]') FROM projects"],{encoding:"utf8",stdio:["ignore","pipe","pipe"]}));
  if(!protectedProjectIds.length)throw Error("Original project inventory absent");
  const query=makeFunctionReference("migration:exportSnapshot");
  const expected=await client.query(query,{});
  const projectIds=expected.projects.filter(row=>!protectedProjectIds.includes(row.id) && JSON.parse(row.document).name==="MVVM Convex persistence acceptance").map(row=>row.id);
  if(!projectIds.length){console.log(JSON.stringify({state:"no_matching_fixtures"}));return;}
  const ids=new Set(projectIds);
  const remaining=Object.fromEntries(Object.entries(expected).map(([table,records])=>[table,records.filter(row=>!ids.has(table==="projects"?row.id:row.project_id))]));
  const folder=new URL(`../.runtime/backups/fixture-archive-${randomUUID()}/`,import.meta.url);
  await mkdir(folder,{recursive:true});
  const text=JSON.stringify(expected);
  stage="archive_and_readback";
  const archive=new URL("before.json",folder);
  await writeFile(archive,text,{flag:"wx"});
  if(await readFile(archive,"utf8")!==text)throw Error("Archive readback mismatch");
  await writeFile(new URL("selection.json",folder),JSON.stringify({projectIds,protectedProjectIds}),{flag:"wx"});
  stage="atomic_cleanup";
  const removed=await client.mutation(makeFunctionReference("migration:removeAcceptanceFixtures"),{expected,projectIds,protectedProjectIds});
  stage="verify_remaining_records";
  if(canonical(await client.query(query,{}))!==canonical(remaining))throw Error("Post-cleanup state requires inspection; archive retained");
  const receipt={state:"fixtures_archived_and_removed",removed,protectedProjects:protectedProjectIds.length,archiveSha256:createHash("sha256").update(text).digest("hex"),folder:folder.pathname,objectsDeleted:false,sessionsDeleted:false};
  await writeFile(new URL("receipt.json",folder),JSON.stringify(receipt,null,2),{flag:"wx"});
  console.log(JSON.stringify(receipt));
}
main().catch(()=>{console.error(JSON.stringify({stage,state:"failed",details:"Private details withheld. Inspect archived state before retrying."}));process.exitCode=1;});
