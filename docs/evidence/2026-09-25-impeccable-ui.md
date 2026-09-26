# Impeccable technical UI audit — 2026-09-25

## Implementation integrity verdict

**Pass within the narrative foundation scope.** The dark studio retains its treatment canvas, reference board, production approval, review, source inspector, and persistent timed transport. Unrendered frames, unavailable generation, and unavailable export remain explicit. No generation success or production acceptance is implied by this audit.

The user explicitly said **“i prefer dark mode”**. Dark mode is the visual authority; this work does not add a light theme or redesign the existing identity. Context: `docs/PRD.md`; Impeccable `SKILL.md`, `reference/audit.md`, `reference/craft-floor.md`, and scoped adapt/harden guidance. The parent ran the context launcher. This was a technical audit and authorized remediation, not a formal visual critique.

## Executive summary

Six grouped findings: **0 P0, 2 P1, 3 P2, 1 P3**. All six were addressed within this change. Narrow project/settings access and navigation overflow were the most consequential issues. Final score **15/20 — Good**, with device, assistive technology, and performance coverage still limited.

| Dimension | Before | After | Evidence / remaining limit |
|---|---:|---:|---|
| Accessibility | 2 | 3 | Skip link, current-view semantics, readable fields and larger controls verified; no screen-reader certification |
| Performance | 2 | 2 | Static build passes; local fonts and lazy reference image decoding; no large-project or throttled performance benchmark |
| Responsive design | 1 | 3 | Setup and four views fit measured 320 CSS pixels; desktop fits 1440 CSS pixels; physical mobile not tested |
| Theming | 2 | 3 | Explicit dark native surfaces, measured text contrast, focus and selection styling; forced-colors styling not device-tested |
| Implementation integrity | 3 | 4 | Stable SVG icon system and truthful foundation states; timing/controller code unchanged |
| **Total** | **10/20** | **15/20** | **Acceptable → Good**, a scoped engineering judgment, not a WCAG certificate |

## Findings and remediation

| Severity | Location | Category / impact | Standard and remediation | Suggested refinement |
|---|---|---|---|---|
| P1 | `apps/web/src/app.css`, narrow sidebar rules around line 1322 | Responsive: project selection and connection settings were `display:none` below 850px, removing core workflow access | Preserve the existing selector and connection control in a compact header; verified both visible and settings expandable at 320px | `$impeccable adapt` |
| P1 | Same responsive rules; preview and welcome geometry around lines 832 and 1450 | Responsive: navigation extended to 367px in a 320px viewport. Fixed-ratio intrinsic sizing also produced setup/preview overflow during confirmation | WCAG 1.4.10 reflow: four equal navigation columns, shrinkable grids, wrapping content, constrained preview. Final measured document widths stay within viewport on setup and every view | `$impeccable adapt` |
| P2 | `apps/web/src/app.css`, control/type rules; `.play`, `.icon-button`, `.dismiss` | Accessibility: 8–11px metadata, 14px mobile treatment input, 32px play and small removal targets reduced readability and touch usability | Craft-floor readability; touch design target 44px (stronger than WCAG 2.5.8 minimum). Desktop secondary text at least 12px; narrow form inputs 16px, labels/copy generally 14px; play/remove/dismiss 44px | `$impeccable typeset` |
| P2 | `apps/web/src/routes/+page.svelte:293`, `:331`, `:352`; `Transport.svelte:123` | Accessibility: no bypass link or semantic current-view indication; slider announced raw milliseconds | WCAG 2.4.1, 4.1.2: workspace skip link, current-page navigation state, expanded connection state, formatted slider value. Enter on skip link focuses `studio-content` | `$impeccable harden` |
| P2 | `apps/web/src/app.css:10`, shared native/focus rules around 1610 | Theming: dark mode was only declared on select controls; browser/native surfaces and some borders had inconsistent treatment | Explicit root dark color scheme; themed selection, caret, scrollbars and focus; brighter control border token; focus styling for disclosure summaries | `$impeccable colorize` |
| P3 | `apps/web/src/lib/Icon.svelte`; page and transport icon uses | Implementation integrity: Unicode symbols varied by platform and font | Replace icon glyphs with authored SVG paths using one stroke convention, decorative and hidden from the accessibility tree. Preserve textual action labels and geometry | `$impeccable polish` |

## Browser evidence

CUA-controlled Chrome extension browser, local web `http://127.0.0.1:5198`, real coordinator on 5199, persisted **Studio browser verification** project revision 10. Its synthetic WAV is an integration fixture, not the chosen pilot song. No project changes were saved in this audit.

