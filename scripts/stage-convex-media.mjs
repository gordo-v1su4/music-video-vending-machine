import {execFileSync} from "node:child_process";
import {readFile,realpath} from "node:fs/promises";
import {resolve,relative,isAbsolute,sep} from "node:path";
import {createHash} from "node:crypto";
import {S3Client,PutObjectCommand,GetObjectCommand} from "@aws-sdk/client-s3";
import {ConvexHttpClient} from "convex/browser";
import {makeFunctionReference} from "convex/server";
const digest=b=>createHash("sha256").update(b).digest("hex");
async function main(){
  const copyOnly=process.argv.includes("--copy-to-mvvm");
  const root=await realpath(process.argv[2]);
  const source=JSON.parse(execFileSync("docker",["exec","mvm-dev-postgres","psql","-X","-v","ON_ERROR_STOP=1","-U","mvm","-d","mvm_dev","-Atc","SELECT COALESCE(json_agg(a),'[]') FROM assets a"],{encoding:"utf8",stdio:["ignore","pipe","pipe"]}));
  const verified=[];
  for(const row of source){
    const path=await realpath(resolve(root,row.object_key));
    const rel=relative(root,path);
    if(isAbsolute(rel)||rel===".."||rel.startsWith(`..${sep}`))throw Error("Source outside asset directory");
    const bytes=await readFile(path);
    if(bytes.length!==row.metadata.sizeBytes||digest(bytes)!==row.metadata.sha256)throw Error("Source integrity failure");
    verified.push({row,bytes,key:`projects/${row.project_id}/originals/${row.id}`});
  }
  let convex;
  if(!copyOnly){
    if(process.env.CONVEX_SELF_HOSTED_URL!=="http://100.118.78.13:13210")throw Error("Wrong destination");
    convex=new ConvexHttpClient(process.env.CONVEX_SELF_HOSTED_URL);
    convex.setAdminAuth(process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY);
  }
  const prefix=copyOnly?"MVVM":"MVM";
  const accessKeyId=process.env[`${prefix}_S3_ACCESS_KEY`],secretAccessKey=process.env[`${prefix}_S3_SECRET_KEY`];
  if(!accessKeyId||!secretAccessKey)throw Error("Scoped credentials required");
  const objects=new S3Client({endpoint:"https://s3.v1su4.dev",region:"us-east-1",forcePathStyle:true,maxAttempts:1,credentials:{accessKeyId,secretAccessKey}});
  const bucket=copyOnly?"mvvm":"music-vending-machine";
  for(const {row,bytes,key} of verified){
    try{await objects.send(new PutObjectCommand({Bucket:bucket,Key:key,Body:bytes,IfNoneMatch:"*",ContentType:row.metadata.mediaType}));}
    catch(error){if(error.$metadata?.httpStatusCode!==412)throw error;}
    const object=await objects.send(new GetObjectCommand({Bucket:bucket,Key:key}));
    const actual=Buffer.from(await object.Body.transformToByteArray());
    if(actual.length!==bytes.length||digest(actual)!==row.metadata.sha256)throw Error("RustFS integrity failure");
    if(convex)await convex.mutation(makeFunctionReference("migration:relocateAsset"),{id:row.id,sourceKey:row.object_key,targetKey:key,sha256:row.metadata.sha256});
  }
  console.log(JSON.stringify({state:"source_media_verified_in_rustfs",bucket,copyOnly,assets:verified.length,bytes:verified.reduce((sum,v)=>sum+v.bytes.length,0),relocatedLegacyKeys:copyOnly?0:verified.filter(v=>v.key!==v.row.object_key).length,sourceModified:false}));
}
main().catch(()=>{console.error("Media staging failed; private details withheld. Source files and PostgreSQL were not modified.");process.exitCode=1;});
