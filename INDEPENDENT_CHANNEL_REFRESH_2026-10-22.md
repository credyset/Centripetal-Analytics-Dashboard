# Independent channel refresh — October 22, 2026

**Review state:** source collection, reconciliation and local integration validated October 22. The GitHub Pages workflow and actual served files establish publication state separately from this source review.

The owner supplied an updated Waalaxy actions CSV, requested actual Video DM send/reply dates where accessible and asked whether creator/Ads exports were still needed. Commercial outcomes are reserved for the owner's manual review with Charles. No commercial decision or effort-hour change is inferred by this refresh.

## Waalaxy invitations

The owner-supplied `invitations (5).csv` has `Date`, `Accepted` and `Sent` columns with 31 contiguous source-date buckets from September 22–October 22, including explicit zero rows. It contains no account ID, source timezone, message sends or reply events. Account attribution follows the user's Charles-only dashboard context; the CSV itself does not independently authenticate the account.

| Scope | Sent | Accepted |
|---|---:|---:|
| Latest CSV: September 22–October 22 | 430 | 132 |
| October 1–22 | 430 | 132 |
| October 19–22 | 59 | 22 |
| Earlier retained source: September 15–21 | 31 | 17 |
| Composite retained series: September 15–October 22 | 461 | 149 |

October 22 is partial. Source-day labels are preserved without Mountain/UTC rebucketing. All October 19–22 nonzero counts occur in October 19's bucket. The new CSV replaces overlapping date buckets, preserving earlier September days with their prior provenance rather than adding the old and new exports together.

Four Accepted buckets were restated:

| Source bucket | Prior Accepted | Latest Accepted |
|---|---:|---:|
| October 5 | 17 | 18 |
| October 7 | 17 | 19 |
| October 12 | 29 | 34 |
| October 13 | 9 | 14 |

These revisions total +13 across overlapping buckets. They do not establish 13 new acceptance events during this refresh or the exact dates those acceptances occurred. There is no linked invitation/prospect cohort in the CSV, so no matched-cohort acceptance rate is inferred.

The October CSV totals match the retained authenticated Home aggregate numerically: 430 invitation actions and 132 reported acceptances. They are overlapping measurements. The Home counters of zero platform message actions and two answered messages retain their separate fixed October window; they do not describe every manual LinkedIn message, unique replying prospect or qualified reply.

The invitation family has its own collection date, coverage, overlap review and source card. Replaying an older generic Waalaxy import must preserve these fields and invitation date buckets without refreshing historical people or overwriting unrelated daily measures.

## Actual Video DM message dates

All ten October 21 worksheet profiles with Loom URLs were already matched to exact CRM people and recording assets. Native Charles LinkedIn conversations were inspected for those ten profiles:

- **Nine** show an outbound message containing the exact corresponding Loom asset. A visible Wednesday label, anchored to the October 22 review and corroborated by the worksheet date, establishes **October 21 at day precision**. This verifies a sent platform message, not recipient delivery, a video view, a reply or a commercial outcome.
- **SubImage** remains source-reported Sent with a matching CRM asset, but its platform send is **unconfirmed**. The correct reviewed conversation ends with February 3 text outreach and does not expose the referenced October Loom asset. This does not establish non-send or deletion.
- No inbound reply after the nine matching videos was visible in this bounded conversation review. This is not an account-wide reply census or a verified zero for all Video DMs.

The nine observations corroborate existing worksheet sends; they must not be added as nine more sends. The separate Cypher incoming message has a visible Monday label anchored to **October 19**, while the retained Waalaxy latest-reply attribute says **October 20**. Both source dates remain visible. No timezone conversion, video-reply attribution or commercial outcome is inferred. Any separately observed outbound text context is also kept outside video-send totals unless video evidence is present.

Native observations expose local display labels/times without a source timezone or stable message/conversation IDs. Exact timestamps remain unavailable; no midnight UTC events are fabricated. Existing Sheet/CSV first/last-message and reply attributes remain source attributes rather than a complete event history. Raw message text, conversation screenshots and private proofs remain outside the published payload.

## Charles creator performance, independently refreshed

A fresh actual workbook was downloaded through the owner-designated signed-in Charles Chrome account. The source window remains **July 25–October 22, 2026 UTC**, with October 22 partial. It is not rebucketed into Mountain days.

| Metric | Latest source result | Scope / definition |
|---|---:|---|
| Impressions | 59,495 | Fixed 90-day source window |
| Unique members reached | 32,579 | Unique within the fixed window; not summed daily |
| Social engagements | 549 | UI social-action definition |
| Workbook Engagements | 559 | Broader export definition; kept separate from social-only actions |
| Followers | 11,558 | Current source stock, not additions during the window |
| Ranked posts | 49 | Capped ranked subset, not a complete publishing register |

| Selected source dates | Impressions | Broader workbook Engagements | New follower additions |
|---|---:|---:|---:|
| October 19–22 | 2,568 | 32 | 72 |
| October 1–22 | 19,911 | 267 | 315 |

The daily additions are not net follower growth. The selected-period headline uses the corresponding daily source rows; the fixed unique-reach total is not redistributed or summed. No additional aggregate creator export is needed now. Complete publishing coverage and post-level organic/boosted joins remain separate collection work.

## Company-page source availability

The company analytics date controls were checked independently. **October 20 is the latest selectable date; October 21 and October 22 are disabled.** Existing company daily data therefore remains unchanged. The source's delay is a coverage boundary, not two new zero days. A future refresh should collect the later dates when the platform makes them available. Company-sponsored measurements overlap the same Ads delivery and are not added to Ads totals.

## Ads conclusion and retained totals

The current authenticated Campaign Manager view shows **all seven ad sets Completed**. The checked September 4–October 22 aggregate matches the retained source totals:

| Spend | Impressions | Clicks |
|---:|---:|---:|
| $3,592.31 | 25,055 | 106 |

The retained daily export still ends **October 21 UTC**. The requested range through October 22 does not create an October 22 row, verify a zero for that day or extend the earlier exported daily evidence. The concluded lifecycle observation and unchanged aggregate do not require another generic Ads export. Retain a later final daily adjustment only if the source exposes changed delivery totals or newly available rows.

## Remaining work and boundaries

- Commercial attendance, qualification, original opportunity acceptance and first-client decisions stay with the owner's Charles review. Existing Pending/minimum outcomes remain unchanged.
- Waalaxy daily invitation buckets are now available through October 22 partial. Dated message/reply actions, positive-reply classification, campaign IDs and source timezone remain incomplete.
- The Video DM message review covers the identified ten-profile cohort plus separate context. It is not an account-wide sent/reply event census; SubImage and exact timestamps remain unresolved.
- Creator aggregate/daily performance is refreshed. A complete publishing census and post-level organic/boosted attribution are not supplied by the capped ranking.
- Company dates after October 20 await source availability. A manual export from the same currently disabled date controls is not a useful request.
- Christian's non-meeting estimate remains **18.25–19.5 hours**; the recording proxy remains separate and unchanged.

No source system settings or outreach messages are changed by this review. Raw files remain in ignored `data/private/`. See [the remaining-data checklist](MANUAL_DATA_REQUEST_2026-10-22.md) for narrow follow-up needs and [the publication policy/review](PUBLICATION_REVIEW_2026-10-22.md) for the approved destination. Local checks cover source reconciliation, duplicate and missing-value handling, message attribution, commercial/effort preservation and the approved publication build. Live deployment requires a successful Pages run and matching served files.
