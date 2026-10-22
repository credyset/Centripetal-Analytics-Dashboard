# Centripetal Analytics Dashboard

Business-development dashboard for Charles Solomon and the Centripetal team, with actual dated source snapshots and separate activity and outcome reporting.

**GitHub is the shared source of truth for the application, curated reporting snapshot and measurement documentation:** https://github.com/credyset/Centripetal-Analytics-Dashboard

Other agents can clone this repository, run the populated dashboard and contribute through branches/pull requests without access to ChatGPT Sites. See [CONTRIBUTING.md](CONTRIBUTING.md).

Latest local refresh: [October 22 channel refinement](REFRESH_REVIEW_2026-10-22.md), [October 21 CRM/meeting review](REFRESH_REVIEW_2026-10-21.md), [Charles outcome definitions](OUTCOME_REVIEW_2026-10-21.md), and [publication review](PUBLICATION_REVIEW_2026-10-21.md). The private source supplements are prepared locally and **have not been published**. The owner instructed “Keep it local for now”; the public site retains its last approved snapshot. No publication approval question is pending. The canonical local-only policy is in `PUBLICATION_POLICY.json`. Earlier corrections remain documented in [ANALYTICS_REVISION_2026-10-16.md](ANALYTICS_REVISION_2026-10-16.md).

For the few inputs that still require owner evidence or an export, see [Remaining manual inputs](MANUAL_DATA_REQUEST_2026-10-22.md). Current generic CRM and creator exports have already been collected independently.

The local October 22 review includes all 76 retained October recording responses, selected Sales-record context and Woodrow/Venus reconciliation, and separately dated referral evidence. Jonathan's two October 22 email replies provide context without establishing an introduction or a formal lost outcome. The current full CRM read completed October 22 at 05:51 MDT. The Video DM workflow review retains 85 history pages:808 unique run IDs, including 703 held,90 filtered and 15 successful. Run counts are separate from delivered outreach and prospect outcomes. The later [Video DM reconciliation](ZAPIER_RECONCILIATION_2026-10-22.md) verifies all ten October 21 Loom-linked records in CRM, distinguishes57 recording URLs from3 notes, and retains the short held-trigger burst as technical context. It does not establish703 missing outreach records. See the updated [remaining-input checklist](MANUAL_DATA_REQUEST_2026-10-22.md).

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
- LinkedIn Ads: current authenticated ad-set and creative daily exports through October 21 UTC, lead quality and campaign economics.
- Waalaxy: verified Charles Home aggregates for October 1–22 (partial), separate from the retained invitation day series through October 15, selected connected people and historical flags. Daily message/reply events and positive outcomes remain missing.
- LinkedIn Content: Charles's current creator workbook supplies 90 daily impression/engagement rows, follower additions and 49 dated ranked posts. The 545 social engagements remain distinct from 555 broader workbook Engagements; the ranked subset is not a publishing census. Company daily organic/sponsored metrics cover through October 20 UTC and overlap Ads.
- Pipedrive: created/updated records, searchable activity records, owner/type breakdowns, automation metadata, overdue inventory, scoped stage-change history, follow-through gaps and separately corroborated Calendly bookings.
- Video DMs: current readiness/status inventory, searchable records, explicit CRM-join review and revision-history boundaries; status changes remain distinct from delivery events.
- Referrals: reconciled current relationship-record inventory, explicit exclusion partitions and retained dated stage changes; referral event and qualification outcomes remain incomplete.
- Time & effort: Christian’s fixed October-to-date recording evidence and separate editable nonmeeting estimates; actual attendance and human hours remain unknown.
- Sources & definitions: dates, refresh method, manual import checklist, known gaps and outcome definitions.

Date presets and custom dates operate on dated evidence. Undated inventories remain explicitly labelled snapshots. Tables support search, sorting and pagination. Charts, fonts and logo are local assets, with no third-party runtime/CDN requests.

## Reporting calendar

Monday–Sunday weeks, `America/Denver`, including daylight-saving changes. Preserve source day boundaries where exports are already aggregated by another timezone. The current review defaults to October 19–22, with October 22 partial; complete-day presets end October 21. Each source is independently bounded: the fresh CRM read does not extend older calendar, content, invitation or recording coverage. Calendar future-event coverage cannot establish bookings created after collection. Time & effort extends its requested October scope through October 22 while retaining the original evidence dates and the separate14.5–15.75-hour owner estimate.

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

Current Charles creator snapshot: see [REFRESH_REVIEW_2026-10-22.md](REFRESH_REVIEW_2026-10-22.md), using the owner-designated signed-in Chrome profile and an actual workbook download. The [October 16 creator review](CONTENT_CREATOR_REVIEW_2026-10-16.md) documents the earlier snapshot and source methods.

Latest reviewed refresh: [REFRESH_REVIEW_2026-10-22.md](REFRESH_REVIEW_2026-10-22.md), following [REFRESH_REVIEW_2026-10-21.md](REFRESH_REVIEW_2026-10-21.md). Configured Pipedrive, Calendly and Centripetal Fireflies MCP sources were read directly; browser evidence uses the designated signed-in accounts, with raw evidence kept private. The full CRM contains 769 records /924 activities collected October 22 at 11:51:50UTC; a separately dated, exhausted archived-deal query returned zero accessible records. All 76 retained October recording responses have been reviewed without increasing confirmed prospect outcomes. `tools/apply_refresh_2026_10_21.py` assembles the CRM/meeting review; `tools/apply_refresh_2026_10_22.py` applies channel details; `tools/apply_completion_audit_2026_10_22.py` applies creator, archive, recording-purpose and source-quality evidence; `tools/apply_latest_review_2026_10_22.py` applies the latest CRM, correspondence reconciliation and independently verified Zapier evidence. Older replays preserve independently newer sources. Prior review: [LIVE_DATA_REFRESH_2026-10-16.md](LIVE_DATA_REFRESH_2026-10-16.md). Private raw files are required to replay collection preparation; a fresh clone uses the tracked shared snapshot directly.

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

See [SOURCE_REVIEW.md](SOURCE_REVIEW.md) for the latest four-chat source review and remaining gaps. See [PLAN.md](PLAN.md) for the agreed scope and implementation sequence.

Referral scope was explicitly added after the five-vector clarification. Newsletter/email, standalone website reporting and Pulley remain outside the visible dashboard. Referrals now contains a reconciled current inventory; dated requests/introductions and owner-confirmed outcomes still require their own event records.

See [REFRESH_REVIEW_2026-10-14.md](REFRESH_REVIEW_2026-10-14.md), [CRM_ACTIVITY_REVIEW.md](CRM_ACTIVITY_REVIEW.md) and [MEETING_SOURCE_REVIEW.md](MEETING_SOURCE_REVIEW.md) for the latest source review. Source snapshots remain on-demand; refreshed source dates are distinct from historical imports and access checks.

## October effort and import coverage

The Time & effort view estimates Christian’s October work with deduplicated recording evidence and a separate adjustable nonmeeting range. It does not measure actual or billable hours. See [OCTOBER_EFFORT_REVIEW.md](OCTOBER_EFFORT_REVIEW.md) and [DATA_GAPS.md](DATA_GAPS.md).
