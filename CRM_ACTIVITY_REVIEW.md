# Pipedrive activity and progression assessment

Collected October 14, 2026, 09:03 PM MDT (2026-10-15T03:03:19Z). Read-only; no production records changed.

## What the fresh read establishes

All accessible non-deleted deals were read in two 500-record pages, and both done/undone activity collections were read with `user_id: 0` to cover all accessible owners. The prior snapshot was preserved in `data/history/20261015T013413Z/` before replacement. Current source inventory remains **722 deals and 923 activities**. Four clearly test-labelled deals (178, 752, 754, 787) and five test activities (1062, 1063, 1064, 1065, 1089) are excluded from business summaries. Deal 178, `Organization_NurtureTEST`, was missed by the earlier boundary-only test matcher; its exclusion is a definition correction, not a newly deleted business record.

Business inventory is **718 deals, 716 open-status records, one won-status record and one lost-status record; 918 activities**. The separately queried Leads Inbox is empty in both active and archived collections. Deals in the Leads Pipeline are not Leads Inbox records.

The principal finding is a measurement gap: **recent deal maintenance and some real stage changes exist, while activity completion recording is stale.** Zero recent CRM completions cannot be interpreted as zero outreach, calls or business-development work. Calendar records and channel systems must remain separate evidence sources.

## Activity inventory and backlog

| Activity type | Records | Marked done | Undone | Overdue | Future |
| --- | --- | --- | --- | --- | --- |
| call | 156 | 146 | 10 | 9 | 1 |
| email | 205 | 169 | 36 | 36 | 0 |
| linkedin_touch | 91 | 11 | 80 | 80 | 0 |
| meeting | 1 | 1 | 0 | 0 | 0 |
| task | 465 | 219 | 246 | 246 | 0 |


| Owner | Records | Marked done | Undone | Overdue |
| --- | --- | --- | --- | --- |
| Alex | 22 | 22 | 0 | 0 |
| Charles Solomon | 9 | 0 | 9 | 9 |
| Christian W | 887 | 524 | 363 | 362 |


There are **372 undone business activities: 371 overdue and one future activity**. No undone record lacks a due date. Overdue age: 24 are 8–30 days late, 157 are 31–90 days late, and 190 exceed 90 days. None is 1–7 days late. This is a legacy scheduled-task backlog requiring triage, not proof of 371 currently missed commitments. Distinguish valid follow-ups from obsolete sequence tasks before acting.

**178 activities lack a deal link (19.4%); 24 lack all deal, person and organization links.** A missing deal link does not necessarily mean no contact attribution. No business activity links to a deal missing from the current accessible business inventory. Created dates, due dates and completion dates on done records are populated in this source read.

Latest legitimate created activity is **1090**, a `call` task titled “Followup in 6 Weeks (Norm Katz - Nuvee )”, created October 6 and due **November 17**. It is the only future unfinished business activity and is linked to NuVee deal **788**. It is a follow-up task, not proof that a November appointment was accepted. Latest legitimate recorded completion is LinkedIn-touch activity **1057** on **August 19**, followed by task **592** that same day. September's latest inventory completion belongs to test data and is excluded.

## Recent time windows

| Window, Mountain dates | Created activities | Automation-linked creations | Marked done | Call tasks created | Call tasks due |
| --- | --- | --- | --- | --- | --- |
| last7CompleteDays: 2026-10-07–2026-10-13 | 0 | 0 | 0 | 0 | 0 |
| last30CompleteDays: 2026-09-14–2026-10-13 | 24 | 23 | 0 | 1 | 0 |
| last90CompleteDays: 2026-07-16–2026-10-13 | 231 | 33 | 215 | 6 | 5 |
| currentWeekToDate: 2026-10-12–2026-10-14 | 0 | 0 | 0 | 0 | 0 |


The last 30 complete days are September 14–October 13. They contain **24 activity creations: 23 automation-referenced tasks and the one NuVee follow-up call task; zero business completions**. All 24 are assigned to Christian. No activity was created in the last seven complete days. The 90-day view contains 231 creations and 215 completions; its older completions should not obscure the August-to-October recording gap. Calls due, call tasks created, and records marked done measure different dates and populations. None by itself establishes a booking or attendance.

Raw activity metadata has **38** `reference_type=automation` records; five are test activities. Business inventory therefore has **33 automation-referenced activities**, ten marked done and 23 overdue. A null reference type is “no automation reference supplied”, not proof of human creation. Do not attribute every updated deal to automation merely because some update timestamps align with workflow activity.

## Snapshot comparison

Baseline: **2026-10-15T01:34:13Z**; current: **2026-10-15T03:03:19Z**, both October 14 Mountain time. There are **no newly observed or missing deal IDs and no newly observed or missing activity IDs**. No compared activity status, owner, type, due date or deal link changed. Two deal records—**495 Michael Merritt** and **762 Shalom Reinman**—have later `updatedAt` timestamps. Compared stage, pipeline, status, value, owner and next/last-activity fields did not change. This establishes record maintenance, not commercial advancement or a known automation cause.

Historical “deals updated in a period” remains a count of records whose **latest retained update** falls in that period. It is not a full count of all deals touched during that period. The last-30-day retained figure remains **43 new deals and 108 latest-updated records**.

## Observed stage changes, with bounded coverage

