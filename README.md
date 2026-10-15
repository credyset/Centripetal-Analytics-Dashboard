# Centripetal Analytics Dashboard

Private business-development dashboard for Charles Solomon and the Centripetal team. A local working concept, using actual dated source snapshots, with separate activity and outcome reporting.

## Live public dashboard

https://centripetal-analytics-dashboard.christian399556.chatgpt.site

Anyone can view the detailed public snapshot. The owner explicitly approved prospect identities and available business record links; source dates and known gaps remain visible. This is separate from the local internal concept. See [DEPLOYMENT.md](DEPLOYMENT.md) for hosting identity and the update procedure.

## Preview

Run Python 3.10 or later from this directory:

```sh
python3 serve.py
```

Open **http://127.0.0.1:8765**. The preview binds to localhost only. The server exposes the application, approved assets and the prepared dashboard snapshot; raw exports, source scripts and Git files are not served.

The repository contains application code and an empty-data setup state. Operational data is deliberately excluded. The working local checkout includes `data/dashboard.json`; a new clone requires authorized source snapshots before it displays actual figures. No synthetic results are presented as real.

## Views

- At a glance (default): the original five dashboard vectors—LinkedIn Ads, Waalaxy, LinkedIn content, Pipedrive and Video DMs—plus a separate Referrals placeholder—with activity, responses, outcomes and source dates. Supplementary research is retained for a future scope expansion.

- Overview: equal emphasis on activity and outcomes, weekly deal creation, follow-up priorities and source coverage.
- LinkedIn Ads: dated spend/delivery, lead quality and campaign economics.
- Waalaxy: labelled historical Charles prospect flags; current campaign activity awaits a verified export.
- LinkedIn Content: daily exposure, account coverage and a ranked post subset; organic/sponsored splits remain unavailable where omitted.
- Pipedrive: created/updated records, CRM activity, pipeline inventory and data-quality issues.
- Video DMs: current readiness/status inventory, searchable records and measurement boundaries.
- Referrals: dedicated placeholder for referral requests, introductions, qualification and sourced outcomes; awaiting the owner's dataset.
- Sources & definitions: dates, refresh method, known gaps and outcome definitions.

Date presets and custom dates operate on dated evidence. Undated inventories remain explicitly labelled snapshots. Tables support search, sorting and pagination. Charts, fonts and logo are local assets, with no third-party runtime/CDN requests.

## Reporting calendar

Monday–Sunday weeks, `America/Denver`, including daylight-saving changes. Preserve source day boundaries where exports are already aggregated by another timezone. The default range is the last 30 complete days; the current partial day is excluded. Partial and historical source coverage must remain visible.

## Data preparation

Normalized local inputs: `data/ads.json`, `crm.json`, `video.json`, `waalaxy.json`, and `content.json`. Combine them with:

```sh
python3 tools/prepare_dashboard.py
```

Source-specific preparation:

- `tools/prepare_channels.py`: audited ad exports, verified Charles Waalaxy baseline and analytics workbooks. Requires `openpyxl`; paths currently reflect the source workspace.
- `tools/prepare_crm.py`: paginated Pipedrive snapshots collected read-only across all accessible owners.
- `tools/prepare_video.py`: Video DM prospect and accepted-connection worksheet snapshots.
- `tools/prepare_extra_vectors.py`: retained supplemental research for future consideration; its output is not assembled into the current five-vector dashboard.

Raw inputs reside in `data/private/` and are ignored by Git. Prepared operational JSON files are also ignored. Store credentials in an authorized collection service, never the front-end code, workbook cells or repository.

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

The new private repository is `credyset/Centripetal-Analytics-Dashboard`. The public snapshot is available through Sites. Next steps for the internal live-data service are reliable source adapters, retained history, a private data store, authenticated hosting and monitored refresh jobs.

A private repository does not make a standard GitHub Pages site private. Protect both the dashboard and its data endpoints before publishing internal records. Keep the local concept available while deployment ownership and access are settled.

## Assets

Centripetal logo and palette follow the workspace brand guidelines. Roboto is Copyright 2015 Google Inc., licensed under Apache 2.0. Lora is Copyright 2011 The Lora Project Authors, licensed under SIL OFL 1.1 with Reserved Font Name Lora. License texts are included in `assets/`.

See [SOURCE_REVIEW.md](SOURCE_REVIEW.md) for the latest four-chat source review and remaining gaps. See [PLAN.md](PLAN.md) for the agreed scope and implementation sequence.

Referral scope was explicitly added after the five-vector clarification. Newsletter/email, standalone website reporting and Pulley remain outside the visible dashboard. Referrals currently shows unavailable metrics and planned definitions; importing/calculating the future referral dataset is a separate implementation step.
