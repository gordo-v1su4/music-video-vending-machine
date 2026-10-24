<!-- graft:start -->
## Graft — repo context graph

This repo is indexed in `graft/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `graft map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `graft ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
  definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `graft grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `graft skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `graft callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `graft/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `graft ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `graft build` (deterministic,
no API key, $0).
<!-- graft:end -->

## UI design and verification

Use the project-local [Impeccable skill](.agents/skills/impeccable/SKILL.md) for UI design, refinement and testing, as requested by the user. Preserve the approved product requirements in `docs/PRD.md`. Dark mode is the user-confirmed default; verify text contrast, keyboard focus, disabled states and responsive layouts in that theme. Apply the Svelte skill alongside Impeccable for component changes.

For existing surfaces, use scoped audit/refinement rather than treating each change as a redesign. Record mechanical checks separately from observed browser behavior, and never report browser emulation as physical-device or Windows WebView2 acceptance. See `docs/ui-design-workflow.md` for provenance and verification expectations.

## Agent skills

### H3 prompt compilation

For H3 Ref2V multi-cut prompts, audio-reactive timing and scoped prompt repairs, use [h3-ref2v-dynamic-compiler](.agents/skills/h3-ref2v-dynamic-compiler/SKILL.md) first. It is the user's preferred writing profile and includes a portable linter. Preserve the official encoder grammar and actual workflow input map; its frame schedule requires a compatible connected scheduler. Use `h3-prompt-writing` for base-mode grammar.

Before delivering or submitting any newly written or revised H3 prompt, run that skill's linter with the actual duration/FPS, fix errors and resolve warnings or record intentional exceptions, then rerun. Audit adjacent shots for repeated completed actions and conflicting entry/exit states. Report the lint result; a pass is not render-quality acceptance. Audit archived prompts read-only.

### Issue tracker

Engineering skills publish to Linear's Music Video Vending Machine project/team V1S. See [issue tracker](docs/agents/issue-tracker.md).

### Triage labels

Reuse the configured five triage labels and native blocking edges. See [triage labels](docs/agents/triage-labels.md).

### Domain docs

Use the shared root glossary and applicable product/ADR decisions. See [domain documentation](docs/agents/domain.md).

### Production handoffs and review tools

When resuming local generation, moving a packet to another agent system, or using wardrobe/identity checks, read [production resume](docs/pilot/agent-production-resume.md) and its role/tool pointers before acting.
