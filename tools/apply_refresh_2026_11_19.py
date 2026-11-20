"""Build a private November 19 dashboard preview from independently dated sources."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from apply_refresh_2026_10_23 import (
    archive_mismatched_row_reviews,
    assert_curated,
    event_key,
    merge_message_review,
    require_current,
)
from prepare_shared_snapshot import curate_snapshot
from publication_redactions import validate_publication_redactions

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_11_19'
REPORTING_DATE = '2026-11-19'
COMPLETE_THROUGH = '2026-11-18'


def read(path):
    return json.loads(path.read_text())


def integrate(before, source, generated_at):
    result = deepcopy(before)
    cards = {card['id']: card for card in result['sources']}

    def refresh_card(ident, section, status, coverage=None, note=None):
        card = cards.setdefault(ident, {'id': ident, 'name': ident.replace('_', ' ').title()})
        require_current(section, card, ident)
        card.update(asOf=section.get('snapshotAt') or section.get('reviewedAt'),
                    checkedAt=REPORTING_DATE, status=status)
        card.pop('reviewedAt', None)
        if section.get('reviewedAt'):
            card['reviewedAt'] = section['reviewedAt']
        if section.get('method'):
            card['method'] = section['method']
        if coverage is not None:
            card['coverage'] = deepcopy(coverage)
        if note is not None:
            card['note'] = note
        return card

    for name, relative in {
        'crm': 'crm/crm.json',
        'referrals': 'crm/referrals.json',
        'video': 'sheets/video.json',
        'meetings': 'meetings/meetings.json',
    }.items():
        incoming = read(source / relative)
        require_current(incoming, before[name], name)
        result[name] = incoming

    crm, referrals = result['crm'], result['referrals']
    refresh_card('crm', crm, 'Current independently collected source inventory', crm['coverage'],
                 'Fresh paginated CRM inventory and separately dated history evidence. Record creation, latest updates and source status changes retain their own meanings.')
    refresh_card('referrals', referrals, 'Current same-source Referral Pipeline inventory', referrals['coverage'],
                 'Referral Pipeline 4 is filtered from the same current CRM collection. Current stage positions and administrative cleanup have separate activity and outcome definitions.')
    for relative in ('crm/source_cards_patch.json', 'meetings/source_cards_patch.json'):
        path = source / relative
        if path.exists():
            for card in read(path):
                require_current(card, cards.get(card['id']), card['id'])
                card['checkedAt'] = REPORTING_DATE
                cards[card['id']] = card

    waalaxy = read(source / 'waalaxy/waalaxy.json')
    require_current({'snapshotAt': waalaxy['invitationCollectedAt']},
                    {'snapshotAt': before['waalaxy']['invitationCollectedAt']}, 'invitation buckets')
    waalaxy.update(read(source / 'sheets/waalaxy_sheet_subset_patch.json'))
    account = waalaxy['accountAnalytics']
    account['preparedAt'] = generated_at
    percent = account['platformDisplayedRates']['acceptancePercent']
    account['platformDisplayedRates']['note'] = (
        f'The {percent:g}% acceptance percentage is descriptive and supplied by Waalaxy. '
        'Matched invitation-cohort conversion is unavailable.')
    result['waalaxy'] = waalaxy
    refresh_card('waalaxy', {'snapshotAt': waalaxy['invitationCollectedAt']},
                 'Current Charles invitation buckets and selected-person worksheet', waalaxy['invitationCoverage'],
                 'Authenticated source-day invitation buckets and the separately collected selected-person subset retain independent clocks. Source timezone and upstream synchronization time are unavailable.')
    refresh_card('waalaxy_invitations', {'snapshotAt': waalaxy['invitationCollectedAt']},
                 'Current authenticated source-date invitation buckets', waalaxy['invitationCoverage'],
                 'November source-day buckets reconcile to the fixed Home aggregate. Historical acceptance-bucket restatements are recorded separately from new source dates.')
    refresh_card('waalaxy_account', account, 'Current Charles Home account aggregate', account['sourceWindow'],
                 'The displayed November 1–20 source aggregate includes the final partial day and overlaps the dated invitation series.')

    creator_patch = read(source / 'linkedin/creator_latest_patch.json')
    assert creator_patch['validation']['allSourceCountsReconciled']
    creator = creator_patch['creatorAnalytics']
    require_current(creator, before['content']['creatorAnalytics'], 'Charles creator analytics')
    result['content']['creatorPreviousSnapshot'] = deepcopy(before['content']['creatorAnalytics'])
    result['content']['creatorAnalytics'] = creator
    result['content']['snapshotAt'] = creator['snapshotAt']
    refresh_card('content', creator, 'Current Charles creator workbook and signed-in chart', creator['coverage'],
                 'All 90 daily impression buckets reconcile to the authenticated chart. UTC source days, overlapping-date restatements and the partial November 20 day retain their own scope.')
    profile = creator['profileAnalytics']
    refresh_card('content_profile', profile, 'Current Charles profile viewer presets', profile['coverage'],
                 'Past 90 days and Past 7 days are fixed LinkedIn presets. The displayed seven chart points differ from the 171-viewer aggregate and retain separate evidence.')

    observed = read(source / 'ads/browser_observations.json')
    prior_zero = before['ads']['zeroDeliveryReview']
    assert observed['accountId'] == prior_zero['accountId']
    assert observed['start'] == prior_zero['coverage']['start']
    assert observed['viewFilterCleared'] and observed['allCompleted'] and observed['adSetsReviewed'] == 7
    assert observed['metrics'] == prior_zero['metrics']
    zero = deepcopy(prior_zero)
    zero.update(snapshotAt=observed['observedAt'], reviewedAt=generated_at,
                retainedPriorReviews=[deepcopy(prior_zero)])
    zero['coverage'].update(end=observed['end'], completeDaysThrough='2026-11-19', finalDayPartial=True)
    zero['notes'] = [
        'Authenticated Performance aggregate shows all seven ad sets Completed with zero spend, impressions, clicks and platform leads from October 22–November 20 UTC. November 20 is partial.',
        'The verified nonnegative aggregate supports zero for contained date selections. Existing exports, form opens and lead qualification keep their original coverage.',
    ]
    result['ads']['zeroDeliveryReview'] = zero
    refresh_card('ads_zero_delivery', zero, 'Current verified zero-delivery aggregate', zero['coverage'], zero['notes'][0])

    video = result['video']
    refresh_card('video', video, 'Current complete workbook inventory', video['coverage'],
                 'Current literal source dates and recording fields were reread across both complete tab ranges. Native observations and CRM joins retain independently dated evidence.')
    refresh_card('video_source_freshness', video['sourceAppearanceRefresh'],
                 'Current workbook and bounded revision comparison',
                 'At least 52 distinct first appearances in November 12–18 and 147 month to date through November 18.',
                 'The month-to-date floor represents 152 row occurrences. Forty-seven additional identities cross the November 18/19 Mountain cutoff and remain unassigned to either day.')

    video_join = source / 'crm/video_crm_patch.json'
    if video_join.exists():
        patch = read(video_join)
        by_row = {(row['sourceRow'], row['id']): row for row in video['rows']}
        for change in patch.get('rowUpdates', []):
            key = change['sourceRow'], change.get('id') or change.get('profile')
            assert key in by_row
            by_row[key].update(change)
        if patch.get('crmReconciliation'):
            video['crmReconciliation'] = patch['crmReconciliation']
    join = video['crmReconciliation']
    refresh_card('video_crm_reconciliation', join, 'Independently dated fixed-cohort CRM crosswalk',
                 join['scope'], 'Current worksheet identity and asset continuity is verified. CRM record observations retain the collection dates and bounded search scope recorded in this review.')

    native_path = source / 'native/message_date_patch.json'
    if native_path.exists():
        native_patch = read(native_path)
        video['messageDateReview'] = merge_message_review(
            video['messageDateReview'], native_patch, video,
            waalaxy['sheetSubset'], waalaxy['sheetSubsetCollectedAt'])
        if native_patch.get('focusedNativeReviews'):
            # This is a newly scoped review group with prior groups nested in it.
            video['messageDateReview']['focusedNativeReviews'] = deepcopy(native_patch['focusedNativeReviews'])
    message_review = video['messageDateReview']
    refresh_card('video_message_dates', message_review, 'Independently dated native conversation evidence',
                 'Profile, message date, sender and asset observations retain their original clocks.',
                 'The worksheet refresh establishes no additional native messages. New conversation checks are merged by stable observed-message identity.')
    for ident in ('video_gap_resolution', 'video_connection_dates', 'waalaxy_snapshot_overlap'):
        if ident in cards:
            cards[ident]['status'] = 'Historical source review; original inventory scope retained'

    meeting_source = source / 'meetings'
    commercial = meeting_source / 'commercial_candidates_public_summary.json'
    if commercial.exists():
        result['meetings']['commercialSourceReview'] = read(commercial)
        result['meetings']['commercialSourceReview']['period'].update(
            end=REPORTING_DATE, currentDayPartial=True)
    crm_commercial = source / 'crm/commercial_candidates.json'
    if crm_commercial.exists():
        context = read(crm_commercial)
        review = result['meetings']['commercialSourceReview']
        review['crmContextReview'] = context
        review['sourceCollectionClocks'] = {
            'meetings': review['snapshotAt'], 'crm': context['snapshotAt']}
        review['snapshotAt'] = max(review['snapshotAt'], context['snapshotAt'])
        existing = {(item.get('dealId'), item['date']) for item in review['cases']}
        for case in context['cases']:
            key = case.get('dealId'), case['date']
            if case['category'] == 'source_closed_lost' and key not in existing:
                review['cases'].append(deepcopy(case))
                existing.add(key)
    approval_path = meeting_source / 'increase_alpha_commercial_approval.json'
    if approval_path.exists():
        approval = read(approval_path)
        assert approval['sourceQualificationVerified'] is True
        assert approval['qualificationEvidenceBasis'] == 'direct_charles_commercial_approval'
        opportunity = deepcopy(approval['observedOpportunity'])
        opportunity['reviewedAt'] = approval['reviewedAt']
        assert opportunity['originalAcceptedAt'] is None
        assert opportunity['originalAcceptanceDateVerified'] is False
        result['meetings']['sourceObservedOpportunities'] = [opportunity]
    audio = meeting_source / 'november_christian_audio_review.json'
    if audio.exists():
        result['time']['novemberRecordingReview'] = read(audio)
        audio_review = result['time']['novemberRecordingReview']
        refresh_card('time_november', audio_review,
                     'Current independently reviewed November recording context',
                     audio_review.get('coverage') or audio_review.get('period'),
                     'Associated recording duration is a source proxy. The independently dated October owner effort estimate retains its original period.')

    result['sources'] = list(cards.values())
    archive_mismatched_row_reviews(result, before)
    result['meta'].update(generatedAt=generated_at, analyticsRevisedAt=generated_at,
        asOfDate=REPORTING_DATE, reportingAsOfDate=REPORTING_DATE, localReviewOn=REPORTING_DATE,
        defaultReportingThrough=REPORTING_DATE, defaultCompleteReportingThrough=COMPLETE_THROUGH,
        defaultDatePreset='7', currentDayPartial=True, revision='November 19 source refresh',
        lastRevisionNote='The default reporting window is November 12–18 Mountain. Source-day buckets and current partial days retain explicit coverage.',
        publicationReview='REFRESH_2026-11-19.md')
    result = curate_snapshot(result)
    previous_outcomes, current_outcomes = before['outcomes'], result['outcomes']
    assert current_outcomes['opportunityAcceptances'] == previous_outcomes['opportunityAcceptances']
    assert current_outcomes['clientWins'] == previous_outcomes['clientWins']
    assert all(item in current_outcomes['heldCalls'] for item in previous_outcomes['heldCalls'])
    prior_call_ids = {item['conversationId'] for item in previous_outcomes['heldCalls']}
    source_calls = {item['conversationId']: item for item in result['meetings'].get('sourceVerifiedHeldCalls', [])}
    for call in current_outcomes['heldCalls']:
        if call['conversationId'] not in prior_call_ids:
            assert call == source_calls[call['conversationId']], 'New held call has no independently verified source record'
    assert result['time']['summary'] == before['time']['summary'], 'Source refresh changed the owner effort estimate'
    assert result['time']['meetings'] == before['time']['meetings'], 'November refresh changed the October audio context'
    for key in ('ownerConfirmedHeldCalls', 'sourceVerifiedHeldCalls'):
        previous = before['meetings'].get(key, [])
        current = result['meetings'].get(key, [])
        assert all(item in current for item in previous), f'Prior {key} evidence was discarded'
    previous_events = {event_key(event): event for event in before['video']['messageDateReview']['platformObservedEvents']}
    current_events = {event_key(event): event for event in result['video']['messageDateReview']['platformObservedEvents']}
    assert previous_events.keys() <= current_events.keys()
    for key, old in previous_events.items():
        current = current_events[key]
        assert current.get('date') == old.get('date')
        assert current.get('observedAt') == old.get('observedAt'), 'Inventory refresh re-dated native proof'
    assert result['ads']['daily'] == before['ads']['daily']
    # Fresh Calendly identity evidence can refresh the nested booking source.
    # Lead identities, dispositions and owner outcome fields retain their values.
    lead_fields = lambda row: {key: value for key, value in row.items() if key != 'bookingCorroboration'}
    assert [lead_fields(row) for row in result['ads']['leads']] == [lead_fields(row) for row in before['ads']['leads']]
    assert_curated(result)
    validate_publication_redactions(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=PRIVATE)
    parser.add_argument('--baseline', type=Path, default=PRIVATE / 'baseline.json')
    parser.add_argument('--output', type=Path, default=PRIVATE / 'dashboard_preview.json')
    args = parser.parse_args()
    before = read(args.baseline)
    assert before['meta']['reportingAsOfDate'] == '2026-11-13'
    result = integrate(before, args.source, datetime.now(timezone.utc).isoformat())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    args.output.chmod(0o600)
    print(f'Prepared private preview through {COMPLETE_THROUGH}, with {REPORTING_DATE} partial')


if __name__ == '__main__':
    main()
