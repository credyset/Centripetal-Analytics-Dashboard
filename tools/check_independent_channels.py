"""Validate independently collected channel evidence and its reporting boundaries."""
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import argparse
import copy
import json
import re

ROOT=Path(__file__).resolve().parents[1]


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def check_video(data):
    video=data['video'];review=video['messageDateReview'];summary=review['summary']
    records=review['records'];events=review['platformObservedEvents']
    by_profile={r['profileId']:r for r in records}
    assert len(by_profile)==len(records), 'Repeated profile in message-date register'
    assert len(events)==len({e['observationId'] for e in events})
    assert len(events)==len({e['dedupKey'] for e in events}), 'Repeated observed message'
    assert review['scope']['coverageCompleteForAllVideoDmMessages'] is False
    assert summary['accountWideActualVideoSends'] is None
    assert summary['accountWideActualVideoReplies'] is None
    native=review['nativePlatformCoverage'];checks=native['profileChecks']
    assert native['coverageCompleteForAccount'] is False
    assert native['platformMessageIdsAvailable'] is False
    assert native['sourceTimezoneKnown'] is False
    assert len(checks)==len({r['profileId'] for r in checks})==native['cohortProfilesChecked']
    check_by_profile={r['profileId']:r for r in checks}
    matched=[r for r in checks if r['status']=='matched']
    unconfirmed=[r for r in checks if r['status']=='checked_unconfirmed']
    assert len(matched)==native['cohortExactOutboundVideoMatches']
    assert len(unconfirmed)==native['cohortPlatformSendsUnconfirmed']
    assert len(matched)+len(unconfirmed)==len(checks)
    assert all(r['platformSendDate'] is None for r in unconfirmed)
    crm_cohort={(r['profile'],r.get('sourceLoomAssetId')):r for r in video['crmReconciliation']['records'] if r.get('crmDealId')}
    inventory=video['rows']
    focused=review.get('focusedNativeReviews') or {}
    focused_checks=focused.get('profileChecks',[])
    focused_by_profile={r['profileId']:r for r in focused_checks}
    if focused:
        assert len(focused_by_profile)==len(focused_checks)==focused['profilesChecked']
        assert focused['sourceTimezone'] is None
        for check in focused_checks:
            assert check['sourceEvidenceBasis']=='native_direct' and check['profileIdentityVerified'] is True
            assert check['senderAccount']=='Charles Solomon' and check['coverageCompleteForThread'] is False
            assert check['crmAssetMatchRequiredForNativeProof'] is False
            assert timestamp(check['observedAt'])<=timestamp(focused['reviewedAt'])<=timestamp(review['reviewedAt'])
    outbound_video=[]
    for event in events:
        assert event['profileId'] in by_profile
        assert event['datePrecision']=='day'
        assert event['occurredAt'] is None and event['sourceTimezone'] is None
        assert event['sourceMessageId'] is None and event['sourceConversationId'] is None
        assert event['channel']=='linkedin_message'
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',event['date'])
        if event.get('sourceEvidenceBasis')=='native_direct':
            assert event.get('profileIdentityVerified') is True and event.get('senderVerifiedWithinMessageBlock') is True, 'Direct native sender/recipient identity is unverified'
            assert event.get('observedAt') and event.get('dateBasis') and event.get('evidenceBasis')
            assert event.get('displayedDateLabel') and event.get('displayedTime')
            assert re.fullmatch(r'[0-9a-f]{64}',event.get('contentFingerprint','')), 'Direct native message lacks a stable content fingerprint'
            if focused:
                assert event['profileId'] in focused_by_profile
                assert event['observedAt']==focused_by_profile[event['profileId']]['observedAt']
        expected='|'.join((event['profileId'],event['direction'],event['date'],event.get('assetId') or 'no-video'))
        if event.get('contentFingerprint') and not event.get('assetId'):
            assert event.get('displayedTime') and event['contentFingerprint'] in event['dedupKey'], 'Text-event identity lacks its own time/content evidence'
            assert event['dedupKey'].startswith('|'.join((event['profileId'],event['direction'],event['date']))+'|')
        else:
            assert event['dedupKey']==expected
        if event['direction']=='outbound' and event['videoIncluded'] is True:
            outbound_video.append(event)
            check=check_by_profile.get(event['profileId']);record=by_profile[event['profileId']]
            direct=event.get('sourceEvidenceBasis')=='native_direct'
            if direct:
                assert event.get('dateTimeAssetAnchoredWithinSameMessageBlock') is True, 'Asset/sender/date/time were not verified within the same message block'
            elif check and check.get('assetId')==event['assetId']:
                assert check['status']=='matched' and check['platformSendDate']==event['date']
            else:
                assert event.get('historicalSourceSnapshotAt'), 'Message outside current bounded check has no historical provenance'
            asset=urlparse(event['assetLink'])
            assert asset.hostname in ('loom.com','www.loom.com')
            assert asset.path=='/share/'+event['assetId'] and re.fullmatch(r'[0-9a-f]{32}',event['assetId'])
            profile_send_dates=[e['date'] for e in events if e['profileId']==event['profileId'] and e['direction']=='outbound' and e['videoIncluded']]
            assert record['platformSendDate']==max(profile_send_dates), 'Latest observed send must follow actual observed messages'
            assert event['sender']=='Charles Solomon' and record['platformVideoAttributionEstablished'] is True
            crm=crm_cohort.get((event['profileId'],event['assetId'])) or crm_cohort.get((event['profileId'],None))
            if direct:
                # Native message proof is independent of whether the original
                # worksheet or currently accessible CRM notes retain the asset.
                pass
            elif crm:
                assert event['crmDealId']==crm['crmDealId'] and event['sourceNoteId'] in crm['crmNoteIds']
            else:
                assert event.get('historicalSourceSnapshotAt'), 'Original native proof was detached from its historical CRM scope'
            if 'currentInventorySnapshotAt' in event:
                assert event['currentInventorySnapshotAt']==video['snapshotAt']
                expected_assets=[r['sourceRow'] for r in inventory if r['id']==event['profileId'] and r.get('recordingAssetId')==event['assetId']]
                expected_profiles=[r['sourceRow'] for r in inventory if r['id']==event['profileId']]
                assert event['currentSourceRows']==(expected_profiles if direct else expected_assets), 'Historical row number reused as current join'
                if direct:
                    assert event['currentAssetSourceRows']==expected_assets, 'Direct native proof invented a worksheet asset match'
                if event.get('sourceInventorySnapshotAt')!=video['snapshotAt']:
                    assert event['historicalSourceSnapshotAt']==event['sourceInventorySnapshotAt'] and event['sourceRowBasis']
            assert event['readReceiptDate'] is None, 'Undated seen marker became a dated receipt'
            if event['platformReadReceiptObserved']:
                assert event['readReceiptBasis'], 'Observed seen marker has no source basis'
    if 'retainedObservedVideoSendEvents' in summary:
        assert summary['retainedObservedVideoSendEvents']==len(outbound_video)
        assert 0<=summary['newVerifiedVideoSendEventsAdded']<=len(outbound_video)
        assert 0<=summary['previouslyReportedSendsCorroborated']<=len(outbound_video)
    else:
        assert len(outbound_video)==len(matched)==summary['newVerifiedVideoSendEventsAdded']
        assert summary['previouslyReportedSendsCorroborated']==len(outbound_video)
    for check in matched:
        assert any(e['profileId']==check['profileId'] and e['assetId']==check['assetId'] and e['date']==check['platformSendDate'] for e in outbound_video), 'Matched profile has no corresponding observed send'
    assert summary['additionalSendsAboveExistingReportedStatusCount']==0, 'Corroborations became extra sends'
    attributed_replies=[e for e in events if e.get('replyToVideoAttributionEstablished') is True]
    for reply in attributed_replies:
        assert reply['direction']=='inbound', 'Outbound content was treated as an attributed prospect reply'
        assert reply.get('attributionBasis'), 'Video reply attribution requires explicit conversation evidence'
        asset=reply.get('replyToVideoAssetId')
        assert asset and re.fullmatch(r'[0-9a-f]{32}',asset), 'Reply attribution has no exact source video asset'
        assert any(sent['profileId']==reply['profileId'] and sent['assetId']==asset and sent['date']<=reply['date'] for sent in outbound_video), 'Attributed reply has no prior observed matching outbound video'
    assert 0<=summary['newVerifiedVideoReplyEventsAdded']<=len(attributed_replies), 'Incremental replies exceed actual attributed source events'
    if attributed_replies or 'retainedObservedVideoReplyEvents' in summary:
        assert summary.get('retainedObservedVideoReplyEvents')==len(attributed_replies), 'Retained video replies must follow explicit source attribution'
    cypher=by_profile['yaoyuyang']
    cypher_reply=[e for e in events if e['profileId']=='yaoyuyang' and e['direction']=='inbound']
    assert len(cypher_reply)==1 and cypher_reply[0]['videoIncluded'] is False
    assert cypher_reply[0]['assetId'] is None and cypher['platformReplyVideoAttributionEstablished'] is False
    assert cypher['platformReplyDate']==cypher_reply[0]['date']
    source_person=next(r for r in data['waalaxy']['sheetSubset']['rows'] if r['profileId']=='yaoyuyang')
    assert cypher['latestLinkedInReplyDate']==source_person['lastReplyAt'], 'Platform date overwrote person-history attribute'
    email=review['separateEmailContext']
    assert len(email)==len({e['sourceMessageId'] for e in email})==summary['relatedActualOutboundEmails']
    for event in email:
        assert event['channel']=='email' and event['direction']=='outbound'
        assert event['includeInVideoDmTotals'] is False
        assert event['videoIncluded'] is None and event['loomShareLinkPresent'] is False
        assert event['occurredAt'].endswith('Z') and event['sourceTimezone']=='UTC'
    if any('reportedVideoSentDate' in row for row in inventory):
        assert summary['rowsWithReportedSendDate']==sum(bool(r.get('reportedVideoSentDate')) for r in inventory), 'Source-row reports became unique-contact or historical-record totals'
        for profile,record in by_profile.items():
            current=[r for r in inventory if r['id']==profile]
            if 'currentWorksheetReportedSendDates' in record:
                dates=sorted({r['reportedVideoSentDate'] for r in current if r.get('reportedVideoSentDate')})
                assert record['currentWorksheetReportedSendDates']==dates
                assert record.get('reportedSendDate')==(dates[-1] if dates else None), 'Current report field retained a historical date'
    else:
        assert summary['rowsWithReportedSendDate']==sum(bool(r.get('reportedSendDate')) for r in records)


