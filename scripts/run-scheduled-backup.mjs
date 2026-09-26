// Installed beside reviewed backup scripts and dependencies, outside any worktree.
import { spawn, spawnSync } from "node:child_process";
import { readFile, writeFile, rename } from "node:fs/promises";
import { join, resolve, isAbsolute } from "node:path";
import { randomUUID } from "node:crypto";
import { verifyBackup } from "./convex-backup.mjs";

const root=resolve(import.meta.dirname,"..");
let stage="configuration";
try{
  const config=JSON.parse(await readFile(join(root,"backup-config.json"),"utf8"));
  for(const key of ["secretsRunner","backupRoot"])if(typeof config[key]!=="string"||!isAbsolute(config[key]))throw Error("Invalid path");
  const timeoutMs=config.timeoutMs??15*60*1000;
  if(!Number.isSafeInteger(timeoutMs)||timeoutMs<1||timeoutMs>15*60*1000)throw Error("Invalid timeout");
  await writeFile(join(root,"last-attempt.json"),JSON.stringify({state:"running",startedAt:new Date().toISOString()}),{mode:0o600});
  stage="backup";
  const env={...process.env,CONVEX_SELF_HOSTED_URL:"http://100.118.78.13:13210"};
  // Always request live BWS values. Do not pass stale app credentials to its child.
  for(const key of Object.keys(env))if(/^(MVVM_|MVM_|CONVEX_SELF_HOSTED_ADMIN_KEY$)/i.test(key))delete env[key];
  const result=await new Promise((accept,reject)=>{
    const child=spawn(process.execPath,[config.secretsRunner,"run","--secret=MVVM_S3_ACCESS_KEY","--secret=MVVM_S3_SECRET_KEY","--secret=MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY","--",process.execPath,join(import.meta.dirname,"backup-convex-live.mjs"),config.backupRoot],{cwd:root,env,windowsHide:true,detached:process.platform!=="win32",stdio:["ignore","pipe","pipe"]});
    const timer=setTimeout(()=>{
      stage="timeout";
      if(child.pid){
        if(process.platform==="win32")spawnSync("taskkill",["/PID",String(child.pid),"/T","/F"],{windowsHide:true,stdio:"ignore",timeout:5000});
        else {try{process.kill(-child.pid,"SIGKILL");}catch{}}
      }
      reject(Error("Backup deadline exceeded"));
    },timeoutMs);
    let stdout="",overflow=false;
    child.stdout.on("data",chunk=>{if(stdout.length+chunk.length>65536){overflow=true;child.kill();}else stdout+=chunk;});
    child.stderr.resume(); // Never persist raw secret-runner diagnostics.
    child.on("error",error=>{clearTimeout(timer);reject(error);});
    child.on("close",code=>{clearTimeout(timer);code===0&&!overflow?accept(stdout):reject(Error("Backup process failed"));});
  });
  stage="verify_receipt";
  const receipt=JSON.parse(result);
  if(receipt.state!=="backup_verified"||resolve(receipt.directory,"..")!==resolve(config.backupRoot))throw Error("Invalid receipt");
  await verifyBackup(receipt.directory,receipt.manifestSha256);
  const status={state:"backup_verified",completedAt:receipt.completedAt,directory:receipt.directory,manifestSha256:receipt.manifestSha256,objects:receipt.objects,bytes:receipt.bytes};
  const temporary=join(root,`status-${randomUUID()}.json`);
  await writeFile(temporary,JSON.stringify(status,null,2),{flag:"wx",mode:0o600});
  await rename(temporary,join(root,"last-success.json"));
  await writeFile(join(root,"last-attempt.json"),JSON.stringify(status),{mode:0o600});
  console.log(JSON.stringify(status));
}catch{
  const failure={state:"failed",stage,failedAt:new Date().toISOString()};
  await writeFile(join(root,"last-failure.json"),JSON.stringify(failure,null,2),{mode:0o600});
  await writeFile(join(root,"last-attempt.json"),JSON.stringify(failure),{mode:0o600});
  console.error(JSON.stringify(failure));process.exitCode=1;
}
