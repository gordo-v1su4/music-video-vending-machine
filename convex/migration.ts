import { internalMutation, internalQuery } from "./_generated/server";
import { v } from "convex/values";
import { rows } from "./schema";

const snapshot = v.object({
  projects: v.array(rows.projects),
  project_events: v.array(rows.project_events),
  assets: v.array(rows.assets),
  upload_intents: v.array(rows.upload_intents),
  operator_sessions: v.array(rows.operator_sessions),
  audio_analysis_jobs: v.array(rows.audio_analysis_jobs),
  transcription_jobs: v.array(rows.transcription_jobs),
});

// Administrator-only cold migration. No provider calls or scheduling occur here.
// A single mutation makes the bounded pilot snapshot all-or-nothing.
export const importSnapshot = internalMutation({
  args: { snapshot },
  handler: async (ctx, args) => {
    for (const table of Object.keys(rows) as (keyof typeof rows)[]) {
      if (await ctx.db.query(table).first()) {
        throw new Error("Migration requires an empty destination; compare existing data before retrying");
      }
    }
    for (const [table, records] of Object.entries(args.snapshot)) {
      const identities = records.map((r) => "id" in r ? r.id : `${r.project_id}:${r.revision}`);
      if (new Set(identities).size !== identities.length) throw new Error(`Duplicate identity in ${table}`);
    }
    for (const data of args.snapshot.projects) await ctx.db.insert("projects", { legacyId: data.id, data });
    for (const data of args.snapshot.project_events) await ctx.db.insert("project_events", { legacyId: `${data.project_id}:${data.revision}`, data });
    for (const data of args.snapshot.assets) await ctx.db.insert("assets", { legacyId: data.id, data });
    for (const data of args.snapshot.upload_intents) await ctx.db.insert("upload_intents", { legacyId: data.id, data });
    for (const data of args.snapshot.operator_sessions) await ctx.db.insert("operator_sessions", { legacyId: data.id, data });
    for (const data of args.snapshot.audio_analysis_jobs) await ctx.db.insert("audio_analysis_jobs", { legacyId: data.id, data });
    for (const data of args.snapshot.transcription_jobs) await ctx.db.insert("transcription_jobs", { legacyId: data.id, data });
    return Object.fromEntries(Object.entries(args.snapshot).map(([table, records]) => [table, records.length]));
  },
});

export const exportSnapshot = internalQuery({
  args: {},
  returns: snapshot,
  handler: async (ctx) => ({
    projects: (await ctx.db.query("projects").collect()).map(r => r.data),
    project_events: (await ctx.db.query("project_events").collect()).map(r => r.data),
    assets: (await ctx.db.query("assets").collect()).map(r => r.data),
    upload_intents: (await ctx.db.query("upload_intents").collect()).map(r => r.data),
    operator_sessions: (await ctx.db.query("operator_sessions").collect()).map(r => r.data),
    audio_analysis_jobs: (await ctx.db.query("audio_analysis_jobs").collect()).map(r => r.data),
    transcription_jobs: (await ctx.db.query("transcription_jobs").collect()).map(r => r.data),
  }),
});

// Repoint only a verified legacy object key; media identity stays unchanged.
export const relocateAsset = internalMutation({
  args: {id:v.string(),sourceKey:v.string(),targetKey:v.string(),sha256:v.string()},
  handler:async(ctx,args)=>{
    const row=await ctx.db.query("assets").withIndex("by_legacy_id",q=>q.eq("legacyId",args.id)).unique();
    if(!row)throw Error("Missing asset");
    const meta=JSON.parse(row.data.metadata);
    if(meta.sha256!==args.sha256 || args.targetKey!==`projects/${row.data.project_id}/originals/${args.id}`)throw Error("Asset identity mismatch");
    if(row.data.object_key===args.targetKey)return;
    if(row.data.object_key!==args.sourceKey)throw Error("Asset changed during migration");
    await ctx.db.patch(row._id,{data:{...row.data,object_key:args.targetKey}});
  },
});

