import { S3Client } from "@aws-sdk/client-s3";
import { writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { restoreObjects, digest } from "./convex-backup.mjs";
export async function runRestoreCommand(args,{environment=process.env,createClient=config=>new S3Client(config),log=console.log}={}){
  const [directory,checksum,...options]=args;
  if(options.length>1||options.some(option=>option!=="--same-bucket"))throw Error("Unsupported restore option");
  if(!directory||!checksum||!environment.MVVM_S3_ACCESS_KEY||!environment.MVVM_S3_SECRET_KEY)throw Error("Archive, pinned manifest hash and destination credentials required");
  const client=createClient({endpoint:"https://s3.v1su4.dev",region:"us-east-1",forcePathStyle:true,maxAttempts:1,credentials:{accessKeyId:environment.MVVM_S3_ACCESS_KEY,secretAccessKey:environment.MVVM_S3_SECRET_KEY}});
  const snapshot=await restoreObjects(directory,checksum,client,"mvvm",undefined,{allowSameBucket:options.includes("--same-bucket")});
  const text=JSON.stringify(snapshot);
  await writeFile(join(directory,"restored-snapshot.json"),text,{flag:"wx"});
  log(JSON.stringify({state:"objects_restored_and_verified",bucket:"mvvm",snapshotSha256:digest(text),databaseImported:false,workersMayStart:false,sessionsRevoked:true}));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
  runRestoreCommand(process.argv.slice(2)).catch(()=>{console.error("Restore failed; private details withheld. Existing objects and restored-snapshot.json are never overwritten; no database changes were attempted. For a repeated command, retain the existing prepared snapshot rather than replacing it.");process.exitCode=1;});
}
