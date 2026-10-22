# Charles's highest-level outcomes

The four cards above the channel summaries use Charles-only scope and the selected reporting period. The owner agreed the definitions on October 21. Source collection finished late October 21 Mountain; local preparation continued after midnight.

| Metric | Date and unit | Required evidence |
|---|---|---|
| Prospect calls held | Distinct prospect meeting, by occurrence date | Charles participated; attendance and prospect purpose confirmed. Scheduled, canceled, no-show, recruiting, internal, existing-client delivery and asynchronous exchanges are excluded. |
| Qualified companies | Unique company among that period's held calls | Latest explicit owner decision or direct documented Charles commercial approval. A stage label or general interest alone is insufficient. |
| New opportunities accepted | Distinct commercial opportunity, by original acceptance date | Charles accepts an active opportunity with a next step. First documentation is not automatically first acceptance; new CRM records are insufficient. |
| New clients won | Unique first-time client, by verified first win date | Actual first engagement and Charles's commercial ownership confirmed. Renewals, expansions and duplicate records are excluded. |

These measures have different event dates and units. They are not a conversion funnel.

## Reviewed October call set

| Company | Held date | Qualification basis | CRM |
|---|---|---|---|
| DEXIQ Robotics | October 2 | Future CFO interest / nurture; current Charles qualification unknown | 751 |
| XCaliber Health | October 5 | Qualified through Charles's scoped contract/proposal after the call | 750 |
| NuVee | October 6 | Owner-confirmed qualified / warm | 788 |
| Nicolette | October 12 | Nurture / not now after budget mismatch; current qualification unknown | 789 |
| Venus Ai Consulting | October 15–16; exact day unresolved | Latest explicit owner decision remains unqualified; newer negotiation context requires reconciliation | 791 / duplicate 805 |

October 1–21 therefore shows **at least five held conversations and at least two qualified companies**. NuVee remains the only qualified company among the four paid lead submissions; XCaliber is a separately evidenced company with no paid attribution assigned.

The original owner attendance confirmations are retained. New inbox evidence shows Venus's original October 15 booking was rescheduled to an accepted October 16 invitation, while Calendly still lists October 15 active. Neither booking alone verifies the actual day. A period containing both dates counts this confirmed meeting once. A selection intersecting only one candidate day stays incomplete, even if wider coverage is later reconciled.

XCaliber's October 5 post-call proposal explicitly establishes a held conversation and Charles's approval of a scoped commercial engagement. Subsequent proposal and start discussions support an active opportunity by October 5. A follow-on October 22 review retrieved September 23 dialogue covering paid scope, retainer pricing and agreed follow-up steps, corroborated by independently dated September 24 correspondence. This establishes the opportunity was already active before October. It appears in a separate evidence table and is excluded from the **new October opportunity** headline; its exact first acceptance date remains unknown. No signed first-client win is verified.

Actual Nicolette and DEXIQ dialogue was matched to accepted invitations and post-call correspondence. Only occurrence-day precision is supported; scheduled start times are not represented as exact attendance starts. Their finance interest and introduction follow-up do not automatically establish current qualification or accepted paid opportunities.

## October 19–21 review

All eleven available Fireflies recordings indexed in this period were reviewed for actual speakers and purpose. They concern existing-client delivery, internal work or vendor feedback. They establish no additional Charles prospect call. Charles's presence in a participant list is not proof he actually spoke or attended.

The fresh Calendly results contain no starts October 19–21. CRM activities and notes establish tasks or outreach, not additional held calls. These source absences do **not** establish a complete actual-call roster, so the four weekly headline totals remain **Pending**, rather than zero.

The accessible CRM has zero October actual won-status records, corroborated by browser won/archive views. That is a CRM record observation, not proof of zero first-time clients. The sole recorded won deal dates to August. Conditional October 19 discussion of future XCaliber and Venus starts does not establish a signed win.

## Remaining decisions

1. Preserve XCaliber's established pre-October acceptance. Its exact original date remains unknown; the October 5 proposal must not become a new October acceptance.
2. Reconcile Venus's latest Charles qualification/commercial decision and its actual held date. Keep its duplicate records joined to one company.
3. Confirm a complete Charles prospect-call roster, including calls absent from accessible recordings and Calendly.
4. Supply executed engagement / first-client start evidence and an existing-client baseline before certifying net-new wins.

## Contributor contract

`OWNER_CONFIRMATIONS.json` preserves the original owner decisions. `OUTCOME_CONFIRMATIONS.json` contains definitions, additional reviewed facts, date corrections and explicit coverage assertions. `tools/apply_outcome_confirmations.py` reapplies both after source preparation. It corrects derived date precision without deleting the original owner evidence.

Held-call rows require a stable `conversationId`, canonical `companyKey`, company, participation/purpose/held confirmations and evidence basis. Use either a verified `heldAt` or a bounded `heldDateRange` with inclusive start/end and a visible uncertainty basis. Deduplicate the same conversation across sources and the same company across CRM records.

Qualification requires `qualified` or `unqualified` plus the decision date and direct evidence. Unknown and nurture dispositions remain outside the qualified count. A later explicit decision can update the company disposition; same-date conflicts remain unresolved.

New-opportunity rows require stable `opportunityId`, original `acceptedAt`, `charlesAccepted: true` and a nonempty `nextStep`. A row explicitly marked `originalAcceptanceDateVerified: false` cannot enter the headline. `observedOpportunities` retains active commercial evidence with uncertain original dates separately.

Win rows require a canonical company key, verified first `wonAt`, `charlesCommercialOwner: true`, `firstTimeClient: true` and `winConfirmed: true`.

Coverage keys are `heldCalls`, `qualification`, `opportunityAcceptances` and `clientWins`. Mark complete only for an explicitly reconciled inclusive date window. Unknown totals remain Pending; positive incomplete counts use ≥. Timestamped facts use America/Denver; date-only evidence keeps its supplied precision. Weeks start Monday.

Validation covers cohort membership, deduplication, unresolved date ranges, original acceptance, first-client wins, partial source days, missing versus zero and stale-source boundaries.
