import { ConvexHttpClient } from "convex/browser";
import { makeFunctionReference } from "convex/server";
import { S3Client } from "@aws-sdk/client-s3";
import { randomUUID } from "node:crypto";
import { writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { createBackup } from "./convex-backup.mjs";
let stage="configuration";
async function main(){
  if(process.env.CONVEX_SELF_HOSTED_URL!=="http://100.118.78.13:13210"||!process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY)throw Error("Dedicated deployment required");
  const client=new ConvexHttpClient(process.env.CONVEX_SELF_HOSTED_URL);
  client.setAdminAuth(process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY);
  const query=makeFunctionReference("migration:exportSnapshot");
  const snapshot=await client.query(query,{});
  const objects=new S3Client({endpoint:"https://s3.v1su4.dev",region:"us-east-1",forcePathStyle:true,maxAttempts:1,credentials:{accessKeyId:process.env.MVVM_S3_ACCESS_KEY,secretAccessKey:process.env.MVVM_S3_SECRET_KEY}});
  const directory=fileURLToPath(new URL(`../.runtime/backups/convex-${randomUUID()}`,import.meta.url));
  stage="snapshot_and_objects";
  const receipt=await createBackup(snapshot,"mvvm",objects,directory);
  stage="source_stability";
  if(JSON.stringify(await client.query(query,{}))!==JSON.stringify(snapshot))throw Error("Snapshot changed during backup; archive not accepted");
  const accepted={...receipt,directory,state:"backup_verified",sourceUnchanged:true,restoreVerified:false,workersMayStart:false};
  await writeFile(`${directory}/accepted.json`,JSON.stringify(accepted,null,2),{flag:"wx"});
  console.log(JSON.stringify(accepted));
}
main().catch(()=>{console.error(JSON.stringify({stage,state:"failed",details:"Private data withheld; incomplete archives must not be used for restore."}));process.exitCode=1;});
