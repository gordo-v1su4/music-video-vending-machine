import { ConvexError, v } from "convex/values";
import { internalMutation, internalQuery } from "./_generated/server";
import { identity, requireSession } from "./sessions";
import { rows } from "./schema";

export const get = internalQuery({ args: { auth: identity, projectId: v.string(), id: v.string() }, handler: async (ctx, args) => {
  await requireSession(ctx, args.auth);
  const row = await ctx.db.query("assets").withIndex("by_legacy_id", q => q.eq("legacyId", args.id)).unique();
  if (!row || row.data.project_id !== args.projectId) throw new ConvexError("ASSET_NOT_FOUND");
  return row.data;
}});
export const beginUpload = internalMutation({ args: { auth: identity, data: rows.upload_intents }, handler: async (ctx, {auth, data}) => {
  await requireSession(ctx, auth);
  if (!await ctx.db.query("projects").withIndex("by_legacy_id", q => q.eq("legacyId", data.project_id)).unique()) throw new ConvexError("NOT_FOUND");
  const metadata = JSON.parse(data.metadata);
  if (metadata.id !== data.id || metadata.projectId !== data.project_id || data.object_key !== `projects/${data.project_id}/originals/${data.id}`) throw new ConvexError("INVALID_DOCUMENT");
  if (await ctx.db.query("assets").withIndex("by_legacy_id", q => q.eq("legacyId", data.id)).unique()) throw new ConvexError("CONFLICT");
  const existing = await ctx.db.query("upload_intents").withIndex("by_legacy_id", q => q.eq("legacyId", data.id)).unique();
  if (existing) {
    if (existing.data.metadata !== data.metadata || existing.data.object_key !== data.object_key) throw new ConvexError("CONFLICT");
    return;
  }
  await ctx.db.insert("upload_intents", {legacyId: data.id, data});
}});

// Object verification happens in the coordinator; only immutable verified metadata
// can be promoted. Completing twice is safe, but a conflicting replay is rejected.
export const completeUpload = internalMutation({ args: { id: v.string(), metadata: v.string(), objectKey: v.string(), analysis: v.union(rows.audio_analysis_jobs, v.null()) }, handler: async (ctx, args) => {
  const pending = await ctx.db.query("upload_intents").withIndex("by_legacy_id", q => q.eq("legacyId", args.id)).unique();
  const existing = await ctx.db.query("assets").withIndex("by_legacy_id", q => q.eq("legacyId", args.id)).unique();
  const source = pending?.data ?? existing?.data;
  if (!source) throw new ConvexError("NOT_FOUND");
  if (source.metadata !== args.metadata || source.object_key !== args.objectKey) throw new ConvexError("CONFLICT");
  if (existing && (existing.data.metadata !== args.metadata || existing.data.object_key !== args.objectKey)) throw new ConvexError("CONFLICT");
  if (!existing) await ctx.db.insert("assets", {legacyId: args.id, data: {id: args.id, project_id: source.project_id, object_key: args.objectKey, metadata: args.metadata, created_at: source.created_at}});
  if (args.analysis) {
    const meta = JSON.parse(source.metadata);
    if (args.analysis.asset_id !== args.id || args.analysis.project_id !== source.project_id || args.analysis.sha256 !== meta.sha256 || args.analysis.duration_ms !== meta.durationMs || args.analysis.status !== "queued") throw new ConvexError("INVALID_DOCUMENT");
    if (!await ctx.db.query("audio_analysis_jobs").withIndex("by_asset", q => q.eq("data.asset_id", args.id)).unique()) await ctx.db.insert("audio_analysis_jobs", {legacyId: args.analysis.id, data: args.analysis});
  }
  if (pending) await ctx.db.delete(pending._id);
}});
export const pendingUploads = internalMutation({ args: {}, handler: async ctx => {
  const pending = await ctx.db.query("upload_intents").withIndex("by_checked").take(32);
  for (const row of pending) await ctx.db.patch(row._id, {data: {...row.data, checked_at: new Date().toISOString()}});
  return pending.map(r => r.data);
}});
export const list = internalQuery({ args: { auth: identity, projectId: v.string() }, handler: async (ctx, args) => {
  await requireSession(ctx, args.auth);
  if (!await ctx.db.query("projects").withIndex("by_legacy_id", q => q.eq("legacyId", args.projectId)).unique()) throw new ConvexError("NOT_FOUND");
  return (await ctx.db.query("assets").withIndex("by_project", q => q.eq("data.project_id", args.projectId)).collect()).map(r => r.data);
}});
