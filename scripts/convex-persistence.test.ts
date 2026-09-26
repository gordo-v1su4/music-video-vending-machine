import { convexTest } from "convex-test";
import { expect, test, vi } from "vitest";
import schema from "../convex/schema";
import { internal } from "../convex/_generated/api";
const modules = import.meta.glob("../convex/**/*.ts");
const dev = { sessionId: null, issuerHash: null, development: true };
const document = (revision: number) => JSON.stringify({ id: "project", revision });

test("transcription retains saved passes when lease expires and refuses replay",async()=>{
  vi.useFakeTimers();
  try {
    const t=convexTest(schema,modules);
    const now=new Date().toISOString();
    await t.run(async ctx=>{
      await ctx.db.insert("assets",{legacyId:"asset",data:{id:"asset",project_id:"project",object_key:"key",metadata:"{}",created_at:now}});
      await ctx.db.insert("transcription_jobs",{legacyId:"job",data:{id:"job",asset_id:"asset",project_id:"project",sha256:"hash",model:"stack-structure-v1",status:"queued",message:null,result:null,receipt:null,created_at:now,updated_at:now,next_poll_at:now}});
    });
    expect((await t.mutation(internal.transcriptionWorker.claim,{token:"worker"}))?.job.id).toBe("job");
    await t.mutation(internal.transcriptionWorker.save,{token:"worker",id:"job",status:"running",message:null});
    const receipt=JSON.stringify({primary:{request_id:"already-submitted"}});
    await t.mutation(internal.transcriptionWorker.save,{token:"worker",id:"job",receipt,message:"Pass saved"});
    vi.advanceTimersByTime(600001);
    await expect(t.mutation(internal.transcriptionWorker.save,{token:"worker",id:"job",message:"Next paid pass"})).rejects.toThrow("LEASE_LOST");
    expect(await t.mutation(internal.transcriptionWorker.claim,{token:"replacement"})).toBeNull();
    const row=await t.run(ctx=>ctx.db.query("transcription_jobs").first());
    expect(row?.data.status).toBe("reconciliation_required");
    expect(row?.data.receipt).toBe(receipt);
  } finally {vi.useRealTimers();}
});

test("transcription recovery rejects stale updates and cannot queue paid work",async()=>{
  const t=convexTest(schema,modules);
  const now=new Date().toISOString();
  const data={id:"transcript",asset_id:"asset",project_id:"project",sha256:"hash",model:"stack-structure-v1" as const,status:"reconciliation_required" as const,message:null,result:null,receipt:null,created_at:now,updated_at:now,next_poll_at:now};
  await t.run(async ctx=>{
    await ctx.db.insert("assets",{legacyId:"asset",data:{id:"asset",project_id:"project",object_key:"key",metadata:JSON.stringify({sha256:"hash"}),created_at:now}});
    await ctx.db.insert("transcription_jobs",{legacyId:"transcript",data});
  });
  await expect(t.mutation(internal.transcription.recover,{auth:dev,expectedUpdatedAt:"2000-01-01T00:00:00Z",data:{...data,status:"completed"}})).rejects.toThrow("CONFLICT");
  await expect(t.mutation(internal.transcription.recover,{auth:dev,expectedUpdatedAt:now,data:{...data,status:"queued"}})).rejects.toThrow("CONFLICT");
  await t.mutation(internal.transcription.recover,{auth:dev,expectedUpdatedAt:now,data:{...data,status:"completed",result:"{}",receipt:"{}"}});
  expect((await t.query(internal.transcription.get,{auth:dev,projectId:"project",assetId:"asset"}))?.status).toBe("completed");
  await expect(t.mutation(internal.transcription.recover,{auth:dev,expectedUpdatedAt:now,data:{...data,status:"completed"}})).rejects.toThrow("CONFLICT");
});

