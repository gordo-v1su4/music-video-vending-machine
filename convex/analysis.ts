import { ConvexError, v } from "convex/values";
import { internalQuery, internalMutation } from "./_generated/server";
import { identity, requireSession } from "./sessions";

export const get = internalQuery({args:{auth:identity,projectId:v.string(),assetId:v.string()},handler:async(ctx,args)=>{
  await requireSession(ctx,args.auth);
  const asset=await ctx.db.query("assets").withIndex("by_legacy_id",q=>q.eq("legacyId",args.assetId)).unique();
  if(!asset || asset.data.project_id!==args.projectId) throw new ConvexError("ASSET_NOT_FOUND");
  return (await ctx.db.query("audio_analysis_jobs").withIndex("by_asset",q=>q.eq("data.asset_id",args.assetId)).unique())?.data ?? null;
}});
export const enqueue = internalMutation({args:{auth:identity,projectId:v.string(),assetId:v.string(),jobId:v.string(),origin:v.string()},handler:async(ctx,args)=>{
  await requireSession(ctx,args.auth);
  const asset=await ctx.db.query("assets").withIndex("by_legacy_id",q=>q.eq("legacyId",args.assetId)).unique();
  if(!asset || asset.data.project_id!==args.projectId) throw new ConvexError("ASSET_NOT_FOUND");
  const meta=JSON.parse(asset.data.metadata);
  if(!meta.mediaType?.startsWith("audio/") || !(meta.durationMs>0)) throw new ConvexError("INVALID_DOCUMENT");
  if(await ctx.db.query("audio_analysis_jobs").withIndex("by_asset",q=>q.eq("data.asset_id",args.assetId)).unique()) return;
  const now=new Date().toISOString();
  await ctx.db.insert("audio_analysis_jobs",{legacyId:args.jobId,data:{id:args.jobId,asset_id:args.assetId,project_id:args.projectId,sha256:meta.sha256,duration_ms:meta.durationMs,provider_origin:args.origin,provider_id:null,status:"queued",stage:"queued",message:null,result:null,receipt:null,created_at:now,updated_at:now,next_poll_at:now}});
}});
