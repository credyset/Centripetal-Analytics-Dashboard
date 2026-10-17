# Fireflies recording reconciliation — October 16, 2026

The eight detailed source IDs previously labelled BD/prospect were reviewed live and reconciled into a purpose-based ledger. **They do not support eight verified qualified calls.** The imported aggregate claims of 19 recordings, 8 BD/prospect, 6 client and 5 internal lack a complete supplied event ledger and remain unverified.

## Reviewed recording inventory

| Minimal purpose label | Indexed date | Recording count | Treatment |
|---|---|---:|---|
| Hiring reference | October 14 | 2 | Exclude from prospect acquisition |
| Client recruiting | October 14 | 1 | Client-related activity; exclude from prospect acquisition |
| Purpose unavailable | October 12 | 1 | Provisional external recording; metadata only |
| Commercial discovery · qualification unknown | October 12 | 1 | Discovery discussion supported; qualification and accepted opportunity unknown |
| Client work | October 8 | 1 | Client delivery; exclude from prospect acquisition |
| Partner / financing | October 8 | 1 | Mixed relationship and financing activity; not a verified qualified prospect |
| Fundraising / networking | October 2 | 1 | Network discussion; qualified finance-service opportunity unknown |

The reviewed inventory is eight accessible source recordings and 219.17 audio minutes. Seven have transcribed dialogue; one has metadata without summary or dialogue. Neither recording counts nor audio minutes establish unique meetings, individual attendance or qualified commercial outcomes. The review retains no sensitive hiring evaluations, transcript text, summaries, contact-email rosters or recording-access links.

All eight prior displayed dates match the source's UTC index dates. That agreement does **not** verify meeting occurrence dates. The connector supplies transcript creation timestamps and audio minutes; it does not expose the calendar-event IDs or attendance records needed here to establish actual meeting dates. The ledger therefore uses `indexedAt` and leaves `occurredAt` null. [Fireflies Transcript Schema](https://docs.fireflies.ai/schema/transcript)

## CRM and booking linkage

One reviewed recording has an exact private participant-email and speaker-name match to CRM deal 762. This corroborates contact identity connected with client work; it does not attribute an acquisition source or establish a new opportunity. No reviewed recording has a verified join to a retained Calendly booking chain.

NuVee, CRM deal 788, retains its verified platform booking scheduled October 6 and its owner-confirmed qualified/warm status. Venus, CRM deal 791, retains its verified platform booking scheduled October 15 and its owner-confirmed unqualified status. **Held status remains unknown for both.**

The bounded live index scan reviewed 100 descending metadata records, with indexed timestamps spanning September 15 through October 16. No exact private participant-identity match was found for either lead in that scope. This does not establish that either booked call was missed or unheld: recordings may be absent, inaccessible, indexed differently or missing participant metadata.

Keyword searches for four distinct lead strings returned identical newest-record lists. Search filtering could not be verified, so those searches were not used as evidence of absence.

## Prepared data contract

`data/fireflies_reconciliation.json` contains:

- `snapshotAt`, `coverage`, `records`, `summary` and supporting source-evidence fingerprints.
- Eight reviewed records with minimal title, source ID, `indexedAt`, null `occurredAt`, audio `durationMinutes`, reviewed `classification` and general `classificationBasis`.
- CRM identity IDs, empty verified booking-chain IDs, explicit `joinStatus`, unverified booked-call `heldStatus`, and unknown qualification.
- Separate known-lead booking reviews, with no change to owner qualification or calendar booking evidence.

`tools/reconcile_fireflies.py` deterministically normalizes the sanitized review evidence. Re-running preserves the actual review timestamp and does not claim a fresh source collection.

The dashboard can safely show **eight reviewed recordings by purpose**. It should leave qualified held-call totals and booked-to-held conversion unavailable until a reliable event-level join and qualification basis exist. The prior 19/8/6/5 rollup should not be presented as a verified source total. External participant domains alone are insufficient for prospect classification.

The review made no changes to source systems, the shared dashboard dataset, UI, Git or Christian's existing effort calculations.
