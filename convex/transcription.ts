import {ConvexError,v} from "convex/values";
import {internalMutation,internalQuery} from "./_generated/server";
import {identity,requireSession} from "./sessions";
import {rows} from "./schema";

export const get=internalQuery({args:{auth:identity,projectId:v.string(),assetId:v.string()},handler:async(ctx,args)=>{
  await requireSession(ctx,args.auth);
  const asset=await ctx.db.query("assets").withIndex("by_legacy_id",q=>q.eq("legacyId",args.assetId)).unique();
  if(!asset || asset.data.project_id!==args.projectId) throw new ConvexError("ASSET_NOT_FOUND");
  const jobs=await ctx.db.query("transcription_jobs").withIndex("by_asset_model",q=>q.eq("data.asset_id",args.assetId)).collect();
  return jobs.sort((a,b)=>Date.parse(b.data.created_at)-Date.parse(a.data.created_at))[0]?.data ?? null;
}});
export const enqueue=internalMutation({args:{auth:identity,projectId:v.string(),assetId:v.string(),jobId:v.string()},handler:async(ctx,args)=>{
  await requireSession(ctx,args.auth);
  const asset=await ctx.db.query("assets").withIndex("by_legacy_id",q=>q.eq("legacyId",args.assetId)).unique();
  if(!asset || asset.data.project_id!==args.projectId) throw new ConvexError("ASSET_NOT_FOUND");
  const meta=JSON.parse(asset.data.metadata);
  if(!meta.mediaType?.startsWith("audio/") || !(meta.durationMs>0)) throw new ConvexError("INVALID_DOCUMENT");
  if(await ctx.db.query("transcription_jobs").withIndex("by_asset_model",q=>q.eq("data.asset_id",args.assetId).eq("data.model","stack-structure-v1")).unique()) return;
  const now=new Date().toISOString();
  await ctx.db.insert("transcription_jobs",{legacyId:args.jobId,data:{id:args.jobId,asset_id:args.assetId,project_id:args.projectId,sha256:meta.sha256,model:"stack-structure-v1",status:"queued",message:null,result:null,receipt:null,created_at:now,updated_at:now,next_poll_at:now}});
}});
export const recover=internalMutation({args:{auth:identity,expectedUpdatedAt:v.string(),allowCompleted:v.optional(v.boolean()),data:rows.transcription_jobs},handler:async(ctx,{auth,expectedUpdatedAt,allowCompleted,data})=>{
  await requireSession(ctx,auth);
  const row=await ctx.db.query("transcription_jobs").withIndex("by_legacy_id",q=>q.eq("legacyId",data.id)).unique();
  if(!row || Date.parse(row.data.updated_at)!==Date.parse(expectedUpdatedAt) || !["failed","reconciliation_required",...(allowCompleted?["completed"]:[])].includes(row.data.status)) throw new ConvexError("CONFLICT");
  const latest=(await ctx.db.query("transcription_jobs").withIndex("by_asset_model",q=>q.eq("data.asset_id",row.data.asset_id)).collect()).sort((a,b)=>Date.parse(b.data.created_at)-Date.parse(a.data.created_at))[0];
  const asset=await ctx.db.query("assets").withIndex("by_legacy_id",q=>q.eq("legacyId",data.asset_id)).unique();
  if(latest?._id!==row._id || !asset || asset.data.project_id!==data.project_id || row.data.asset_id!==data.asset_id || row.data.project_id!==data.project_id || row.data.sha256!==data.sha256 || JSON.parse(asset.data.metadata).sha256!==data.sha256 || row.data.model!==data.model || data.status!=="completed") throw new ConvexError("CONFLICT");
  // Recovery cannot queue a new provider call. Domain reconciliation runs in Rust.
  await ctx.db.patch(row._id,{data:{...row.data,status:"completed",result:data.result,receipt:data.receipt,message:"Recovered existing provider responses; no new paid request.",updated_at:new Date().toISOString()}});
}});
