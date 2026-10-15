# Contributor data priorities and accuracy gaps

Assessment date: October 15, 2026. Based on the committed shared snapshot and source reviews, not a new collection of the operational systems. Business sources were principally collected October 14 Mountain time; the October effort review was collected October 15. Counts below are dated diagnostics, not permanently current values.

This guide supplements README.md and DATA_GAPS.md. The shared reporting contract is `data/shared-dashboard.json`; follow CONTRIBUTING.md for changes. The goal is to improve the accuracy of business-development activity, commercial outcomes and Christian's separate effort estimate. Do not add acquisition categories or alter source systems merely to fill a chart.

Field names proposed below describe desired additions, not fields already implemented everywhere. Agree their definitions and extend normalizers, the shared schema and calculations together before relying on them in a displayed KPI.

## Work in this order

| Priority | Data improvement | Why it has high impact | Completion evidence |
| --- | --- | --- | --- |
| 1 | A reliable prospect/deal identity crosswalk and dated touchpoint-to-outcome links | Makes cross-channel deduplication and channel comparisons possible; prevents counting the same booking as three results | Stable source IDs, explicit match evidence, unresolved queue, and one canonical outcome ID across channel/CRM/calendar records |
| 2 | Confirmed meeting purpose, attendance and qualification outcomes | Separates booked calls from held sales conversations and poor-fit bookings | Booking chain, scheduled time, held/no-show/canceled outcome, commercial purpose, associated prospect/deal, qualification decision and confirmation date |
| 3 | Actual Video DM and Charles Waalaxy send/reply event dates | Converts undated inventory and lifetime flags into weekly activity and response metrics | Source-dated events with action type, recipient ID, campaign/channel and explicit definitions; complete coverage or visible gaps |
| 4 | CRM stage/status reconciliation, change history and accepted-opportunity definitions | Makes progression and pipeline outcomes defensible | Owner-reviewed outcome conflicts; timestamped transitions with agreed advancement map; working opportunities have next steps |
| 5 | Current Charles/company private LinkedIn and paid delivery data, with consistent cohorts | Makes exposure, engagement and acquisition denominators comparable | Same complete reporting period, correct account, campaign/post IDs, paid/organic classification, source timezone and metric definitions |
| 6 | Referral event register and real contract economics | Makes a currently missing channel visible and connects outcomes to meaningful commercial value | Dated introductions, linked deals and confirmed outcomes; signed recurring/one-time value separated from collected revenue |
| 7 | Christian's calendar, attendance and direct nonmeeting work log | Replaces the low-confidence effort reconstruction with measured human time | Dated Christian-only entries, source, workstream and overlap handling; estimates retained separately |

Priorities are about accuracy, not permission to declare unverified outcomes. Start with recent leads, working sales conversations and new outreach, rather than attempting to reconstruct every historical record at once.

## 1. Identity and attribution: the shared dependency

Recommended minimum fields for a private reconciliation crosswalk: `canonicalPersonId`, `canonicalCompanyId`, source system/account, source record ID, normalized LinkedIn profile, CRM person/organization/deal IDs, match method, reviewer, review date and confidence. Normalize business emails privately when authorized for exact matching; publish only the curated identifiers/details needed by the dashboard. A stable source ID must not be replaced by a spreadsheet row number or display name.

The current CRM deal rows do not expose stable person/organization IDs, although some activities have them. If available from the authorized source, retain those IDs in the normalized model. Link the corresponding form submission ID, Waalaxy prospect ID, video prospect ID and referral ID. People, companies, deals, submissions and appointments are different entities: one person may submit twice or hold several meetings; one company may have multiple contacts or deals.

For each attribution link, capture the touchpoint ID, outcome ID, source channel/campaign, touchpoint timestamp, evidence and whether it is owner-confirmed, source-reported, identity-only or unknown. Exact identity establishes a relationship between records, not that an ad caused a booking. Keep first-known source, assisted touches and owner-confirmed acquisition source separate. Until a model is agreed, report linked outcomes and unattributed outcomes instead of assigning every deal to a channel or forcing percentages to sum to 100%.

