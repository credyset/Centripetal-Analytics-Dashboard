# Referral Pipeline reconciliation — October 16, 2026

Fresh collection: **2026-10-17T00:31:49Z**. Source: verified Pipedrive Referral Pipeline **4**. Main CRM remains at **2026-10-15T03:03:19Z** and was not changed.

## Reconciled partitions

| Partition | Records | Exact stage / policy |
| --- | ---: | --- |
| Active non-test-labelled records | 60 | Open records outside stages 38 and 40 and explicit test titles |
| Office Hours | 245 | Stage 38 |
| Graveyard / Newsletter | 40 | Stage 40 |
| Explicit test records | 3 | 752, 754, 787 |
| Total source Referral Pipeline | 348 | Mutually exclusive union |

**348 = 60 + 245 + 40 + 3.** Non-test-labelled business inventory is 345; all 348 source records currently have open status. Active is an inventory definition, not a claim of engagement, qualification or period introductions.

## Complete collection and filter correction

The connector accepted `pipeline_id=4` but returned records from pipelines 1, 2 and 4. Both returned pages (500 + 255 rows) were read to completion, then the verified pipeline ID was applied locally. The resulting 348 Referral Pipeline IDs are unique. All fifteen exact Referral Pipeline stages were retrieved, including zero-count stages. Source pagination and a SHA-256 of curated normalized source records/stage metadata are retained in the derived dataset. No source-system write was performed.

| Active current position | Records |
| --- | ---: |
| Centripetal Amigos | 14 |
| Centripetal Circle | 32 |
| Intro Promised | 2 |
| Opportunity ( Referred ) | 2 |
| Inner Circle | 9 |
| Intro Made | 1 |

## Earlier-import corrections

The previous import claimed 137 total, 52 active and 105 excluded; the latter two sum to 157. That account is internally inconsistent before any comparison with the live source.

- **454 Robert Adelson:** Office Hours, stage 38. Removed from the active referral list.
- **761 Melanie Ortiz:** current Intro Made, stage 29. The prior list incorrectly used Inner Circle, stage 39. Retained structured history records Intro Promised → Intro Made on October 14; the earlier shorthand “Centripetal Circle → Intro Made” is not the exact observed transition.
- **793 Jonathan S. Katz:** current Intro Promised, stage 28. Now included; omitted from the prior active record list.
- **203 Christian Wutz:** its organization is test-labelled but its deal title is not. Retained in the active inventory and flagged for owner confirmation, preserving the existing explicit-deal-title test rule. It is not silently certified as a qualified referral.
- Current active IDs absent from the previous list: 601, 613, 626, 631, 749, 792, 793, 800, 801.
- 8 prior listed records have a different current stage. Individual IDs and old/current stages are retained in `priorImportComparison.stageMismatches`.

## Fresh referral scope versus older CRM

The older main CRM snapshot has 346 Referral Pipeline records; current collection has 348. Fresh IDs absent from that older inventory are 800, 801. These are now-current referral records, not proof of newly qualified leads or current-month introductory meetings. The 755 mixed-pipeline source rows were used only to complete this referral collection; the full main CRM dataset and headline inventory were not refreshed.

## Movement and automation evidence boundaries

Two observed structured stage events are preserved with their original source snapshot date: Melanie Ortiz, Intro Promised → Intro Made on October 14, and Jonathan S. Katz, Centripetal Amigos → Intro Promised on October 12. They come from retained October 14 history and were not re-created from the current stage snapshot. No additional period progression, introduction or qualification is inferred.

The read-only automation-list endpoint returned Not Found. Accordingly the reported 30-day touchpoint cycle and Pipedrive/Trello synchronization claims are **not independently verified**. They are retained only as reported claims; cycle and operational synchronization status are not asserted.

## Reproducibility and checks

`tools/reconcile_referrals.py` rebuilds partitions and reconciliation diagnostics from the curated retained snapshot in `data/referral_reconciliation.json`. It never writes to Pipedrive. Assertions verify unique IDs, pipeline identity, all 15 known stage IDs, disjoint active/excluded populations, complete stage totals and the 348 = 60 + 245 + 40 + 3 identity. No email addresses, phone numbers, notes or correspondence bodies are included in the curated records.
