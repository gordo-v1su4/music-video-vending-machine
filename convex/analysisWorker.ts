import { ConvexError, v } from "convex/values";
import { internalMutation, type MutationCtx } from "./_generated/server";
import { rows } from "./schema";
const name = "audio-analysis";
async function requireLease(ctx: MutationCtx, token: string) {
  const lease = await ctx.db.query("worker_leases").withIndex("by_name", q => q.eq("name", name)).unique();
  if (!lease || lease.token !== token || lease.expiresAt <= Date.now()) throw new ConvexError("LEASE_LOST");
  return lease;
}
export const claim = internalMutation({args: {token: v.string()}, handler: async (ctx, {token}) => {
  const now = Date.now();
  const lease = await ctx.db.query("worker_leases").withIndex("by_name", q => q.eq("name", name)).unique();
  if (lease && lease.expiresAt > now) return null;
  // A prior submission may have reached the provider; never return it to queued.
  const interrupted = await ctx.db.query("audio_analysis_jobs").withIndex("by_status_poll", q => q.eq("data.status", "submitting")).take(32);
  for (const row of interrupted) await ctx.db.patch(row._id, {data:{...row.data, status:"reconciliation_required", stage:"submission_uncertain", message:"The previous submission must be reconciled before another submission.", updated_at:new Date(now).toISOString()}});
  const queued = await ctx.db.query("audio_analysis_jobs").withIndex("by_status_poll", q => q.eq("data.status", "queued").lte("data.next_poll_at", new Date(now).toISOString())).take(1);
  const running = await ctx.db.query("audio_analysis_jobs").withIndex("by_status_poll", q => q.eq("data.status", "running").lte("data.next_poll_at", new Date(now).toISOString())).take(1);
  const row = [...queued,...running].filter(r => Date.parse(r.data.next_poll_at)<=now).sort((a,b) => Date.parse(a.data.next_poll_at)-Date.parse(b.data.next_poll_at))[0];
  if (!row) return null;
  const data = {name, token, jobId:row.data.id, expiresAt:now+5*60*1000};
  if (lease) await ctx.db.replace(lease._id,data); else await ctx.db.insert("worker_leases",data);
  const asset = await ctx.db.query("assets").withIndex("by_legacy_id",q => q.eq("legacyId",row.data.asset_id)).unique();
  if (!asset || asset.data.project_id !== row.data.project_id) throw new ConvexError("ASSET_NOT_FOUND");
  return {job:row.data, asset:asset.data};
}});
export const save = internalMutation({args:{token:v.string(), data:rows.audio_analysis_jobs},handler:async(ctx,{token,data})=>{
  const lease = await requireLease(ctx,token); if (lease.jobId !== data.id) throw new ConvexError("CONFLICT");
  const row = await ctx.db.query("audio_analysis_jobs").withIndex("by_legacy_id",q=>q.eq("legacyId",data.id)).unique();
  if (!row || row.data.asset_id!==data.asset_id || row.data.project_id!==data.project_id || row.data.sha256!==data.sha256 || row.data.provider_origin!==data.provider_origin || row.data.duration_ms!==data.duration_ms) throw new ConvexError("CONFLICT");
  if (row.data.status==="submitting" && data.status==="queued") throw new ConvexError("CONFLICT");
  if (["completed","failed","reconciliation_required"].includes(row.data.status)) throw new ConvexError("CONFLICT");
  await ctx.db.patch(row._id,{data:{...data,updated_at:new Date().toISOString()}});
}});
export const release = internalMutation({args:{token:v.string()},handler:async(ctx,{token})=>{
  const lease = await requireLease(ctx,token);
  await ctx.db.delete(lease._id);
}});
