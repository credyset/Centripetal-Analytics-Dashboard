"""Integrate independently reviewed evidence for October 30–November 12."""
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from apply_refresh_2026_10_23 import assert_curated, event_key, merge_message_review, require_current
from prepare_shared_snapshot import curate_snapshot
from publication_redactions import validate_publication_redactions

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private'
REFRESH = PRIVATE / 'refresh_2026_11_13'
AUDIT = PRIVATE / 'audit_2026_11_13_14day'
START, END, PARTIAL = '2026-10-30', '2026-11-12', '2026-11-13'


def read(path):
    return json.loads(path.read_text())


def review_messages(before, video, waalaxy, proof):
    keyed_rows = {(row['sourceRow'], row['id']): row for row in video['rows']}
    prior = before['messageDateReview']
    seen_keys = {event_key(row) for row in prior['platformObservedEvents']}
    events, records, checks = [], {}, defaultdict(list)
    for thread in proof:
        profile = thread['profileId']
        source = keyed_rows[thread['sourceRow'], profile]
        for block in thread['events']:
            kind, date, shown_time = block['kind'], block['day'], block['displayedTime']
            asset = block.get('assetId')
            assert START <= date <= PARTIAL
            if kind == 'initial_video':
                assert date == source['reportedVideoSentDate'] and asset == source['recordingAssetId']
            elif kind == 'video_follow_up':
                assert date == PARTIAL or date == source['reportedFollowUpSentDate']
            else:
                assert kind == 'general_reply' and profile == 'walidromaya'
            inbound = kind == 'general_reply'
            direction = 'inbound' if inbound else 'outbound'
            fingerprint = hashlib.sha256(f'{profile}|{direction}|{date}|{shown_time}|{kind}|{asset}'.encode()).hexdigest()
            label = {'2026-11-05': 'NOV 5', '2026-11-09': 'MONDAY', '2026-11-11': 'WEDNESDAY', PARTIAL: 'TODAY'}[date]
            event = dict(observationId=f'linkedin-ui:2026-11-13:{profile}:{direction}:{fingerprint[:23]}',
                dedupKey=f'{profile}|{direction}|{date}|{asset or shown_time + ":" + fingerprint}',
                sourceMessageId=None, sourceConversationId=None, profileId=profile,
                company=source['company'], contact=source['contact'], sourceRow=source['sourceRow'],
                sourceInventorySnapshotAt=video['snapshotAt'], sourceSheetDealId=source.get('dealId'),
                sourceKind='native_linkedin_existing_conversation', sourceEvidenceBasis='native_direct',
                date=date, datePrecision='day', occurredAt=None, sourceTimezone=None,
                displayedDateLabel=label, displayedTime=shown_time, contentFingerprint=fingerprint,
                observedAsOfDate=PARTIAL, dateBasis='Visible message day anchored to the signed-in November 13 review. Source timezone is unknown.',
                channel='linkedin_message', direction=direction, sender=source['contact'] if inbound else 'Charles Solomon',
                messageKind=kind, videoIncluded=bool(asset), assetId=asset,
                assetLink=f'https://www.loom.com/share/{asset}' if asset else None,
                evidenceLink=source['linkedin'], observedAt=thread['observedAt'], profileIdentityVerified=True,
                senderVerifiedWithinMessageBlock=True, dateTimeAssetAnchoredWithinSameMessageBlock=bool(asset),
                evidenceBasis='Matching recipient, author, source day and displayed time in the same LinkedIn conversation.',
                replyToVideoAttributionEstablished=False, platformReadReceiptObserved=block['seen'],
                readReceiptDate=None, loomVideoViewedEstablished=False)
            if block['seen']:
                event.update(readReceiptBasis='The exact authored message had an undated LinkedIn Seen marker.',
                    readReceiptSourceObservedAt=thread['observedAt'], readReceiptAppliesTo='linkedin_message_only')
            if inbound:
                event['replyContext'] = block['context']
            key = event_key(event)
            assert key not in seen_keys, 'Duplicate observed message'
            seen_keys.add(key)
            events.append(event)
            checks[profile].append(event)
            record = records.setdefault(profile, {'profileId': profile})
            if asset:
                record.update(platformVideoAttributionEstablished=True, platformCheckStatus='matched')
            elif inbound:
                record.update(platformReplyVideoAttributionEstablished=False, platformReplyDate=date,
                    platformReplyBasis=block['context'])
            else:
                record['platformFollowUpDate'] = max(record.get('platformFollowUpDate', ''), date)

    observed_at = max(thread['observedAt'] for thread in proof)
    selected = [row for row in events if row['date'] <= END]
    patch = dict(snapshotAt=observed_at, reviewedAt=observed_at,
        scope={'videoSnapshotAt': video['snapshotAt']}, platformObservedEvents=events, records=list(records.values()))
    merged = merge_message_review(prior, patch, video, waalaxy['sheetSubset'], waalaxy['sheetSubsetCollectedAt'])
    merged['focusedNativeReviews'] = dict(snapshotAt=observed_at, reviewedAt=observed_at, sourceTimezone=None,
        profilesChecked=len(checks), profileChecks=[dict(profileId=profile, sourceRow=rows[0]['sourceRow'],
            observedAt=rows[0]['observedAt'], evidenceLink=rows[0]['evidenceLink'], sourceEvidenceBasis='native_direct',
            profileIdentityVerified=True, senderAccount='Charles Solomon', coverageCompleteForThread=False,
            crmAssetMatchRequiredForNativeProof=False, observationIds=[r['observationId'] for r in rows],
            assetObserved=any(r['videoIncluded'] for r in rows)) for profile, rows in checks.items()],
        retainedPriorReviews=[dict(deepcopy(prior['focusedNativeReviews']), historicalOnly=True)],
        notes=['Targeted native LinkedIn review. Additional sends or replies outside the reviewed threads remain unmeasured.'])
    sends = [r for r in merged['platformObservedEvents'] if START <= r['date'] <= END and r['videoIncluded'] and r['direction'] == 'outbound']
    followups = [r for r in selected if r['messageKind'] == 'video_follow_up']
    reported_sends = {(r['contactId'], r['date']) for r in video['datedActions'] if START <= r['date'] <= END and r['type'] == 'Send status'}
    reported_followups = {(r['contactId'], r['date']) for r in video['datedActions'] if START <= r['date'] <= END and r['type'] == 'Follow-up status'}
    assert len(sends) == len(reported_sends) == 19 and {(r['profileId'], r['date']) for r in sends} == reported_sends
    assert len(followups) == len(reported_followups) == 13 and {(r['profileId'], r['date']) for r in followups} == reported_followups
    merged['fourteenDayNativeReview'] = dict(start=START, end=END, reportedSends=19, verifiedSends=19,
        reportedFollowUps=13, verifiedFollowUps=13, generalRepliesObserved=1, videoAttributedRepliesObserved=0,
        accountCoverageComplete=False, partialDayFollowUpsObserved=sum(r['date'] == PARTIAL for r in events))
    merged['summary']['newNovemberObservedVideoSendsAdded'] = len(sends)
    return merged


