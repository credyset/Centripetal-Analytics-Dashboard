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
    outbound_video=[]
    for event in events:
        assert event['profileId'] in by_profile
        assert event['datePrecision']=='day'
        assert event['occurredAt'] is None and event['sourceTimezone'] is None
        assert event['sourceMessageId'] is None and event['sourceConversationId'] is None
        assert event['channel']=='linkedin_message'
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}',event['date'])
        expected='|'.join((event['profileId'],event['direction'],event['date'],event.get('assetId') or 'no-video'))
        assert event['dedupKey']==expected
        if event['direction']=='outbound' and event['videoIncluded'] is True:
            outbound_video.append(event)
            check=check_by_profile.get(event['profileId']);record=by_profile[event['profileId']]
            if check and check.get('assetId')==event['assetId']:
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
            if crm:
                assert event['crmDealId']==crm['crmDealId'] and event['sourceNoteId'] in crm['crmNoteIds']
            else:
                assert event.get('historicalSourceSnapshotAt'), 'Original native proof was detached from its historical CRM scope'
            if 'currentInventorySnapshotAt' in event:
                assert event['currentInventorySnapshotAt']==video['snapshotAt']
                expected_rows=[r['sourceRow'] for r in inventory if r['id']==event['profileId'] and r.get('recordingAssetId')==event['assetId']]
                assert event['currentSourceRows']==expected_rows, 'Historical row number reused as current join'
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
    assert summary['newVerifiedVideoReplyEventsAdded']==0
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=ROOT/'data/shared-dashboard.json')
    data=json.loads(parser.parse_args().snapshot.read_text())
    check_video(data);check_retained_sources(data);check_creator(data)
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
