# Repo-local skill setup audit

Checked 2026-10-09. There are **39 local `SKILL.md` files** under `.agents/skills`; [the inventory](installed-skills.json) records each path and SHA-256. This is a filesystem installation check, not a claim that every skill is exposed in every host's command palette.

The requested Matt-style flow is present: `ask-matt`, `grill-with-docs`, `grilling`, `to-spec`, `to-tickets`, `setup-matt-pocock-skills`, `implement`, `tdd`, `code-review`, `domain-modeling` and `writing-for-agents`. Related local skills include prototype, research, handoff, diagnosing-bugs and triage. The folder also contains other skills, including Impeccable; the count should not be described as 39 upstream Matt skills.

The router explicitly points from grill-with-docs through to-spec/to-tickets to implementation. Its local setup templates refer to `mattpocock/skills`; no upstream commit/install lock was established in this bounded audit. Hashes verify these current local copies, not upstream identity or freshness. No skill was reinstalled or replaced.

Setup now supplies the previously absent project configuration: [Linear tracker](issue-tracker.md), [live label mapping](triage-labels.md) and [shared domain doc rules](domain.md), with a pointer in the existing `AGENTS.md`. These are the files the engineering flow consumes. Tracker/model/artist labels do not grant approval authority; only the user's approved packet and current role scope do that.

The user already authorized completing this setup and publishing the planning breakdown. Repeated interview/confirmation steps in setup/to-spec/to-tickets were satisfied by that explicit session authorization. No credentials, GitHub issues, provider adapters, model installations or release-state changes were introduced.