The browser's existing zoom affected viewport override dimensions. Measurements below use **observed `innerWidth`**, not the requested tool dimensions. Requested 256×675 produced 320 CSS-pixel width; requested 1152×720 produced 1440 CSS-pixel width. Temporary overrides were reset afterwards.

| Scenario | Observed result |
|---|---|
| Initial narrow | Project/settings hidden; navigation right edge 367px at 320px viewport |
| Final setup, Story, References, Production, Review at 320px | Each reported document `scrollWidth: 301`, viewport `innerWidth: 320` (scrollbar consumes remainder); no horizontal document overflow |
| Final desktop Story at 1440px | `scrollWidth: 1421`, preview width 239px; no horizontal document overflow |
| Narrow connection control | Opens and closes real connection settings, with expanded/collapsed accessibility state |
| Narrow project selection | Opens persisted revision 10 through the native project selector |
| Narrow navigation | Four controls, each approximately 61px high; only current view has `aria-current="page"` |
| Narrow controls | Treatment input 16px; play approximately 44×44px |
| Keyboard | Visible lavender focus on library button; skip-link Enter moves actual DOM focus to main workspace |
| Preview | Play showed audio readiness state, progressed to 2,904ms, and Pause retained that position; no listening or visual-generation claim |
| Truthful unavailable states | Production says generation is not connected; Review says no checks have run and finished export unavailable |

Computed foreground/background contrast samples, WCAG relative luminance formula:

| Sample | Ratio |
|---|---:|
| Body against root | 12.08:1 |
| Treatment text against paper | 8.52:1 |
| Treatment placeholder against paper | 5.02:1 |
| Source note against inspector | 6.05:1 |

Desktop and narrow screenshots were inspected through CUA during the pass. Screenshot capture intermittently timed out, including final narrow capture; no final screenshot file is claimed. Final width, state and contrast evidence came from read-only rendered DOM measurements. This is one initial inspection and one confirmation phase; confirmation included targeted repair of newly exposed intrinsic-size overflow, not further aesthetic iteration.

## Detector and automated validation

One source detector run:

```powershell
./.agents/skills/impeccable/scripts/impeccable.cmd detect --json apps/web/src/app.css apps/web/src/routes/+page.svelte apps/web/src/lib/Transport.svelte apps/web/src/lib/Icon.svelte
```

Result: exit 0, `[]`. Evidence is in ignored `.runtime/impeccable-ui-detect.json`. **No reported findings, and thus no reported false positives to waive.** Static non-HTML scanning did not find the actual rendered overflow; manual context verification was necessary. A subsequent narrow intrinsic-sizing repair was browser-measured and rebuilt without repeating the detector, honoring the one-run budget. No ignore configuration was added.

From `apps/web`:

- `bun run check`: 0 errors, 0 warnings, including final sizing changes.
- `bun run test`: 36 pass, 0 fail, 105 assertions. These cover API trust boundaries and timing/playback identity; delayed-media tests use injected media doubles, not actual browser network buffering.
- `bun run build`: static output produced successfully, including final sizing changes. Latest log: ignored `.runtime/impeccable-ui-build.log`.
- `npx --yes @sveltejs/mcp svelte-autofixer <file> --svelte-version 5` for `+page.svelte`, `Transport.svelte`, and `Icon.svelte`: no issues or suggestions. An initial concurrent Bun tool-install attempt hit Windows cache-copy contention; the sequential npm invocations above succeeded.

No snapshot-only tests were added for CSS. Rendered dimensions and interactions were checked in the actual browser. Playback/controller logic was not modified; transport changes are the SVG icon and formatted accessible value only.

## Patterns, positives, and remaining coverage

The systemic issues were compact desktop typography reused on mobile, hiding rather than reflowing navigation controls, and unconstrained intrinsic sizes. The existing palette, locally bundled fonts, explicit empty/unavailable states, labeled native form controls, revision safety, and nonautomatic production approval were retained.

Unverified: Windows Tauri/WebView2, physical touch or synthesized multitouch, screen-reader announcements, Windows forced colors, 200% browser zoom, large asset collections, slow-network performance, real generated-media review, and full production acceptance. Reference cards now request lazy/async image rendering, but asset-fetch/cache scaling remains outside this audit. Asset originals, approval semantics and backend behavior were not changed.

Recommended next work: `$impeccable harden` for assistive-technology/device coverage, `$impeccable optimize` only after measuring large-project asset behavior, then `$impeccable polish` on the accepted product surface. Ordinary implementation can continue; these limitations must remain explicit in release acceptance.
