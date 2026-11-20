"""Check the portable, curated reporting snapshot before sharing changes."""
from pathlib import Path
import argparse
from datetime import date, datetime
import json
from publication_redactions import validate_publication_redactions
from video_connection_inventory import validate_video_connection_inventory

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--snapshot', type=Path, default=ROOT/'data/shared-dashboard.json')
source = parser.parse_args().snapshot
data = json.loads(source.read_text())
validate_publication_redactions(data)
validate_video_connection_inventory(data.get('video') or {})
assert all(k in data for k in ('meta','ads','crm','video','waalaxy','content','referrals','time','sources'))
assert data['meta']['timezone'] == 'America/Denver'
# Every retained daily series below is already normalized to one account/source
# grain. A repeated day cannot substitute for an absent reporting day.
creator=data.get('content',{}).get('creatorAnalytics',{}).get('exportAnalytics',{})
daily_series=[('creator',creator.get('daily',[])),
              ('creator followers',creator.get('followers',{}).get('daily',[])),
              ('company',data.get('content',{}).get('companyAnalytics',{}).get('daily',[])),
              ('ads',data.get('ads',{}).get('daily',[])),
              ('invitations',[r for r in data.get('waalaxy',{}).get('daily',[])
                              if r.get('invitationsSent') is not None or r.get('invitationsAccepted') is not None])]
for label,series in daily_series:
    days=[r['date'] for r in series]
    assert len(days)==len(set(days)), f'Duplicate source day in {label}'
    assert all(isinstance(day,str) and date.fromisoformat(day).isoformat()==day for day in days), f'Invalid source day in {label}'


# This opaque source ID is employment evidence, outside prospect-publication scope.
# Guard by source identity rather than a candidate-name blacklist, so aliases and
# new personal-context fields cannot quietly return during a later source merge.
employment_exclusions={'01M5CWDYQKG89SJR4KZ07H7DQ3'}
employment_title='Recruiting interview (excluded from business-development outcomes)'
employment_allowed={'id','recordingId','title','indexedAt','occurredAt','dateBasis','durationMinutes',
    'classification','classificationBasis','reviewedDialogue','sentenceCount','speakerCount',
    'charlesSpeakerConfirmed','christianSpeakerLabelObserved','charlesListedInParticipants',
    'evidenceCollectedAt','sourceEvidenceSha256','commercialOutcomeDecisionApplied',
    'qualificationDecisionApplied','ownerReviewRequired','audioDurationIsAttendance','crmDealIds',
    'publicationPolicy'}
def check_employment_publication(value):
    if isinstance(value,dict):
        if value.get('id',value.get('recordingId')) in employment_exclusions:
            assert value.get('title')==employment_title, 'Excluded employment source restored a personal recording title'
            assert set(value)<=employment_allowed, 'Unnecessary personal employment fields entered the public record'
            policy=value.get('publicationPolicy',{})
            assert policy.get('scope')=='employment_context_minimized'
            assert policy.get('requiredDisplayTitle')==employment_title
            assert all(policy.get(k) is True for k in ['candidateIdentityWithheld','originalTitleWithheld',
                'employmentDetailsWithheld','recordingAccessLinksWithheld','rawEvidenceRetainedPrivately'])
            assert value.get('classificationBasis')=='Employment/recruiting purpose verified; excluded from business-development outcomes. Personal employment details are withheld from publication.'
        for item in value.values():check_employment_publication(item)
    elif isinstance(value,list):
        for item in value:check_employment_publication(item)
check_employment_publication(data)
for entity in ('deals','activities'):
    rows = data['crm'][entity]
    assert len(rows) == len({row['id'] for row in rows}), f'Duplicate CRM {entity} IDs'
assert len(data['video']['rows']) == data['video']['summary']['sourceRows']
company_targets=data['video'].get('companyOnlyTargets')
if company_targets is not None:
    video=data['video'];summary=video['summary'];coverage=video['sourceCoverage']
    assert len(company_targets)==summary['companyOnlyTargetRows']
    assert summary['allTargetRows']==summary['sourceRows']+len(company_targets)
    assert len(company_targets)==len({r['sourceRow'] for r in company_targets})
    assert not ({r['sourceRow'] for r in company_targets}&{r['sourceRow'] for r in video['rows']})
    for row in company_targets:
        assert row.get('company') and type(row['sourceRow']) is int
        assert set(row)<={'sourceRow','company','status','action','score','rank','tier','stage'}
        assert all(isinstance(v,str) for k,v in row.items() if k!='sourceRow')
    assert coverage['allTargetRows']==summary['allTargetRows']
    assert coverage['mainReturnedRowsIncludingHeader']==1+summary['allTargetRows']+coverage['excludedNonProspectPhysicalRows']

