# Centripetal Analytics Dashboard

Business-development dashboard for Charles Solomon and the Centripetal team, with actual dated source snapshots and separate activity and outcome reporting. **Content performance focuses on Charles’s personal LinkedIn profile.** Company-page exports are retained as collapsed supplementary context and never contribute to his headline content metrics.

**GitHub is the shared source of truth for the application, curated reporting snapshot and measurement documentation:** https://github.com/credyset/Centripetal-Analytics-Dashboard

Other agents can clone this repository, run the populated dashboard and contribute through branches/pull requests without access to ChatGPT Sites. See [CONTRIBUTING.md](CONTRIBUTING.md).

Previous accuracy follow-up: [October 29 accuracy review](ACCURACY_REVIEW_2026-10-29.md). It restores the full CRM history chart, 120 source connection dates, current snapshot comparisons, Apaluma’s verified profile alias and six undated Seen indicators, and separately establishes recent zero paid delivery.

Latest quality review: [November 20 checks and corrections](QC_REVIEW_2026-11-20.md). Source collection and QC review dates remain separate.

Latest source collection: [November 19 refresh](REFRESH_2026-11-19.md). At a glance opens to November 12–18, the last seven complete Mountain days. Select Month through last complete day for November 1–18, or Last 14 complete days for November 5–18. November 19 is partial. Earlier findings remain in the [November 13 fourteen-day accuracy review](ACCURACY_REVIEW_2026-11-13.md).

Earlier focused findings remain in [October 24 CRM and Video DM gap resolution](GAP_RESOLUTION_2026-10-24.md), including historical native-message proof, bounded source-profile first appearances and the eight-thread Charles Team-mailbox review. Those reviews retain their original dates.

Earlier reviewed refresh: [October 23 source review](REFRESH_REVIEW_2026-10-23.md) and [native Video DM review](NATIVE_VIDEO_REVIEW_2026-10-23.md), under the standing publication approval. Earlier evidence: [October 22 effort and dashboard review](DASHBOARD_REVIEW_2026-10-22.md), [October 22 channel refinement](REFRESH_REVIEW_2026-10-22.md), [October 21 CRM/meeting review](REFRESH_REVIEW_2026-10-21.md), [Charles outcome definitions](OUTCOME_REVIEW_2026-10-21.md), and [October 22 publication review](PUBLICATION_REVIEW_2026-10-22.md). On October 22 the owner explicitly instructed publication of the completed local metrics and revised structure to this GitHub project and GitHub Pages. This supersedes the earlier local-only hold. `PUBLICATION_POLICY.json` records the destination and approved scope; raw exports and private evidence remain excluded. Earlier corrections remain documented in [ANALYTICS_REVISION_2026-10-16.md](ANALYTICS_REVISION_2026-10-16.md).

