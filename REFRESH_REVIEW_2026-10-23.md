# Live-source refresh — October 23, 2026

**State:** independent collection and reconciliation are complete for the accessible sources below. The curated snapshot and application passed source, display, preservation and publication checks. GitHub Pages publication is verified separately after deployment; automatic source refresh is not enabled.

The reporting frame is October 23 in `America/Denver`, with October 22 the last complete Mountain day. Collection occurred during the evening of October 23 Mountain and therefore carries actual October 24 UTC timestamps. UTC-aggregated source days remain UTC source days.

## Completed source collection

| Source | Reconciled result | Scope and limits |
|---|---|---|
| Pipedrive | 780 accessible non-deleted deals; 924 activities, including 776 business deals and 919 business activities | All returned deal pages and both activity states across accessible owners were exhausted. Collection completed October 24 at 03:11:09 UTC. This is a paginated inventory, not an atomic event history. |
| CRM differences | 11 new records; nine retained records changed; no activity inventory changes | Compared with the preceding October 22 census. Five observed stage changes were read from the selected histories; stage changes do not establish attendance or commercial acceptance. |
| Current-week CRM | October 19–23: 26 created records / 42 records whose latest update falls in the window | All accessible business-record scope. New records are not necessarily net-new companies or accepted opportunities; latest update is not an edit-event count. |
| Referrals | 349 = 61 active + 245 Office Hours + 40 Graveyard/Newsletter + 3 tests | Derived from the exact same CRM collection. Positions are not requests, introductions or qualified opportunities. Earlier event/context reviews keep their original dates. |
| Video DM worksheets | 468 valid prospect rows / 460 unique profiles; 66 valid Loom references; 22 literal video-date reports and 44 follow-up-date reports | Both allocated worksheet ranges were read. Status/helper rules have been standardized, so classification changes are not automatically new activity. Row positions changed. |
| Worksheet-to-CRM review | 103 current ID/asset candidate rows have current CRM record evidence; 101 exact profiles and 64 of 66 assets corroborated | Twenty-two exact profiles were resolved from current CRM notes rather than missing person-profile fields. Current source rows were freshly joined by identity/asset. Note creation does not establish a send date. |
| October 21–22 source-date cohort | 21 dated worksheet reports; 19 valid Loom rows; 19 exact CRM profile/asset matches | Two other recording fields are empty. Zero missing matches applies only to those 19 asset rows and does not establish 19 actual sends. |
| Charles creator analytics | 64,419 impressions / 36,760 unique members reached; 545 social actions / 555 broader workbook Engagements; 11,569 followers | Fresh Charles-authenticated workbook/UI. The 90 UTC source days run July 27–October 24; October 24 is partial. There are 49 unique ranked posts, a capped subset. Window shifts and source restatements are not pure incremental growth. |
| Company content | 49 UTC daily rows, September 4–October 22; 25,064 impressions, of which 25,055 are sponsored | Organic and sponsored counters remain separate. Sponsored counters reconcile to Ads on 48 matching dates through October 21. October 22 is an explicit company-source zero with no retained Ads row; no paid zero is manufactured. |
| Charles profile analytics | 1,313 Profile viewers in the authenticated Past 90 days preset | Separate collection clock and preset; exact aggregate boundaries and source timezone are unavailable. This total does not follow the dashboard date filter. No viewer identities are published. |
| Concluded Ads | All seven ad sets Completed; $3,592.31 spend / 25,055 impressions / 106 clicks | Fresh September 4–October 23 UTC aggregate/status check agrees with retained exports. No new daily rows were imported; paid daily evidence still ends October 21. |
| Waalaxy Home | 430 invitations / 133 reported acceptances / 0 platform message actions / 2 answered messages | Authenticated Charles account; displayed October 1–24 source window, final day partial and timezone unknown. The older daily CSV remains independently dated at 430/132. No additional acceptance is assigned to October 23 or 24. |
| Native Video DM review | Nine additional October 22 sends corroborated; 18 observed video sends across 19 reviewed asset profiles | Exact recipient, Charles sender, displayed day and identical Loom asset. SubImage remains historically unconfirmed; these observations corroborate overlapping worksheet reports, not extra sends. No new incoming replies were visible in the nine bounded threads. |
| Calendly | 29 event records / 26 booking chains; 26 active and 3 canceled events | Charles's authenticated July 16–November 13 scheduled-start scope, all invitee pages. Two upcoming generic booking chains are scheduled October 29. Calendar status is not attendance. |
| Fireflies | 100 paginated metadata records, including 84 October-indexed IDs; eight new dialogues and 11 earlier insufficient responses reviewed | Recording IDs are not unique meetings. The earlier 65 purpose-classified bodies keep their earlier review ages. Transcript indexing time is not a verified occurrence time. |
| Christian's meeting proxy | 324.77 associated audio minutes across six counted records | Adds one 96.19-minute recording to the prior 228.58-minute proxy. A parallel 30-minute segment contributes no additional meeting or time. Actual attendance, billable time and combined human hours remain unknown. |