Known join gaps: 59 Video DM rows have a CRM deal ID, 58 resolve and one is stale (XCaliber Health / Prakash Khot references deal 290). Only two of the 47 ready rows have CRM IDs. Resolve through source evidence; never reassign based only on a similar company name. The Pulley research list and operational Video DM queue are different populations; research-ready contacts require an explicit reviewed promotion into the operational workflow.

## 2. Meetings and lead quality

Required booking fields: source account, event/invitee IDs, booking-chain ID, original booking creation time, scheduled start, cancellation/reschedule events and current-booking flag. Add meeting purpose (sales/prospect, partner/referral, internal, interview, other/unknown), verified held outcome, attendance evidence, outcome confirmation time, linked prospect/deal and next step. Never treat a past scheduled end time, generic event type, CRM stage or completed task as attendance proof.

Current limits:

- Charles's Calendly read contains 27 event records / 25 unique booking chains. Nine interview chains are excluded; 16 generic chains remain commercially unclassified. This is an event-start-bounded extraction, not every booking ever created in the selected date range.
- NuVee has a corroborated booking and remains owner-qualified/warm. Venus Ai Consulting also has a corroborated booking and remains owner-unqualified. A booking must not requalify either lead automatically. NuVee's November 17 follow-up is a task, not an accepted future appointment.
- Actual held-call totals remain unverified. Prioritize confirming recent matched calls and working opportunities before collecting more anonymous calendar totals.

Maintain qualification as a decision history: decision, decision time, reviewer, qualification reason, commercial fit, intent and next step. A later qualification update must not silently rewrite what was known in an earlier reporting period. Four paid submissions and one owner-qualified lead are a small cohort; do not imply a stable forecast from that rate.

## 3. Outreach events and denominators

Minimum event fields: `eventId`, `prospectId`, channel/account, campaign or sequence ID, action type, `occurredAt`, timestamp/source timezone, evidence method and linked CRM IDs. Distinguish prepared, queued, attempted, platform-confirmed sent/delivered where available, replied, positive reply, opted out and failed. If a platform provides sent but not delivered, keep delivery unknown. Capture who classified a positive reply and when.

### Video DMs

The snapshot has 428 rows, 420 valid unique profiles, two missing profile URLs, six duplicate profiles and two conflicting profile statuses. There are 47 ready rows, 48 sheet-classified completed rows and 29 explicit Sent/Done statuses. These are different measures. A Loom link may trigger the broader completed classification and is not send evidence.

Add an immutable prospect ID and separate `rowCreatedAt` (only where verified), `firstObservedAt`, `videoPreparedAt`, `sentAt`, `firstReplyAt`, reply disposition and follow-up due/completed dates. A newly observed row is not necessarily newly created. A corrected URL is not a new prospect or new send. A transition discovered between snapshots has an observation interval; do not assign it an exact delivery time. If historical send dates are unavailable, begin a dated log prospectively and mark the earlier history unavailable.

### Waalaxy

Use Charles's account only. The available verified export is July 6, with dated activity through June 26; invitation/message/reply flags describe people over historical coverage. They do not establish October actions or total message counts. A current export from Christian's account is not a substitute.

Request campaign daily metrics plus recipient-level event data when exportable. Keep invitations sent, accepted invitations, initial messages, follow-up messages, unique contacted people, unique repliers and positive replies separate. A person receiving three messages contributes three sends but one unique recipient. For acceptance/reply rates, define the eligible sent cohort and observation lag; same-week replies divided by same-week sends can mix unrelated cohorts.

## 4. Pipedrive: inventory is stronger than event history

The read covers 722 accessible nondeleted deals and 923 activities; business totals exclude four test deals and five test activities (718 deals / 918 activities). Preserve explicit exclusions and source scope. Do not assume an API inventory includes deleted/merged history or records inaccessible to the connected account.