archive=data['crm'].get('archiveReview')
if archive:
    assert archive['success'] and archive['paginationComplete']
    assert archive['actualFirstClientWins'] is None
audit=data['video'].get('sourceVerification')
if audit:
    join=audit['crmJoin']
    assert join['foundRows']+len(join['missingDealIds'])==join['distinctSheetDealIds']==join['sheetRowsWithDealId']
    assert join['organizationIdMatchedRows']+len(join['organizationIdMismatchRows'])==join['organizationIdComparableRows']
    assert sum(join['ownerRows'].values())==join['foundRows']
    assert audit['verifiedVideoDmSends'] is None and audit['verifiedReplyEvents'] is None
context=data['crm'].get('commercialContextReview')
if context:
    assert context['confirmedOutcomeAdditions']==0
    assert len(context['records'])==len({r['dealId'] for r in context['records']})
    assert {r['dealId'] for r in context['records']}<={r['id'] for r in data['crm']['deals']}
reply_context=data['waalaxy'].get('replyContextReview')
if reply_context:
    assert not any(reply_context['counterChanges'].values())
    for record in reply_context['records']:
        assert record['occurredAt'] is None and record['eventId'] is None
        assert record['outboundVideoEvidence'] is False
        assert record['datePrecision']=='date_only' and record['sourceTimezone'] is None
        matched=[r for r in data['waalaxy']['sheetSubset']['rows'] if r['profileId']==record['profileId']]
        assert len(matched)==1 and matched[0]['lastReplyAt']==record['latestReplyDate']
assert abs(sum(row['spend'] for row in data['ads']['daily'])-data['ads']['totals']['spend']) < .02
ad_review=data['ads'].get('browserReview') or {}
if ad_review.get('adSets'):
    for total,key in [('spend','spend'),('impressions','impressions'),('clicks','clicks'),('rawLeads','leads'),('formOpens','opens')]:
        assert abs(sum(r[key] for r in ad_review['adSets'])-ad_review['totals'][total])<.001
    assert ad_review['totals']['qualifiedLeads'] is None and ad_review['totals']['heldProspectCalls'] is None
creator=data['content'].get('creatorAnalytics')
if creator:
    assert creator['account']['identityVerified'] and creator['account']['name']=='Charles Solomon'
    assert creator['coverage']['sourceTimezone']=='UTC' and creator['coverage']['finalDayPartial']
    assert creator['chart']['display']=='Cumulative'
    assert sum(r['impressions'] for r in creator['daily'])==creator['summary']['impressions']
    assert creator['chart']['points'][-1]['cumulativeImpressions']==creator['summary']['impressions']
    assert all(r['engagements'] is None for r in creator['daily']), 'Window total must not become daily counts'
    assert len(creator['daily'])==len({r['date'] for r in creator['daily']})
    assert sum(creator['summary'][k] for k in ('reactions','comments','reposts','saves','sendsOnLinkedIn'))==creator['summary']['socialEngagements']
    assert len(creator['topPosts'])==len({r['activityId'] for r in creator['topPosts']})
    export=creator.get('exportAnalytics')
    if export:
        daily=export['daily']
        assert [r['date'] for r in daily]==[r['date'] for r in creator['daily']]
        assert sum(r['impressions'] for r in daily)==creator['summary']['impressions']
        assert sum(r['engagements'] for r in daily)==export['summary']['engagements']==creator['summary']['exportEngagements']
        assert all(r['engagements'] is None for r in creator['daily']), 'Broader workbook events became daily social-only counts'
        posts=export['rankedPosts'];p=export['postCoverage']
        assert len(posts)==len({r['postId'] for r in posts})==p['uniqueRankedPosts']
        assert p['completePublishingHistory'] is False
        for metric in ('impression','engagement'):
            ranked=[r for r in posts if r[metric+'Rank'] is not None]
            assert len(ranked)==p[metric+'RankedRows']<=p['rankingCapPerMetric']
            assert len(ranked)==len({r[metric+'Rank'] for r in ranked})
        assert [r['date'] for r in export['followers']['daily']]==[r['date'] for r in daily]
        assert sum(r['newFollowers'] for r in export['followers']['daily'])==export['followers']['newFollowersInWindow']
