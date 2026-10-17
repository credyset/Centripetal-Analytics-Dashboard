# Analytics corrections applied — October 16, 2026

> This records the earlier October 16 correction pass. The later full source refresh and owner confirmations supersede its cutoff and attendance gaps: [LIVE_DATA_REFRESH_2026-10-16.md](LIVE_DATA_REFRESH_2026-10-16.md).

Live dashboard: https://credyset.github.io/Centripetal-Analytics-Dashboard/#glance

This revision applies supported data and interpretation corrections before structural redesign. Source systems were read only. The refreshed referral and recording-review timestamps are separate from the retained October 14 full CRM/calendar snapshots, paid exports and Video DM inventory. Publishing does not make those unchanged feeds current. Business reporting remains anchored through October 13; Christian's effort view retains its explicitly dated October 1–15 scope.

## Applied corrections

| Area | Result | Reporting boundary |
| --- | --- | --- |
| Waalaxy invitation activity | 402 sent / 114 accepted across 31 source-export dates September 15–October 15, including explicit zero days | Invitation-only export; final source day partial, timezone absent. Account attribution follows the prior contributor, because this aggregate CSV contains no account identifier. Acceptances/sends in the same window are not an invitation-cohort conversion rate. |
| Waalaxy display | New invitation figures follow retained source-day date filters; historical prospect/message/reply flags stay separate | Out-of-coverage selections are unavailable. Explicit source zeros are zero. Historical person reference ends June 26, collected July 6. |
| Referrals | 348 source records = 60 active relationship records + 245 Office Hours + 40 Graveyard/Newsletter + 3 explicit tests | 345 non-test business records; current positions are not period introduction events or independently qualified opportunities. One included record remains flagged for review. |
| Referral identities | Robert Adelson excluded as Office Hours; Melanie Ortiz correctly in Intro Made; Jonathan Katz included in Intro Promised | Two previously retained structured history events remain separately dated, rather than being inferred from current stages or latest updates. |
| Referral automation | Recurring-cycle and Trello claims labelled unverified | The automation endpoint did not expose verifiable active configuration. No completion forecasts or assumed successful runs are reported. |
| Fireflies | Eight previously supplied recordings reviewed by purpose and displayed in the existing CRM evidence section | Seven contain dialogue and one has metadata only. They are not eight verified prospect calls or a complete account-wide meeting census. |
| Fireflies classification | Two hiring references, one client recruiting, one client work, one partner/financing, one commercial discovery with unknown qualification, one fundraising/networking and one purpose-unavailable recording | External email domains do not independently establish prospecting intent. No HR opinions, transcript bodies, contact rosters or access URLs are published. |
| Meeting outcomes | No unsupported held-call conversion or qualification added | One recording corroborates a CRM identity; no reviewed recording has a verified Calendly event join. NuVee remains qualified/warm and Venus unqualified; both retain corroborated bookings with attendance unknown. |
| Import safety | Scoped imports are repeatable; newer shared sources survive older local input preparation | Added partition, invitation-total, duplicate-recording and source-preservation checks. The former hardcoded replacement importer is now a compatibility entrypoint requiring explicit inputs. |

See REFERRAL_RECONCILIATION_2026-10-16.md and FIREFLIES_RECONCILIATION_2026-10-16.md for collection scope, source limitations and source-specific checks. The referral connector ignored the requested pipeline filter; the review completed both account pages before filtering to pipeline 4 locally. Fireflies keyword filtering was unreliable; its bounded metadata scan does not prove unmatched calls were never held.

## Most useful owner-supplied exports or confirmations

1. **Charles's Waalaxy campaign analytics / event export:** current invitations, initial/follow-up messages, replies and positive replies, with campaign/prospect IDs, dates, timezone and account identity. The invitation CSV already on disk was used; it does not need resending unless account attribution is incorrect.
2. **Current private LinkedIn analytics:** Charles's profile and the Centripetal company page, with post IDs/URLs, publication dates, metric windows, impressions/clicks/engagement and organic/boosted splits. Public follower observations cannot fill these metrics.
3. **Video DM delivery log or dated workbook fields:** stable prospect/profile/CRM IDs, actual sent date, reply date/outcome and follow-up date. A current undated status export alone cannot reconstruct earlier delivery dates.
4. **A short meeting-outcome confirmation:** NuVee October 6 and Venus October 15: held, canceled or no-show; purpose and next step. No need to resend the full Calendly inventory already accessible. Qualification changes require an explicit owner decision.
5. **Christian-only calendar/work log:** actual October attendance and nonmeeting work, with measured versus recalled/estimated time identified. Existing recording length and draft coordination allowances are not a timesheet.

Full Pipedrive exports are not required for the reconciled referral count: the read-only connector supplied a complete accessible inventory. Remaining CRM status/outcome/value corrections need operational-owner decisions or actual event history, not another flat export. Lead Gen Form submissions are useful when new leads appear or retained counts cease to reconcile.

## Validation

Source totals, unique IDs, disjoint referral partitions, exclusions and retained stage IDs reconcile. Reapplying the same scoped inputs produces no changes. Tests confirm an older local prepared snapshot cannot erase the newer invitation, referral or recording review. Unrelated source sections, owner lead dispositions, Calendly event records, effort estimates and the complete-day reporting cutoff remain unchanged. UI checks cover explicit zero days versus unavailable dates, referral stage inventory versus dated history, and recording index dates versus unverified meeting occurrence.
