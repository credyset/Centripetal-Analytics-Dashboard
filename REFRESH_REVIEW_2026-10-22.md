# October 22 channel refinement — local only

The owner authorized continued work. The existing instruction to keep the update local remains in force: no GitHub push, Pages deployment or Sites publication occurred. This review adds authenticated channel detail to the October 21 CRM, calendar, recording and creator review. Those older source collection times remain unchanged.

The dashboard still defaults to October 19–21, with its October 21 CRM reporting day partial. The newer Waalaxy aggregate includes October 22 and is labelled as a separate fixed source window. Source day boundaries are retained rather than inferred into Mountain days.

## Newly collected evidence

| Source | Evidence now applied | Date / scope boundary |
|---|---|---|
| LinkedIn Ads | Authenticated Ad Set Performance and Ad Performance exports, All columns, broken out by day. 116 ad-set/day rows and 117 ad/day rows reconcile across all additive counters. $3,592.31 spend, 25,055 impressions, 106 clicks, 62 form opens, four submissions, 10,804 video views and 419 completions. | Actual rows September 4–October 21 UTC. Requested October 22 has no row, so it remains unavailable rather than an invented zero. Five delivering A–E ad sets / six ads; two older UI ad sets have no exported delivery rows. Figures may restate. |
| Centripetal company content | Authenticated Charles company-admin Metrics workbook: 47 daily UTC rows, 24,698 impressions (9 organic / 24,689 sponsored), 105 clicks, eight reactions, no comments and one repost. Header confirms 899 followers as a separate snapshot. | September 4–October 20. The source explicitly says data may be delayed up to two days and rejects October 21. The workbook has only Metrics, not a post register. Daily unique impressions are not added into period reach; engagement rates are not averaged. |
| Company / Ads overlap | Every daily sponsored impression, click, reaction, comment and repost agrees with the corresponding fresh Ads source over September 4–October 20 UTC. | These sponsored metrics are the same paid activity. Never add company sponsored totals to Ads, or add personal and company views into unduplicated reach. |
| Charles Waalaxy Home | Account name and exact LinkedIn profile independently verified in Charles's native Chrome. Fixed This month source window: 430 invitation actions, 132 accepted invitations, zero platform message actions and two answered messages. | October 1–22 displayed source days, October 22 partial; timezone unspecified. No daily CSV was retained, so this is not merged into older invitation days and cannot supply filtered weekly totals. Zero platform actions does not imply zero manual LinkedIn/Video DM sends; two answers are not confirmed positive replies or unique prospects. |
| Video DM workbook | Modified timestamp predates the completed October 21 collection; no newer content was established. | Retain 428 valid rows / 420 profiles and the independently dated 168-person accepted-connections subset. The current Charles login does not establish the Sheet sender or last successful upstream sync. |
| XCaliber commercial timing | Actual September 23 dialogue covers paid scope, retainer pricing and agreed data-room/proposal/follow-up steps. Independently dated September 24 inbox correspondence corroborates the next step. | Accepted active opportunity established by September 24, before October. October 5 is not net-new October acceptance. Exact first-ever acceptance date remains unknown; no signed first-client evidence found. |

## Period examples now supported

- Ads October 19–21 UTC: **$180.31**, 1,225 impressions, three clicks, one form open and zero submissions, across three explicit source days.
- Ads October 1–21 UTC: **$1,373.06**, 10,575 impressions, 43 clicks, 21 form opens and two submissions.
- Company October 19–20 UTC: **859 sponsored impressions**, zero organic impressions and two clicks. This is partial coverage of an October 19–21 selection; October 21 is unavailable.
- Company October 1–20 UTC: **10,209 sponsored impressions**, zero organic impressions and 42 clicks. This is not a complete October 1–21 company total.
- Waalaxy **430 / 132** is a fixed October 1–22 snapshot. It is not this week's invitation count and is not added to the older September 15–October 15 day series or connected-person flags.

The four Charles outcome headlines retain the reviewed October minimum of **at least five held calls / at least two qualified companies**. Current-week held-call completeness, net-new accepted opportunities and first-time client wins remain unresolved. Venus remains under the last explicit owner unqualified decision; both duplicate CRM records stay joined to one company and the held-date conflict stays visible.

Christian's separate non-meeting estimate remains **14.5–15.75 hours**. Recording evidence remains five deduplicated audio durations / 228.58 minutes, with no combined human-hours claim.

## Remaining high-impact inputs

1. **Charles's business decisions and complete call roster.** Confirm Venus's latest qualification/active next step and actual held day, actual first-time client execution dates and an existing-client baseline. Calls outside accessible Calendly/Fireflies still need reconciliation. XCaliber's pre-October acceptance is now established independently; an October acceptance assumption is no longer needed.
2. **Waalaxy daily/action export.** Charles-only daily invitations/acceptances and message/reply actions for October 1 onward, with sender/campaign IDs, exact extraction time, timezone and explicit zero days. Include positive/negative reply classification and prospect/CRM joins where available. Platform-displayed 30.7% acceptance and 1.5% response rates have undefined denominators and are not cohort conversion rates.
3. **Company and Charles post register.** Post IDs/URLs, exact publication dates, author/distribution identity, measurement window, organic/sponsored delivery and campaign/creative joins. The new company workbook has daily metrics only; a missing post table is not zero posts. Company October 21+ will require a later source refresh after its stated delay.
4. **Video DM delivery and sync evidence.** Actual send/follow-up times, channel, video-included evidence, replies/outcomes, stable recipient/CRM IDs and last successful Sheet sync. Prepared links, status values and connected-person attributes remain distinct.
5. **Referral and effort events.** Dated requests/introductions and verified automation execution; Christian's own calendar, actual attendance and work log. Existing snapshots and an owner allowance do not measure those events or hours.
6. **CRM historical completeness and attribution.** Archived-inclusive collection, broader stage history, original business decision dates and stable channel joins remain incomplete. No generic fresh deal/activity export is required for this review: that source was collected independently already.

## Contributor implementation notes

Private raw sources and analysis live in `data/private/refresh_2026_10_22/`; inbox/recording investigation also retains the October 21 evidence folder. Neither is tracked or served by the local preview.

- `tools/normalize_ads_2026_10_22.py` parses the source UTF-16 TSV exports, reconciles grains and preserves owner outcomes. The LinkedIn Ads skill analyzer was also run independently at each grain.
- `tools/normalize_company_content_2026_10_22.js` parses the actual XLS Metrics worksheet, preserves zero versus unavailable, and verifies company-sponsored overlap with Ads at daily and aggregate levels.
- `tools/apply_refresh_2026_10_22.py` applies isolated reviewed patches to a retained October 21 baseline, then reapplies canonical outcomes, the separate effort estimate and the local-only policy.
- `content.companyAnalytics` and `waalaxy.accountAnalytics` retain independent collection dates. Updating them does not refresh Charles's creator window, older invitation days, selected-person snapshots, CRM or meeting evidence.
- Older imports preserve these independent supplements and their source-card dates. The local-only policy rejects deployment builds until an explicit owner instruction and intentional policy change permit publication.

Validation passed for source reconciliation, source-preservation imports, outcome counting and date boundaries, JavaScript syntax and the local static build. Browser checks covered the weekly and October selections, the company's partial coverage and Waalaxy's fixed month window. The deployment build correctly rejects the local-only snapshot. Raw files, validation screenshots and generated preview output remain ignored by Git.

GitHub remains the shared application/data source of truth for a future authorized release. This newer local branch has not been pushed; the existing public GitHub Pages snapshot is unchanged.
