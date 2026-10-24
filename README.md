# Centripetal Analytics Dashboard

Business-development dashboard for Charles Solomon and the Centripetal team, with actual dated source snapshots and separate activity and outcome reporting.

**GitHub is the shared source of truth for the application, curated reporting snapshot and measurement documentation:** https://github.com/credyset/Centripetal-Analytics-Dashboard

Other agents can clone this repository, run the populated dashboard and contribute through branches/pull requests without access to ChatGPT Sites. See [CONTRIBUTING.md](CONTRIBUTING.md).

Latest collected source review: [October 23 live-source refresh](REFRESH_REVIEW_2026-10-23.md). CRM, both worksheet ranges, Charles creator performance, company daily metrics and calendar/recording evidence were recollected independently. The reviewed refresh also includes concluded Ads status/totals, Waalaxy Home, Charles profile viewers and nine additional directly observed October 22 Video DM sends. Older invitation buckets and paid daily exports retain their original source dates. Source collection, local integration and successful live deployment are separate steps.

Latest reviewed refresh: [October 23 source review](REFRESH_REVIEW_2026-10-23.md) and [native Video DM review](NATIVE_VIDEO_REVIEW_2026-10-23.md), under the standing publication approval. Earlier evidence: [October 22 effort and dashboard review](DASHBOARD_REVIEW_2026-10-22.md), [October 22 channel refinement](REFRESH_REVIEW_2026-10-22.md), [October 21 CRM/meeting review](REFRESH_REVIEW_2026-10-21.md), [Charles outcome definitions](OUTCOME_REVIEW_2026-10-21.md), and [October 22 publication review](PUBLICATION_REVIEW_2026-10-22.md). On October 22 the owner explicitly instructed publication of the completed local metrics and revised structure to this GitHub project and GitHub Pages. This supersedes the earlier local-only hold. `PUBLICATION_POLICY.json` records the destination and approved scope; raw exports and private evidence remain excluded. Earlier corrections remain documented in [ANALYTICS_REVISION_2026-10-16.md](ANALYTICS_REVISION_2026-10-16.md).

For the few inputs that still require owner evidence or a narrower event export, see [Remaining manual inputs](MANUAL_DATA_REQUEST_2026-10-23.md). No additional generic CRM, creator, Ads or invitation export is currently required. Commercial outcomes are reserved for the owner's manual review with Charles.

The October 23 collection contains 780 accessible non-deleted CRM records / 924 activities, 468 valid worksheet prospect rows / 460 unique profiles and 84 October-indexed recording IDs. Current positions, reported activity dates, actual message observations and commercial outcomes remain separate measures. Earlier recording body reviews and the [October 22 Video DM workflow review](ZAPIER_RECONCILIATION_2026-10-22.md) retain their original dates. The 703 held Zapier IDs describe a technical trigger burst, not 703 missing outreach records. The fresh October 21–22 worksheet cohort has 19 valid Loom rows, all matched to exact CRM profile/asset evidence; this does not verify 19 actual sends.

## Live public dashboard

**GitHub Pages:** https://credyset.github.io/Centripetal-Analytics-Dashboard/#glance

The GitHub Pages workflow publishes approved code and `data/shared-dashboard.json` changes from `main` only when the canonical publication policy permits it. Pull requests run validation/build checks without deploying. Source collection remains on demand.

Existing Sites mirror: https://centripetal-analytics-dashboard.christian399556.chatgpt.site

Anyone can view the detailed public snapshot. The owner explicitly approved prospect identities and available business record links; source dates and known gaps remain visible. This is separate from the local internal concept. See [DEPLOYMENT.md](DEPLOYMENT.md) for hosting identity and the update procedure.

## Preview

Run Python 3.10 or later from this directory:

```sh
python3 serve.py
```

Open **http://127.0.0.1:8765**. The preview binds to localhost only. The server exposes the application, approved assets and the prepared dashboard snapshot; raw exports, source scripts and Git files are not served.

The repository includes application code and the curated reporting snapshot in `data/shared-dashboard.json`. On the published `main` branch this is the approved live input. A local review branch may contain a newer unpublished snapshot; inspect `meta.publicationStatus` and the publication review before sharing it. Raw exports, credentials and private transcript evidence remain excluded. The app loads the shared snapshot first, then falls back to a local prepared snapshot or the empty setup state when unavailable.

## Views

- At a glance (default): Charles's four highest-level outcomes first, followed by the original five vectors—LinkedIn Ads, Waalaxy, LinkedIn content, Pipedrive and Video DMs—plus Referrals and Christian Time & effort. Incomplete outcomes show confirmed minimums or Pending, never inferred zeros.