The [November refresh review](REFRESH_2026-11-19.md#remaining-confirmations) lists the targeted evidence still needed. Charles’s dated commercial decisions are the highest priority. See [the October gap review](DATA_GAPS.md) for historical context.

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
- LinkedIn Ads: all seven ad sets show Completed. The unfiltered account aggregate verifies zero spend, impressions, clicks and platform leads for October 22–November 20 UTC, final day partial. Daily delivery exports end October 21.
- Waalaxy: 35 invitations sent and 11 reported acceptances across November 12–18 source dates; November 1–18 totals are 97 and 35. Signed-in Home tooltips reconcile to the separately scoped source aggregate.
- LinkedIn Content: Charles’s personal workbook reports 9,345 impressions, 68 workbook engagements and 147 new followers over November 12–18 UTC. November 1–18 supplies 38,504 impressions, 156 workbook engagements and 395 new followers. Profile-view presets remain separate.
- Pipedrive: 100 new deal records, 139 latest-updated records and 72 activities marked done over the selected Mountain dates. The latest census contains 945 accessible deals and 1,022 activities, including five test rows in each. Dated reviews explain target-list imports and historical activity backfill. Complete commercial totals remain pending.
- Video DMs: 667 contact prospect rows, 50 company-only targets and 654 distinct supplied profiles (717 target rows across the two grains). A separately dated November 20 helper review verifies 53 Ready rows and 268 current connection-ledger rows, of which 230 are helper-labelled Connected and 38 Verify connection. These are current inventory, not period acceptance/send events. The latest week has eight native-verified follow-ups; no native video send was found dated to this week in the bounded evidence. November 1–18 has 19 native-verified sends and 21 follow-ups. Revisions establish at least 52 distinct first appearances in the week and 147 in the complete month.
- Referrals: 104 active records, 283 Graveyard/Newsletter records and three tests. Verified dated introductions and follow-ups remain separate from current stage inventory and task backfill.
- Time & effort: November associated audio totals 117.33 minutes across three distinct recordings, with 16 duplicate minutes excluded. November non-meeting hours and actual attendance remain unmeasured. October audio and the 21.75–23-hour estimate through October 28 remain separate historical evidence.
- Sources & definitions: dates, refresh method, manual import checklist, known gaps and outcome definitions.

Date presets and custom dates operate on dated evidence. Undated inventories remain explicitly labelled snapshots. Tables support search, sorting and pagination. Charts, fonts and logo are local assets, with no third-party runtime/CDN requests.

## Reporting calendar

Calendar weeks are Monday–Sunday in `America/Denver`. At a glance defaults to the seven complete days ending November 18. November 19 is partial. Creator and Ads retain UTC source dates, and Waalaxy retains its source-day labels. The non-meeting estimate covers October 1–28.

## Data preparation

Normalized local inputs: `data/ads.json`, `crm.json`, `video.json`, `waalaxy.json`, and `content.json`, with optional `meetings.json` for calendar corroboration. Combine them and refresh the tracked shared snapshot with:

```sh
python3 tools/prepare_dashboard.py
```

The November 20 source-backed QC supplement uses `tools/apply_qc_2026_11_20.py`, with independent review evidence kept private. It retains original source clocks and reporting windows. The latest November refresh uses `tools/apply_refresh_2026_11_19.py` to build a private preview from independently reviewed inputs. The October 28/29 refresh used `tools/apply_refresh_2026_10_28.py` with separately retained source manifests. Its default is a private preview; the reviewed `--write-shared` step updates the dated effort decision and both dashboard snapshots together. Optional native-message evidence preserves earlier observation dates. Raw source packages are not included in Git.

Source-specific preparation:

- `tools/prepare_channels.py`: audited ad exports, verified Charles Waalaxy baseline and analytics workbooks. Requires `openpyxl`; paths currently reflect the source workspace.
- `tools/prepare_crm.py`: paginated Pipedrive snapshots across all accessible owners, scoped structured change history and activity diagnostics.
- `tools/prepare_meetings.py`: Charles Calendly event lifecycle, reschedule-chain deduplication and verified CRM identity matches. Calendar status does not establish attendance or qualification.
- `tools/prepare_video.py`: Video DM prospect and accepted-connection worksheet snapshots.
- `tools/prepare_time.py`: curated Christian October meeting/work evidence and unconfirmed assumptions, preserving separate measures.
- `tools/prepare_extra_vectors.py`: retained supplemental research for future consideration; its output is not assembled into the current five-vector dashboard.

Raw inputs reside in `data/private/` and are ignored by Git. Local normalized JSON files are also ignored. Within `data/`, only `empty.json` and the explicitly curated `shared-dashboard.json` are tracked. `OWNER_CONFIRMATIONS.json` separately retains explicit owner outcomes so source imports cannot erase them. `tools/prepare_dashboard.py` refreshes both local and shared snapshots; `tools/prepare_shared_snapshot.py` can curate an existing local dashboard separately. Store credentials in an authorized collection service, never the front-end code, workbook cells or repository.

Current source collection and bounds: [REFRESH_2026-11-19.md](REFRESH_2026-11-19.md), with earlier findings in the [October 23 review](REFRESH_REVIEW_2026-10-23.md). Refresh tools accept explicit, independently dated private patches and prepare a private combined preview before any canonical/shared write. They preserve owner decisions and hours, retain historical native proof and correspondence separately, and archive incompatible row-scoped reviews after worksheet reordering. See [CONTRIBUTING.md](CONTRIBUTING.md) for checks; ignored private files are not needed to view the tracked snapshot or run replay regressions, but are required to reproduce source preparation.

`tools/apply_mailbox_review_2026_10_24.py` validates a curated targeted inbox supplement and writes a private preview only. Its independent `crm.mailboxReview` retains collection clocks and earlier review batches, keeps raw correspondence and addresses private, and cannot update commercial decisions or event/hour counters.

Collection is currently manual/on demand. The approved curated snapshot is published through GitHub Pages, with an older Sites mirror that is not automatically refreshed. Automatic refresh and an authenticated internal deployment have not been enabled. The browser concept is not an authenticated production service.

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

See [the October 29 refresh](REFRESH_2026-10-29.md) and [current data gaps](DATA_GAPS.md) for current coverage and targeted follow-up. The [October 24 gap-resolution review](GAP_RESOLUTION_2026-10-24.md), [October 23 checklist](MANUAL_DATA_REQUEST_2026-10-23.md) and [SOURCE_REVIEW.md](SOURCE_REVIEW.md) retain earlier evidence. See [PLAN.md](PLAN.md) for the agreed scope and implementation sequence.

Referral scope was explicitly added after the five-vector clarification. Newsletter/email, standalone website reporting and Pulley remain outside the visible dashboard. Referrals now contains a reconciled current inventory; dated requests/introductions and owner-confirmed outcomes still require their own event records.

Earlier source reviews remain in [REFRESH_REVIEW_2026-10-14.md](REFRESH_REVIEW_2026-10-14.md), [CRM_ACTIVITY_REVIEW.md](CRM_ACTIVITY_REVIEW.md) and [MEETING_SOURCE_REVIEW.md](MEETING_SOURCE_REVIEW.md). Source snapshots remain on-demand; refreshed source dates are distinct from historical imports and access checks.

## October effort and import coverage

The Time & effort view estimates Christian’s October work with deduplicated recording evidence and a separate adjustable nonmeeting range. It does not measure actual or billable hours. See [OCTOBER_EFFORT_REVIEW.md](OCTOBER_EFFORT_REVIEW.md) and [DATA_GAPS.md](DATA_GAPS.md).
