# Centripetal Advisors analytics dashboard — planning draft

Date: October 14, 2026. Status: local working concept built and browser-verified. New private repository: https://github.com/credyset/Centripetal-Analytics-Dashboard. No production website or unattended refresh has been deployed.

## Current delivery

- Local preview: http://127.0.0.1:8765. At a glance plus six detailed dashboard views and source definitions, working date presets/custom dates and searchable/sortable tables.
- Current Pipedrive snapshot: 722 accessible non-deleted deals and 923 activities across all owners. Business metrics exclude three test deals and five test activities.
- Current Video DM snapshot: 428 source rows, 418 unique valid LinkedIn profiles and 47 ready rows. Spreadsheet-classified sent/completed remains distinct from verified delivery.
- Ads: reconciled daily data through October 12. Charles content: daily export through September 10. Company-page and verified Charles Waalaxy baselines are historical and labelled accordingly.
- The active Chrome profile was Christian's; unrelated LinkedIn/Waalaxy account figures were excluded. Current Charles campaign/content exports remain a source gap.
- Application code and preparation tools are versioned. Operational JSON, raw exports and validation screenshots are excluded from Git. The local server blocks raw exports and project internals.
- Next production work: retained change history, reliable fresh channel exports, authenticated hosting, source credential ownership and monitored daily collection.

## Purpose and decisions to resolve

Give Charles and the team one place to see business-development activity, responses, meetings, and commercial progress. The dashboard should answer: what happened, what produced useful conversations, what progressed, and what needs attention?

Confirmed by the owner: an internal browser dashboard for Charles and the team; daily refresh wherever a reliable source allows it, with manual imports elsewhere; equal prominence for activity and outcomes; Charles's LinkedIn/Waalaxy activity and the Centripetal company page only; Monday–Sunday weeks in Mountain time.

Reporting calendar: `America/Denver`, including daylight-saving changes. Store source timestamps and timezone information, then derive local reporting dates. Date-only source aggregates cannot always be reassigned accurately to Mountain time; preserve and label their original day boundaries.

Scope: exclude Jess's personal LinkedIn/Waalaxy activity from the first dashboard. Pipedrive covers Centripetal business-development records in Sales, Leads and Referral pipelines, with owner filters; the selected social account scope does not imply excluding other owners' legitimate Centripetal CRM records.

Current direction: develop a local custom-dashboard concept, then create a new private GitHub repository for the project. This replaces the managed Data Studio recommendation. GitHub owner and repository are settled: `credyset/Centripetal-Analytics-Dashboard`. Open decisions: private deployment destination and team access, collection/import ownership, and operational definitions for qualified leads and accepted sales opportunities.

Working proposal: a private, Centripetal-branded browser dashboard, an executive overview with activity and outcome summaries of equal prominence, five channel views, and a weekly operating review. Direct reads where verified; dated exports where a durable integration has not been verified. Start with the latest complete 30 days and a 90-day comparison where the source supports both periods. Keep older evidence explicitly dated.

## Overview structure and refresh agreement

- Activity panel: invitations/messages, content published, Video DM sends where substantiated, prospects first observed, and CRM activities completed. Keep units distinct rather than summing them into a single activity score.
- Outcome panel: replies/positive replies, qualified leads, bookings, held meetings, accepted opportunities, and wins. Pipeline value appears only where the deal scope, currency and valuation basis are clear.
- Equal visual weight for both panels, followed by trend charts and a short follow-up/exception list. Each headline links to its supporting channel view.
- Default daily reporting should use the previous complete day, with the current partial day explicitly labelled. The dashboard must use each source's actual coverage rather than imply all feeds are equally fresh.
- Pipedrive and the native Video DM workbook are candidates for a daily scheduled read. Unattended authentication, pagination, change-history retrieval and hosting must be validated before daily automation is promised.
- LinkedIn Ads, Waalaxy and content begin with dated imports until reliable recurring access is verified. A daily dashboard refresh does not make an older export current.
- Every feed shows its last successful collection time, coverage end, refresh method and expected cadence. Preserve the last good snapshot if a read fails.
- Manual-import procedure: designated owner supplies the source export and period/account identifiers; validate the file; merge idempotently; retain the raw file; publish updated coverage. Assign ownership and actual import frequency before launch.
- Proposed daily collection window: early morning Mountain time, initially around 6–7 AM, reporting the previous complete day. This is a suggested operating window, not an installed schedule or exact-time guarantee. Weekly comparisons use Monday–Sunday Mountain boundaries and comparable complete days.

