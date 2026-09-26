# UI design and verification

User decisions (2026-09-25): use [Impeccable](https://impeccable.style/docs/) for UI design and testing, with dark mode as the default. The approved PRD defines the product; the existing studio workspace supplies the visual context for scoped refinements.

## Pinned skill

- Upstream: https://github.com/pbakaus/impeccable
- Commit: `9d715cc4f5564a990ca8345abfdd5df6dc9b41c8`
- Source directory: `.agents/skills/impeccable`
- Skill metadata version: `4.4.0` (the upstream npm package version is a separate release identifier).
- Installed using the Codex skill-installer helper with an explicit commit ref. Do not silently track upstream main.
- Local entry point: [SKILL.md](../.agents/skills/impeccable/SKILL.md).

## Working method

1. Load Impeccable context for the specific surface and the relevant command reference. Existing-code audits may use the implementation as context when PRODUCT.md/DESIGN.md do not exist. The approved PRD remains authoritative; absent design documents are not permission to invent user preferences.
2. Use the Operate mode appropriate to an editing studio. Preserve the Story, References, Production and Review workflow, persistent preview, approvals and candidate/Keep rules.
3. Audit accessibility, performance, responsive behavior, theming and implementation integrity. Distinguish demonstrated defects from suggestions or unverified conditions.
4. Before UI edits, read the craft floor and apply the Svelte code-writer checks. Refine concrete findings while preserving existing behavior.
5. Run the mechanical detector on changed markup targets after implementation, plus Svelte checks, relevant tests and a production build. Verify detector findings in context rather than treating every match as a defect.
6. Inspect desktop and narrow browser layouts in one batch, fix the findings, and perform a bounded confirmation. Exercise real forms, keyboard focus and preview states. Record engine, viewport or resizing limits, and what was not exercised.

Dark mode must retain readable secondary text, visible focus, distinct disabled states and usable touch targets. A passing static scan does not establish accessibility conformance, touch-device behavior, media quality or Windows desktop acceptance.

UI changes use the same GitHub gate as other implementation work: current-head Greptile 5/5, passing CI and addressed findings before merge.
