# Live Video DM and Calendly source review

Read-only collection on October 14, 2026, Mountain time. Source systems were not changed. Operational source exports and prepared JSON remain local and excluded from Git.

## Video DM workbook

Read the full prospect and accepted-connection tabs from the connected Centripetal workbook. Retained the preceding normalized snapshot under `data/history/` before refreshing the private source files.

- Final inventory, refreshed at 9:10 p.m. Mountain: 428 prospect rows, 420 unique normalized LinkedIn profiles, 2 unresolved profile URLs, 47 ready rows, 48 sheet-classified sent/completed rows, and 29 explicit Sent/Done status rows.
- The two retained snapshots, collected October 14 at approximately 7:33 p.m. and 8:59 p.m. Mountain, show zero newly observed row identities and zero explicit Sent/Done status changes. These are snapshot differences over that interval, not a count of prospect creation or delivery during a reporting day.
- A final read at 9:10 p.m. confirmed two separately authorized profile/identity repairs from the Video DM workstream. They increased valid profile coverage from 418 to 420, without new prospect rows or sends. The final delta explicitly classifies two identity corrections and zero additional prospects/status sends. Analytics made no source-sheet edits.
- The sheet-classified completed total includes Loom links. A recording link does not prove the message was delivered. Explicit Sent/Done is self-reported status; actual sending timestamps remain unverified.
- Duplicate identities are excluded from status-transition comparisons. Missing profile URLs remain unresolved; source row numbers are not stable identity keys.

`data/video.json` now includes `snapshotDelta` and source-range coverage. `tools/prepare_video.py` reads the retained collection manifest instead of assigning preparation time as source freshness.

## Calendly coverage and reconciliation

Authenticated source: Charles Solomon's Calendly account. Its account timezone is America/New_York; all dashboard period dates are derived in America/Denver with daylight saving applied.

The connector returned 27 scheduled-event records with start times from July 16 through November 12, 2026, covering the last 90 complete Mountain days, the partial current day and the next 30 days. No pagination remained. A separate query for event starts after that future window returned no additional records. Invitees were collected for all 27 events, with no additional invitee pages.

- Raw lifecycle inventory: 25 active events and 2 canceled events.
- Two canceled events explicitly link to active rescheduled replacements. Grouping by the original booking chain yields 25 unique bookings, rather than counting each replacement as a new initial booking.
- Nine bookings use the Interview event type. Keep these separate from business-call indicators until their purpose is reviewed.
- The remaining 16 unique chains use generic 30-minute meeting types. These are **unclassified bookings**, not 16 verified commercial or qualified calls.
- Two generic bookings are upcoming as of collection. Two generic booking chains were originally created in the last 30 complete reporting days, September 14–October 13. The October 14 booking is current-day partial and excluded from that complete-period metric.
- An active event with a past end time does not prove attendance. Verified held-call and commercial-call totals remain unavailable.

Booking creation uses the original chain's `bookingCreatedAt`. Scheduled occurrence uses `startAt`. The prepared dataset retains canceled sources and rescheduled replacements; count one `bookingChainId` for original booking creations and only `isCurrentBooking` records for upcoming bookings. Created-date metrics describe the retrieved event-start scope, rather than a separate created-at API filter.

## Lead identity corroboration

Exact normalized name and email matches to retained Pipedrive records corroborate two previously submitted leads. Emails are retained only in private source evidence and omitted from the prepared dataset.

| Lead | CRM deal | Booking created, Mountain | Scheduled start, Mountain | Interpretation |
|---|---:|---|---|---|
| NuVee | 788 | October 5, 2026, 2:49 p.m. | October 6, 2026, 11:30 a.m. | Platform booking confirmed. Owner qualification remains qualified/warm. Attendance unverified. |
| Venus Ai Consulting | 791 | October 9, 2026, 8:46 p.m. | October 15, 2026, 11:30 a.m. | Platform booking confirmed. Owner qualification remains unqualified. Booking does not change lead quality. |

NuVee event UUID: `cb09b80e-170c-40ec-a563-9e02aa9947e8`. Created UTC: `2026-10-05T20:49:57.152087Z`; scheduled UTC: `2026-10-06T17:30:00Z`.

Venus event UUID: `d9459ee9-6d38-4476-a820-3a4eb2473599`. Created UTC: `2026-10-10T02:46:13.352841Z`; scheduled UTC: `2026-10-15T17:30:00Z`. The invitee carries a LinkedIn Marketing Solutions UTM source hint, which is supporting context rather than proof of campaign causation.

Seven raw event records have exact name/email matches to accessible CRM deal records. This includes the canceled source and its replacement, so those matches are not additive unique contacts or sourced opportunities. Identity matching alone establishes neither sales qualification nor attribution.

## Prepared data contract

`data/meetings.json` contains:

- `snapshotAt`, `timezone`, `coverage`, and a minimal verified `account` scope.
- `events`: source event ID/type/status, creation and scheduled timestamps, cancellation timestamp, reschedule-chain IDs, original booking creation date, current-booking flag, interview exclusion classification, invitee counts, CRM deal IDs, and explicit attendance uncertainty.
- `summary`: source inventory and clearly bounded unclassified-booking indicators.
- `verifiedLinks`: the two lead-to-CRM-to-calendar identity corroborations, owner qualification, booking dates and unverified held status.
- `provenance`: SHA256 hashes of retained source evidence; `notes` defining safe interpretations.

The prepared dataset omits invitee names, emails, phone numbers, meeting notes, question answers, locations, meeting join links and cancellation/rescheduling links. Raw source files and a PII-minimized join manifest are under `data/private/`.

Recommended dashboard use: add Calendly booking evidence to Pipedrive's outcome view, retain unclassified versus qualified business distinctions, show original bookings separately from scheduled dates, and display held-call outcomes as unverified until attendance evidence exists. Do not introduce a new acquisition vector or sum the same linked booking across ads, CRM and calendar.

No Fireflies transcript content was retrieved. No claim about held meetings was derived from recordings, calendars or CRM completion flags.

## Final Video DM reconciliation

A final full read at 9:10 p.m. Mountain on October 14 incorporates two profile repairs separately authorized by the owner in the Video DM chat. Inventory remains 428 rows; valid unique profiles are now 420, with two unresolved URLs. The helper reclassified two rows from Review to Awaiting connection. Ready remains 47, sheet-classified completed 48 and explicit Sent/Done 29. The repairs are identity corrections, not two newly added prospects or sends. The 8:59 p.m. snapshot is retained for comparison.