company=data['content'].get('companyAnalytics')
if company:
    rows=company['daily'];summary=company['summary']
    assert company['coverage']['sourceTimezone']=='UTC'
    assert len(rows)==len({r['date'] for r in rows})
    assert min(r['date'] for r in rows)==company['coverage']['start']
    assert max(r['date'] for r in rows)==company['coverage']['end']
    if company['coverage'].get('completeWithinExport'):
        assert len(rows)==(date.fromisoformat(company['coverage']['end'])-date.fromisoformat(company['coverage']['start'])).days+1, 'Complete company export has missing source days'
    ads_by_day={r['date']:r for r in data['ads']['daily']}
    compared_dates={r['date'] for r in rows}&set(ads_by_day)
    assert compared_dates, 'No dates overlap for the company/Ads reconciliation'
    for metric,ad_key in [('impressions','impressions'),('clicks','clicks'),('reactions','reactions'),('comments','comments'),('reposts','shares')]:
        for row in rows:
            assert row[metric+'Organic']+row[metric+'Sponsored']==row[metric+'Total']
            if row['date'] in compared_dates:
                assert row[metric+'Sponsored']==ads_by_day[row['date']][ad_key], 'Company-sponsored Ads overlap changed'
        for channel in ('organic','sponsored','total'):
            assert sum(r[metric+channel.capitalize()] for r in rows)==summary[channel][metric]
    assert all(summary[k]['uniqueReach'] is None and summary[k]['engagementRate'] is None for k in ('organic','sponsored','total'))
    reconciliation=(company.get('reconciliation') or {}).get('ads')
    if reconciliation and 'comparedDateCount' in reconciliation:
        assert reconciliation['comparedDateCount']==len(compared_dates)
        assert reconciliation['companyDatesWithoutPaidRows']==sorted({r['date'] for r in rows}-set(ads_by_day))
        assert reconciliation['completeAcrossCompanyWindow']==(len(compared_dates)==len(rows))
        for metric,ad_key in [('impressions','impressions'),('clicks','clicks'),('reactions','reactions'),('comments','comments'),('reposts','shares')]:
            totals=reconciliation['metrics'][metric]
            assert totals['companySponsoredOnComparedDates']==sum(r[metric+'Sponsored'] for r in rows if r['date'] in compared_dates)
            assert totals['paidSource']==sum(ads_by_day[date][ad_key] for date in compared_dates)
            assert totals['equal'] is True
    assert company['postCoverage']['publishedPostCount'] is None, 'Missing post register became zero'
context=data.get('meetings',{}).get('businessContextReview')
if context:
    calendar_events={e['id']:e for e in data['meetings']['events']}
    assert len(context['records'])==len({r['eventId'] for r in context['records']})
    fields={'eventId','inviteeName','company','stage','industry','fundraisingTiming','financialNeeds','financeHandling','cancellationReason','cancellationSourceDate','reviewedAt'}
    reviewed=datetime.fromisoformat(context['reviewedAt'].replace('Z','+00:00'))
    assert reviewed.utcoffset() is not None
    for row in context['records']:
        assert set(row)<=fields, 'Booking business context contains uncurated fields'
        event=calendar_events[row['eventId']]
        assert datetime.fromisoformat(row['reviewedAt'].replace('Z','+00:00'))<=reviewed
        for key in ('inviteeName','company','stage','industry','fundraisingTiming','financeHandling','cancellationReason'):
            assert row.get(key) is None or isinstance(row[key],str)
        needs=row.get('financialNeeds')
        assert needs is None or isinstance(needs,list) and all(isinstance(v,str) and v for v in needs)
        if row.get('cancellationReason'):
            assert event['status']=='canceled' and event.get('canceledAt')
            assert datetime.fromisoformat(row['cancellationSourceDate'].replace('Z','+00:00'))==datetime.fromisoformat(event['canceledAt'].replace('Z','+00:00'))
