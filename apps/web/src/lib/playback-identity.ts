import type { Project } from "./api";

/** Immutable asset IDs identify audio; refreshed blob URLs do not change it. */
export function playbackIdentity(
  project: Pick<Project, "id" | "master" | "breaks">,
) {
  return JSON.stringify([
    project.id,
    project.master ? [project.master.assetId, project.master.durationMs] : null,
    [...project.breaks]
      .sort((a, b) => a.songStartMs - b.songStartMs || a.id.localeCompare(b.id))
      .map((b) => [
        b.id,
        b.kind,
        b.songStartMs,
        b.durationMs,
        b.assetId ?? null,
      ]),
  ]);
}