The last legitimate recorded business completion is August 19. Recent zero completions therefore indicate a logging gap, not zero business work. Of 24 last-30-day created activities, 23 carry an automation reference and one is NuVee's follow-up task. Activity owner is not proof of the person who performed the work; a null automation reference is not proof of manual creation.

High-impact additions/corrections:

- **Updated records:** collect structured field-change events or a durable change log. A deal's latest `updatedAt` cannot count every touch in an earlier period after a later edit replaces it. Separate administrative maintenance from stage advancement and human activity.
- **Progression:** history currently covers only 44 selected deals, with 33 stage events since September 1. Complete the agreed scope and retain per-deal pagination/coverage. Map stage IDs explicitly into entry, working, parking, terminal and referral milestones; stage ordering alone is unsafe, particularly across pipelines.
- **Outcome conflicts:** 19 open-status Sales records occupy Closed Won/Lost-labelled stages. OneFlo appears in multiple records with terminal stage labels but open status. Obtain owner decisions; preserve correction history. The one actual won-status record does not by itself prove a signed retainer or recognized revenue.
- **Next steps:** working Sales records XCaliber Health and Menos AI lack future linked CRM activities. Verify external commitments, then have the authorized operational owner record the next action and due date.
- **Backlog:** 371 of 372 unfinished business activities are overdue, including 190 over 90 days. Obtain current/obsolete/sequence-generated classifications before reporting missed commitments. Retiring tasks today must not manufacture historical completions.
- **Links:** 178 activities lack a deal link; 24 lack deal, person and organization links. Account-wide activity totals and pipeline-filtered totals can legitimately differ. Show the excluded/unlinked population rather than silently losing it.
- **Value:** open values are zero/unpopulated. Request value basis, amount, currency, recurring fee, one-time fee, expected term, expected/actual close dates and signed-contract evidence where relevant. Keep forecast, signed contract value, recurring revenue and collected revenue separate; an unset zero is not a zero-dollar opportunity.

## 5. Paid and organic LinkedIn: align the population and dates

### Ads

Latest retained daily coverage is September 4–October 14 UTC ($3,200.93 spend, four submissions). Obtain campaign/ad/form IDs, objective, account/currency, daily delivery metrics and submission IDs with exact timestamps. Preserve gross spend and any explicit currency/refund treatment; do not silently convert currencies.

Reconcile source submission totals to unique submissions, duplicate/test exclusions and owner qualification. Campaign objectives differ: form campaigns and website-visit campaigns need separate economics. All selected spend divided by one qualified submission is a blended reporting measure, not proof of that lead's campaign-specific acquisition cost. Label all-click versus destination/link clicks; match numerator and denominator definitions before calculating CTR or conversion rates. Video attention currently has full-window totals without daily detail and must not follow arbitrary date filters.

### Content

Private Charles daily analytics end September 10; the company private baseline is 2025. October 14 public follower counts and two observed posts are a sample, not a current publishing census or impressions feed.

Request account/post IDs, post URL, publication time, metric extraction time/window, impressions/reach/clicks/engagement components, organic/sponsored breakdown, follower changes and boost campaign IDs. Keep Charles and the company distinct. A company repost and Charles's original are related posts, not necessarily duplicate exposure; audiences overlap and cannot be summed as unique reach. Lifetime post engagement cannot be labelled engagement occurring this week. Confirm whether daily rows are incremental or cumulative and whether the export supplies engagements directly or only components; do not invent a missing engagement total or use an unweighted average of rates. Reconcile boosted spend to Campaign Manager before any combined spend metric.

## 6. Referrals, website evidence and commercial value

Referrals need an event register: referral ID, referring person/partner, prospect, requested/promised/introduced/responded dates, owner, qualification decision, booking/held evidence, CRM deal ID, next step and verified outcome/value. A referrer record may introduce multiple prospects. Current Referral Pipeline positions and a few scoped transitions can seed a review queue; they do not constitute a complete period register or automatically establish sourced wins.

