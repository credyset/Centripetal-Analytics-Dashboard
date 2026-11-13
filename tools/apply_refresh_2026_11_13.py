"""Build the November 13 curated dashboard from reviewed private source patches."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from apply_refresh_2026_10_23 import (archive_mismatched_row_reviews, assert_curated,
    event_key, merge_message_review, require_current)
from prepare_shared_snapshot import curate_snapshot
from publication_redactions import validate_publication_redactions

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_11_13'
REPORTING_DATE = '2026-11-13'
COMPLETE_THROUGH = '2026-11-12'


def read(path):
    return json.loads(path.read_text())


def native_events(proof, video):
    events = []
    for row in proof['verified']:
        profile, asset = row['profileId'], row['assetId']
        matches = [candidate for candidate in video['rows'] if candidate['id'] == profile
            and candidate.get('recordingAssetId') == asset]
        assert len(matches) == 1 and row['sender'] == 'Charles Solomon'
        matched = matches[0]
        date = row['sourceDate']
        assert date == '2026-11-11' and matched['reportedVideoSentDate'] == date
        fingerprint = hashlib.sha256(f"{profile}|{date}|{row['displayedTime']}|{asset}".encode()).hexdigest()
        events.append(dict(observationId=f'linkedin-ui:2026-11-13:{profile}:outbound:{fingerprint[:23]}',
            dedupKey=f'{profile}|outbound|{date}|{asset}', sourceMessageId=None,
            sourceConversationId=None, profileId=profile, company=matched['company'],
            contact=matched['contact'], sourceRow=matched['sourceRow'],
            sourceInventorySnapshotAt=video['snapshotAt'], crmDealId=None,
            sourceSheetDealId=matched.get('dealId'), sourceKind='native_linkedin_existing_conversation',
            sourceEvidenceBasis='native_direct', date=date, datePrecision='day', occurredAt=None,
            sourceTimezone=None, displayedDateLabel='WEDNESDAY', displayedTime=row['displayedTime'],
            contentFingerprint=fingerprint, observedAsOfDate=REPORTING_DATE,
            dateYearBasis='relative_weekday_with_known_observation_day', dateYearConfidence='high',
            dateBasis='The Wednesday label in the authored message resolves to November 11 in the Friday November 13 browser session. Source timezone is unavailable.',
            channel='linkedin_message', direction='outbound', sender=row['sender'],
            messageKind='initial_video', videoIncluded=True, assetId=asset,
            assetLink=f'https://www.loom.com/share/{asset}', evidenceLink=matched['linkedin'],
            observedAt=proof['recordedAt'], observationClockBasis='Evidence recorded after the signed-in browser review; displayed message day and time are separate.',
            profileIdentityVerified=True, senderVerifiedWithinMessageBlock=True,
            dateTimeAssetAnchoredWithinSameMessageBlock=True,
            evidenceBasis='Exact recipient profile, authored LinkedIn block, displayed day and time, and identical Loom asset.',
            replyToVideoAttributionEstablished=False, platformReadReceiptObserved=False,
            readReceiptDate=None, loomVideoViewedEstablished=False))
    assert len({event_key(event) for event in events}) == len(events)
    return events


def integrate(before, source, generated_at):
    result = deepcopy(before)
    cards = {card['id']: card for card in result['sources']}

    def refresh_card(key, section, status, coverage=None, note=None):
        card = cards.setdefault(key, {'id': key, 'name': key.replace('_', ' ').title()})
        require_current(section, card, key)
        card.update(asOf=section.get('snapshotAt') or section.get('reviewedAt'),
            checkedAt=REPORTING_DATE, status=status)
        if coverage is not None:
            card['coverage'] = deepcopy(coverage)
        if note is not None:
            card['note'] = note

    for key, relative in {'crm': 'crm/crm.json', 'referrals': 'crm/referrals.json',
            'video': 'sheets/video.json', 'waalaxy': 'waalaxy/waalaxy.json',
            'meetings': 'meetings/meetings.json'}.items():
        incoming = read(source / relative)
        require_current(incoming, before[key], key)
        result[key] = incoming
    for key in ('crm', 'referrals', 'video'):
        section = result[key]
        refresh_card(key, section, 'Current independently collected source inventory', section.get('coverage'))
    waalaxy = result['waalaxy']
    refresh_card('waalaxy', {'snapshotAt': waalaxy['sheetSubsetCollectedAt']},
        'Current selected-person worksheet', waalaxy['sheetSubset']['scope'],
        'Selected accepted profiles and historical person attributes have separate coverage from account actions.')
    refresh_card('waalaxy_invitations', {'snapshotAt': result['waalaxy']['invitationCollectedAt']},
        'Current source-date invitation buckets', result['waalaxy']['invitationCoverage'],
        'Earlier CSV buckets and authenticated chart tooltips retain their own provenance. Date attribution and timezone are unavailable.')
    refresh_card('waalaxy_account', result['waalaxy']['accountAnalytics'], 'Current Charles Home account aggregate',
        result['waalaxy']['accountAnalytics']['sourceWindow'], 'The November aggregate reconciles to the observed November buckets and is displayed separately.')
    for card in read(source / 'meetings/source_cards_patch.json'):
        require_current(card, cards.get(card['id']), card['id'])
        cards[card['id']] = card

    creator = read(source / 'linkedin/creator_latest_patch.json')
    assert creator['validation']['allSourceCountsReconciled']
    result['content']['creatorPreviousSnapshot'] = deepcopy(before['content']['creatorAnalytics'])
    result['content']['creatorAnalytics'] = current_creator = creator['creatorAnalytics']
    require_current(current_creator, before['content']['creatorAnalytics'], 'Charles creator analytics')
    result['content']['snapshotAt'] = current_creator['snapshotAt']
    refresh_card('content', current_creator, 'Current Charles personal creator workbook and signed-in chart', current_creator['coverage'],
        'All 90 daily impression rows reconcile to the signed-in chart. The November 13 UTC source day is partial.')
    profile = current_creator['profileAnalytics']
    refresh_card('content_profile', profile, 'Current Charles profile viewer presets', profile['coverage'],
        'Past 90 days and Past 7 days are fixed LinkedIn presets. The November 7–13 chart labels do not define the dashboard week or a selected-period viewer total.')

    observed = read(source / 'ads/browser_observations.json')
    previous_ads = before['ads']['zeroDeliveryReview']
    assert observed['accountId'] == previous_ads['accountId']
    assert observed['adSetIds'] == previous_ads['scope']['adSetIds']
    assert observed['viewFilterCleared'] and observed['allCompleted'] and observed['totalAdSets'] == 7
    assert observed['metrics'] == previous_ads['metrics']
    assert observed['start'] == previous_ads['coverage']['start']
    current_ads = dict(deepcopy(previous_ads), snapshotAt=observed['observedAt'], reviewedAt=generated_at,
        coverage=dict(previous_ads['coverage'], end=observed['end'], completeDaysThrough=COMPLETE_THROUGH),
        retainedPriorReviews=[previous_ads], notes=[
            'The unfiltered authenticated Performance view showed all seven retained ad sets Completed. The aggregate reports $0.00 Spent, 0 Impressions, 0 Clicks and 0 platform Leads for October 22–November 13 UTC, with November 13 partial.',
            'Verified zero applies to these four nonnegative metrics for selections inside the observed interval. Daily exports, per-ad-set dashes, form opens, bookings and video metrics keep their separate coverage.'])
    result['ads']['zeroDeliveryReview'] = current_ads
    refresh_card('ads_zero_delivery', current_ads, 'Current verified zero-delivery aggregate', current_ads['coverage'], current_ads['notes'][0])

    video = result['video']
    fresh_join = source / 'crm/november_video_crm_reconciliation.json'
    if fresh_join.exists():
        join = read(fresh_join)
        assert join['appliesToSnapshotAt'] == video['snapshotAt']
        old = video.get('crmReconciliation')
        if old and old.get('appliesToSnapshotAt') != video['snapshotAt']:
            archive_mismatched_row_reviews(result, before)
        video['crmReconciliation'] = join
        refresh_card('video_crm_reconciliation', join, 'Current targeted November CRM cross-check',
            'Nine November worksheet send dates have valid video assets and no exact CRM match in the reviewed searches.',
            'The separate November 9 follow-up cross-check matched eight earlier asset notes. Neither check establishes a send or reply date.')
    for key in ('gapResolutionReview', 'sourceFreshnessReview', 'sourceFieldAuditReview'):
        child = video.get(key)
        if not child:
            continue
        scope = child.get('appliesToSnapshotAt') or child.get('appliesToVideoInventorySnapshotAt')
        if scope and scope != video['snapshotAt']:
            video.setdefault('historicalSourceReviews', {})[key] = video.pop(key)
    proof = read(source / 'native/verified_sends.json')
    events = native_events(proof, video)
    old_review = before['video']['messageDateReview']
    video['messageDateReview'] = merge_message_review(old_review, {
        'snapshotAt': proof['recordedAt'], 'reviewedAt': proof['recordedAt'],
        'scope': {'videoSnapshotAt': video['snapshotAt']}, 'platformObservedEvents': events,
        'records': [{'profileId': event['profileId'], 'platformVideoAttributionEstablished': True,
            'platformCheckStatus': 'matched', 'platformSendDate': event['date']} for event in events],
        'novemberTargetedReview': {'candidateProfiles': 9, 'exactVerifiedSends': len(events),
            'newRepliesVerified': 0, 'completeAccountCoverage': False, 'reportingDay': '2026-11-11'}},
        video, result['waalaxy']['sheetSubset'], result['waalaxy']['sheetSubsetCollectedAt'])
    video['messageDateReview']['focusedNativeReviews'] = {
        'snapshotAt': proof['recordedAt'], 'reviewedAt': proof['recordedAt'],
        'sourceTimezone': None, 'profilesChecked': len(events),
        'profileChecks': [{
            'profileId': event['profileId'], 'sourceRow': event['sourceRow'],
            'observedAt': event['observedAt'], 'evidenceLink': event['evidenceLink'],
            'sourceEvidenceBasis': 'native_direct', 'profileIdentityVerified': True,
            'senderAccount': 'Charles Solomon', 'coverageCompleteForThread': False,
            'crmAssetMatchRequiredForNativeProof': False, 'assetObserved': True,
            'observationIds': [event['observationId']], 'newVideoSendEvents': 1,
        } for event in events],
        'retainedPriorReviews': [dict(deepcopy(old_review['focusedNativeReviews']), historicalOnly=True)],
        'notes': ['Two exact asset messages verified. The selected threads do not establish complete send or reply coverage.'],
    }
    video['messageDateReview']['summary']['newNovemberObservedVideoSendsAdded'] = len(events)
    for key in ('video_gap_resolution', 'video_connection_dates', 'waalaxy_snapshot_overlap'):
        if key in cards:
            cards[key]['status'] = 'Historical source review; original inventory scope retained'
    refresh_card('video_message_dates', video['messageDateReview'], 'Current bounded native LinkedIn verification',
        f"{len(events)} exact November 11 sends verified in the reviewed cohort. Earlier native proof retains its original observation dates.",
        'Native checks did not establish full send, follow-up or reply coverage. Worksheet dates remain visible as source reports.')
    appearance = video['sourceAppearanceRefresh']
    refresh_card('video_source_freshness', appearance, 'Current workbook and revision comparison',
        'At least 88 distinct profiles first appear in revisions inside November 6–12. Six more are bounded to partial November 13.',
        'First appearances are lower bounds between revisions. Exact row creation times remain unknown.')

    result['meetings']['commercialSourceReview'] = read(source / 'meetings/commercial_candidates_public_summary.json')
    result['time']['meetings'] = read(source / 'meetings/october_time_meetings_addendum.json')
    result['time']['period'].update(end='2026-10-31', currentDayPartial=False)
    result['time']['snapshotAt'] = result['time']['meetings']['snapshotAt']
    result['time']['reviewedAsOf'] = REPORTING_DATE
    result['time']['evidenceCollectionThrough'] = result['time']['snapshotAt']
    result['time']['novemberRecordingReview'] = read(source / 'meetings/november_christian_audio_review.json')
    cards['time'] = read(source / 'meetings/october_time_source_card.json')
    result['sources'] = list(cards.values())
    archive_mismatched_row_reviews(result, before)
    result['meta'].update(generatedAt=generated_at, analyticsRevisedAt=generated_at,
        asOfDate=REPORTING_DATE, reportingAsOfDate=REPORTING_DATE, localReviewOn=REPORTING_DATE,
        defaultReportingThrough=REPORTING_DATE, defaultCompleteReportingThrough=COMPLETE_THROUGH,
        defaultDatePreset='7', currentDayPartial=True, revision='November 13 source refresh',
        lastRevisionNote='At a glance defaults to November 6–12 Mountain. Each source retains its own dates and evidence limits.',
        publicationReview='REFRESH_2026-11-13.md')
    result = curate_snapshot(result)
    assert result['outcomes'] == before['outcomes'], 'Source collection changed owner decisions'
    assert result['time']['summary']['ownerEstimateRange'] == before['time']['summary']['ownerEstimateRange']
    assert {event_key(event) for event in old_review['platformObservedEvents']} <= {
        event_key(event) for event in result['video']['messageDateReview']['platformObservedEvents']}
    assert result['ads']['daily'] == before['ads']['daily']
    assert_curated(result)
    validate_publication_redactions(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=PRIVATE)
    parser.add_argument('--baseline', type=Path, default=PRIVATE / 'baseline.json')
    parser.add_argument('--output', type=Path, default=PRIVATE / 'dashboard_preview.json')
    args = parser.parse_args()
    baseline = read(args.baseline)
    assert baseline['meta']['reportingAsOfDate'] == '2026-10-29'
    result = integrate(baseline, args.source, datetime.now(timezone.utc).isoformat())
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f"Validated preview through {COMPLETE_THROUGH}, with {REPORTING_DATE} partial")


if __name__ == '__main__':
    main()
