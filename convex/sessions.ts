import { ConvexError, v } from "convex/values";
import { internalMutation, internalQuery, type QueryCtx } from "./_generated/server";

// These functions are internal. Only the trusted coordinator may supply identity.
export const identity = v.object({ sessionId: v.union(v.string(), v.null()), issuerHash: v.union(v.string(), v.null()), development: v.boolean() });
type Identity = { sessionId: string | null; issuerHash: string | null; development: boolean };
export async function requireSession(ctx: QueryCtx, auth: Identity) {
  if (auth.sessionId === null && auth.issuerHash === null && auth.development) return;
  if (!auth.sessionId || !auth.issuerHash) throw new ConvexError("UNAUTHORIZED");
  const row = await ctx.db.query("operator_sessions").withIndex("by_legacy_id", q => q.eq("legacyId", auth.sessionId!)).unique();
  if (!row || row.data.issuer_hash !== auth.issuerHash || row.data.revoked_at !== null || !(Date.parse(row.data.expires_at) > Date.now())) throw new ConvexError("UNAUTHORIZED");
}
export const valid = internalQuery({ args: { auth: identity }, handler: async (ctx, { auth }) => {
  try { await requireSession(ctx, auth); return true; } catch (error) { if (error instanceof ConvexError && error.data === "UNAUTHORIZED") return false; throw error; }
}});
export const identify = internalQuery({ args: { tokenHash: v.string(), issuerHash: v.string() }, handler: async (ctx, args) => {
  const row = await ctx.db.query("operator_sessions").withIndex("by_token", q => q.eq("data.token_hash", args.tokenHash)).unique();
  if (!row || row.data.issuer_hash !== args.issuerHash || row.data.revoked_at !== null || !(Date.parse(row.data.expires_at) > Date.now())) return null;
  return row.data.id;
}});
export const create = internalMutation({ args: { id: v.string(), tokenHash: v.string(), issuerHash: v.string(), clientLabel: v.string() }, handler: async (ctx, args) => {
  if (!/^(?:\\x)?[a-f0-9]{64}$/.test(args.tokenHash) || !/^(?:\\x)?[a-f0-9]{64}$/.test(args.issuerHash)) throw new ConvexError("INVALID_HASH");
  const label = args.clientLabel.trim();
  if (!label || [...label].length > 80 || /[\x00-\x1f\x7f-\x9f]/.test(label)) throw new ConvexError("INVALID_LABEL");
  if (await ctx.db.query("operator_sessions").withIndex("by_legacy_id", q => q.eq("legacyId", args.id)).unique()) throw new ConvexError("CONFLICT");
  if (await ctx.db.query("operator_sessions").withIndex("by_token", q => q.eq("data.token_hash", args.tokenHash)).unique()) throw new ConvexError("CONFLICT");
  const now = Date.now();
  const data = { id: args.id, token_hash: args.tokenHash, issuer_hash: args.issuerHash, client_label: label, created_at: new Date(now).toISOString(), expires_at: new Date(now + 12*60*60*1000).toISOString(), revoked_at: null };
  await ctx.db.insert("operator_sessions", { legacyId: args.id, data });
  return { id: data.id, client_label: label, created_at: data.created_at, expires_at: data.expires_at };
}});
export const revoke = internalMutation({ args: { auth: identity, all: v.boolean() }, handler: async (ctx, { auth, all }) => {
  await requireSession(ctx, auth);
  if (!auth.sessionId || !auth.issuerHash) throw new ConvexError("UNAUTHORIZED");
  const rows = all ? await ctx.db.query("operator_sessions").withIndex("by_issuer", q => q.eq("data.issuer_hash", auth.issuerHash!)).collect() : await ctx.db.query("operator_sessions").withIndex("by_legacy_id", q => q.eq("legacyId", auth.sessionId!)).collect();
  for (const row of rows) if (row.data.issuer_hash === auth.issuerHash && row.data.revoked_at === null) await ctx.db.patch(row._id, { data: { ...row.data, revoked_at: new Date().toISOString() } });
}});
export const current = internalQuery({ args: { auth: identity }, handler: async (ctx, {auth}) => {
  await requireSession(ctx, auth);
  if (!auth.sessionId) return null;
  const row = await ctx.db.query("operator_sessions").withIndex("by_legacy_id", q => q.eq("legacyId", auth.sessionId!)).unique();
  if (!row) throw new ConvexError("UNAUTHORIZED");
  const {id, client_label, created_at, expires_at} = row.data;
  return {id, client_label, created_at, expires_at};
}});