A structured-only flow review covered **44 current deals**: all 35 current Sales Pipeline deals, four recent opportunity/referral records, and five Leads Pipeline records in Intro Call Scheduled. Every reviewed deal completed its flow pagination in one page, with per-deal coverage retained. Of 102 observed stage/status/pipeline change records over all returned history, **33 stage changes dated September 1 onward** were retained. Non-change notes, mail content and correspondence were discarded and never persisted in the history files. This is complete for the explicitly reviewed accessible flow scope; it is **not account-wide history**. No generic numeric-stage-order rule classifies a change as forward progression.

Concrete examples:

- **NuVee 788:** Intro Call Scheduled → Call Complete on October 6; Call Complete (Leads Pipeline) → Parking Lot (Short Term, Sales Pipeline) on October 11. The source now supports those recorded transitions, while the stage label alone does not independently verify attendance. Follow-up activity 1090 remains due November 17.
- **XCaliber Health 750:** Intro Meeting → Follow-up / Need Analysis September 23; → Parking Lot (Long Term) October 5; → Negotiating Contract about 21 minutes later that same day. It is currently negotiating, with no unfinished linked CRM task. The intermediate reclassification should remain visible.
- **OneFlo 196:** Parking Lot (Long Term) → Intro Meeting September 2; → Negotiating Contract September 7 Mountain time; → Closed Won stage September 10. Its deal status remains **open**. A second OneFlo record, **165**, moved from Hightouch Manual into Closed Won stage September 28 and also remains open. Neither is a verified won client or recognized revenue from this read.
- **Big Interview 283:** Parking → Negotiating September 3, then back to Parking October 6 and shorter-term parking October 11. Nimbl 444 and H3ir 445 also moved from working stages into parking. Such changes should not inflate commercial-progress counts.
- **Melanie Ortiz 761:** Inner Circle → Intro Promised October 1; → Intro Made October 14. **Jonathan S. Katz 793:** Centripetal Amigos → Intro Promised October 12. These are observed referral milestones rather than accepted Sales Pipeline opportunities.

All five scheduled-stage Leads records—**755, 756, 757, 791, 796**—were created directly in their current stage and have no later structured stage transition. Their stage positions cannot be reconstructed as historical booking events. Predictable Labs appears twice (755 and 756) with different scheduled-call dates, requiring booking/person-level deduplication rather than blindly counting two independent prospects.

## Sales follow-up and outcome hygiene

Current Sales Pipeline inventory has **35 open-status records**, comprising **19 in Closed Won/Lost-labelled stages, 14 in parking, and two in working sales stages**. The 19 status/label conflicts are not 19 verified outcomes. The sole actual won-status record in the complete CRM inventory is **engin sciences inc, deal 162**, in the Leads Pipeline/Graveyard, won August 19 Mountain time. Its status does not establish a new retained client or revenue. All open deal values are zero/unpopulated; show valuation as unavailable.

The two working Sales records are **XCaliber Health 750** (Negotiating Contract, nine days at current stage) and **Menos AI 795** (Intro Meeting, created October 13). Both lack a future linked CRM activity. That is a visible next-step scheduling gap; recent email or calendar interactions may still exist elsewhere. Among 14 parking records, only NuVee has a future CRM task. Agree reactivation dates for genuinely live parking records rather than treating every parking record as an active opportunity.

## Custom date fields and source gaps

| CRM custom field | Populated business deal records | Latest date where applicable |
| --- | --- | --- |
| Scheduled Call Date | 65 | 2026-10-22 |
| Last Call Date | 8 | 2026-03-24 |
| Last Calendly Meeting | 17 | 2025-09-11 |
| Calendly Meetings Completed | 18 | Not an event-date field |
| Meeting Outcome | 7 | Not an event-date field |
| Has Fireflies Transcript | 169 | Not an event-date field |


`Scheduled Call Date` is populated on 65 business records, including NuVee October 6, Venus AI October 15, and Quantex Health October 22. It is a latest/current field with no booking creation timestamp, cancellation history or stable appointment ID. It is richer than the activity due-date log for those calls, but cannot replace deduplicated calendar events. Last Call Date and Last Calendly Meeting are visibly stale. A “Has Fireflies Transcript” enum flag is a pointer for verification, not proof that an identified transcript confirms the specific meeting.

## Recommended dashboard and operating steps

1. Show activity **created**, **marked done**, and **due** separately; add type, owner and explicit automation-reference filters. Preserve source task titles and IDs, without correspondence bodies or contact addresses.
2. Present the overdue queue as a dated backlog with aging and sequence/task context. Have the team resolve obsolete scheduled tasks and identify current commitments before drawing execution conclusions.
3. Surface XCaliber and Menos next-step gaps, and retain NuVee's November 17 follow-up. Resolve the OneFlo duplicates and the 19 open/terminal-stage-label conflicts with the CRM owner.
4. Show observed stage events with reviewed-scope coverage; distinguish parking, administrative reclassification, referral milestones and working sales transitions. Agree the advancement map before publishing a progression KPI.
5. Use calendar booking IDs and creation/scheduled/cancellation timestamps for booking analytics. Keep held-meeting verification separate and join transcripts or explicit dispositions where available.
6. Keep snapshot comparison separate from event history. Repeated daily snapshots can track newly observed records and position changes going forward, without inventing earlier history.
7. Fill usable opportunity values and document their basis before enabling commercial pipeline valuation. Preserve missing values rather than presenting an apparent zero-dollar pipeline.

Prepared data is `data/crm.json`; the repeatable normalizer is `tools/prepare_crm.py`. Raw snapshots and the preserved baseline stay outside published assets. Fresh source collection is verified here; unattended scheduling has not been installed.
