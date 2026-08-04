# Design Document Version History

Every unique version of the project's design document, extracted from git history (oldest first). Files are named `<date>_<commit>_<subject-slug>.md`.

**Exception:** the 2026-06 pre-POC entry was never committed to this repo as `DESIGN.md` — it's the original planning doc (`Greenroom_Dev_Design_Document.md`, supplied externally, not generated from `git log`) that predates the 2026-06-17 POC doc below. Its filename uses `pre-poc` in place of a commit hash for that reason. Its proposed architecture (ASP.NET Core orchestrator, Go code judge, Azure AI Foundry/Cosmos DB/AKS) was never built as described — the actual v1.0 POC below used a different, simpler stack (FastAPI, Supabase, Groq) from day one. Kept for historical context on the original vision, not as a record of what shipped.

## Images

`images/` holds every unique version of the diagrams these docs embed
(deduped by content, same as the docs themselves), named
`<date>_<commit>_<original-filename>`. Each snapshot above links to the
image versions that were actually live as of that commit, so opening an
older snapshot shows the diagrams as they looked at the time, not today's:

| File | Versions |
|---|---|
| `2026-06_proposed-architecture-interview-session-flow.png` | 1 — the earliest proposed architecture diagram of any kind for this project, from the pre-POC pitch/sprint deck (`MockBot_Final.pptx`, Sprint 2 / Week 2, "Architecture: Interview Session Flow" — the first of two architecture slides in that deck). Never embedded inline in a `DESIGN.md`/dev-design-doc Markdown file; kept here as the original proposed-architecture artifact, referenced from the pre-POC entry below. |
| `architecture.svg` | 1 — added 2026-06-24 ([2c01196](https://github.com/VishwajeetRaut/greenroom/commit/2c01196)), used only by the two v2.0-era snapshots before the doc moved to `docs/diagrams/*.png` |
| `architecture.png` | 2 — 2026-06-30 ([33152fa](https://github.com/VishwajeetRaut/greenroom/commit/33152fa)), 2026-07-08 ([9b380dd](https://github.com/VishwajeetRaut/greenroom/commit/9b380dd), current) |
| `user-flow.png` | 2 — same two commits |
| `developer-flow.png` | 2 — same two commits |
| `legend.png` | 1 — added 2026-06-30, never changed since; not embedded inline in any snapshot's Markdown but kept for completeness |

The 2026-06-17 (POC) and 2026-07-08 `e52a88f` snapshots have no diagrams —
neither version embedded any images.

| Date | Commit | Message |
|---|---|---|
| 2026-06 | pre-poc (external) | [Greenroom Dev Design Document v1.0 — original pitch/roadmap doc, predates the in-repo DESIGN.md](2026-06_pre-poc_greenroom-dev-design-document-v1-0.md) |
| 2026-06-17 | [e878d99](https://github.com/VishwajeetRaut/greenroom/commit/e878d99) | [feat: LangChain LCEL agent, bug fixes, POC design doc](2026-06-17_e878d99_feat-langchain-lcel-agent-bug-fixes-poc-design-doc.md) |
| 2026-06-24 | [2c01196](https://github.com/VishwajeetRaut/greenroom/commit/2c01196) | [docs: update design doc v2.0 + architecture diagram](2026-06-24_2c01196_docs-update-design-doc-v2-0-architecture-diagram.md) |
| 2026-06-24 | [8a121d6](https://github.com/VishwajeetRaut/greenroom/commit/8a121d6) | [Update in design document](2026-06-24_8a121d6_update-in-design-document.md) |
| 2026-06-30 | [33152fa](https://github.com/VishwajeetRaut/greenroom/commit/33152fa) | [docs: add industry-grade design document with architecture diagrams and full audit](2026-06-30_33152fa_docs-add-industry-grade-design-document-with-architecture-di.md) |
| 2026-07-01 | [f3dd313](https://github.com/VishwajeetRaut/greenroom/commit/f3dd313) | [docs: fix consistency issues and remove redundant sections from DESIGN.md](2026-07-01_f3dd313_docs-fix-consistency-issues-and-remove-redundant-sections-fr.md) |
| 2026-07-01 | [8511c88](https://github.com/VishwajeetRaut/greenroom/commit/8511c88) | [Remove a redundant section from the design doc](2026-07-01_8511c88_remove-a-redundant-section-from-the-design-doc.md) |
| 2026-07-08 | [e52a88f](https://github.com/VishwajeetRaut/greenroom/commit/e52a88f) | [docs: update DESIGN.md to v4.0 — question bank expansion, new services, concurrency/scalability/rate-limit feedback, PlantUML diagrams](2026-07-08_e52a88f_docs-update-design-md-to-v4-0-question-bank-expansion-new-se.md) |
| 2026-07-08 | [7b46b81](https://github.com/VishwajeetRaut/greenroom/commit/7b46b81) | [docs: update DESIGN.md to v4.0 with new diagrams and industry-grade structure](2026-07-08_7b46b81_docs-update-design-md-to-v4-0-with-new-diagrams-and-industry.md) |
| 2026-07-08 | [92b5fa3](https://github.com/VishwajeetRaut/greenroom/commit/92b5fa3) | [docs: apply fork edits, remove em dashes, fix broken section references](2026-07-08_92b5fa3_docs-apply-fork-edits-remove-em-dashes-fix-broken-section-re.md) |
| 2026-07-15 | [a1e1533](https://github.com/VishwajeetRaut/greenroom/commit/a1e1533) | [docs: update DESIGN.md with everything merged since the last revision](2026-07-15_a1e1533_docs-update-design-md-with-everything-merged-since-the-la.md) |
| 2026-07-29 | [83d08dd](https://github.com/VishwajeetRaut/greenroom/commit/83d08dd) | [docs: update DESIGN.md to v5.0, ACTION_ITEMS, and EVALUATION_METRICS with real data](2026-07-29_83d08dd_docs-update-design-md-to-v5-0-action-items-and-evaluatio.md) |
| 2026-08-04 | [d61451d](https://github.com/VishwajeetRaut/greenroom/commit/d61451d) **(current)** | [docs: update DESIGN.md to v6.0 and ACTION_ITEMS with this week's changes](2026-08-04_d61451d_docs-update-design-md-to-v6-0-and-action-items-with-this-weeks.md) |