The dedicated archived-deals endpoint was checked separately and exhausted with zero accessible records. Its collection clock is separate from the non-archived inventory. The configured CRM credential does not identify Charles's mailbox, and the Mailbox API offers no user selector; this does not establish current Charles Sales Inbox coverage.

## Decisions and evidence retained

Commercial outcomes remain unchanged for the owner's manual review with Charles. In particular, a Call Complete stage set by automation, a new CRM record, a scheduled booking and a founder discussion are not substituted for the four agreed headline outcome definitions.

Christian's separate owner-provided non-meeting range remains **18.25–19.5 hours through October 22**. October 23 non-meeting work is unmeasured. The added recording proxy does not increase the owner range or create a combined human-hour total.

The earlier native review retains **nine October 21 video observations**, their original collection times and original source rows, plus two general LinkedIn observations. The new nine October 22 sends bring the retained native register to 20 observations, including 18 video sends. All 19 asset profiles were checked; SubImage remains unconfirmed. Current literal worksheet reports overlap these observations and are not added to them. The earlier Nace email report remains separate historical email context. Seen indicators are read-receipt context, not video views or dated receipts. See the [native Video DM review](NATIVE_VIDEO_REVIEW_2026-10-23.md).

Two bounded invitation-CSV download attempts produced no new file or browser download entry. Waalaxy Home retains its fresh aggregate clock, while daily CSV coverage and acceptance buckets retain their earlier clock. The older 430/132 Home/CSV comparison is explicitly historical, rather than a reconciliation to the new 430/133 Home window.

## Integration and publication controls

`tools/apply_refresh_2026_10_23.py` defaults to a private preview and accepts explicit source-family patches. A canonical write requires `--write-shared`. Current recording-field/CRM row reviews must match the exact inventory snapshot and row/profile map; incompatible older reviews are archived as historical evidence rather than applied to reordered rows.

Partial native imports preserve independently dated email, reply and conversation evidence. A complete review-bundle wrapper is required to replace a coverage cohort intentionally. Original observed messages remain deduplicated; a source refresh does not re-date them.

Raw workbooks, CSVs, API responses, transcript/message bodies and screenshots remain in ignored private storage. Curated source-specific publication rules also minimize excluded personal record context during final curation and fail closed if it reappears. Commercial decisions and owner hours are checked for preservation. CI runs the replay and publication-minimization regressions before building.

The existing approved destination is the Centripetal GitHub repository and GitHub Pages. A successful deployment and matching served files must be verified separately before calling this collected update live. See [remaining data needs](MANUAL_DATA_REQUEST_2026-10-23.md) and the [earlier October 22 review](INDEPENDENT_CHANNEL_REFRESH_2026-10-22.md) for retained source evidence.
