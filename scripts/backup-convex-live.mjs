import { ConvexHttpClient } from "convex/browser";
import { makeFunctionReference } from "convex/server";
import { S3Client } from "@aws-sdk/client-s3";
import { randomUUID } from "node:crypto";
import { writeFile, lstat, statfs } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { isAbsolute, join, resolve } from "node:path";
import { createBackup } from "./convex-backup.mjs";
let stage="configuration";
export async function backupDestination(args){
  if(args.length>1 || (args.length===1 && !isAbsolute(args[0])))throw Error("Backup root must be one absolute directory");
  const root=args[0]??fileURLToPath(new URL("../.runtime/backups",import.meta.url));
  const entry=await lstat(root);
  if(!entry.isDirectory()||entry.isSymbolicLink())throw Error("Backup root must be an existing directory, not a link");
  const disk=await statfs(root);
  if(disk.bavail*disk.bsize<10*1024**3)throw Error("Backup disk has less than 10 GiB free");
  return join(root,`convex-${randomUUID()}`);
}
async function main(){
  const directory=await backupDestination(process.argv.slice(2));
  if(process.env.CONVEX_SELF_HOSTED_URL!=="http://100.118.78.13:13210"||!process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY)throw Error("Dedicated deployment required");
  const client=new ConvexHttpClient(process.env.CONVEX_SELF_HOSTED_URL);
  client.setAdminAuth(process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY);
  const query=makeFunctionReference("migration:exportSnapshot");
  const snapshot=await client.query(query,{});
  const objects=new S3Client({endpoint:"https://s3.v1su4.dev",region:"us-east-1",forcePathStyle:true,maxAttempts:1,credentials:{accessKeyId:process.env.MVVM_S3_ACCESS_KEY,secretAccessKey:process.env.MVVM_S3_SECRET_KEY}});
  stage="snapshot_and_objects";
  const receipt=await createBackup(snapshot,"mvvm",objects,directory);
  stage="source_stability";
  if(JSON.stringify(await client.query(query,{}))!==JSON.stringify(snapshot))throw Error("Snapshot changed during backup; archive not accepted");
  const accepted={...receipt,directory,completedAt:new Date().toISOString(),state:"backup_verified",sourceUnchanged:true,restoreVerified:false,workersMayStart:false};
  await writeFile(`${directory}/accepted.json`,JSON.stringify(accepted,null,2),{flag:"wx"});
  console.log(JSON.stringify(accepted));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  main().catch(()=>{console.error(JSON.stringify({stage,state:"failed",details:"Private data withheld; incomplete archives must not be used for restore."}));process.exitCode=1;});
}