test("expired worker cannot save and uncertain submission is never requeued", async () => {
  vi.useFakeTimers();
  try {
    const t = convexTest(schema, modules);
    const now = new Date().toISOString();
    const data = {id:"job",asset_id:"asset",project_id:"project",sha256:"hash",duration_ms:1000,provider_origin:"https://example.test",provider_id:null,status:"queued" as const,stage:"queued",message:null,result:null,receipt:null,created_at:now,updated_at:now,next_poll_at:now};
    await t.run(async ctx => {
      await ctx.db.insert("assets",{legacyId:"asset",data:{id:"asset",project_id:"project",object_key:"key",metadata:"{}",created_at:now}});
      await ctx.db.insert("audio_analysis_jobs",{legacyId:"job",data});
    });
    const first = await t.mutation(internal.analysisWorker.claim,{token:"first"});
    expect(first?.job.id).toBe("job");
    expect(await t.mutation(internal.analysisWorker.claim,{token:"second"})).toBeNull();
    await t.mutation(internal.analysisWorker.save,{token:"first",data:{...data,status:"submitting"}});
    vi.advanceTimersByTime(300001);
    await expect(t.mutation(internal.analysisWorker.save,{token:"first",data:{...data,status:"running",provider_id:"remote"}})).rejects.toThrow("LEASE_LOST");
    expect(await t.mutation(internal.analysisWorker.claim,{token:"second"})).toBeNull();
    const jobs = await t.run(ctx=>ctx.db.query("audio_analysis_jobs").collect());
    expect(jobs[0].data.status).toBe("reconciliation_required");
  } finally { vi.useRealTimers(); }
});

test("upload promotion is atomic, idempotent and refuses conflicting replays", async () => {
  const t = convexTest(schema, modules);
  await t.mutation(internal.projects.commit, {auth: dev, id: "project", expectedRevision: null, document: document(0), assetIds: []});
  const metadata = JSON.stringify({id: "asset", projectId: "project", sha256: "hash", durationMs: 1000});
  const objectKey = "projects/project/originals/asset";
  const data = {id: "asset", project_id: "project", object_key: objectKey, metadata, created_at: new Date().toISOString(), checked_at: new Date().toISOString()};
  await t.mutation(internal.assets.beginUpload, {auth: dev, data});
  await expect(t.mutation(internal.assets.completeUpload, {id: "asset", metadata: "changed", objectKey, analysis: null})).rejects.toThrow("CONFLICT");
  expect(await t.mutation(internal.assets.pendingUploads, {})).toHaveLength(1);
  expect(await t.query(internal.assets.list, {auth: dev, projectId: "project"})).toHaveLength(0);
  await t.mutation(internal.assets.completeUpload, {id: "asset", metadata, objectKey, analysis: null});
  await t.mutation(internal.assets.completeUpload, {id: "asset", metadata, objectKey, analysis: null});
  expect(await t.mutation(internal.assets.pendingUploads, {})).toHaveLength(0);
  expect(await t.query(internal.assets.list, {auth: dev, projectId: "project"})).toHaveLength(1);
  await expect(t.query(internal.assets.get, {auth: dev, projectId: "other", id: "asset"})).rejects.toThrow("ASSET_NOT_FOUND");
});

test("revision compare-and-swap retains one event for competing writes", async () => {
  const t = convexTest(schema, modules);
  await t.mutation(internal.projects.commit, { auth: dev, id: "project", expectedRevision: null, document: document(0), assetIds: [] });
  const results = await Promise.allSettled([1,2].map(() => t.mutation(internal.projects.commit, { auth: dev, id: "project", expectedRevision: 0, document: document(1), assetIds: [] })));
  expect(results.filter(r => r.status === "fulfilled")).toHaveLength(1);
  expect((await t.query(internal.projects.events, {auth: dev, id: "project", after: -1})).map(e => e.revision)).toEqual([0,1]);
});