def integrate(before, generated_at):
    result = deepcopy(before)
    video = read(REFRESH / 'bridge_14d_video/video.json')
    require_current(video, before['video'], 'Video worksheet')
    crosswalk = read(REFRESH / 'bridge_14d_video/crm_14d_patch.json')
    rows = {(row['sourceRow'], row['id']): row for row in video['rows']}
    for update in crosswalk['rowUpdates']:
        rows[update['sourceRow'], update['id']].update(update)
    video['crmReconciliation'] = crosswalk['crmReconciliation']
    video['messageDateReview'] = review_messages(before['video'], video, result['waalaxy'],
        read(AUDIT / 'native/thread_observations.json'))
    result['video'] = video

    crm_path = AUDIT / 'crm'
    result['crm']['mailboxReview'] = read(crm_path / 'crm_mailbox_review_patch.json')
    result['referrals']['eventReview'] = read(crm_path / 'referral_event_review_patch.json')
    crm_summary = read(crm_path / 'crm_14day_summary.json')
    result['crm']['fourteenDayReview'] = {key: crm_summary[key] for key in ('period', 'periodCounts', 'november5Cleanup')}
    result['video']['crmReportedReplyContext'] = crm_summary['video']['crmReportedNonBuyerReply']

    meetings_path = REFRESH / 'meetings'
    meetings = result['meetings']
    meetings['fireflies'].update(read(meetings_path / 'fireflies_14d_patch.json'))
    review = read(meetings_path / 'commercial_candidates_14d_public_summary.json')
    review['cases'].extend(read(crm_path / 'bridge_commercial_source_cases.json')['cases'])
    meetings['commercialSourceReview'] = review
    calls = read(meetings_path / 'held_calls_14d_patch.json')['heldCalls']
    venus = crm_summary['venusHeldEvidence']
    assert venus['occurredEarlierInWeek'] and not venus['exactActualDayEstablished']
    calls.append(dict(conversationId='mailbox:venus-ai:2026-11-02-week', companyKey='company:venus-ai-consulting',
        company='Venus AI Consulting', dealId=venus['dealId'], heldAt=None,
        heldDateRange={'start': '2026-11-02', 'end': '2026-11-05'},
        charlesParticipated=True, prospectMeeting=True, heldConfirmed=True, qualification='unknown',
        dateBasis='Charles’s November 6 email confirms a negotiation phone call earlier that week. An updated invitation scheduled November 3. The exact held day remains unresolved.',
        evidenceBasis='Charles-authored post-call Team Sales Inbox message and dated reschedule.',
        reviewedAt=crm_summary['mailboxReviewAt']))
    meetings['sourceVerifiedHeldCalls'] = calls
    review['headline']['heldProspectCalls'] = f'≥{len(calls)}'
    review['snapshotAt'] = max(review['snapshotAt'], crm_summary['mailboxReviewAt'])
    review['note'] = 'The bounded recording and mailbox review confirms two held conversations in the first week. Complete coverage and commercial decisions still require Charles’s dated confirmation.'

    cards = {card['id']: card for card in result['sources']}
    for card in read(crm_path / 'source_cards_patch.json') + [read(meetings_path / 'fireflies_14d_source_card.json')]:
        require_current(card, cards.get(card['id']), card['id'])
        cards[card['id']] = card
    cards['video'].update(asOf=video['snapshotAt'], note='Both worksheet tabs checked again. Four literal partial-day November 13 follow-up dates were added. One prose-only date cell was excluded.')
    cards['video_source_freshness'].update(asOf=video['sourceAppearanceRefresh']['reviewedAt'],
        coverage='At least 138 distinct first appearances across 143 added row occurrences in verified intervals within October 30–November 12.',
        note='First appearances are bounded by worksheet revisions. Exact creation times remain unavailable.')
    cards['video_message_dates'].update(asOf=video['messageDateReview']['reviewedAt'],
        coverage='19 sends and 13 follow-ups verified in the 14-day worksheet cohort. One general inbound reply was observed.',
        note='All known worksheet reports in the cohort have exact native matches. Complete account-wide activity and video-attributed replies remain unmeasured.')
    cards['video_crm_reconciliation'].update(coverage='Nine of 19 dated video assets have exact profile and Loom links in CRM notes. All 19 sends are independently verified in LinkedIn.')
    result['sources'] = list(cards.values())
    result['meta'].update(generatedAt=generated_at, analyticsRevisedAt=generated_at,
        revision='November 13 fourteen-day accuracy review', publicationReview='ACCURACY_REVIEW_2026-11-13.md',
        lastRevisionNote='14 complete days audited. The seven-day At a glance default stays anchored to November 6–12.')
    result = curate_snapshot(result)
    assert result['outcomes']['opportunityAcceptances'] == before['outcomes']['opportunityAcceptances']
    assert result['outcomes']['clientWins'] == before['outcomes']['clientWins']
    assert result['ads'] == before['ads'] and result['content'] == before['content']
    assert_curated(result)
    validate_publication_redactions(result)
    return result


if __name__ == '__main__':
    baseline = read(AUDIT / 'baseline.json')
    result = integrate(baseline, datetime.now(timezone.utc).isoformat())
    (AUDIT / 'dashboard_preview.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
