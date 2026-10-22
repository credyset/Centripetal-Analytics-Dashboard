# CRM browser evidence — October 21, 2026

Read-only browser review supplements the complete October 16 Pipedrive export. It does **not** replace that export or advance its deal/activity coverage. The current observations show the open pipeline boards across **Everyone**, with the **Show closed deals** action visible. Source totals include any tests and duplicate companies.

| Pipeline | Current source open-view inventory | Visible cards captured | Cards with readable source IDs |
| --- | ---: | ---: | ---: |
| Leads | 377 | 70 | 38 |
| Sales | 42 | 42 | 38 |
| Referrals | 348 | 90 | 38 |

The browser virtualizes card lists and truncates some accessibility URLs. Unreadable IDs remain unresolved. Neither the visible-card sample nor the three source totals is a new cleaned account-wide business-record total. Each pipeline and card retains its capture time; the complete baseline remains dated October 16.

## Current observations

- Leads: Video DM Outreach contains **59** records; Intro Call Scheduled contains **4**; Hightouch Manual contains **60**; Graveyard contains **254**. These are current stage inventories, not sends, bookings created during this week, or held calls.
- Fifteen visible source IDs, **832–846**, are absent from the retained October 16 full snapshot. They occupy Video DM Outreach, with latest-update labels on October 19–21. This establishes newly observed CRM identities in this comparison, not fifteen new accepted opportunities, fifteen sends, or verified creation dates.
- Sales: the open-view board contains **6** records in the stage named Closed Won and **13** in the stage named Closed Lost. Stage names do not establish actual status, closed dates, first-time clients or October wins.
- NuVee, deal **788**, appears in Parking Lot (Short Term). Its explicit owner-confirmed qualified/warm disposition is preserved. A Charles-accepted opportunity date and active next step remain unconfirmed.
- Venus appears under deal **791** in Leads / Intro Call Scheduled and deal **805** in Sales / Negotiating Contract. These company identities and business dispositions need reconciliation. The owner-confirmed unqualified lead disposition is not silently reversed by another record's stage.
- Referrals: displayed stage counts reconcile to **348** source records: Amigos 14, Circle 35, Inner Circle 9, Intro Promised 2, Intro Made 1, Opportunity (Referred) 2, Office Hours 245 and Graveyard (Newsletter) 40. This remains relationship inventory, including tests; it does not establish dated introductions, held meetings, qualified referrals or accepted opportunities. Prior cleaned partitions remain tied to their original full-source date.

## Values and dates

Sales stage monetary headers differ from the visible deal-card amounts. Intro Meeting displays $2,400 in its header while its two cards show $6,000 and $10,000; Negotiating Contract displays $7,250 while its cards show $2,000 and $12,500. This may reflect weighting, but the amount basis was not verified. The supplement retains the source labels separately and does not present them as revenue or qualified pipeline.

Latest-update labels are retained verbatim because their display timezone was not exposed. They do not establish when a call occurred, a Video DM was delivered, a qualification decision was made or a stage transition happened. Preparation time does not refresh source collection time.

A separate October 21 handoff document describes date-triggered movement from Intro Call Scheduled to Call Complete. That is a configuration claim awaiting live verification, and reinforces the need to verify attendance independently of stage position.

## Remaining source needs

The available Chrome download interaction did not complete an export. This is a collection limitation, not a conclusion that the signed-in user lacks export permission. The next useful source package is:

1. An all-status, all-owner deal export with stable deal/company/person IDs; created, updated, stage-change, won/lost dates; actual status; commercial owner; source; values/currency; next step; and custom qualification/interaction fields.
2. Activity records with stable IDs, owner, type, linked records, created/due/completed dates, completion status and automation/reference fields.
3. Retained stage-transition and relevant field-change history covering October, with from/to values and event timestamps.
4. Charles confirmation of held prospect meetings, qualification for those companies, explicitly accepted active opportunities with dates/next steps, and first-time client wins with actual agreement dates.
5. Reconciliation of duplicate company records, especially Venus 791/805, before counting company-level outcomes or attribution.

`tools/prepare_crm_browser_review_2026_10_21.py` deterministically parses the retained browser accessibility captures into the ignored private `crm_browser_patch.json`. It validates that explicit stage counts reconcile to each observed pipeline total. It does not access browser sessions, change source systems, replace the full CRM export or publish data.
