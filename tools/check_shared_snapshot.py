"""Check the portable, curated reporting snapshot before sharing changes."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
source = ROOT/'data/shared-dashboard.json'
data = json.loads(source.read_text())
assert all(k in data for k in ('meta','ads','crm','video','waalaxy','content','referrals','time','sources'))
assert data['meta']['timezone'] == 'America/Denver'
for entity in ('deals','activities'):
    rows = data['crm'][entity]
    assert len(rows) == len({row['id'] for row in rows}), f'Duplicate CRM {entity} IDs'
assert len(data['video']['rows']) == data['video']['summary']['sourceRows']
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
company=data['content'].get('companyAnalytics')
if company:
    rows=company['daily'];summary=company['summary']
    assert company['coverage']['sourceTimezone']=='UTC'
    assert len(rows)==len({r['date'] for r in rows})
    assert min(r['date'] for r in rows)==company['coverage']['start']
    assert max(r['date'] for r in rows)==company['coverage']['end']
    ads_by_day={r['date']:r for r in data['ads']['daily']}
    for metric,ad_key in [('impressions','impressions'),('clicks','clicks'),('reactions','reactions'),('comments','comments'),('reposts','shares')]:
        for row in rows:
            assert row[metric+'Organic']+row[metric+'Sponsored']==row[metric+'Total']
            assert row[metric+'Sponsored']==ads_by_day[row['date']][ad_key], 'Company-sponsored Ads overlap changed'
        for channel in ('organic','sponsored','total'):
            assert sum(r[metric+channel.capitalize()] for r in rows)==summary[channel][metric]
    assert all(summary[k]['uniqueReach'] is None and summary[k]['engagementRate'] is None for k in ('organic','sponsored','total'))
    assert company['postCoverage']['publishedPostCount'] is None, 'Missing post register became zero'
ref=data.get('referrals') or {}
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