function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>`${JSON.stringify(k)}:${stable(v)}`).join(",")}}`;
  return JSON.stringify(value);
}

// Run only after copy/readback verification and switching coordinators into a
// maintenance window. Exact row comparisons reject changes since that copy.
export const relocatePayloadBucket = internalMutation({
  args: {
    audio_analysis_jobs: v.array(rows.audio_analysis_jobs),
    transcription_jobs: v.array(rows.transcription_jobs),
  },
  handler: async (ctx, expected) => {
    const leases = await ctx.db.query("worker_leases").collect();
    if (leases.some(lease => lease.expiresAt > Date.now())) throw Error("Active worker lease");
    let changed = 0;
    for (const table of ["audio_analysis_jobs", "transcription_jobs"] as const) {
      const current = await ctx.db.query(table).collect();
      const originals = new Map(expected[table].map(row => [row.id, row]));
      if (originals.size !== expected[table].length || current.length !== originals.size) throw Error("Migration snapshot changed");
      for (const row of current) {
        if (stable(row.data) !== stable(originals.get(row.data.id))) throw Error("Migration snapshot changed");
        if (["queued", "submitting", "running"].includes(row.data.status)) throw Error("Active job");
        function move(value: typeof row.data.result) {
          if (!value || typeof value === "string") return value;
          if (value.bucket !== "music-vending-machine" || !/^[a-f0-9]{64}$/.test(value.sha256)
            || value.key !== `projects/${row.data.project_id}/mvvm/payloads/${value.sha256}.json`
            || !Number.isSafeInteger(value.bytes) || value.bytes < 0 || value.bytes > 8 * 1024 * 1024) throw Error("Invalid source payload reference");
          changed++;
          return {...value, bucket:"mvvm"};
        }
        const result=move(row.data.result), receipt=move(row.data.receipt);
        // Narrow the two row shapes before patching; no casts hide a schema mismatch.
        if ("model" in row.data) {
          await ctx.db.patch(row._id, {data:{...row.data,result,receipt}});
        } else {
          await ctx.db.patch(row._id, {data:{...row.data,result,receipt}});
        }
      }
    }
    return {changed};
  },
});

// Bounded cleanup of this migration's archived acceptance fixtures only.
// The caller saves expected to private storage before invoking this mutation.
export const removeAcceptanceFixtures = internalMutation({
  args: { expected: snapshot, projectIds: v.array(v.string()), protectedProjectIds: v.array(v.string()) },
  handler: async (ctx, args) => {
    const ids=new Set(args.projectIds), protectedIds=new Set(args.protectedProjectIds);
    if (!ids.size || ids.size!==args.projectIds.length || [...ids].some(id=>protectedIds.has(id))) throw Error("Invalid fixture identities");
    const identity=(row:{id?:string;project_id?:string;revision?:number})=>row.id??`${row.project_id}:${row.revision}`;
    for(const table of Object.keys(rows) as (keyof typeof rows)[]){
      const current=(await ctx.db.query(table).collect()).map(row=>row.data);
      const sort=(records:typeof current)=>[...records].sort((a,b)=>identity(a).localeCompare(identity(b)));
      if(stable(sort(current))!==stable(sort(args.expected[table])))throw Error("Migration snapshot changed");
    }
    for(const id of ids){
      const project=args.expected.projects.find(row=>row.id===id);
      if(!project)throw Error("Missing fixture project");
      const doc=JSON.parse(project.document);
      if(doc.id!==id || doc.name!=="MVVM Convex persistence acceptance" || project.revision>1)throw Error("Not an acceptance fixture");
    }
    for(const asset of args.expected.assets.filter(row=>ids.has(row.project_id))){
      const meta=JSON.parse(asset.metadata);
      const known=(meta.name==="recovery-fixture.bin" && meta.sha256==="558af3b50aa60f2dffa84240acfa189646a0a5afa9759e65fbfe41d6056a8e54" && meta.sizeBytes===30)
        || (meta.name==="silence.wav" && meta.sha256==="643f8a8dc8bd9c19225afffad2becfec5426180b3749cb208abdf1a6c8354efc" && meta.sizeBytes===32044);
      if(!known || meta.id!==asset.id || meta.projectId!==asset.project_id)throw Error("Unknown fixture asset");
    }
    const jobs=[...args.expected.audio_analysis_jobs,...args.expected.transcription_jobs].filter(row=>ids.has(row.project_id));
    if(jobs.some(row=>["queued","submitting","running"].includes(row.status)))throw Error("Active fixture job");
    for(const job of args.expected.audio_analysis_jobs.filter(row=>ids.has(row.project_id))){
      if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(job.provider_origin))throw Error("Not a loopback fixture provider");
    }
    const leases=await ctx.db.query("worker_leases").collect();
    if(leases.some(row=>row.expiresAt>Date.now()))throw Error("Active worker lease");
    const removed:Record<string,number>={};
    for(const table of Object.keys(rows) as (keyof typeof rows)[]){
      removed[table]=0;
      if(table==="operator_sessions")continue;
      for(const row of await ctx.db.query(table).collect()){
        const belongs=table==="projects" && "id" in row.data ? ids.has(row.data.id)
          : "project_id" in row.data && ids.has(row.data.project_id);
        if(belongs){await ctx.db.delete(row._id);removed[table]++;}
      }
    }
    const jobIds=new Set(jobs.map(row=>row.id));
    for(const lease of leases)if(jobIds.has(lease.jobId))await ctx.db.delete(lease._id);
    return removed;
  },
});