- Overview: equal emphasis on activity and outcomes, weekly deal creation, follow-up priorities and source coverage.
- LinkedIn Ads: current authenticated daily exports through October 21 UTC, plus a fresh September 4–October 23 UTC lifecycle/aggregate check showing all seven ad sets Completed. The checked aggregate remains $3,592.31 spend / 25,055 impressions / 106 clicks; no October 22 daily zero is invented.
- Waalaxy: selected invitation source-date buckets now extend through October 22 partial. The new CSV supplies 430 Sent / 132 Accepted over September 22–October 22, all within October; October 19–22 supplies 59 /22. Earlier September days remain separately sourced. Accepted buckets can be revised retrospectively; exact event dates and matched invitation cohorts are unverified. Fresh Home reports 430 Sent / 133 Accepted, 0 platform message actions and 2 answered messages over its October 1–24 source window (last day partial, timezone unknown). It remains separate from the older CSV; direct export retries produced no new file.
- LinkedIn Content: the October 23 Mountain collection supplies 90 UTC daily rows for July 27–October 24, with October 24 partial: 64,419 impressions / 36,760 unique members reached, 545 social engagements and 555 broader workbook Engagements. Follower stock is 11,569; 49 ranked posts remain a capped subset. Separate profile analytics show 1,313 viewers in the Past 90 days preset, with exact date boundaries and timezone unavailable. Company daily organic/sponsored data now extends through October 22 UTC. Sponsored counters reconcile to Ads only over their 48 matching dates through October 21; the company-only October 22 row does not establish an Ads zero.
- Pipedrive: 780 accessible non-deleted records / 924 activities, current stage/owner/type inventories, creation/latest-update metrics, scoped observed changes and calendar identity evidence. New records are not automatically accepted opportunities; marked-done tasks and Call Complete stages do not establish held meetings.
- Video DMs: 468 current prospect rows, 22 literal worksheet video dates and 44 follow-up dates, plus freshly rebuilt CRM joins. Retained native conversations corroborate nine October 21 and nine October 22 outbound Loom messages, a confirmed minimum of 18. All 19 asset profiles were checked; historical SubImage remains unconfirmed. Source reports and observed messages overlap; general replies, video attribution, delivery receipts and views remain distinct.
- Referrals: 349 current Pipeline 4 records = 61 active + 245 Office Hours + 40 Graveyard/Newsletter + 3 tests, derived from the same CRM collection. Stage positions are not referral events or qualification decisions.
- Time & effort: 324.77 deduplicated associated audio minutes and the separate 18.25–19.5-hour owner non-meeting estimate through October 22. October 23 non-meeting work is unmeasured; actual attendance, human hours and a combined total remain unknown.
- Sources & definitions: dates, refresh method, manual import checklist, known gaps and outcome definitions.

Date presets and custom dates operate on dated evidence. Undated inventories remain explicitly labelled snapshots. Tables support search, sorting and pagination. Charts, fonts and logo are local assets, with no third-party runtime/CDN requests.

## Reporting calendar

Monday–Sunday weeks, `America/Denver`, including daylight-saving changes. The prepared October 23 frame defaults to October 19–23, with October 23 partial; complete-day presets end October 22. Source collections occurred during October 23 Mountain and therefore carry actual October 24 UTC collection timestamps. Creator/company/Ads exports retain their UTC source days, without rebucketing into Mountain days. Each source has its own coverage: a newer inventory or calendar read does not refresh older message proof, invitation buckets or paid exports. Christian's non-meeting estimate still covers only through October 22.

## Data preparation

Normalized local inputs: `data/ads.json`, `crm.json`, `video.json`, `waalaxy.json`, and `content.json`, with optional `meetings.json` for calendar corroboration. Combine them and refresh the tracked shared snapshot with:

```sh
python3 tools/prepare_dashboard.py
```

Source-specific preparation:

- `tools/prepare_channels.py`: audited ad exports, verified Charles Waalaxy baseline and analytics workbooks. Requires `openpyxl`; paths currently reflect the source workspace.
- `tools/prepare_crm.py`: paginated Pipedrive snapshots across all accessible owners, scoped structured change history and activity diagnostics.
- `tools/prepare_meetings.py`: Charles Calendly event lifecycle, reschedule-chain deduplication and verified CRM identity matches. Calendar status does not establish attendance or qualification.
- `tools/prepare_video.py`: Video DM prospect and accepted-connection worksheet snapshots.
- `tools/prepare_time.py`: curated Christian October meeting/work evidence and unconfirmed assumptions, preserving separate measures.
- `tools/prepare_extra_vectors.py`: retained supplemental research for future consideration; its output is not assembled into the current five-vector dashboard.

