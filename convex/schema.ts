import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

const nullableText = v.union(v.string(), v.null());
// Domain JSON is opaque to storage. Encoding avoids Convex's nested-array limit
// for full-resolution analysis curves; Rust still validates domain documents.
const blob = v.object({ kind: v.literal("rustfs-json-v1"), bucket: v.string(), key: v.string(), sha256: v.string(), bytes: v.number() });
const nullableJson = v.union(v.string(), blob, v.null());
const timestamps = { created_at: v.string(), updated_at: v.string(), next_poll_at: v.string() };
export const rows = {
  projects: v.object({ id: v.string(), revision: v.number(), document: v.string(), updated_at: v.string() }),
  project_events: v.object({ project_id: v.string(), revision: v.number(), document: v.string(), created_at: v.string() }),
  assets: v.object({ id: v.string(), project_id: v.string(), object_key: v.string(), metadata: v.string(), created_at: v.string() }),
  upload_intents: v.object({ id: v.string(), project_id: v.string(), object_key: v.string(), metadata: v.string(), created_at: v.string(), checked_at: v.string() }),
  operator_sessions: v.object({ id: v.string(), token_hash: v.string(), issuer_hash: v.string(), client_label: v.string(), created_at: v.string(), expires_at: v.string(), revoked_at: nullableText }),
  audio_analysis_jobs: v.object({ id: v.string(), asset_id: v.string(), project_id: v.string(), sha256: v.string(), duration_ms: v.number(), provider_origin: v.string(), provider_id: nullableText,
    status: v.union(v.literal("queued"), v.literal("submitting"), v.literal("running"), v.literal("completed"), v.literal("failed"), v.literal("reconciliation_required")),
    stage: v.string(), message: nullableText, result: nullableJson, receipt: nullableJson, ...timestamps }),
  transcription_jobs: v.object({ id: v.string(), asset_id: v.string(), project_id: v.string(), sha256: v.string(),
    status: v.union(v.literal("queued"), v.literal("running"), v.literal("completed"), v.literal("failed"), v.literal("reconciliation_required")),
    model: v.union(v.literal("legacy-nova-3"), v.literal("stack-structure-v1")), message: nullableText, result: nullableJson, receipt: nullableJson, ...timestamps }),
};
export default defineSchema({
  worker_leases: defineTable({name: v.string(), token: v.string(), jobId: v.string(), expiresAt: v.number()}).index("by_name", ["name"]),
  projects: defineTable({ legacyId: v.string(), data: rows.projects }).index("by_legacy_id", ["legacyId"]),
  project_events: defineTable({ legacyId: v.string(), data: rows.project_events }).index("by_legacy_id", ["legacyId"]).index("by_project_revision", ["data.project_id", "data.revision"]),
  assets: defineTable({ legacyId: v.string(), data: rows.assets }).index("by_legacy_id", ["legacyId"]).index("by_project", ["data.project_id"]).index("by_object_key", ["data.object_key"]),
  upload_intents: defineTable({ legacyId: v.string(), data: rows.upload_intents }).index("by_legacy_id", ["legacyId"]).index("by_checked", ["data.checked_at"]).index("by_object_key", ["data.object_key"]),
  operator_sessions: defineTable({ legacyId: v.string(), data: rows.operator_sessions }).index("by_legacy_id", ["legacyId"]).index("by_token", ["data.token_hash"]).index("by_issuer", ["data.issuer_hash"]).index("by_expiry", ["data.expires_at"]).index("by_revocation", ["data.revoked_at"]),
  audio_analysis_jobs: defineTable({ legacyId: v.string(), data: rows.audio_analysis_jobs }).index("by_legacy_id", ["legacyId"]).index("by_asset", ["data.asset_id"]).index("by_status_poll", ["data.status", "data.next_poll_at"]),
  transcription_jobs: defineTable({ legacyId: v.string(), data: rows.transcription_jobs }).index("by_legacy_id", ["legacyId"]).index("by_asset_model", ["data.asset_id", "data.model"]).index("by_status_poll", ["data.status", "data.next_poll_at"]),
});