Website/GA4 is supporting attribution evidence and is not a new visible acquisition category. If available, add successful inquiry IDs/timestamps, confirmed booking/conversion IDs, form/landing-page identity, campaign UTMs and an authorized CRM linkage. The retained GA4 audit has incomplete successful-inquiry/booking measurement, so zero recorded key events is not zero actual demand. Preserve its America/New_York source-day aggregates; do not silently relabel them Mountain days or identify a person from aggregate sessions. Exclude preview/test conversions. No new tracking changes are authorized by this guide.

## 7. Christian's October time

The three distinct Christian-associated recordings total 184.96 audio minutes after removing a 33-minute duplicate. Fireflies dates are indexing/creation metadata; actual meeting dates and Christian's join/leave duration are not established. Missing recordings or participant metadata can exclude real work. Charles's Calendly account does not cover Christian's calendar.

The separate 6–14.5-hour nonmeeting range is an unconfirmed reconstruction of asynchronous direction, review and coordination. Improve it with a Christian-only calendar export, attendance confirmation and dated work log: entry ID, start/end or minutes, workstream, task/reference, measured versus recalled/estimated basis and overlap note. Mark human retrospective estimates as estimates. Never turn agent runtime, commit intervals or gaps between meetings into labor hours. Do not combine the recording proxy and estimated work into an actual/billable total until attendance and overlap are reconciled. The editable browser assumptions are session-only and do not update GitHub.

## 8. Cross-cutting collection and reporting requirements

For every imported dataset retain source/account, actual collection time, event date range, source timezone, extraction filters, units/currency, record count, pagination status, deleted/test handling and known omissions. In private evidence retain the export or checksum as appropriate; publish a minimal coverage/quality summary, not raw credentials or correspondence. Distinguish collected-at, occurred-at, updated-at and first-observed-at. A successful deployment refreshes the website, not the sources.

Prefer explicit availability states: measured zero, unavailable, partial coverage, historical only and not applicable. Empty arrays or absent daily rows should not automatically become measured zeros. Define per-account/metric coverage rather than one broad envelope when feeds have different dates. Timestamped events use America/Denver for dashboard reporting; already aggregated UTC or New York days retain their source boundaries unless hourly/raw events permit a correct rebucketing.

For conversion rates, define the unit (person, company, submission, booking or deal), entry cohort, eligibility exclusions, observation horizon and as-of date. Keep funnel conversion for a submission cohort separate from bookings occurring in the same date range. Recent cohorts have less time to progress; do not mistake that for worsening quality. Small counts should show their numerator/denominator and uncertainty instead of false precision.

Retain snapshots and event IDs going forward. Source replay/import must be idempotent: no duplicate events, double-counted reschedules or repeated cumulative totals. Partial collection failures preserve the prior successful snapshot with a visible stale/partial label, rather than silently replacing it with zeros. Source coverage dates advance only for a genuinely complete refreshed source window, not because the page was republished.

## Contributor acceptance checklist

1. State which metric becomes more accurate and which source/account/population supports it.
2. Supply exact fields, date coverage, timezone, definitions and confidence; classify unknown outcomes explicitly.
3. Reconcile source totals, deduplicate at the correct entity/event level and list unresolved joins/exclusions.
4. Update only the relevant shared snapshot subtrees and source metadata; avoid advancing other feeds' freshness.
5. Update calculations/normalizers for any new fields. Data additions alone do not make an unimplemented metric work.
6. Verify affected totals, filters, cohort boundaries and absence of false-zero/duplicate behavior; run the shared snapshot checker.
7. Include a short change note and evidence limitations in the pull request. Use a separate owner-approved operational action for CRM/sheet repairs or new tracking; analytical access alone does not authorize them.

Useful source-specific references: CRM_ACTIVITY_REVIEW.md, MEETING_SOURCE_REVIEW.md, REFRESH_REVIEW_2026-10-14.md, OCTOBER_EFFORT_REVIEW.md and TIME_MEETING_REVIEW.md. Historical review documents describe their collection dates; the currently committed snapshot determines what the dashboard actually contains.