Raw inputs reside in `data/private/` and are ignored by Git. Local normalized JSON files are also ignored. Within `data/`, only `empty.json` and the explicitly curated `shared-dashboard.json` are tracked. `OWNER_CONFIRMATIONS.json` separately retains explicit owner outcomes so source imports cannot erase them. `tools/prepare_dashboard.py` refreshes both local and shared snapshots; `tools/prepare_shared_snapshot.py` can curate an existing local dashboard separately. Store credentials in an authorized collection service, never the front-end code, workbook cells or repository.

Current source collection and bounds: [REFRESH_REVIEW_2026-10-23.md](REFRESH_REVIEW_2026-10-23.md), following the [October 22 independent channel review](INDEPENDENT_CHANNEL_REFRESH_2026-10-22.md). `tools/apply_refresh_2026_10_23.py` accepts explicit, independently dated private patches and defaults to a private combined preview. `--write-shared` explicitly applies the reviewed result to canonical local/shared files. It preserves owner decisions and hours, retains historical native proof and emails separately, and archives incompatible row-scoped reviews after worksheet reordering. See [CONTRIBUTING.md](CONTRIBUTING.md) for checks; no ignored private files are needed to view the tracked snapshot or run the replay regressions. Private collection files are required to reproduce the source preparation.

Collection is currently manual/on demand. The approved curated snapshot is published through GitHub Pages, with a separately maintained Sites mirror. Automatic refresh and an authenticated internal deployment have not been enabled. The browser concept is not an authenticated production service.

## Data boundaries

- A CRM deal is not automatically an accepted sales opportunity.
- Latest update timestamps do not reconstruct every historical edit or prove progression.
- Actual status and won/lost timestamps govern wins/losses; Closed Won/Lost stage names can disagree with status.
- An activity marked done does not independently verify attendance.
- A Loom URL does not prove a Video DM was delivered. Spreadsheet-classified sent/completed and explicit send statuses are distinct.
- Person-level sent/replied flags are not counts of all messages or replies.
- A top-post ranking is not a complete publishing calendar.
- Missing metrics and missing coverage remain unavailable, rather than becoming zero.
- Paid and boosted content must be reconciled to avoid counting spend/outcomes twice.

## Deployment and next work

The shared public repository is `credyset/Centripetal-Analytics-Dashboard`. GitHub Pages is the primary shareable dashboard and automatically deploys changes merged to `main` through `.github/workflows/pages.yml`. The Sites mirror is a separate publication destination and does not automatically follow GitHub changes. Next steps for the internal live-data service are reliable source adapters, retained history, a private data store, authenticated hosting and monitored refresh jobs.

A private repository does not make a standard GitHub Pages site private. Protect both the dashboard and its data endpoints before publishing internal records. Keep the local concept available while deployment ownership and access are settled.

## Assets

Centripetal logo and palette follow the workspace brand guidelines. Roboto is Copyright 2015 Google Inc., licensed under Apache 2.0. Lora is Copyright 2011 The Lora Project Authors, licensed under SIL OFL 1.1 with Reserved Font Name Lora. License texts are included in `assets/`.

See [the October 23 checklist](MANUAL_DATA_REQUEST_2026-10-23.md) for current gaps and [SOURCE_REVIEW.md](SOURCE_REVIEW.md) for the earlier four-chat review. See [PLAN.md](PLAN.md) for the agreed scope and implementation sequence.

Referral scope was explicitly added after the five-vector clarification. Newsletter/email, standalone website reporting and Pulley remain outside the visible dashboard. Referrals now contains a reconciled current inventory; dated requests/introductions and owner-confirmed outcomes still require their own event records.

Earlier source reviews remain in [REFRESH_REVIEW_2026-10-14.md](REFRESH_REVIEW_2026-10-14.md), [CRM_ACTIVITY_REVIEW.md](CRM_ACTIVITY_REVIEW.md) and [MEETING_SOURCE_REVIEW.md](MEETING_SOURCE_REVIEW.md). Source snapshots remain on-demand; refreshed source dates are distinct from historical imports and access checks.

## October effort and import coverage

The Time & effort view estimates Christian’s October work with deduplicated recording evidence and a separate adjustable nonmeeting range. It does not measure actual or billable hours. See [OCTOBER_EFFORT_REVIEW.md](OCTOBER_EFFORT_REVIEW.md) and [DATA_GAPS.md](DATA_GAPS.md).