## Verified groundwork

- The completed LinkedIn/GA4 audit provides a reconciled paid-ad baseline through October 12, with lead dispositions updated October 13. It is historical seed data, not a live feed.
- Read-only Pipedrive calls succeeded for pipelines, stages, activity types, sample deals, and a sample deal's flow. Current pipelines are Sales Pipeline (1), Leads Pipeline (2), and Referral Pipeline (4). Their different purposes must remain visible. Existing connector reads do not by themselves establish an unattended daily refresh service.
- Existing July specification: `Centripetal/strategy/gtm_dashboard_build_spec_for_peter.md`. Reuse its operating questions, but validate current names, stages, formulas and definitions. A scheduled call is not automatically a qualified lead; a numerical stage increase is not automatically advancement.
- Existing relationship dashboard: `Centripetal/engagement_analysis/monday_dashboard_v1.html` and its builder. The builder uses a fixed May 21, 2026 reference date. It is useful design/context evidence, not current reporting.
- The Video DM workbook is readable: spreadsheet `1_Vq5-hM3POad1V14rZjX6gfaUojUnnTvxjjSv1zDJ8M`. Main tab ID 569014042; accepted-connections tab ID 1939678986. Main headers include deal/org IDs, LinkedIn URL, Charles's status, Loom link, response status, connection status/date, match key and follow-up action. The visible schema has no dedicated row-added or video-sent timestamp.
- Pulley listbuilding is a separate uploaded Excel workbook in Drive (`1eui4Gik_6z08ssg_f--QXONYa8wB8gdn`), not a native Google Sheet. It needs a file adapter. Its priority tab is a subset, not another independent population to add to the full contact list.
- Local Charles and Jess Waalaxy prospect exports exist, dated July/August. Their fields include sent/replied flags and first/latest message dates. These are dated person snapshots, not complete message-event histories.
- Local personal-profile and company-page content analytics exports exist, mostly from 2025. Current exports/access still need verification.
- `Centripetal - Video DM / Match LinkedIn video prospects` verified the workbook on October 14: 428 prospect rows, 47 ready rows, 48 rows classified already sent/completed, and six duplicated LinkedIn profiles. Those are row-level source classifications, not deduplicated verified sends. Only 59 prospect rows have populated deal/org IDs. The sheet's sent/completed helper accepts a Loom link or exact Sent/Done status, while dated Sent text has inconsistent treatment. Follow-up categories overlap the main action categories. Connection-tab message dates represent automation activity, not authoritative video-send dates.
- `Centripetal - Listbuilding` reconfirmed a 204-contact Pulley list with 152 classified net new, and a 30-contact priority subset containing 22 net-new records. Here net new means no verified person-level connection or reply in the supplied export; it does not mean newly added during a dashboard reporting period. Full listbuilding date/ID coverage remains to be mapped if that source is included.

## First version's views

| View | Initial metrics and decisions |
|---|---|
| Overview | Qualified leads, new bookings, held meetings, accepted opportunities, sourced pipeline where verified; weekly activity summary; trends and records needing follow-up |
| LinkedIn Ads | Spend, impressions, clicks, video retention, form opens/submissions, verified qualified leads, cost per qualified lead; campaign/ad-set/ad filters and objective-specific interpretation |
| Waalaxy | Invitations sent/accepted, messages sent, replies, positive replies where dispositioned, active campaigns and queue; profile/campaign/sequence breakdowns |
| LinkedIn content | Published posts, impressions, reach where supplied, reactions/comments/reposts, available saves/link clicks/video metrics; post/account/topic comparisons; organic and sponsored components |
| Pipedrive | New deals, distinct deals updated, actual stage transitions, bookings and completed calls, overdue follow-up, stalled deals, opportunities, won/lost and value; separated by pipeline and owner |
| Video DMs | New prospects first observed, eligible/ready queue, spreadsheet-classified sent/completed totals, separately verified dated sends where supported, responses, follow-up backlog, CRM linkage |

Proposed filters: date range, account/owner, campaign, pipeline and source. Every view shows its coverage dates, last successful refresh, metric definitions, and whether a number is verified, source-reported, or unavailable.

## Metric rules that must precede charts