ref=data.get('referrals') or {}
event_review=ref.get('eventReview')
if event_review:
    events=event_review['events']
    crm_deals={r['id']:r for r in data['crm']['deals']}
    request_message_keys=set()
    assert len(events)==len({e['eventId'] for e in events})
    assert event_review['coverage']['status']=='incomplete'
    for event in events:
        assert event['verified'] and event['charlesIncluded']
        if event['type']=='introduction':assert event['direction']=='inbound' and event['prospectDealId']
        elif event['type']=='follow_up':assert event['direction']=='outbound' and event['sentByCharles'] is True
        elif event['type']=='request':
            assert event['direction']=='outbound' and event['sentByCharles'] is True
            assert type(event.get('communicationCount')) is int and event['communicationCount']==1, 'Count request communications, not target companies'
            assert event.get('sourceSystem') and event.get('sourceMessageId'), 'Requests need stable source-message evidence'
            message_key=(event['sourceSystem'],event['sourceMessageId'])
            assert message_key not in request_message_keys, 'One request communication cannot become per-target events'
            request_message_keys.add(message_key)
            contact_id=event.get('sourceContactDealId')
            assert type(contact_id) is int and contact_id in crm_deals and not crm_deals[contact_id].get('isTest'), 'Request contact needs an actual business CRM record'
            if event.get('referrerPersonId') is not None:
                assert event['referrerPersonId']==crm_deals[contact_id].get('personId'), 'Request contact person does not match CRM evidence'
            targets=event.get('requestedCompanies')
            assert isinstance(targets,list), 'Request targets must be explicit; an unknown target list is empty'
            target_names=set()
            for target in targets:
                name=target.get('company')
                assert isinstance(name,str) and name.strip(), 'Named request targets need a company name'
                normalized_name=name.strip().casefold()
                assert normalized_name not in target_names, 'A requested company cannot be duplicated'
                target_names.add(normalized_name)
                target_id=target.get('prospectDealId')
                if target_id is not None:
                    assert type(target_id) is int and target_id in crm_deals and not crm_deals[target_id].get('isTest'), 'Request target needs an actual business CRM record'
                    target_deal=crm_deals[target_id]
                    assert normalized_name in {str(target_deal.get(k) or '').strip().casefold() for k in ('title','company')}, 'Request target name does not match its CRM join'
        else:raise AssertionError('Unrecognized curated referral event type')
        if event['datePrecision']=='timestamp':
            assert event['occurredAt'].endswith('Z') and event['sourceTimezone']=='UTC' and event['sourceMessageId']
        else:assert event['datePrecision']=='day' and event['sourceTimezone'] is None
        assert event['heldCallConfirmed'] is None and event['acceptedOpportunityConfirmed'] is None and event['firstClientWinConfirmed'] is None
        if event.get('referralDealId') is None:
            assert event['type']=='request' and event['sourceContactDealId'] in crm_deals, 'Only a source-linked request may lack a Referral Pipeline deal'
        else:
            assert event['referralDealId'] in {r['dealId'] for r in ref['records']}
        if event['prospectDealId']:assert event['prospectDealId'] in {r['id'] for r in data['crm']['deals']}
if ref.get('partitions'):
    s=ref['summary']
    assert s['totalPipelineDeals']==len(ref['records'])+s['excludedOfficeHoursCount']+s['excludedGraveyardNewsletterCount']+s['excludedTestCount'], 'Referral partitions do not reconcile'
    assert s['activeReferralDeals']==len(ref['records'])==sum(s['stageDistribution'].values())
    assert len(ref['records'])==len({r['dealId'] for r in ref['records']})
    assert not any(r.get('partition')!='active' for r in ref['records']), 'Excluded referral row in active records'
w=data['waalaxy']
if w.get('invitationCoverage'):
    c=w['invitationCoverage']
    rows=[r for r in w['daily'] if 'invitationsSent' in r and c['start']<=r['date']<=c['end']]
    assert len(rows)==len({r['date'] for r in rows})==c['sourceDays']
    assert sum(r['invitationsSent'] for r in rows)==w['invitationSummary']['sent']
    assert sum(r['invitationsAccepted'] for r in rows)==w['invitationSummary']['accepted']
    assert w['invitationSummary']['cohortAcceptanceRate'] is None
ff=(data.get('meetings') or {}).get('fireflies') or {}
if 'records' in ff:
    assert len(ff['records'])==len({r['id'] for r in ff['records']}), 'Duplicate recording IDs'
    for r in ff['records']:
        assert r.get('occurredAt') or r.get('indexedAt'), 'Recording has no dated evidence'
        assert r['durationMinutes']>=0
october_review=ff.get('octoberPurposeReview')
if october_review:
    reviewed_ids=set(october_review['recordingIds'])
    reviewed_rows=[r for r in ff['records'] if r['id'] in reviewed_ids]
    assert len(reviewed_rows)==len(reviewed_ids)==october_review['retainedOctoberIndexedRecords']
    assert sum(october_review['reviewStatusCounts'].values())==len(reviewed_ids)
    for status,count in october_review['reviewStatusCounts'].items():
        assert sum(r.get('purposeReviewStatus')==status for r in reviewed_rows)==count
    assert sum(r['sentenceCount']>0 for r in reviewed_rows)==october_review['nonemptyDialogueRecords']
    assert october_review['completeActualHeldCallRosterEstablished'] is False
    assert october_review['recordsAreDistinctMeetings'] is False
    assert any(s['id']=='fireflies_october_review' for s in data['sources'])