def check_retained_sources(data):
    content=data['content'];company=content['companyAnalytics'];availability=content['companyAvailabilityReview']
    imported=availability['newDailyRowsImported']
    assert isinstance(imported,int) and 0<=imported<=len(company['daily'])
    assert availability['matchesRetainedAggregates'] is True
    assert availability['latestAvailableDate']==company['coverage']['end']==max(r['date'] for r in company['daily'])
    assert availability['reportingWindow']['end']==availability['latestAvailableDate']
    unavailable=availability['unavailableDates']
    assert len(unavailable)==len(set(unavailable))
    assert all(date>availability['latestAvailableDate'] for date in unavailable)
    assert not set(unavailable)&{r['date'] for r in company['daily']}
    for key,value in availability['displayedTotals'].items():assert company['summary']['total'][key]==value
    if 'importedDates' in availability:
        imported_dates=availability['importedDates']
        assert len(imported_dates)==len(set(imported_dates))==imported
        assert set(imported_dates)<={r['date'] for r in company['daily']}
        assert sorted(imported_dates)==sorted(r['date'] for r in company['daily'] if r['date']>availability['previousRetainedThrough'])
    if imported==0:
        assert timestamp(company['collectedAt'])<timestamp(availability['reviewedAt']), 'Availability-only check refreshed old daily-source age'
    else:
        assert company['method']=='Authenticated Charles company-admin XLS export'
        assert company['review']['dailyRows']==len(company['daily'])
        assert company['coverage']['completeWithinExport'] is True
        assert company['coverage']['finalDayPartial'] is False
        assert company['coverage']['requestedEndUnavailable'] in unavailable
        assert all(company['review']['checks'].values()), 'New company days have unreconciled source checks'
    ads=data['ads'];lifecycle=ads['lifecycleReview']
    assert lifecycle['identityVerified'] is True
    assert lifecycle['platformStatus']=='Completed'
    assert lifecycle['adSetsReviewed']==lifecycle['completedAdSets']==7 and lifecycle['activeAdSets']==0
    assert lifecycle['newDailyRowsImported']==0 and lifecycle['concludedAt'] is None
    assert lifecycle['retainedDailyThrough']==ads['coverage']['end']==max(r['date'] for r in ads['daily'])
    assert lifecycle['matchesRetainedExportTotals'] is True
    for key,value in lifecycle['displayedTotals'].items():assert abs(ads['totals'][key]-value)<.001
    assert timestamp(ads['collectedAt'])<timestamp(lifecycle['reviewedAt']), 'Status review refreshed old daily-source age'


