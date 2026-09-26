import { S3Client } from "@aws-sdk/client-s3";
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { restoreObjects, digest } from "./convex-backup.mjs";
async function main(){
  const [directory,checksum]=process.argv.slice(2);
  if(!directory||!checksum||!process.env.MVVM_S3_ACCESS_KEY||!process.env.MVVM_S3_SECRET_KEY)throw Error("Archive, pinned manifest hash and destination credentials required");
  const client=new S3Client({endpoint:"https://s3.v1su4.dev",region:"us-east-1",forcePathStyle:true,maxAttempts:1,credentials:{accessKeyId:process.env.MVVM_S3_ACCESS_KEY,secretAccessKey:process.env.MVVM_S3_SECRET_KEY}});
  const snapshot=await restoreObjects(directory,checksum,client,"mvvm");
  const text=JSON.stringify(snapshot);
  await writeFile(join(directory,"restored-snapshot.json"),text,{flag:"wx"});
  console.log(JSON.stringify({state:"objects_restored_and_verified",bucket:"mvvm",snapshotSha256:digest(text),databaseImported:false,workersMayStart:false,sessionsRevoked:true}));
}
main().catch(()=>{console.error("Restore failed; private details withheld. Existing objects are never overwritten; no database changes were attempted.");process.exitCode=1;});
