import test from "node:test";
import assert from "node:assert/strict";
import { externalize, materialize, readPayload } from "./migration-payloads.mjs";

function fixture() {
  const objects = new Map();
  const client = { async send(command) {
    const { Key, Body } = command.input;
    if (Body) {
      if (objects.has(Key)) throw Object.assign(Error("exists"), { $metadata: { httpStatusCode: 412 } });
      objects.set(Key, Buffer.from(Body));
      return {};
    }
    if (!objects.has(Key)) throw Error("missing");
    return { Body: { transformToByteArray: async () => objects.get(Key) } };
  } };
  const snapshot = { audio_analysis_jobs: [{ id: "job", project_id: "project", result: JSON.stringify({ curve: Array.from({length: 40000}, (_,i) => i/10000) }), receipt: null }], transcription_jobs: [] };
  return { objects, client, snapshot };
}

test("large curves survive externalization, repeat staging and complete readback", async () => {
  const { client, snapshot, objects } = fixture();
  const staged = await externalize(snapshot, client, "mvvm");
  assert.equal(staged.audio_analysis_jobs[0].result.kind, "rustfs-json-v1");
  assert.equal(staged.audio_analysis_jobs[0].result.bucket, "mvvm");
  assert.deepEqual(await materialize(staged, client, "mvvm"), snapshot);
  assert.deepEqual(await externalize(snapshot, client, "mvvm"), staged);
  assert.equal(objects.size, 1);
  assert.equal(typeof snapshot.audio_analysis_jobs[0].result, "string");
});

test("corrupt payload cannot materialize or pass a retry readback", async () => {
  const { client, snapshot, objects } = fixture();
  const staged = await externalize(snapshot, client, "mvvm");
  const ref = staged.audio_analysis_jobs[0].result;
  objects.get(ref.key)[10] ^= 1;
  await assert.rejects(materialize(staged, client, "mvvm"), /checksum/);
  await assert.rejects(externalize(snapshot, client, "mvvm"), /checksum/);
});

test("cross-project and wrong-bucket references are refused before object access", async () => {
  const { client, snapshot } = fixture();
  const staged = await externalize(snapshot, client, "mvvm");
  const ref = staged.audio_analysis_jobs[0].result;
  const forbidden = { send() { assert.fail("must not access object store"); } };
  await assert.rejects(readPayload(ref, forbidden, "other-project", "mvvm"), /Invalid/);
  await assert.rejects(readPayload({...ref, bucket: "pindeck"}, forbidden, "project", "mvvm"), /Invalid/);
});

test("missing payload fails closed", async () => {
  const { client, snapshot, objects } = fixture();
  const staged = await externalize(snapshot, client, "mvvm");
  objects.clear();
  await assert.rejects(materialize(staged, client, "mvvm"), /missing/);
});

test("bucket configuration is required and cannot silently select the source bucket", async () => {
  const { client, snapshot } = fixture();
  await assert.rejects(externalize(snapshot, client), /Configured bucket/);
  const old = await externalize(snapshot, client, "music-vending-machine");
  await assert.rejects(materialize(old, client, "mvvm"), /Invalid payload reference/);
  assert.deepEqual(await materialize(old, client, "music-vending-machine"), snapshot);
});

test("oversized payload is rejected before a write", async () => {
  const { snapshot } = fixture();
  snapshot.audio_analysis_jobs[0].result = JSON.stringify("x".repeat(8 * 1024 * 1024));
  const forbidden = { send() { assert.fail("must not write oversized payload"); } };
  await assert.rejects(externalize(snapshot, forbidden, "mvvm"), /exceeds limit/);
});