1. Maintain activity, response, qualification, booking, held meeting, opportunity, and win as separate events. A prospect row or outreach-stage deal is not an accepted sales opportunity.
2. Count distinct deal IDs for deals updated; distinguish cosmetic/automated updates from commercial progression. Use change history and an explicit transition map. Moves to nurture, newsletter, graveyard or parking are dispositions, not automatic forward progress. Show event counts separately from unique deals advancing.
3. Separate bookings created in the period from meetings scheduled to occur in the period and meetings actually held. Deduplicate reschedules/cancellations by booking/activity identity. Inspect Calendly and CRM linkage if CRM alone cannot reliably represent these events.
4. Normalize LinkedIn URLs and retain source-native IDs for joining. Match to CRM using verified IDs or documented matching rules. Person, company, deal and activity counts are different populations.
5. Keep paid-sourced outcomes separate from subsequent Waalaxy/Video DM influence. Preserve unresolved attribution; do not assign revenue from matching names alone.
6. Represent boosted posts once in the content register, linked to their sponsored campaign/ad. Their spend belongs in paid totals once. Label organic, sponsored and combined measurements; do not sum overlapping reach or combined and paid-only metrics.
7. Recompute ratios from additive totals. Show denominators and comparable windows. An unavailable field is not zero; no denominator means a rate is unavailable.
8. Retain dates and reporting semantics from the source. Waalaxy attributes accepted invitations to their invitation-send date in campaign analytics; distinguish that cohort view from actual acceptance-date activity.
9. Lifetime flags and first/latest message dates cannot reconstruct all messages sent in a week. Use campaign analytics exports for period activity and prospect snapshots for identity and current status.
10. Without a trusted added/sent date, report current totals and changes first observed since snapshots begin. Never label a detected status change as an exact historical send date. Row numbers are not stable prospect IDs.
11. Compare content at consistent post age when snapshots allow it. Otherwise label lifetime totals and post age, rather than implying older posts outperform newer posts over the same exposure window.
12. A Loom link establishes that a video asset exists, not that it was delivered. Preserve the workbook's classification and derive a separate confirmed-send definition. Resolve duplicate-profile status conflicts explicitly; do not silently prefer a status or add overlapping follow-up categories to main status totals. Exclude formula-filled separator rows from prospect counts.

## Proposed technical approach

Develop and review the Centripetal-branded concept locally first. After that concept stage, create a new private GitHub repository for the dashboard code, metric definitions, source adapters and documentation. The private repository is `credyset/Centripetal-Analytics-Dashboard`.

Source reads / dated imports → retained snapshots and prepared reporting data → custom browser dashboard.

### Repository, data and private hosting

- GitHub provides version history, collaboration and a deployable project home. The private repository has been created and populated after the local concept review.
- The concept should provide Overview, LinkedIn Ads, Waalaxy, LinkedIn Content, Pipedrive and Video DMs, using the agreed branding, equal activity/outcome prominence and Mountain-time reporting calendar.
- Use the reconciled paid-ad baseline and clearly labelled unavailable sections or sample data for feeds not yet prepared. Keep sample and actual figures visibly distinguishable. Prototype refresh labels describe real source coverage, not a live integration.
- Keep connector credentials and raw private exports out of tracked browser assets. Use a separate data store or reporting workbook for operational records and history; the front end receives only data appropriate to its authenticated audience.
- A private repository does not automatically make an ordinary GitHub Pages deployment private. Standard Pages sites may be publicly accessible even when their source repository is private. GitHub's restricted Pages access is an Enterprise Cloud organization feature; check actual account eligibility before choosing it.
- For the internal live dashboard, connect the repository to a host with access control, or use restricted GitHub Pages if the organization is eligible. Choose that deployment after the local concept and ownership decisions. Authentication must protect both the page and underlying data files/endpoints.
- Daily collection runs separately from page rendering. A server-side or scheduled job can read Pipedrive and Sheets where authorized and supported; manual imports supply the remaining feeds. Keep the prepared data format independent of its eventual storage/hosting location.
- A GitHub Actions refresh is an option to validate, not an installed automation. Confirm authorized credentials, runtime limits, persistence, repository access and source API constraints before enabling it.
- Preserve raw snapshots and import manifests, separate first-observed times from actual source-event times, and make imports idempotent. Keep collection and calculation separate from display.

Core reporting entities: campaigns; posts; prospects/contacts; channel actions; CRM deals; deal changes; meetings; Video DM status snapshots; source/import coverage. A small reporting workbook or lightweight database can support the first scope.

## Implementation sequence after the plan is settled

