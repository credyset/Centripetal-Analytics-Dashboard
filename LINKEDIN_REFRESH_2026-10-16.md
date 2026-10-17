# LinkedIn source refresh review — October 16, 2026

Read-only collection is complete. This review prepares isolated refresh files; it does not apply or publish dashboard changes.

## LinkedIn Ads

Authenticated account: **515259390**, linked to Centripetal company page **66767979**. New ad-set and creative daily exports were generated **October 17 at 00:51 UTC / October 16 at 18:51 Mountain**.

**Coverage: September 4–October 16, 2026, UTC.** October 16 UTC had ended at collection. October 16 Mountain was still in progress. Daily buckets retain the platform timezone; they cannot be accurately rebucketed into Mountain days without hourly data. Figures can restate.

**Totals:** $3,328.98 spent; 23,206 impressions; 100 clicks; 59 form opens; 4 submissions; 1 owner-qualified lead.

| Variant | Objective | Spend | Impressions | Clicks | Opens | Submissions |
|---|---|---:|---:|---:|---:|---:|
| A | Lead generation | $433.35 | 2,309 | 9 | 4 | 0 |
| B | Lead generation | $158.96 | 693 | 3 | 2 | 0 |
| C | Lead generation | $1,000.00 | 6,431 | 34 | 31 | 3 |
| D | Lead generation | $870.15 | 4,603 | 23 | 22 | 1 |
| E | Website visits | $866.52 | 9,170 | 31 | 0 | 0 |

Compared with the retained October 14 snapshot: **+$128.05 spend, +1,087 impressions, +0 clicks, +0 submissions.**

The two fresh exports agree on totals. They contain **106 ad-set daily rows, 107 creative daily rows, 43 calendar buckets, five delivered ad sets and six ads**; row keys are unique.

**Lead quality:** NuVee remains qualified/warm and Venus Ai Consulting remains unqualified. No fresh qualification or meeting outcome is inferred from ad conversion counts. Fresh lead detail downloads remain blocked by LinkedIn Company Page / Lead Gen Forms manager permissions. Retained lead sources contain four unique submission IDs; the platform count remains four.

## LinkedIn content

**Current public followers:** Charles Solomon **11,486**; Centripetal company page **867**. These are net increases of **21** and **15** from the October 14 observations, not daily follower acquisition counts.

**Fresh public content sample:** 20 visible Charles post containers and 7 Charles posts reposted by the company. One known overlapping post is deduplicated, leaving 26 displayed post observations. New Charles activity includes today’s CAC/pro forma posts, shown as 3h and 4h old at collection. The company feed was sorted Recent.

Public reaction, comment and repost counters are point-in-time observations. Missing counters remain null. Relative publication labels remain relative; publication dates are not invented. The sample does not establish total publishing cadence or period-specific engagement.

**Private analytics remain historical:** latest verified Charles export covers September 11, 2025–September 10, 2026; company page export covers April 22–July 20, 2025. No newer private Charles/company content workbook was found in the inspected local sources. Current authenticated browser is Christian Wutz, so Charles renders as a non-self profile and the company page renders visitor controls. Current private impressions, reach, clicks and organic/boosted breakdown were unavailable.

## Prepared files and application guidance

- `data/ads_refresh.json`: updated campaign/ad daily metrics, objectives, source timing and reconciliation checks.
- `data/content_refresh.json`: retains historical private analytics and adds separate October 16 public observations.
- Raw downloads and browser evidence stay under `data/private/channels/2026-10-16/`; do not publish or commit raw exports.
- Existing `ads.json`, `content.json`, application code and shared dashboard snapshot were not changed by this review.
- Apply owner-confirmed held-call status in the CRM/meeting reconciliation step separately; the paid platform appointment column is not that confirmation.
