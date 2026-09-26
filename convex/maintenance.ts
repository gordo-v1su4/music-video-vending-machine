import {internalMutation,internalQuery} from "./_generated/server";
export const health=internalQuery({args:{},handler:async ctx=>{await ctx.db.query("projects").first();return true;}});
export const pruneSessions=internalMutation({args:{},handler:async ctx=>{
  const cutoff=new Date(Date.now()-7*24*60*60*1000).toISOString();
  const expired=await ctx.db.query("operator_sessions").withIndex("by_expiry",q=>q.lt("data.expires_at",cutoff)).take(1000);
  const revoked=await ctx.db.query("operator_sessions").withIndex("by_revocation",q=>q.gt("data.revoked_at",null).lt("data.revoked_at",cutoff)).take(1000);
  const ids=[...new Set([...expired,...revoked].filter(r=>Date.parse(r.data.expires_at)<Date.parse(cutoff)||(r.data.revoked_at!==null && Date.parse(r.data.revoked_at)<Date.parse(cutoff))).map(r=>r._id))].slice(0,1000);
  for(const id of ids)await ctx.db.delete(id);
  return ids.length;
}});