1. Create the local visual concept, including the overview and five channel views, filters, freshness indicators and follow-up priorities. No cloud publication is required for this stage.
2. Review layout and metric definitions against the agreed activity/outcome emphasis. Confirm actual versus sample/unavailable data coverage.
3. Create the new private GitHub repository after the concept stage, under the agreed account/organization, and add the project files and documentation.
4. Complete source adapters and the reconciled reporting layer. Add actual stage-event history and snapshots; bring in current Waalaxy/content exports.
5. Reconcile selected periods and records to each source. Test duplicate imports, missing fields, reschedules, backward stage moves, boosted-post overlap and multiple channels touching one lead.
6. Establish an authenticated deployment and daily/manual refresh procedures. Verify access to the page and data, then make it available to the agreed team viewers.

## Acceptance criteria

- Re-importing the same source does not duplicate activity, spend, posts or leads.
- Source totals match for a selected comparable period, or the discrepancy is explained visibly.
- Pipeline movements use actual history, not only today's stage or last-updated time.
- Contacts merely prepared/imported are not counted as messages sent.
- Missing dates and fields remain explicit; historical trend limits are visible.
- Paid spend and attributed outcomes are counted once across ads and boosted content.
- Source outages show stale coverage, retain the last good snapshot and do not replace values with zero.
- A user can trace an overview figure to its metric definition and supporting source records.

## Platform references checked October 14

- Waalaxy supports campaign analytics CSV downloads, with its own response/cohort definitions: https://intercom.help/waalaxy/en/articles/6362393-focus-campaign-dashboard-analytics
- LinkedIn personal-post metrics and boosted-post breakdowns vary by available analytics: https://www.linkedin.com/help/linkedin/answer/a518885?lang=en-US
- Pipedrive documents deal field changelogs and deal flow: https://developers.pipedrive.com/docs/api/v1/Deals
- GitHub Pages hosting and source visibility: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- Restricted Pages access for Enterprise Cloud organizations: https://docs.github.com/en/enterprise-cloud%40latest/pages/getting-started-with-github-pages/changing-the-visibility-of-your-github-pages-site

## Future additions

Calendly detail, collections and delivery/sales costs. Website traffic, newsletter, referral inventory and Pulley preparation are now included as dated supplementary evidence; verified inquiry and attributed commercial outcomes still need instrumentation. Calendly should join the first scope if required to substantiate booked/held-call metrics. Keep other additions modular and do not delay the initial operating dashboard.

## October 14 team review and At a glance

Four Centripetal chats independently reviewed current sources. See SOURCE_REVIEW.md for accepted definitions and gaps. The default screen now follows the five operating vectors in the client-provided GTM Operating Plan. Channel metrics sit underneath, preserving dated, cumulative and snapshot bases. The newsletter live source supersedes its September totals and includes the sender-deleted warning. Pulley remains outbound support; CRM and bookings remain shared outcome systems. No cross-channel total is inferred from overlapping audiences.

## Owner scope clarification

The owner chose to keep the original five dashboard vectors for now: LinkedIn Ads, Waalaxy, LinkedIn content, Pipedrive and Video DMs. At a glance and the prepared source inventory follow that scope. Newsletter, standalone referral/partner reporting, website/inbound and Pulley research remain retained background evidence for future consideration. The five executive cards represent these dashboard vectors, rather than the broader operating-plan categories. Existing CRM pipeline filters remain available.

## Referrals section requested

The owner subsequently added Referrals as a separate sixth category, initially without data. The navigation, At a glance card and dedicated section show planned activity and outcome measures with unavailable values. No earlier CRM inventory or supplemental findings populate these metrics. A future data import requires stable referral identity, event dates, referrer/partner, prospect, owner, follow-up status and linked CRM deal; qualification and source attribution remain explicit.

## Public publication requested and completed

On October 14 the owner requested a shareable live dashboard and selected anyone on the internet as its audience. A sanitized public snapshot is hosted with Sites at https://centripetal-analytics-dashboard.christian399556.chatgpt.site. It excludes prospect identities, private links and record tables while retaining the reporting filters and aggregate metrics. The original internal dataset remains local. This supersedes earlier statements that no public website is deployed; automatic collection and authenticated internal hosting remain future work. See DEPLOYMENT.md for the retained project identity and publication process.

## Detailed public snapshot approved

The owner explicitly approved public prospect identities and available business details, with sign-in/password protection planned later. The hosted package now retains the curated prospect identities, company names, original CRM record links, profile/video links, record tables and ranked content. This supersedes the earlier aggregate-only publication policy. Credentials, raw exports and local paths stay excluded. Source coverage is unchanged; no fresh data collection or automatic refresh is implied.