if data.get('time'):
    effort = data['time']
    meetings = effort['meetings']
    assert abs(sum(e['countedMinutes'] for e in meetings['events'])-meetings['summary']['recordedMinutes']) < .001
    assert all(not e.get('duplicateOfId') or e['countedMinutes'] == 0 for e in meetings['events'])
    assert all(0 <= w['planningAllowance']['hoursLow'] <= w['planningAllowance']['hoursHigh'] for w in effort['workstreams'])
    if effort['summary'].get('ownerEstimateRange'):
        owner_range=effort['summary']['ownerEstimateRange']
        assert effort['summary']['nonMeetingEstimateHoursLow']==owner_range['low']
        assert effort['summary']['nonMeetingEstimateHoursHigh']==owner_range['high']
        assert not any(w['planningAllowance'].get('enabled') for w in effort['workstreams']), 'No owner workstream allocation supplied'
    elif effort['summary'].get('ownerAdjustedEstimate'):
        for w in effort['workstreams']:
            a=w['planningAllowance']
            for bound in ('Low','High'):
                assert abs(a['hours'+bound]-a['baselineHours'+bound]*a['ownerAdjustmentMultiplier'])<.000001, 'Owner uplift compounded or wrong base'
        for bound in ('Low','High'):
            assert abs(effort['summary']['nonMeetingEstimateHours'+bound]-sum(w['planningAllowance']['hours'+bound] for w in effort['workstreams']))<.000001
confirmations=data.get('meetings',{}).get('ownerConfirmedHeldCalls',[])
assert len(confirmations)==len({r['bookingChainId'] for r in confirmations}), 'Duplicate confirmed booking chain'
for proof in confirmations:
    link=next(r for r in data['meetings']['verifiedLinks'] if r['dealId']==proof['dealId'])
    lead=next(r for r in data['ads']['leads'] if r['company']==proof['company'])
    assert link['heldVerified'] and lead['meetingHeld'] and lead['meetingBooked'], 'Owner outcome or corroborated booking lost in source refresh'
    assert link['heldAt']==lead['heldAt']==proof['heldAt'] and link['heldEvidenceSource']==proof['evidenceSource']
subset=data['waalaxy'].get('sheetSubset')
if subset:
    rows=subset['rows'];m=subset['metrics']
    assert len(rows)==len({r['profileId'] for r in rows})==m['connectedProspects']
    assert sum(r['messageSentFlag'] for r in rows)==m['messageRecipientFlags']
    assert sum(r['messageRepliedFlag'] for r in rows)==m['replyingProspectFlags']
    assert m['currentPeriodMessageEvents'] is None and m['currentPeriodReplyEvents'] is None
    assert m['acceptanceRate'] is None and m['accountWideProspects'] is None
account=data['waalaxy'].get('accountAnalytics')
if account:
    assert account['account']['independentlyVerified']
    assert account['account']['linkedInProfile']=='https://www.linkedin.com/in/solomoncharles'
    assert account['sourceWindow']['sourceTimezone'] is None
    assert account['integration']['includeInSelectedPeriodTotals'] is False
    assert account['integration']['mergeIntoDailySeries'] is False
    assert account['platformDisplayedRates']['cohortRateEstablished'] is False
    assert all(isinstance(v,int) and v>=0 for v in account['metrics'].values())
valuation=data['crm'].get('assessment',{}).get('valuationCoverage')
if valuation:
    assert valuation['nonzeroValuedRecords']+valuation['zeroOrUnsetRecords']==valuation['businessOpenRecords']
    assert sum(r['value'] for r in valuation['records'] if r['currency']=='USD')==sum(r['value'] for r in valuation['knownPortionByCurrency'] if r['currency']=='USD')
    assert valuation['completeQualifiedPipelineValue'] is None

def inspect(value):
    if isinstance(value, dict):
        assert not {'provenance','sourcePath','sourceUrl'}.intersection(value), 'Private source reference'
        for child in value.values(): inspect(child)
    elif isinstance(value, list):
        for child in value: inspect(child)
    elif isinstance(value, str):
        assert '/Users/' not in value, 'Local filesystem path'
inspect(data)
print('Shared snapshot: JSON, source totals, record IDs, effort accounting and curation checks passed.')
