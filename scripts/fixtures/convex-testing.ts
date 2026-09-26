// Copied ONLY into the disposable acceptance backend, never the app deployment.
import { v } from "convex/values";
import { internalMutation } from "./_generated/server";

export const transcriptionState = internalMutation({
  args: { assetId: v.string(), mode: v.union(v.literal("legacy"), v.literal("running"), v.literal("read"), v.literal("receipt")), receipt: v.optional(v.any()) },
  handler: async (ctx, { assetId, mode, receipt }) => {
    const row = await ctx.db.query("transcription_jobs").withIndex("by_asset_model", q => q.eq("data.asset_id", assetId)).unique();
    if (!row) throw new Error("Fixture job missing");
    if (mode === "read") {
      if (typeof row.data.receipt !== "string") throw new Error("Expected inline fixture receipt");
      return JSON.parse(row.data.receipt);
    }
    const data = { ...row.data };
    if (mode === "running") data.status = "running";
    if (mode === "receipt") data.receipt = JSON.stringify(receipt);
    if (mode === "legacy") {
      if (typeof data.result !== "string") throw new Error("Expected inline fixture result");
      const result = JSON.parse(data.result);
      delete result.words;
      data.result = JSON.stringify(result);
    }
    await ctx.db.patch(row._id, { data });
    return null;
  },
});

export const clearTranscription = internalMutation({
  args: { projectId: v.string() },
  handler: async (ctx, { projectId }) => {
    const rows = await ctx.db.query("transcription_jobs").collect();
    for (const row of rows) if (row.data.project_id === projectId) await ctx.db.delete(row._id);
  },
});

export const relocateAsset = internalMutation({
  args: { id: v.string(), key: v.string() },
  handler: async (ctx, { id, key }) => {
    const row = await ctx.db.query("assets").withIndex("by_legacy_id", q => q.eq("legacyId", id)).unique();
    if (!row) throw new Error("Fixture asset missing");
    await ctx.db.patch(row._id, { data: { ...row.data, object_key: key } });
  },
});

export const analysisState = internalMutation({
  args: { assetId: v.string(), submitting: v.boolean() },
  handler: async (ctx, { assetId, submitting }) => {
    const row = await ctx.db.query("audio_analysis_jobs").withIndex("by_asset", q => q.eq("data.asset_id", assetId)).unique();
    if (!row) throw new Error("Fixture job missing");
    await ctx.db.patch(row._id, { data: { ...row.data,
      next_poll_at: new Date().toISOString(),
      ...(submitting ? { status: "submitting" as const } : {}),
    } });
  },
});
