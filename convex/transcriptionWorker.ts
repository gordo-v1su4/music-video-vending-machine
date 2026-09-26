import {ConvexError,v} from "convex/values";
import {internalMutation,type MutationCtx} from "./_generated/server";
import {rows} from "./schema";
const name="transcription";
async function leaseFor(ctx:MutationCtx,token:string){
  const lease=await ctx.db.query("worker_leases").withIndex("by_name",q=>q.eq("name",name)).unique();
  if(!lease || lease.token!==token || lease.expiresAt<=Date.now())throw new ConvexError("LEASE_LOST");
  return lease;
}
export const claim=internalMutation({args:{token:v.string()},handler:async(ctx,{token})=>{
  const now=Date.now();
  const lease=await ctx.db.query("worker_leases").withIndex("by_name",q=>q.eq("name",name)).unique();
  if(lease && lease.expiresAt>now)return null;
  const interrupted=await ctx.db.query("transcription_jobs").withIndex("by_status_poll",q=>q.eq("data.status","running")).take(32);
  for(const row of interrupted)await ctx.db.patch(row._id,{data:{...row.data,status:"reconciliation_required",message:"Transcription was interrupted; reconcile retained responses before another paid request.",updated_at:new Date(now).toISOString()}});
  const queued=await ctx.db.query("transcription_jobs").withIndex("by_status_poll",q=>q.eq("data.status","queued").lte("data.next_poll_at",new Date(now).toISOString())).take(1);
  const row=queued.filter(r=>Date.parse(r.data.next_poll_at)<=now).sort((a,b)=>Date.parse(a.data.next_poll_at)-Date.parse(b.data.next_poll_at))[0];
  if(!row)return null;
  const data={name,token,jobId:row.data.id,expiresAt:now+600000};
  if(lease)await ctx.db.replace(lease._id,data);else await ctx.db.insert("worker_leases",data);
  const asset=await ctx.db.query("assets").withIndex("by_legacy_id",q=>q.eq("legacyId",row.data.asset_id)).unique();
  if(!asset || asset.data.project_id!==row.data.project_id)throw new ConvexError("ASSET_NOT_FOUND");
  return {job:row.data,asset:asset.data};
}});
export const save=internalMutation({args:{token:v.string(),id:v.string(),status:v.optional(rows.transcription_jobs.fields.status),message:v.union(v.string(),v.null()),receipt:v.optional(rows.transcription_jobs.fields.receipt),result:v.optional(rows.transcription_jobs.fields.result)},handler:async(ctx,args)=>{
  const lease=await leaseFor(ctx,args.token);
  if(lease.jobId!==args.id)throw new ConvexError("CONFLICT");
  const row=await ctx.db.query("transcription_jobs").withIndex("by_legacy_id",q=>q.eq("legacyId",args.id)).unique();
  if(!row || !["queued","running"].includes(row.data.status) || (row.data.status==="running" && args.status==="queued"))throw new ConvexError("CONFLICT");
  const data={...row.data,message:args.message,updated_at:new Date().toISOString(),next_poll_at:new Date(Date.now()+30000).toISOString()};
  if(args.status!==undefined)data.status=args.status;
  if(args.receipt!==undefined)data.receipt=args.receipt;
  if(args.result!==undefined)data.result=args.result;
  await ctx.db.patch(row._id,{data});
  await ctx.db.patch(lease._id,{expiresAt:Date.now()+600000});
}});
export const release=internalMutation({args:{token:v.string()},handler:async(ctx,{token})=>{const lease=await leaseFor(ctx,token);await ctx.db.delete(lease._id);}});
