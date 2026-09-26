import { createHash } from "node:crypto";
import { GetObjectCommand, PutObjectCommand } from "@aws-sdk/client-s3";

const digest = bytes => createHash("sha256").update(bytes).digest("hex");
const limit = 128 * 1024;

export async function externalize(snapshot, client, bucket) {
  if (typeof bucket !== "string" || !bucket) throw Error("Configured bucket required");
  const result = structuredClone(snapshot);
  for (const table of ["audio_analysis_jobs", "transcription_jobs"]) {
    for (const row of result[table]) for (const field of ["result", "receipt"]) {
      if (typeof row[field] !== "string" || Buffer.byteLength(row[field]) <= limit) continue;
      const body = Buffer.from(row[field]);
      if (body.length > 8 * 1024 * 1024) throw Error("Payload exceeds limit");
      const sha256 = digest(body);
      const key = `projects/${row.project_id}/mvvm/payloads/${sha256}.json`;
      // Content-addressed keys are never replaced with different bytes.
      try { await client.send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: body, ContentType: "application/json", IfNoneMatch: "*" })); }
      catch (error) { if (error.$metadata?.httpStatusCode !== 412) throw error; }
      const ref = { kind: "rustfs-json-v1", bucket, key, sha256, bytes: body.length };
      if (await readPayload(ref, client, row.project_id, bucket) !== row[field]) throw Error("Payload readback differs");
      row[field] = ref;
    }
  }
  return result;
}

export async function readPayload(ref, client, projectId, bucket) {
  if (typeof bucket !== "string" || !bucket) throw Error("Configured bucket required");
  if (ref.kind !== "rustfs-json-v1" || ref.bucket !== bucket || !/^[a-f0-9]{64}$/.test(ref.sha256) || ref.key !== `projects/${projectId}/mvvm/payloads/${ref.sha256}.json` || !Number.isSafeInteger(ref.bytes) || ref.bytes < 0 || ref.bytes > 8 * 1024 * 1024) throw Error("Invalid payload reference");
  const response = await client.send(new GetObjectCommand({ Bucket: ref.bucket, Key: ref.key }));
  const bytes = Buffer.from(await response.Body.transformToByteArray());
  if (bytes.length !== ref.bytes || digest(bytes) !== ref.sha256) throw Error("Payload checksum mismatch");
  return bytes.toString("utf8");
}

export async function materialize(snapshot, client, bucket) {
  if (typeof bucket !== "string" || !bucket) throw Error("Configured bucket required");
  const result = structuredClone(snapshot);
  for (const table of ["audio_analysis_jobs", "transcription_jobs"]) {
    for (const row of result[table]) for (const field of ["result", "receipt"]) {
      if (row[field] && typeof row[field] === "object") row[field] = await readPayload(row[field], client, row.project_id, bucket);
    }
  }
  return result;
}