test("revocation blocks commits and event reads after a project was read", async () => {
  const t = convexTest(schema, modules);
  const issuerHash = "a".repeat(64);
  await t.mutation(internal.sessions.create, {id: "session", tokenHash: "b".repeat(64), issuerHash, clientLabel: "test"});
  const auth = {sessionId: "session", issuerHash, development: false};
  await t.mutation(internal.projects.commit, {auth, id: "project", expectedRevision: null, document: document(0), assetIds: []});
  expect(await t.query(internal.projects.get, {auth, id: "project"})).not.toBeNull();
  await t.mutation(internal.sessions.revoke, {auth, all: false});
  await expect(t.mutation(internal.projects.commit, {auth, id: "project", expectedRevision: 0, document: document(1), assetIds: []})).rejects.toThrow("UNAUTHORIZED");
  await expect(t.query(internal.projects.events, {auth, id: "project", after: -1})).rejects.toThrow("UNAUTHORIZED");
  expect((await t.query(internal.projects.get, {auth: dev, id: "project"}))?.revision).toBe(0);
});

test("failed asset ownership check leaves project and event unchanged", async () => {
  const t = convexTest(schema, modules);
  await t.mutation(internal.projects.commit, {auth: dev, id: "project", expectedRevision: null, document: document(0), assetIds: []});
  await expect(t.mutation(internal.projects.commit, {auth: dev, id: "project", expectedRevision: 0, document: document(1), assetIds: ["missing"]})).rejects.toThrow("ASSET_NOT_FOUND");
  expect((await t.query(internal.projects.get, {auth: dev, id: "project"}))?.revision).toBe(0);
  expect(await t.query(internal.projects.events, {auth: dev, id: "project", after: -1})).toHaveLength(1);
});

test("sessions store hashes, expire at twelve hours, and prune only aged inactive rows", async () => {
  vi.useFakeTimers();
  try {
    const t = convexTest(schema, modules);
    const issuerHash = "a".repeat(64);
    const tokenHash = "b".repeat(64);
    const created = await t.mutation(internal.sessions.create, {id:"expiry", tokenHash, issuerHash, clientLabel:"Test"});
    expect(Date.parse(created.expires_at) - Date.parse(created.created_at)).toBe(43200000);
    const stored = await t.run(ctx => ctx.db.query("operator_sessions").first());
    expect(stored?.data.token_hash).toBe(tokenHash);
    const auth = {sessionId:"expiry", issuerHash, development:false};
    expect(await t.query(internal.sessions.identify, {tokenHash, issuerHash})).toBe("expiry");
    vi.advanceTimersByTime(43200000);
    expect(await t.query(internal.sessions.identify, {tokenHash, issuerHash})).toBeNull();
    await expect(t.mutation(internal.projects.commit, {auth, id:"expired-write", expectedRevision:null, document:document(0), assetIds:[]})).rejects.toThrow("UNAUTHORIZED");
    expect(await t.mutation(internal.maintenance.pruneSessions, {})).toBe(0);
    vi.advanceTimersByTime(7*24*60*60*1000+1);
    await t.mutation(internal.sessions.create, {id:"active", tokenHash:"c".repeat(64), issuerHash, clientLabel:"Active"});
    await t.mutation(internal.sessions.create, {id:"revoked", tokenHash:"d".repeat(64), issuerHash, clientLabel:"Revoked"});
    await t.mutation(internal.sessions.revoke, {auth:{...auth,sessionId:"revoked"},all:false});
    expect(await t.mutation(internal.maintenance.pruneSessions, {})).toBe(1);
    expect(await t.query(internal.sessions.valid, {auth:{...auth,sessionId:"active"}})).toBe(true);
    expect(await t.run(ctx=>ctx.db.query("operator_sessions").collect())).toHaveLength(2);
    vi.advanceTimersByTime(7*24*60*60*1000+1);
    expect(await t.mutation(internal.maintenance.pruneSessions, {})).toBe(1);
    expect((await t.run(ctx=>ctx.db.query("operator_sessions").collect())).map(row=>row.legacyId)).toEqual(["active"]);
  } finally { vi.useRealTimers(); }
});
