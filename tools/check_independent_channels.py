"""Validate independently collected channel evidence and its reporting boundaries."""
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
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
    crm_cohort={r['profile']:r for r in video['crmReconciliation']['records'] if r.get('crmDealId')}
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
            check=check_by_profile[event['profileId']];record=by_profile[event['profileId']]
            assert check['status']=='matched' and check['assetId']==event['assetId']
            asset=urlparse(event['assetLink'])
            assert asset.hostname in ('loom.com','www.loom.com')
            assert asset.path=='/share/'+event['assetId'] and re.fullmatch(r'[0-9a-f]{32}',event['assetId'])
            assert check['platformSendDate']==event['date']==record['platformSendDate']==record['reportedSendDate']
            assert event['sender']=='Charles Solomon' and record['platformVideoAttributionEstablished'] is True
            crm=crm_cohort[event['profileId']]
            assert event['crmDealId']==crm['crmDealId'] and event['sourceNoteId'] in crm['crmNoteIds']
            assert event['readReceiptDate'] is None, 'Undated seen marker became a dated receipt'
            if event['platformReadReceiptObserved']:
                assert event['readReceiptBasis'], 'Observed seen marker has no source basis'
    assert len(outbound_video)==len(matched)==summary['newVerifiedVideoSendEventsAdded']
    assert summary['previouslyReportedSendsCorroborated']==len(outbound_video)
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
    assert summary['rowsWithReportedSendDate']==sum(bool(r.get('reportedSendDate')) for r in records)


def check_retained_sources(data):
    content=data['content'];company=content['companyAnalytics'];availability=content['companyAvailabilityReview']
    assert availability['newDailyRowsImported']==0 and availability['matchesRetainedAggregates'] is True
    assert availability['latestAvailableDate']==company['coverage']['end']==max(r['date'] for r in company['daily'])
    assert availability['reportingWindow']['end']==availability['latestAvailableDate']
    assert not set(availability['unavailableDates'])&{r['date'] for r in company['daily']}
    for key,value in availability['displayedTotals'].items():assert company['summary']['total'][key]==value
    assert timestamp(company['collectedAt'])<timestamp(availability['reviewedAt']), 'Availability check refreshed old daily-source age'
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
    data=json.loads((ROOT/'data/shared-dashboard.json').read_text())
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
    print('Independent channels: scoped platform messages, day precision, reply/email boundaries, retained company/Ads dates and creator reconciliation passed.')


if __name__=='__main__':main()
