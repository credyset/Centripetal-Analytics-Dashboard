# CRM refresh — October 16, 2026

Collected **October 16, 2026, 06:52 PM MDT** (2026-10-17T00:52:01Z). Read-only source collection. No Pipedrive records were changed. Refreshed data is held separately for parent integration; the earlier `data/crm.json` remains preserved.

## Complete current source scope

- 755 unique accessible non-deleted deals: pages 500 + 255.
- 924 unique activities across accessible owners: 547 done and 377 undone. Both activity states were explicitly requested with user_id 0; response owner IDs were checked.
- Three pipelines, 33 stages, nine activity types, five configured users and 82 deal fields read.
- Four explicit test deals (178, 752, 754, 787) and five test activities excluded from business reporting. Record 203 retains its organization test-label review flag and remains included pending owner confirmation.
- Business reporting: 751 deals (749 open, one won, one lost) and 919 activities.
- Reporting cutoff: October 15 complete Mountain day; October 16 is current-day partial.
- The old normalized CRM and old source/history manifest were backed up under `data/private/crm_refresh_2026-10-16/baseline/`. Fresh source files have independent manifests and hashes.

## Changes since October 14 source snapshot

- 34 newly observed deal IDs, one no-longer-observed ID (756, previously Predictable Labs). This is not proof of deletion; visibility or record consolidation requires separate confirmation.
- 28 retained deal IDs have changed compared fields; 20 have different current stage positions. No compared deal status changed.
- One newly observed activity, 1091: Charles’s monthly Centripetal Circle touchpoint for Dana Billsky Asher, created and due October 16, with an explicit automation reference. No previously compared activity completion, type, due date, owner or deal link changed.
- New stage 43 is Video DM Outreach in Leads Pipeline; stage 44 is New Lead in Sales Pipeline. Current business inventory has 44 records in Video DM Outreach. Stage membership does not establish an actual Video DM send.
- Normalized-title review groups include Venus AI (791, 805), Menos AI (795, 799, 818), Talvy (806, 831), and furl (808, 830). Organization IDs are retained. These are review flags, not automatic entity merges; record creations are not necessarily net-new companies.

## Activity and dated-window assessment

- Business activity inventory: 546 marked done; 373 undone, comprising 371 overdue, 1 due today, and 1 future activity. No undone activity lacks a due date.
- 34 business activities carry an explicit automation reference. A missing reference does not prove manual creation.
- Latest legitimate recorded completion remains August 19. That is a CRM recording gap, not proof of no later meetings or outreach.
- Last 30 complete days, September 16–October 15: 44 new deal records, 111 records whose latest update falls in the window, 24 created activities and zero legitimate recorded completions. Latest-update metrics do not reconstruct every earlier edit.
- October 16 activity 1091 belongs only to current-day partial reporting, not the complete-day metrics. NuVee’s existing activity 1090 remains due November 17.

## Valuation correction

**The earlier “all open values are unpopulated” statement is no longer current.** Three open Sales/Intro Meeting records now carry nonzero source-entered values:

| Deal ID | Source title | USD value |
| --- | --- | ---: |
| 802 | Aethon Aerial Solutions | 10,000 |
| 803 | Aethion Sister Company | 6,000 |
| 804 | Norther Ontario Company | 4,000 |

The known portion totals **$20,000 across three of 749 business open records**. The other 746 have zero or unset values. Valuation basis is unverified; this is not a complete qualified pipeline valuation, contracted value or recognized revenue. Nineteen open-status records still occupy Closed Won/Lost-labelled stages.

## Retained history versus current records

Current deals and activities were freshly collected October 16. The 33 retained structured stage events across a 44-deal subset were collected October 14 and are explicitly labelled with their original source timestamp. No new history was invented from the 20 current-position differences. Scope remains partial, and numeric stage order is not interpreted as forward commercial progress.

## Referral coherence

The refreshed Referral Pipeline is derived from this exact full-CRM source snapshot. It reconciles **348 = 60 active + 245 Office Hours + 40 Graveyard/Newsletter + three explicit tests**. The same 348 IDs occur in refreshed CRM and refreshed referrals. The two outputs share their snapshot timestamp and should be integrated together. Current positions remain inventory; Opportunity (Referred) is not independent qualification.

## Owner confirmations and evidence layers

This collector does not infer qualification or attendance from a stage, a scheduled activity, or a completion flag. The parent workflow has separate current owner confirmation that NuVee’s October 6 call and Venus’s October 15 call were held; those confirmations must be retained with their own provenance in the meeting/outcome layer. Owner confirmation can establish held status even when no matching CRM activity was completed. It does not automatically change qualification or create opportunity/revenue evidence.

## Prepared outputs and checks

- `data/crm_refresh.json`: fresh normalized CRM, current activity/valuation diagnostics, comparison to preserved baseline, and explicitly dated retained history.
- `data/referral_refresh.json`: same-snapshot referral partitions and curated records.
- `tools/refresh_crm_snapshot.py`: repeatable normalization and reconciliation from retained fresh private snapshots.
- Assertions cover unique IDs, completed pagination, test exclusions, source-date boundaries, same-snapshot referral ID equality, no embedded email addresses, and preservation of the original main CRM/baseline files. No notes, correspondence bodies, phone fields or contact emails are published in these curated outputs.
