import type { components } from "./generated/api";
import type { Project } from "./api";

export type Character = components["schemas"]["Character"];
export type Look = components["schemas"]["Look"];
export type LookAssignment = components["schemas"]["LookAssignment"];
/** Section id → Character id → Look id ('' means the Character is not in that section). */
export type LookPlan = Record<string, Record<string, string>>;

export function planFromAssignments(project: Pick<Project, "characters" | "lookAssignments">): LookPlan {
  const plan: LookPlan = {};
  for (const assignment of project.lookAssignments ?? []) {
    const row: Record<string, string> = {};
    for (const lookId of assignment.lookIds) {
      const owner = (project.characters ?? []).find((c) => c.looks.some((l) => l.id === lookId));
      if (owner) row[owner.id] = lookId;
    }
    plan[assignment.sectionId] = row;
  }
  return plan;
}

/** Every section gets an explicit entry, so an empty row records "no Character here". */
export function assignmentsFromPlan(plan: LookPlan, sectionIds: string[]): LookAssignment[] {
  return sectionIds.map((sectionId) => ({
    sectionId,
    lookIds: Object.values(plan[sectionId] ?? {}).filter(Boolean),
  }));
}

/** Mirrors the domain rules for production approval so the UI can explain what is missing. */
export function lookPlanProblems(project: Pick<Project, "characters" | "lookAssignments" | "sections">): string[] {
  const characters = project.characters ?? [];
  if (!characters.length) return [];
  const assignments = project.lookAssignments ?? [];
  const problems: string[] = [];
  const unplanned = project.sections.filter((s) => !assignments.some((a) => a.sectionId === s.id));
  if (unplanned.length)
    problems.push(`${unplanned.length} ${unplanned.length === 1 ? "section needs" : "sections need"} a saved Look plan.`);
  const looks = characters.flatMap((c) => c.looks);
  const unapproved = new Set(
    assignments.flatMap((a) => a.lookIds).filter((id) => !looks.some((l) => l.id === id && l.approved)),
  );
  if (unapproved.size)
    problems.push(`${unapproved.size} assigned ${unapproved.size === 1 ? "Look needs" : "Looks need"} approval.`);
  return problems;
}

export function sectionLooks(project: Pick<Project, "characters" | "lookAssignments">, sectionId: string) {
  const ids = (project.lookAssignments ?? []).find((a) => a.sectionId === sectionId)?.lookIds;
  if (!ids) return null;
  return (project.characters ?? []).flatMap((c) =>
    c.looks.filter((l) => ids.includes(l.id)).map((look) => ({ character: c, look })),
  );
}

/** A Look is approvable once hair and costume are described and its sheet has an exact reference. */
export function lookReadiness(look: Look, references: Project["references"]): string | null {
  if (!look.hair.trim() || !look.costume.trim()) return "Describe hair and costume first.";
  if (!look.sheetReferenceIds.some((id) => references.some((r) => r.id === id && r.role === "exact")))
    return "Add an exact-constraint reference to its Character sheet.";
  return null;
}
