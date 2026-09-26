// One-time private bucket provisioning. Credentials are injected, never persisted.
import { S3Client, HeadBucketCommand, CreateBucketCommand, GetBucketPolicyCommand, PutObjectCommand, GetObjectCommand } from "@aws-sdk/client-s3";
import { randomUUID, randomBytes, createHash } from "node:crypto";
import { writeFile } from "node:fs/promises";

const bucket = "mvvm";
const endpoint = "https://s3.v1su4.dev";
const digest = data => createHash("sha256").update(data).digest("hex");
let stage = "configuration";
async function main() {
  const accessKeyId = process.env.PROXMOX_HOME_RUSTFS_ACCESS_KEY;
  const secretAccessKey = process.env.PROXMOX_HOME_RUSTFS_SECRET_KEY;
  if (!accessKeyId || !secretAccessKey || !process.argv.includes("--apply")) throw Error("Explicit provisioning and injected credentials required");
  const client = new S3Client({ endpoint, region: "us-east-1", forcePathStyle: true, maxAttempts: 1, credentials: { accessKeyId, secretAccessKey } });
  stage = "bucket_preflight";
  let created = false;
  try { await client.send(new HeadBucketCommand({ Bucket: bucket })); }
  catch (error) {
    if (error.$metadata?.httpStatusCode !== 404) throw error;
    stage = "create_private_bucket";
    await client.send(new CreateBucketCommand({ Bucket: bucket }));
    created = true;
  }
  stage = "policy_preflight";
  try {
    await client.send(new GetBucketPolicyCommand({ Bucket: bucket }));
    throw Error("Existing bucket policy requires inspection; no policy changed");
  } catch (error) { if (error.name !== "NoSuchBucketPolicy") throw error; }
  const key = `projects/${randomUUID()}/storage-acceptance.bin`;
  const body = randomBytes(65536);
  const receipt = { bucket, endpoint, key, created, bytes: body.length, sha256: digest(body), state: "planned", checkedAt: new Date().toISOString() };
  const output = new URL("../.runtime/mvvm-bucket-provision.json", import.meta.url);
  await writeFile(output, JSON.stringify(receipt, null, 2), { flag: "wx" });
  stage = "private_roundtrip";
  await client.send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: body, IfNoneMatch: "*" }));
  const full = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
  if (digest(await full.Body.transformToByteArray()) !== receipt.sha256) throw Error("Readback mismatch");
  const part = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key, Range: "bytes=13-63" }));
  if (!Buffer.from(await part.Body.transformToByteArray()).equals(body.subarray(13,64))) throw Error("Range mismatch");
  stage = "anonymous_denial";
  const anonymous = await fetch(`${endpoint}/${bucket}/${key}`, { redirect: "error", signal: AbortSignal.timeout(15000) });
  await anonymous.body?.cancel();
  if (anonymous.status !== 403) throw Error("Private object was not denied anonymously");
  Object.assign(receipt, { state: "verified", rangeVerified: true, anonymousStatus: anonymous.status, appCutover: false });
  await writeFile(output, JSON.stringify(receipt, null, 2));
  console.log(JSON.stringify(receipt));
}
main().catch(() => { console.error(JSON.stringify({ stage, state: "failed", details: "Withheld to protect credentials. Inspect the private receipt before retrying." })); process.exitCode = 1; });
