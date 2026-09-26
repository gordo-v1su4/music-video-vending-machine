/** Stage the bounded private-pilot data set; never cuts over or submits jobs. */
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { ConvexHttpClient } from "convex/browser";
import { makeFunctionReference } from "convex/server";
import { S3Client } from "@aws-sdk/client-s3";
import { externalize, materialize } from "./migration-payloads.mjs";

const tables = ["projects", "project_events", "assets", "upload_intents", "operator_sessions", "audio_analysis_jobs", "transcription_jobs"];
let stage = "configuration";
const canonical = value => JSON.stringify(normalize(value));
function normalize(value) {
  if (Array.isArray(value)) return value.map(normalize);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map(k => [k, normalize(value[k])]));
  return value;
}
function ordered(snapshot) {
  return Object.fromEntries(tables.map(t => [t, [...snapshot[t]].sort((a,b) => canonical(a).localeCompare(canonical(b)))]));
}
function sourceSnapshot() {
  // One SELECT uses one PostgreSQL MVCC snapshot across every table.
  const sql = "SELECT json_build_object(" + tables.map(t => `'${t}',(SELECT COALESCE(json_agg(t),'[]'::json) FROM ${t} t)`).join(",") + ")";
  const output = execFileSync("docker", ["exec", "mvm-dev-postgres", "psql", "-X", "-v", "ON_ERROR_STOP=1", "-U", "mvm", "-d", "mvm_dev", "-Atc", sql], { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], maxBuffer: 8 * 1024 * 1024 });
  const snapshot = JSON.parse(output);
  for (const records of Object.values(snapshot)) for (const row of records) {
    for (const field of ["document", "metadata", "result", "receipt"]) {
      if (field in row && row[field] !== null) row[field] = canonical(row[field]);
    }
  }
  return snapshot;
}
async function main() {
  const url = process.env.CONVEX_SELF_HOSTED_URL;
  const key = process.env.MVVM_CONVEX_SELF_HOSTED_ADMIN_KEY;
  if (url !== "http://100.118.78.13:13210" || !key) throw Error("Dedicated MVVM endpoint and admin credential required");
  const client = new ConvexHttpClient(url);
  const objects = new S3Client({ endpoint: "https://s3.v1su4.dev", region: "us-east-1", forcePathStyle: true, maxAttempts: 1, credentials: { accessKeyId: process.env.MVM_S3_ACCESS_KEY, secretAccessKey: process.env.MVM_S3_SECRET_KEY } });
  client.setAdminAuth(key);
  const exportRef = makeFunctionReference("migration:exportSnapshot");
  const importRef = makeFunctionReference("migration:importSnapshot");
  stage = "read_source";
  const snapshot = sourceSnapshot();
  stage = "read_destination";
  let destination = await client.query(exportRef, {});
  const empty = tables.every(t => destination[t].length === 0);
  if (empty) {
    if (!process.argv.includes("--import")) throw Error("Empty destination; explicit --import required");
    stage = "store_payloads";
    const storedSnapshot = await externalize(snapshot, objects, "music-vending-machine");
    stage = "import_snapshot";
    try { await client.mutation(importRef, { snapshot: storedSnapshot }); }
    catch (error) {
      const text = String(error.message);
      console.error(JSON.stringify({ categories: ["ArgumentValidationError", "SchemaValidationError", "not a valid", "Unsupported", "empty destination", "Duplicate identity", "Could not find", "Unauthorized", "too large", "Invalid", "undefined", "reserved"].filter(s => text.includes(s)), fields: [...text.matchAll(/(?:Path|Field|field):?\s+([A-Za-z_][\w.]*)/g)].map(m => m[1]) }));
      throw error;
    }
    destination = await client.query(exportRef, {});
  }
  stage = "compare_materialized_records";
  if (canonical(ordered(snapshot)) !== canonical(ordered(await materialize(destination, objects, "music-vending-machine")))) throw Error("Destination differs from source; no overwrite attempted");
  // A repeat cannot overwrite a populated destination.
  let refused = false;
  try { await client.mutation(importRef, { snapshot: destination }); } catch { refused = true; }
  if (!refused) throw Error("Populated destination incorrectly accepted import");
  if (canonical(ordered(await client.query(exportRef, {}))) !== canonical(ordered(destination))) throw Error("Rejected import changed destination");
  const anonymous = new ConvexHttpClient(url);
  let privateRead = false;
  try { await anonymous.query(exportRef, {}); } catch { privateRead = true; }
  if (!privateRead) throw Error("Anonymous snapshot access was allowed");
  const unchanged = canonical(ordered(sourceSnapshot())) === canonical(ordered(snapshot));
  console.log(JSON.stringify({ state: "staged_and_compared", counts: Object.fromEntries(tables.map(t => [t,snapshot[t].length])), snapshotSha256: createHash("sha256").update(canonical(ordered(snapshot))).digest("hex"), sourceUnchangedDuringCheck: unchanged, repeatImportRefused: refused, anonymousReadRefused: privateRead, cutover: false }));
}
main().catch(error => { console.error(JSON.stringify({stage, errorType: error.constructor.name, validationPath: String(error.message).match(/Path: ([\w.\[\]]+)/)?.[1] ?? null})); console.error("Migration staging failed. Details withheld to protect private records and credentials; source was not modified."); process.exitCode = 1; });
