// Copies verified payloads only. Does not change the live Convex references.
import { ConvexHttpClient } from "convex/browser";
import { makeFunctionReference } from "convex/server";
import { S3Client, PutObjectCommand } from "@aws-sdk/client-s3";
import { mkdir, writeFile } from "node:fs/promises";
import { createHash, randomUUID } from "node:crypto";
import { readPayload } from "./migration-payloads.mjs";

const sha = value => createHash("sha256").update(value).digest("hex");
let stage = "configuration";
async function main() {
  if (process.env.CONVEX_SELF_HOSTED_URL !== "http://100.118.78.13:13210") throw Error("Dedicated endpoint required");
  const convex = new ConvexHttpClient(process.env.CONVEX_SELF_HOSTED_URL);
  if (!process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY) throw Error("Administrator credential required");
  convex.setAdminAuth(process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY);
  function objects(prefix) {
    const accessKeyId = process.env[`${prefix}_S3_ACCESS_KEY`];
    const secretAccessKey = process.env[`${prefix}_S3_SECRET_KEY`];
    if (!accessKeyId || !secretAccessKey) throw Error("Scoped credentials required");
    return new S3Client({endpoint:"https://s3.v1su4.dev",region:"us-east-1",forcePathStyle:true,maxAttempts:1,credentials:{accessKeyId,secretAccessKey}});
  }
  const source = objects("MVM"), destination = objects("MVVM");
  stage = "snapshot";
  const query = makeFunctionReference("migration:exportSnapshot");
  const original = await convex.query(query, {});
  const originalText = JSON.stringify(original);
  const folder = new URL(`../.runtime/backups/mvvm-bucket-${randomUUID()}/`, import.meta.url);
  await mkdir(folder, { recursive: true });
  await writeFile(new URL("before.json", folder), originalText, { flag: "wx" });
  const planned = structuredClone(original);
  let references = 0, bytes = 0;
  stage = "copy_and_verify";
  for (const table of ["audio_analysis_jobs", "transcription_jobs"]) {
    for (const row of planned[table]) for (const field of ["result", "receipt"]) {
      const ref = row[field];
      if (!ref || typeof ref !== "object") continue;
      const text = await readPayload(ref, source, row.project_id, "music-vending-machine");
      const body = Buffer.from(text);
      try { await destination.send(new PutObjectCommand({Bucket:"mvvm",Key:ref.key,Body:body,ContentType:"application/json",IfNoneMatch:"*"})); }
      catch (error) { if (error.$metadata?.httpStatusCode !== 412) throw error; }
      const relocated = {...ref, bucket: "mvvm"};
      if (await readPayload(relocated, destination, row.project_id, "mvvm") !== text) throw Error("Destination differs");
      row[field] = relocated;
      references++; bytes += body.length;
    }
  }
  stage = "source_stability";
  if (JSON.stringify(await convex.query(query, {})) !== originalText) throw Error("Source changed; copied objects retained but no cutover plan accepted");
  await writeFile(new URL("planned.json", folder), JSON.stringify(planned), { flag: "wx" });
  const receipt = {state:"copied_verified_not_cut_over",references,bytes,sourceSnapshotSha256:sha(originalText),plannedSnapshotSha256:sha(JSON.stringify(planned)),sourceUnchanged:true,metadataModified:false,folder:folder.pathname};
  await writeFile(new URL("receipt.json", folder), JSON.stringify(receipt,null,2), {flag:"wx"});
  console.log(JSON.stringify(receipt));
}
main().catch(() => { console.error(JSON.stringify({stage,state:"failed",details:"Private details withheld; no live metadata mutations are performed by this script."})); process.exitCode=1; });
