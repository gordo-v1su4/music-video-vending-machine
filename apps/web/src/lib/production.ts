// Types and pure helpers for the production journey (scripts/mvvm_gen/production*.py via /pilot-api/production).

export type Decision = "pending" | "approved" | "rejected";
export type Reference = {
  id: string;
  role: string;
  decision: Decision;
  path: string;
  sha256?: string;
  provenance?: string;
  transform?: string;
  note?: string;
  character?: string;
  frame?: number;
};
export type Character = {
  id: string;
  name: string;
  look: string;
  look_note?: string;
  refmod?: { name: string; sha256: string; mode: string; source_ref?: string; created?: string };
};
export type Slot = {
  slot: string;
  title: string;
  song_s: [number, number];
  kind: "supplied" | "generate";
  characters: string[];
  location: string;
  entry: string;
  exit: string;
  camera: string;
  action?: string;
  cuts: number;
  source?: string;
  range_s?: [number, number];
};
export type Packet = {
  id: string;
  revision: number;
  fingerprint: string;
  approved: boolean;
  blocking: string[];
  approval?: { fingerprint: string; by: string; at: string };
  brief: string;
  characters: Character[];
  references: Reference[];
  sequence: { id: string; song_start_s: number; song_end_s: number; clips: Slot[] };
  workflow: { name: string; model: string; render_size: Record<string, number>; route: string };
  allowance: { attempts_per_shot: number; repair_renders: number; gpu_minutes: number; paid_fallback: boolean };
};
export type Shot = { id: string; in: number; out: number; status: "proposed" | "reviewed"; note: string; by: string | null };
export type Clip = {
  id: string;
  label: string;
  source: "generated" | "supplied";
  path: string;
  sha256: string;
  media: { frames: number; fps: number; width: number; height: number; duration_s: number; audio: boolean };
  lineage: Record<string, unknown>;
  shots: Shot[];
};
export type LintFinding = { code: string; severity: "error" | "warning" | "info"; message: string; where?: string };
export type Lint = { ok: boolean; frames: number; duration_actual_s: number; findings: LintFinding[] };
export type SavedPrompt = {
  slot: string;
  text: string;
  input_map: Record<string, unknown>;
  duration: number;
  cuts: number | null;
  packet_revision: number;
  lint: Lint;
  saved_at: string;
};
export type Run = {
  label: string;
  slot: string;
  preset: string;
  prompt_id: string;
  status: "queued" | "running" | "complete" | "failed" | "uncertain";
  condition?: string;
  queued_at?: string;
  seconds?: number;
  gpu_peak_mib?: number;
  output?: string;
  clip_id?: string;
  checks?: { decoded: boolean; frames: number; black_spans: number[][]; freeze_spans: number[][]; audio: boolean };
};
export type Finding = {
  id: string;
  candidate: string;
  reviewer: { id: string; model: string; access: string };
  scope: "shot" | "clip" | "sequence";
  kind: "technical" | "brief" | "artistic";
  range_s?: [number, number];
  severity: "info" | "minor" | "major" | "hard";
  gate?: "identity" | "look" | null;
  gate_status?: "alleged" | "confirmed" | "cleared";
  text: string;
  evidence?: string[];
  uncertainty?: string;
  scores?: Record<string, number | null>;
  action?: string;
};
export type Segment = { clip_id: string; label: string; in_s: number; out_s: number; song_s: number };
export type Join = { at_s: number; verdict: "valid" | "unsafe"; reasons: string[] };
export type EditCandidate = {
  id: string;
  label: string;
  status: "candidate" | "kept" | "rejected";
  segments: Segment[];
  joins: Join[];
  url?: string;
  built_at?: string;
  repair_of?: string;
  note?: string;
};
export type Edit = { active: string | null; candidates: EditCandidate[] };
export type Repair = {
  id: string;
  finding: string;
  candidate: string;
  kind: "trim" | "reorder" | "replace" | "re-prompt" | "rerender" | "gap-fill";
  scope: string;
  neighbors: string[];
  rationale: string;
  gpu_attempts: number;
  gpu_attempts_used: number;
  packet_revision: number;
  status: "proposed" | "approved" | "rejected" | "applied";
  decided_by?: string;
  result?: string;
};
export type State = {
  packet: Packet;
  clips: Clip[];
  prompts: Record<string, SavedPrompt>;
  runs: Run[];
  findings: Finding[];
  edit: Edit;
  song: {
    bpm: number | null;
    source?: string;
    chunks: { index: number; start_s: number; end_s: number; sections: string[]; shots: { start_s: number; role: string; energy: number }[] }[];
  };
  teams: Record<string, { provider: string; model: string; host: string; transport: string; media_access: string }>;
  repairs: Repair[];
  repair_allowance: { repair_renders: number; used: number; remaining: number };
};

export const API = "/pilot-api/production";

export async function call<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(API + path, body === undefined ? undefined : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
  if (!res.ok) throw new Error(data.error ?? `HTTP ${res.status}`);
  return data as T;
}

/** Seconds as m:ss.s for song/clip times. */
export function clock(s: number): string {
  const m = Math.floor(s / 60);
  const r = s - m * 60;
  return `${m}:${r.toFixed(1).padStart(4, "0")}`;
}

/** Percent position of a song time inside the planned passage. */
export function pct(t: number, start: number, end: number): number {
  return Math.min(100, Math.max(0, ((t - start) / (end - start)) * 100));
}

/** Input map a slot's prompt must resolve against: RefMod subjects + one scene picture + the song. */
export function inputMap(slot: Slot, characters: Character[]) {
  const subjects: Record<string, string> = {};
  const order = slot.characters.includes("lune") ? ["lune", "rafa"] : slot.characters;
  order.forEach((id, i) => (subjects[String(i + 1)] = characters.find((c) => c.id === id)?.name ?? id));
  return { subjects, pictures: { "1": slot.location }, audios: { "1": "song" } };
}

export function slotDuration(slot: Slot): number {
  return +(slot.song_s[1] - slot.song_s[0]).toFixed(3);
}

/** Hard gates block selection: a confirmed identity/Look failure on a candidate. */
export function hardBlocked(findings: Finding[], candidate: string): boolean {
  return findings.some((f) => f.candidate === candidate && f.gate && f.gate_status === "confirmed");
}
