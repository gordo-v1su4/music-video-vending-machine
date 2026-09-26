import { ConvexError, v } from "convex/values";
import { internalMutation, internalQuery } from "./_generated/server";
import { identity, requireSession } from "./sessions";

export const list = internalQuery({ args: { auth: identity }, handler: async (ctx, { auth }) => {
  await requireSession(ctx, auth);
  return (await ctx.db.query("projects").collect()).sort((a,b) => Date.parse(b.data.updated_at)-Date.parse(a.data.updated_at)).map(r => r.data.document);
}});
export const get = internalQuery({ args: { auth: identity, id: v.string() }, handler: async (ctx, { auth, id }) => {
  await requireSession(ctx, auth);
  return (await ctx.db.query("projects").withIndex("by_legacy_id", q => q.eq("legacyId", id)).unique())?.data ?? null;
}});
// Domain validation remains in Rust. Commit revision and event atomically,
// rechecking session validity so revocation cannot race a previously read project.
export const commit = internalMutation({ args: { auth: identity, id: v.string(), expectedRevision: v.union(v.number(), v.null()), document: v.string(), assetIds: v.array(v.string()) }, handler: async (ctx, args) => {
  await requireSession(ctx, args.auth);
  const current = await ctx.db.query("projects").withIndex("by_legacy_id", q => q.eq("legacyId", args.id)).unique();
  if (args.expectedRevision === null ? current !== null : !current || current.data.revision !== args.expectedRevision) throw new ConvexError("CONFLICT");
  const document = JSON.parse(args.document);
  const revision = args.expectedRevision === null ? 0 : args.expectedRevision + 1;
  if (!Number.isSafeInteger(revision) || revision < 0 || document.id !== args.id || document.revision !== revision) throw new ConvexError("INVALID_DOCUMENT");
  for (const id of args.assetIds) {
    const asset = await ctx.db.query("assets").withIndex("by_legacy_id", q => q.eq("legacyId", id)).unique();
    if (!asset || asset.data.project_id !== args.id) throw new ConvexError("ASSET_NOT_FOUND");
  }
  const now = new Date().toISOString();
  const data = { id: args.id, revision, document: args.document, updated_at: now };
  if (current) await ctx.db.replace(current._id, { legacyId: args.id, data });
  else await ctx.db.insert("projects", { legacyId: args.id, data });
  await ctx.db.insert("project_events", { legacyId: `${args.id}:${revision}`, data: { project_id: args.id, revision, document: args.document, created_at: now } });
  return data;
}});
export const events = internalQuery({ args: { auth: identity, id: v.string(), after: v.number() }, handler: async (ctx, { auth, id, after }) => {
  await requireSession(ctx, auth);
  return (await ctx.db.query("project_events").withIndex("by_project_revision", q => q.eq("data.project_id", id).gt("data.revision", after)).take(100)).map(r => r.data);
}});
