# October 21 refresh — local review

The refreshed dashboard is prepared locally. It has **not** been pushed to public GitHub or GitHub Pages. Publication of the private creator analytics still requires explicit approval following the earlier automatic approval-review rejection.

The default view covers October 19–21, Mountain time, with October 21 partial. Month-to-date and complete-day presets are available. Each source retains its own collection time and date boundary. Preparing this update does not refresh an older source.

## Evidence applied

| Source | Refreshed evidence | Boundary |
|---|---|---|
| LinkedIn Ads | Current all-seven-ad-set browser view: $3,592.31 spend, 25,055 impressions, 106 clicks, four source-reported submissions and 62 form opens, September 4–October 22 UTC. | Final UTC day partial. Daily CSV download stalled; retained daily charts still end October 16. Five platform conversions / one platform appointment are tracking events, not verified commercial outcomes. |
| Charles creator | Verified signed-in Charles Chrome profile; all 90 cumulative impression points July 25–October 22 UTC; 58,532 impressions, 32,032 unique members reached, 543 social engagements. | October 22 UTC partial; collected October 21 Mountain. Daily impressions derived; fixed-window reach/social totals not allocated to days. Three top posts are a sample, with publication dates unavailable. |
| Video DM Sheet | 428 valid rows / 420 valid unique profiles; 45 ready, 62 helper-classified completed, 41 follow-up, 58 sync flags. | Blank/helper rows excluded. Exact Sent/Done statuses remain 29. Loom URLs, helper classifications and sync flags do not independently verify delivery/sync. |
| Dated sheet statuses | Twelve Sent statuses October 21, two follow-up statuses October 21, one email-send status October 19. | Self-reported current Sheet values; incomplete activity history. Video content, channel and delivery unverified. |
| Waalaxy selected people | Live Sheet: 168 connected people. Separate October 20 CSVs: 206 selected people. | 167 overlapping profiles; never sum the populations. Sender ID/upstream sync unverified. Person attributes are not message/reply event counts. |
| CRM browser | Raw open-view inventories: 377 Leads, 42 Sales, 348 Referrals; fifteen visible IDs absent from the retained export. | Partial visible-card collection, with tests/duplicates. Complete October 16 deal/activity snapshot and October 15 reporting cutoff retained. New observation is not a created record, send, held call, accepted opportunity or win. |
| Christian effort | Reporting scope through October 21; owner estimate 14.5–15.75 hours unchanged. | No new attendance/time source collected. Five deduplicated recordings total 228.58 audio minutes, last collected October 16. No incremental hours or combined worked-hours total inferred. |

Current company-page private content performance, account-wide Waalaxy activity and fresh Calendly/Fireflies history remain incomplete.

## Highest-level outcomes

Four Charles-only cards precede the channel cards: held prospect calls, unique qualified companies among those calls, explicitly accepted new opportunities with a next step, and first-time clients won. Different event cohorts and units mean these are not a conversion funnel.

The bounded confirmations remain NuVee on October 6 (qualified/warm) and Venus Ai Consulting on October 15 (unqualified). October month to date has **at least two confirmed calls / at least one qualified company**. The complete October 19–21 call roster, accepted opportunities and first-client wins remain unknown. Empty incomplete evidence displays Pending rather than zero.

## Highest-impact missing inputs

1. **Charles meeting/outcome register, October 1–21.** Company/contact; actual held date/time/timezone; Charles participation; prospect/client/partner/internal purpose; held/canceled/no-show; qualification/reviewer/date; original opportunity acceptance date and active next step; first-client win date. Stable calendar, recording and CRM IDs deduplicate meetings. Explicit complete-period confirmation is needed before zero is meaningful.
2. **Pipedrive exports, all owners/pipelines/actual statuses.** Deal ID, organization/person IDs, commercial owner, pipeline/stage, actual status, created/updated/stage-changed dates, won/lost dates, amount/currency, source/channel/campaign and next activity. Also export both done and undone activities: ID/type, owner, linked deal/person/organization, created/updated/due/marked-done timestamps and outcome. Structured change history is needed for progression; latest-update dates do not reconstruct it. Chrome blocked the generated deal-export download during this collection.
3. **Current Calendly and Fireflies evidence.** Event/recording IDs, actual occurrence dates, event lifecycle, cancellation/reschedule links, participants, duration, purpose and CRM IDs. Include Christian's attendance for effort. Recording index/upload time is not occurrence time; booking status is not attendance. Relevant permissioned summaries can resolve purpose without publishing raw transcripts.
4. **Waalaxy account/campaign activity.** Sender/account ID, source timezone/extraction time, campaign/list IDs, invitation/message/reply action IDs and dates, positive/negative reply classification and CRM joins. Invitation export ends October 15; selected-person snapshots cannot establish later account totals or cohort acceptance rates.
5. **Company-page and paid/boosted post detail.** Daily/per-post analytics, publication dates, post IDs/URLs, organic versus sponsored delivery, social actions/clicks, spend and campaign/creative IDs. Charles's impression gap is filled; current daily social and company data remain incomplete. Reconcile boosts with Ads before summing results.
6. **Video DM action logging/connection verification.** Actual send/follow-up dates, channel, recording ID, recipient/profile ID, reply date/outcome, held-call/CRM links and successful sync IDs. Thirty-three accepted Video DM profiles lack acceptance dates. The live helper intentionally keeps them at Verify connection; this is missing evidence, not a demonstrated formula error.
7. **Referral and effort events.** Request/introduction dates, partner, prospect, CRM ID and Charles's qualification/acceptance/win decision; Christian's additional attendance and work log after October 16. Current relationship stages and an owner estimate do not establish dated actions or actual hours.
8. **Ads daily export.** Campaign Manager account 515259390: Ad Set Performance, All columns, broken out by day, September 4 through the newest available reporting day. Include all seven ad sets, currency/timezone and report generation time. Add creative/post IDs and current lead details where permitted. Fresh aggregates cannot allocate the additional spend/impressions to individual later days.

## Repeatability and publication

Ignored raw sources and review candidates reside in `data/private/refresh_2026_10_21/`. The curated snapshot excludes raw transcript bodies, source Sheet free-text notes, emails, phone numbers and credentials. Normalizers retain counts, hashes and source boundaries. `tools/apply_refresh_2026_10_21.py` assembles patches, reapplies canonical owner decisions and marks publication pending. Older imports preserve newer supplements and the publication hold.

GitHub remains the shared application/data source of truth. The ChatGPT Sites mirror was not updated. The public site remains on its last approved GitHub commit until publication approval is resolved.
