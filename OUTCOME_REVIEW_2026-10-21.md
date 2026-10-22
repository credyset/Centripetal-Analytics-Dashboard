# Charles's highest-level outcomes

The four cards above the channel summaries use the reporting-period filter and Charles-only scope. The definitions were confirmed by the dashboard owner on October 21, 2026.

| Metric | Date and unit | Required evidence |
|---|---|---|
| Prospect calls held | Distinct commercial meeting, by actual occurrence date | Charles participated; prospect purpose and attendance confirmed. Scheduled, canceled, no-show, recruiting, internal and asynchronous exchanges are excluded. |
| Qualified companies | Unique company among that period's held prospect calls | Latest explicit owner qualification. A repeated meeting does not add another qualified company. |
| New opportunities accepted | Distinct commercial opportunity, by original acceptance date | Charles explicitly accepted the active opportunity and a next step is recorded. A new CRM record, automated task or current stage label is insufficient. |
| New clients won | Unique first-time client company, by verified first win date | First engagement and Charles's commercial ownership confirmed. Existing-client renewals, expansions and reopened duplicates are excluded. |

These counts have different units and event cohorts. They must not be presented as a conversion funnel.

## Existing bounded confirmations

| Company | Held call date | Qualification | CRM evidence |
|---|---|---|---|
| NuVee | October 6, 2026 | Qualified / warm | Deal 788 |
| Venus Ai Consulting | October 15, 2026 | Unqualified | Deal 791 |

On October 16, the owner confirmed that these linked calls were held on their respective dates above. Exact start times and attendance durations remain unavailable. The records are a bounded confirmed set, not a complete October call register. They do not establish accepted opportunities or wins.

For October 19–21, no held-call outcome has yet been confirmed in this register. The cards show **Pending**, not zero. Selecting October month to date shows **at least 2** confirmed calls and **at least 1** qualified company until complete coverage is reconciled.

## Owner review needed

For every Charles prospect meeting since the last review, supply or confirm the company, actual held date, attendance, qualification and supporting calendar/recording/CRM reference. Separately confirm accepted opportunities with the original acceptance date and active next step, and first-time clients with the verified win date. A list of known existing clients prevents renewals and expansions from becoming net-new wins.

Explicitly confirm a complete date window before interpreting an empty register as zero. A positive count under incomplete coverage is a confirmed minimum (displayed as ≥); an empty incomplete register remains pending.

## Contributor data contract

`OWNER_CONFIRMATIONS.json` remains canonical for the two linked call confirmations above. `OUTCOME_CONFIRMATIONS.json` holds definitions, coverage assertions and additional reviewed records. `tools/apply_outcome_confirmations.py` builds `data.outcomes` after source preparation and during shared curation. It never infers attendance, qualification, acceptance or wins from source activity.

Additional held-call rows require `conversationId`, canonical `companyKey`, company, `heldAt`, `charlesParticipated: true`, `prospectMeeting: true`, `heldConfirmed: true`, evidence basis and confirmation date. Qualification uses `qualification: "qualified"` or `"unqualified"` plus `qualificationConfirmedOn`. Use the same canonical company key across all of its contacts and CRM deals. A qualification decision from a later call can update the latest recorded company disposition; conflicting decisions on the same review date remain unresolved.

Opportunity rows require a stable `opportunityId`, canonical company key, company, original `acceptedAt`, `charlesAccepted: true`, a nonempty `nextStep`, evidence basis and confirmation date. Keep the same opportunity ID through re-openings and duplicate CRM records.

Win rows require canonical company key, company, first `wonAt`, `charlesCommercialOwner: true`, `firstTimeClient: true`, `winConfirmed: true`, evidence basis and confirmation date. A current stage label is not win evidence.

Coverage keys are `heldCalls`, `qualification`, `opportunityAcceptances` and `clientWins`. Use `status: "complete"` only with explicit inclusive `start` and `end` dates and a review note establishing complete source reconciliation. Qualification totals also require complete held-call coverage and known dispositions for the selected company cohort.

Timestamped events use America/Denver. Confirmed date-only events keep their supplied occurrence date, with their date basis visible. The week starts Monday. Week and month presets run to the stated source cutoff; complete-day presets stop before a partial current day. Each underlying source retains its own coverage cutoff.

Validation: `node tools/check_outcome_metrics.js` checks deduplication, cohort membership, explicit acceptance, first wins, Mountain date boundaries, missing-versus-zero handling and stale CRM coverage.