def check_creator(data):
    creator=data['content']['creatorAnalytics'];export=creator['exportAnalytics']
    assert creator['account']['identityVerified'] is True and creator['account']['name']=='Charles Solomon'
    assert creator['coverage']['sourceTimezone']=='UTC' and creator['coverage']['finalDayPartial'] is True
    assert [r['date'] for r in creator['daily']]==[r['date'] for r in export['daily']]
    assert len(export['daily'])==len({r['date'] for r in export['daily']})
    total=0
    assert len(creator['chart']['points'])==len(export['daily'])
    for row,point,social_row in zip(export['daily'],creator['chart']['points'],creator['daily']):
        total+=row['impressions']
        assert point['date']==row['date'] and point['cumulativeImpressions']==total
        assert social_row['engagements'] is None, 'Broader export engagement became social-only daily count'
    assert total==creator['summary']['impressions']==export['summary']['impressions']
    assert sum(r['engagements'] for r in export['daily'])==export['summary']['engagements']==creator['summary']['exportEngagements']
    assert sum(creator['summary'][k] for k in ('reactions','comments','reposts','saves','sendsOnLinkedIn'))==creator['summary']['socialEngagements']
    assert export['postCoverage']['completePublishingHistory'] is False
    assert len(export['rankedPosts'])==len({r['postId'] for r in export['rankedPosts']})
    assert sum(r['newFollowers'] for r in export['followers']['daily'])==export['followers']['newFollowersInWindow']
    assert creator['summary']['membersReached']==export['summary']['membersReached']


