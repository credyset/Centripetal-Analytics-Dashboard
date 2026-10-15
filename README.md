# Centripetal Analytics Dashboard

Business-development dashboard for Charles Solomon and the Centripetal team, with actual dated source snapshots and separate activity and outcome reporting.

**GitHub is the shared source of truth for the application, curated reporting snapshot and measurement documentation:** https://github.com/credyset/Centripetal-Analytics-Dashboard

Other agents can clone this repository, run the populated dashboard and contribute through branches/pull requests without access to ChatGPT Sites. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Live public dashboard

https://centripetal-analytics-dashboard.christian399556.chatgpt.site

Anyone can view the detailed public snapshot. The owner explicitly approved prospect identities and available business record links; source dates and known gaps remain visible. This is separate from the local internal concept. See [DEPLOYMENT.md](DEPLOYMENT.md) for hosting identity and the update procedure.

## Preview

Run Python 3.10 or later from this directory:

```sh
python3 serve.py
```

Open **http://127.0.0.1:8765**. The preview binds to localhost only. The server exposes the application, approved assets and the prepared dashboard snapshot; raw exports, source scripts and Git files are not served.

The repository includes application code and the owner-approved curated reporting snapshot in `data/shared-dashboard.json`, so a fresh clone displays the current retained figures. It contains the same approved reporting data as the live publication, including the October effort evidence. Raw exports, credentials and private transcript evidence remain excluded. The app loads the shared snapshot first, then falls back to a local prepared snapshot or the empty setup state when unavailable.

## Views

- At a glance (default): the original five dashboard vectors—LinkedIn Ads, Waalaxy, LinkedIn content, Pipedrive and Video DMs—plus Referrals and a separate Christian Time & effort support category—with activity, responses, outcomes and source dates. Supplementary acquisition research is retained for a future scope expansion.

- Overview: equal emphasis on activity and outcomes, weekly deal creation, follow-up priorities and source coverage.
- LinkedIn Ads: dated spend/delivery, lead quality and campaign economics.
- Waalaxy: labelled historical Charles prospect flags; current campaign activity awaits a verified export.
- LinkedIn Content: retained daily exposure and ranked posts, plus separately dated current public followers and observed public engagement. Private current-period analytics and organic/sponsored splits remain unavailable where omitted.
- Pipedrive: created/updated records, searchable activity records, owner/type breakdowns, automation metadata, overdue inventory, scoped stage-change history, follow-through gaps and separately corroborated Calendly bookings.
- Video DMs: current readiness/status inventory, searchable records and measurement boundaries.
- Referrals: dedicated placeholder for referral requests, introductions, qualification and sourced outcomes; awaiting the owner's dataset.
- Time & effort: Christian’s fixed October-to-date recording evidence and separate editable nonmeeting estimates; actual attendance and human hours remain unknown.
- Sources & definitions: dates, refresh method, manual import checklist, known gaps and outcome definitions.

Date presets and custom dates operate on dated evidence. Undated inventories remain explicitly labelled snapshots. Tables support search, sorting and pagination. Charts, fonts and logo are local assets, with no third-party runtime/CDN requests.

## Reporting calendar

Monday–Sunday weeks, `America/Denver`, including daylight-saving changes. Preserve source day boundaries where exports are already aggregated by another timezone. The default range is 30 days anchored to the latest complete CRM reporting day; publishing an older snapshot today does not advance its cutoff. Time & effort has its separately labelled October-to-date scope. Partial and historical source coverage must remain visible.

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

Raw inputs reside in `data/private/` and are ignored by Git. Local normalized JSON files are also ignored. Only `data/empty.json` and the explicitly curated `data/shared-dashboard.json` are tracked. `tools/prepare_dashboard.py` refreshes both local and shared snapshots; `tools/prepare_shared_snapshot.py` can curate an existing local dashboard separately. Store credentials in an authorized collection service, never the front-end code, workbook cells or repository.

Collection is currently manual/on demand. A public sanitized snapshot is deployed through Sites. Automatic refresh and an authenticated internal deployment have not been enabled. The browser concept is not an authenticated production service.

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

The shared private repository is `credyset/Centripetal-Analytics-Dashboard`. Sites is a publishing destination built from the shared project; GitHub changes do not yet trigger automatic publication. The current public snapshot is available through Sites. Next steps for the internal live-data service are reliable source adapters, retained history, a private data store, authenticated hosting and monitored refresh jobs.

A private repository does not make a standard GitHub Pages site private. Protect both the dashboard and its data endpoints before publishing internal records. Keep the local concept available while deployment ownership and access are settled.

## Assets

Centripetal logo and palette follow the workspace brand guidelines. Roboto is Copyright 2015 Google Inc., licensed under Apache 2.0. Lora is Copyright 2011 The Lora Project Authors, licensed under SIL OFL 1.1 with Reserved Font Name Lora. License texts are included in `assets/`.

See [SOURCE_REVIEW.md](SOURCE_REVIEW.md) for the latest four-chat source review and remaining gaps. See [PLAN.md](PLAN.md) for the agreed scope and implementation sequence.

Referral scope was explicitly added after the five-vector clarification. Newsletter/email, standalone website reporting and Pulley remain outside the visible dashboard. Referrals currently shows unavailable metrics and planned definitions; importing/calculating the future referral dataset is a separate implementation step.

See [REFRESH_REVIEW_2026-10-14.md](REFRESH_REVIEW_2026-10-14.md), [CRM_ACTIVITY_REVIEW.md](CRM_ACTIVITY_REVIEW.md) and [MEETING_SOURCE_REVIEW.md](MEETING_SOURCE_REVIEW.md) for the latest source review. Source snapshots remain on-demand; refreshed source dates are distinct from historical imports and access checks.

## October effort and import coverage

The Time & effort view estimates Christian’s October work with deduplicated recording evidence and a separate adjustable nonmeeting range. It does not measure actual or billable hours. See [OCTOBER_EFFORT_REVIEW.md](OCTOBER_EFFORT_REVIEW.md) and [DATA_GAPS.md](DATA_GAPS.md).
