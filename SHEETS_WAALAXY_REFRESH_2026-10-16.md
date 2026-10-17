# Google Sheets and scoped Waalaxy refresh — October 16, 2026

The Centripetal Video DM workbook was read live at approximately **6:52 p.m. Mountain**. Collection used the read-only Centripetal Google Sheets connector. All current tabs and their complete allocated ranges were inspected; no source cells were changed.

## Source located

Spreadsheet: `1_Vq5-hM3POad1V14rZjX6gfaUojUnnTvxjjSv1zDJ8M`.

| Tab | Complete requested range | Returned rows including header | Usable records |
|---|---|---:|---:|
| Video DM prospects | A1:AC1206 | 430 | 428 prospect rows |
| Accepted Connections (Video Prospects) | A1:AN1011 | 148 | 147 connected profiles |

The workbook currently has two tabs. The first now includes a `Synced to Pipedrive` column. The accepted-connections tab supplies Waalaxy-shaped prospect fields: profile status, list, message/reply flags, import date, connection date and first/last messaging dates. No linked source spreadsheet, authenticated sender-account ID or upstream export/sync timestamp appears in the inspected cells. No live Waalaxy account API capability was discovered among the enabled tools.

This is a usable refreshed **connected-prospect subset through Google Sheets**, rather than a newly authenticated account-wide Waalaxy export. It belongs to the user-identified Charles Video DM workflow. The source columns do not independently verify the upstream Charles sender/account ID. Christian's and Jess's unrelated account datasets were not imported or merged.

## Video DM inventory

| Metric | Previous retained snapshot | Current live sheet |
|---|---:|---:|
| Prospect rows | 428 | 428 |
| Unique valid profiles | 420 | 420 |
| Missing valid profile URLs | 2 | 2 |
| Ready for Video DM | 47 | 57 |
| Connected source rows | 115 | 127 |
| Awaiting connection | 307 | 295 |
| Review | 11 | 13 |
| Sheet-classified sent/completed | 48 | 48 |
| Explicit Sent/Done | 29 | 29 |
| Rows with CRM deal IDs | 59 | 82 |

Forty-three rows carry the source's `Synced to Pipedrive` flag. That flag is not independent proof of a successful CRM identity synchronization. Two profile URLs changed for otherwise unique, exactly matching company/contact identities. The refresh reconciles these as identity corrections: **zero newly observed prospect rows and zero removed prospect rows**. No newly explicit Sent/Done status was observed.

The retained duplicate-profile count remains six, with two conflicting helper classifications. Differences in helper action, connection state or CRM identifiers are observed snapshot changes, not dated prospect creation, message sending or sales progression. The comparable-identity delta excludes duplicate identities; inventory totals continue to count source rows.

Sheet-classified completion includes recording-link presence. A recording link does not prove delivery. Explicit Sent/Done is a self-reported status, and neither count demonstrates sends in the selected reporting period.

## Refreshed Waalaxy-shaped subset

- **147 unique connected profiles**, up from 135 in the retained accepted-connections tab.
- **125 Video DMs profiles** match 125 unique profiles in the main prospect tab, representing 127 source rows because duplicates remain.
- **22 Pulley Contacts profiles** form a separate subset and do not match the main Video DM prospect roster.
- **46 profiles** carry a message-sent flag; **11 profiles** carry a message-replied flag. These are people with recorded flags, not total messages or replies.
- **111 profiles** have a connection date; **36** have none. The latest supplied connection date is October 15.
- The latest supplied LinkedIn message date is April 19; the latest reply date is October 7. Fresh sheet collection does not make these older attributes current message-event history.

First/last dates describe selected prospects. They cannot reconstruct all messages or replies. Current-period account-wide message/reply counts, a whole-account prospect total and an invitation acceptance rate remain unavailable from this source. In particular, dividing these selected connected profiles by account invitation actions would create an invalid rate.

## Sources preserved

The older verified Charles baseline remains unchanged: July 6 snapshot, 8,082 unique prospects, with dated historical coverage ending June 26. The separate September 15–October 15 invitation source remains unchanged: 31 source days, 402 sent and 114 accepted actions, including its existing source-timezone and account-attribution caveats. Connected-person records are not a replacement for that invitation-event series.

The accepted-connections subset receives its own collection timestamp. Upstream sync/export time remains unknown. The latest supplied source attribute date is reported separately from collection freshness.

## Outputs and safe integration

`tools/prepare_sheets_waalaxy_refresh.py` produces:

- `data/video_refresh.json`: current inventory, minimal curated prospect rows, first-observed differences, self-reported dated status markers and source provenance.
- `data/waalaxy_refresh.json`: `sheetSubset` with selected connected-person metrics, minimal profile/date/flag records and `dailyPeopleAttributes`; `preservedSources` retains the older baseline and newer dated invitation source separately.

The `sheetSubset` should supplement the Waalaxy view, with explicit subset and freshness labels. Its person attributes must not replace account-wide invitation events or be presented as current message totals.

Private raw evidence is under `data/private/sheets_refresh_2026-10-16/`, separate from all previous snapshots. Prepared refresh rows omit emails, phone numbers, source notes/hooks, response text and recording-access URLs. Source hashes allow the retained exports to be checked. No app, shared dashboard JSON, Git, time data, CRM data or production source was modified.
