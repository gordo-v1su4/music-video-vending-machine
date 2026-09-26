import { convexTest } from "convex-test";
import { expect, test } from "vitest";
import schema from "../convex/schema";
import { internal } from "../convex/_generated/api";
const modules = import.meta.glob("../convex/**/*.ts");
const hash="a".repeat(64);
const ref={kind:"rustfs-json-v1" as const,bucket:"music-vending-machine",key:`projects/project/mvvm/payloads/${hash}.json`,sha256:hash,bytes:123};
const job={id:"job",asset_id:"asset",project_id:"project",sha256:hash,model:"stack-structure-v1" as const,status:"completed" as const,message:null,result:ref,receipt:"{}",created_at:"2026-09-26",updated_at:"2026-09-26",next_poll_at:"2026-09-26"};

test("bucket switch preserves every other field and rejects stale retry",async()=>{
  const t=convexTest(schema,modules);
  await t.run(ctx=>ctx.db.insert("transcription_jobs",{legacyId:job.id,data:job}));
  const expected={audio_analysis_jobs:[],transcription_jobs:[job]};
  expect(await t.mutation(internal.migration.relocatePayloadBucket,expected)).toEqual({changed:1});
  const actual=await t.run(ctx=>ctx.db.query("transcription_jobs").first());
  expect(actual?.data).toEqual({...job,result:{...ref,bucket:"mvvm"}});
  await expect(t.mutation(internal.migration.relocatePayloadBucket,expected)).rejects.toThrow("snapshot changed");
});

test("changed job data is not overwritten by a prepared migration",async()=>{
  const t=convexTest(schema,modules);
  await t.run(ctx=>ctx.db.insert("transcription_jobs",{legacyId:job.id,data:{...job,message:"new recovery"}}));
  await expect(t.mutation(internal.migration.relocatePayloadBucket,{audio_analysis_jobs:[],transcription_jobs:[job]})).rejects.toThrow("snapshot changed");
  expect((await t.run(ctx=>ctx.db.query("transcription_jobs").first()))?.data.message).toBe("new recovery");
});

test("invalid later reference rolls back earlier changes",async()=>{
  const t=convexTest(schema,modules);
  const second={...job,id:"second",result:{...ref,key:"projects/another/mvvm/payloads/wrong.json"}};
  await t.run(async ctx=>{
    await ctx.db.insert("transcription_jobs",{legacyId:job.id,data:job});
    await ctx.db.insert("transcription_jobs",{legacyId:second.id,data:second});
  });
  await expect(t.mutation(internal.migration.relocatePayloadBucket,{audio_analysis_jobs:[],transcription_jobs:[job,second]})).rejects.toThrow("Invalid source");
  expect((await t.run(ctx=>ctx.db.query("transcription_jobs").collect())).every(row=>typeof row.data.result==="object" && row.data.result?.bucket==="music-vending-machine")).toBe(true);
});

test("active jobs and live leases prevent the bucket switch",async()=>{
  const t=convexTest(schema,modules);
  const active={...job,status:"running" as const};
  await t.run(ctx=>ctx.db.insert("transcription_jobs",{legacyId:active.id,data:active}));
  await expect(t.mutation(internal.migration.relocatePayloadBucket,{audio_analysis_jobs:[],transcription_jobs:[active]})).rejects.toThrow("Active job");
  await t.run(ctx=>ctx.db.insert("worker_leases",{name:"transcription",token:"worker",jobId:job.id,expiresAt:Date.now()+600000}));
  await expect(t.mutation(internal.migration.relocatePayloadBucket,{audio_analysis_jobs:[],transcription_jobs:[active]})).rejects.toThrow("Active worker lease");
});

test("fixture cleanup preserves protected projects and sessions, and refuses stale archives",async()=>{
  const t=convexTest(schema,modules);
  await t.run(async ctx=>{
    for(const id of ["real","fixture"]) await ctx.db.insert("projects",{legacyId:id,data:{id,revision:0,document:JSON.stringify({id,name:"MVVM Convex persistence acceptance"}),updated_at:"now"}});
    await ctx.db.insert("operator_sessions",{legacyId:"session",data:{id:"session",token_hash:"hash",issuer_hash:"issuer",client_label:"retained",created_at:"now",expires_at:"later",revoked_at:null}});
  });
  const expected=await t.query(internal.migration.exportSnapshot,{});
  await expect(t.mutation(internal.migration.removeAcceptanceFixtures,{expected,projectIds:["real"],protectedProjectIds:["real"]})).rejects.toThrow("Invalid fixture identities");
  const removed=await t.mutation(internal.migration.removeAcceptanceFixtures,{expected,projectIds:["fixture"],protectedProjectIds:["real"]});
  expect(removed.projects).toBe(1);
  const after=await t.query(internal.migration.exportSnapshot,{});
  expect(after.projects.map(row=>row.id)).toEqual(["real"]);
  expect(after.operator_sessions).toEqual(expected.operator_sessions);
  await expect(t.mutation(internal.migration.removeAcceptanceFixtures,{expected,projectIds:["fixture"],protectedProjectIds:["real"]})).rejects.toThrow("snapshot changed");
});

test("a fixture-like project name cannot authorize deletion of real media",async()=>{
  const t=convexTest(schema,modules);
  await t.run(async ctx=>{
    await ctx.db.insert("projects",{legacyId:"fixture",data:{id:"fixture",revision:0,document:JSON.stringify({id:"fixture",name:"MVVM Convex persistence acceptance"}),updated_at:"now"}});
    await ctx.db.insert("assets",{legacyId:"asset",data:{id:"asset",project_id:"fixture",object_key:"key",metadata:JSON.stringify({name:"song.mp3",sha256:hash,sizeBytes:100}),created_at:"now"}});
  });
  const expected=await t.query(internal.migration.exportSnapshot,{});
  await expect(t.mutation(internal.migration.removeAcceptanceFixtures,{expected,projectIds:["fixture"],protectedProjectIds:[]})).rejects.toThrow("Unknown fixture asset");
  expect(await t.query(internal.migration.exportSnapshot,{})).toEqual(expected);
});
