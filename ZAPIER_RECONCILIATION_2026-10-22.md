# Video DM trigger history and CRM reconciliation

The retained 703 held IDs describe Google Sheets trigger entries in a short October 20 burst. They do not establish 703 Video DMs, eligible CRM writes or missing prospect records. The October 21 cohort with valid Loom URLs is fully represented in Pipedrive: all ten profiles and recording asset IDs match their CRM people and deal notes.

| Evidence | Finding | Meaning for the dashboard |
|---|---|---|
| Retained held history | 703 distinct IDs, all labelled Too much data, within October 20 14:56:26–28 Mountain | Technical trigger history; no outreach or missing-record count follows from this number. |
| Six targeted held payloads | Four contain only row identifiers/hash data. Two contain prospect data with blank structured Sent status and blank Loom fields. Filtering and CRM steps were not attempted in any of these six. | None of the reviewed samples establishes an eligible sent-video sync. The targeted sample does not establish the eligibility of every held entry. |
| October 21 dated Sent labels | Twelve distinct worksheet profiles | Self-reported statuses with date-only precision; actual delivery and sender identity are not independently measured. |
| October 21 valid recording URLs | Ten Loom share URLs | These ten match CRM people by exact LinkedIn profile and match the same asset ID in linked deal notes 837–846. Zero missing CRM records in this specific ten-row cohort. |
| Other two October 21 Sent rows | Navigara/Jirka Bachel and Dark Watch/Noel Thomas have a LinkedIn DM note in the recording field, rather than a recording URL | Their October 21 runs stopped at the filter, whose structured Sent field was blank at trigger time. They are retained as reported DM activity; video inclusion and the need for a video-specific CRM sync are unverified. |
| Whole recording column | 60 nonempty cells:57 valid Loom URLs and three text notes | Nonblank recording cells must not all be labelled video assets. The third note is Chromie: “Sent a video DM without loom.” Its actual delivery remains unverified. |

Zapier documents Too much data as flood protection when a trigger receives a large batch. Its Google Sheets guidance also explains that worksheet structure changes can cause unexpected trigger behavior. The observed two-second burst, payloads without eligible Sent data and nearby file revision are consistent with a bulk worksheet-trigger event. The exact edit that caused the burst is not established. [Held-run guidance](https://help.zapier.com/hc/en-us/articles/37454233721869-How-to-troubleshoot-held-Zap-or-step-runs), [Google Sheets guidance](https://help.zapier.com/hc/en-us/articles/8496276985101-Work-with-Google-Sheets-in-Zap-workflows).

The published trigger watches columnQ, Loom Link; the downstream filter reads columnP, Status (CS Column). These are separate source fields. Their different positions alone do not establish a mapping defect. Both reviewed filtered runs had a non-URL note inQ and no data in the filter's Sent field at trigger time.

The 85 retained history pages contain841 entries and 808 distinct run IDs. Thirty-three repeated held IDs occur across adjacent pages with identical timestamps/status. Pagination is non-atomic and tied timestamps can produce repeats or omissions; these are counts of the retained observations, not a certified complete execution census. October 21's ten successful runs align with the ten verified CRM records. No source workflow was changed or replayed.

## Remaining information that improves analytics

| Priority | Required information | Collection approach |
|---|---|---|
| 1 | Charles's latest qualification decisions, original acceptance dates/next steps and actual first-client dates; any held prospect calls outside the accessible roster | Reuse inbox/dialogue/contract evidence. Ask Charles only about unresolved decisions and exceptions, especially Venus. A stage label does not settle the previously agreed definitions. |
| 2 | Message event ID, prospect profile, actual sender, send/reply date and timezone, channel, video included yes/no/unknown, reply meaning and CRM link | Read accessible message/action history first. Supplement with a narrow event export or log where unavailable. A Loom asset and a CRM note establish a join, not a delivery receipt. |
| 3 | Daily Charles Waalaxy invitation, acceptance, message and reply events for October 16 onward, plus account/campaign IDs and source timezone | The fixed October aggregate is already collected. Attempt the daily/action export; request the original file only if direct access cannot produce it. |
| 4 | Complete October personal/company publishing register, metric windows, post IDs, organic/boosted breakdown and ad joins | Use the signed-in source and Ads exports. Current ranked-post data is capped; company metrics after October 20 need a later source refresh after its stated delay. |
| 5 | Dated referral requests, introductions, follow-ups and linked targets/outcomes | Reconcile actual correspondence first; add only missing dated events. A promised introduction or incumbent-provider reply does not establish a completed introduction. |
| Optional measured effort | Christian's actual attendance and dated work durations | Keep14.5–15.75 non-meeting hours as the supplied estimate; recording duration remains separate until attendance/work logs exist. |

Another generic CRM export, another copy of the reviewed76 recordings, and a bulk replay of the held queue are not prerequisites for updating this dashboard. Existing sources already support current inventory, the verified ten-record cohort and explicitly bounded activity metrics. The owner approved publication of the reviewed October 22 curated update to GitHub and Pages; raw evidence remains private. See [the publication review](PUBLICATION_REVIEW_2026-10-22.md).