def check_native_attribution_regressions(data):
    """Direct proof can survive absent joins, while reply attribution needs evidence."""
    fixture=copy.deepcopy(data);review=fixture['video']['messageDateReview']
    original=next(e for e in review['platformObservedEvents']
                  if e['direction']=='outbound' and e['videoIncluded'] is True)
    direct=copy.deepcopy(original)
    asset=next(candidate for candidate in ('a'*32,'b'*32,'c'*32)
               if all(r.get('recordingAssetId')!=candidate for r in fixture['video']['rows']))
    direct.update(observationId='synthetic-native-without-crm-asset',sourceEvidenceBasis='native_direct',
                  assetId=asset,assetLink='https://www.loom.com/share/'+asset,
                  dedupKey='|'.join((original['profileId'],'outbound',original['date'],asset)),
                  crmDealId=None,sourceNoteId=None,
                  currentInventorySnapshotAt=fixture['video']['snapshotAt'],
                  currentSourceRows=[r['sourceRow'] for r in fixture['video']['rows'] if r['id']==original['profileId']],
                  currentAssetSourceRows=[],profileIdentityVerified=True,senderVerifiedWithinMessageBlock=True,
                  dateTimeAssetAnchoredWithinSameMessageBlock=True,contentFingerprint='f'*64)
    # This synthetic fixture exercises message invariants separately from the
    # retained real six-profile proof metadata; it cannot change that source.
    review.pop('focusedNativeReviews',None)
    review['platformObservedEvents'].append(direct)
    review['summary']['retainedObservedVideoSendEvents']=sum(e['direction']=='outbound' and e['videoIncluded'] is True for e in review['platformObservedEvents'])
    check_video(fixture)  # Missing CRM/worksheet asset is not missing native proof.
    reply=copy.deepcopy(direct)
    reply.update(observationId='synthetic-explicit-video-reply',direction='inbound',sender='Synthetic prospect',
                 videoIncluded=False,assetId=None,assetLink=None,
                 dedupKey='|'.join((direct['profileId'],'inbound',direct['date'],'no-video',direct['displayedTime'],'e'*64)),
                 contentFingerprint='e'*64,dateTimeAssetAnchoredWithinSameMessageBlock=False,
                 replyToVideoAttributionEstablished=True,replyToVideoAssetId=asset,
                 attributionBasis='Explicit response to a question about the source video.')
    review['platformObservedEvents'].append(reply)
    review['summary']['retainedObservedVideoReplyEvents']=sum(e.get('replyToVideoAttributionEstablished') is True for e in review['platformObservedEvents'])
    review['summary']['newVerifiedVideoReplyEventsAdded']=1
    check_video(fixture)  # An attributed text reply contains no video itself.
    for mutate in (
        lambda e:e.pop('attributionBasis'),
        lambda e:e.update(replyToVideoAssetId='d'*32),
        lambda e:e.update(direction='outbound'),
    ):
        invalid=copy.deepcopy(fixture)
        target=next(e for e in invalid['video']['messageDateReview']['platformObservedEvents']
                    if e['observationId']=='synthetic-explicit-video-reply')
        mutate(target)
        try:check_video(invalid)
        except AssertionError:pass
        else:raise AssertionError('Unsupported native video-reply attribution was accepted')
    assert fixture.get('outcomes')==data.get('outcomes')
    assert fixture.get('time')==data.get('time')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=ROOT/'data/shared-dashboard.json')
    data=json.loads(parser.parse_args().snapshot.read_text())
    check_video(data);check_retained_sources(data);check_creator(data);check_native_attribution_regressions(data)
    # These checks must reject the damaging interpretations, not just parse JSON.
    for mutate in (
        lambda d:d['video']['messageDateReview']['platformObservedEvents'].append(copy.deepcopy(d['video']['messageDateReview']['platformObservedEvents'][0])),
        lambda d:d['video']['messageDateReview']['summary'].update(accountWideActualVideoSends=9),
        lambda d:d['video']['messageDateReview']['separateEmailContext'][0].update(includeInVideoDmTotals=True),
    ):
        invalid=copy.deepcopy(data);mutate(invalid)
        try:check_video(invalid)
        except AssertionError:pass
        else:raise AssertionError('Invalid business interpretation was accepted')
    for mutate in (
        lambda d:d['content']['companyAvailabilityReview']['unavailableDates'].append(d['content']['companyAnalytics']['coverage']['end']),
        lambda d:d['content']['companyAvailabilityReview']['displayedTotals'].update(impressions=-1),
        lambda d:d['ads']['daily'].append(dict(d['ads']['daily'][-1],date='2099-01-01',spend=0,impressions=0,clicks=0)),
    ):
        invalid=copy.deepcopy(data);mutate(invalid)
        try:check_retained_sources(invalid)
        except AssertionError:pass
        else:raise AssertionError('Invalid source availability or invented paid day was accepted')
    print('Independent channels: scoped platform messages, day precision, reply/email boundaries, retained company/Ads dates and creator reconciliation passed.')


if __name__=='__main__':main()
