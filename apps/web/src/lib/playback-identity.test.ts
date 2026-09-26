import { describe, expect, test } from "bun:test";
import { playbackIdentity } from "./playback-identity";
import type { Project } from "./api";

const project: Project = {
  id: "project",
  name: "Film",
  revision: 1,
  createdAt: "",
  updatedAt: "",
  master: { assetId: "song", durationMs: 30000, approved: false },
  treatment: "Original",
  sections: [],
  references: [],
  shots: [],
  revisions: [],
  activeRevisionId: null,
  productionApproval: null,
  breaks: [
    {
      id: "break",
      kind: "insertion",
      songStartMs: 5000,
      durationMs: 3000,
      assetId: null,
    },
  ],
};

describe("playback reset boundary", () => {
  test("ordinary saved edits preserve identity, including approvals, references, sections and pins", () => {
    const changed: Project = {
      ...project,
      name: "Renamed",
      revision: 20,
      updatedAt: "updated",
      treatment: "Rewritten",
      master: { ...project.master!, approved: true },
      productionApproval: { fingerprint: "new", localAttemptsPerShot: 3 },
      references: [
        {
          id: "ref",
          assetId: "image",
          name: "Person",
          role: "exact",
          description: "New reference",
        },
      ],
      sections: [
        {
          id: "section",
          name: "Opening",
          startMs: 0,
          endMs: 30000,
          intent: "Changed",
        },
      ],
      shots: [
        {
          id: "shot",
          sectionId: "section",
          startMs: 0,
          endMs: 30000,
          intent: "Shot",
          pinned: true,
          status: "gap",
          attempts: 0,
        },
      ],
      activeRevisionId: "new-cut",
    };
    expect(playbackIdentity(changed)).toBe(playbackIdentity(project));
  });

  const changes: Record<string, Project> = {
    "project switch": { ...project, id: "other" },
    "master replacement": {
      ...project,
      master: { ...project.master!, assetId: "other-song" },
    },
    "master duration": {
      ...project,
      master: { ...project.master!, durationMs: 40000 },
    },
    "break behavior": {
      ...project,
      breaks: [{ ...project.breaks[0], kind: "cutout" }],
    },
    "break timing": {
      ...project,
      breaks: [{ ...project.breaks[0], songStartMs: 10000 }],
    },
    "break duration": {
      ...project,
      breaks: [{ ...project.breaks[0], durationMs: 5000 }],
    },
    "dialogue replacement": {
      ...project,
      breaks: [{ ...project.breaks[0], assetId: "dialogue" }],
    },
  };
  for (const [name, changed] of Object.entries(changes)) {
    test(`${name} invalidates the old playback session`, () => {
      expect(playbackIdentity(changed)).not.toBe(playbackIdentity(project));
    });
  }
  test("equivalent break ordering and omitted nullable IDs do not cause resets", () => {
    const extra = { ...project.breaks[0], id: "later", songStartMs: 15000 };
    const first = { ...project, breaks: [...project.breaks, extra] };
    const second = {
      ...project,
      breaks: [extra, { ...project.breaks[0], assetId: undefined }],
    };
    expect(playbackIdentity(first)).toBe(playbackIdentity(second));
  });
});
