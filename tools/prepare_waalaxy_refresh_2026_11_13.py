"""Normalize directly observed Charles Home date buckets into an isolated local patch."""
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'data/private/refresh_2026_11_13'
OUT=PRIVATE/'waalaxy'


def read(path):
    return json.loads(path.read_text())


def write(name,value):
    p=OUT/name
    p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    p.chmod(0o600)


def days(start,end):
    first=date.fromisoformat(start)
    return [(first+timedelta(days=i)).isoformat() for i in range((date.fromisoformat(end)-first).days+1)]


def metric_totals(rows):
    return {k:sum(x[k] for x in rows) for k in ('sent','accepted')}


def summary_segment(rows,stamp,label,digest,partial=False):
    return {'start':rows[0]['date'],'end':rows[-1]['date'],'sourceDays':len(rows),
        'sourceType':'authenticated_home_chart_tooltips','sourceLabel':label,'sourceSha256':digest,
        'collectedAt':stamp,'retainedFromPriorSource':False,'finalDayPartial':partial,**metric_totals(rows)}


def build():
    evidence_path=OUT/'browser_observations.json'
    source_hash=hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    e=read(evidence_path)
    assert e['account']=='Charles Solomon' and e['profile'].rstrip('/')=='https://www.linkedin.com/in/solomoncharles'
    month,bridge=e['month'],e['bridge']
    assert month['period']=='This month' and bridge['period']=='Last 30 days' and month['sourceTimezone'] is None
    assert [x['date'] for x in month['daily']]==days('2026-11-01','2026-11-13')
    assert [x['date'] for x in bridge['daily']]==days('2026-10-28','2026-10-31')
    assert all(isinstance(x[k],int) and x[k]>=0 for x in [*month['daily'],*bridge['daily']] for k in ['sent','accepted'])
    assert metric_totals(month['daily'])=={'sent':month['totalSent'],'accepted':month['totalAccepted']}=={'sent':66,'accepted':22}
    assert metric_totals([x for x in month['daily'] if '2026-11-06'<=x['date']<='2026-11-12'])=={'sent':62,'accepted':22}
    assert metric_totals(bridge['daily'][1:])=={'sent':0,'accepted':0}
    prior=read(ROOT/'data/shared-dashboard.json')['waalaxy']
    assert prior['invitationCoverage']['end']=='2026-10-29', 'Use the retained October 29 baseline.'
    current=deepcopy(prior)
    by_day={x['date']:x for x in current['daily']}
    historical=deepcopy(prior['daily'])
    invitation_fields={'invitationsSent','invitationsAccepted'}
    assert len(by_day)==len(historical)
    merged_new=[*bridge['daily'][1:],*month['daily']]
    new_rows=[{'date':x['date'],'invitationsSent':x['sent'],'invitationsAccepted':x['accepted']} for x in merged_new]
    for row in new_rows:
        by_day.setdefault(row['date'],{'date':row['date']}).update(row)
    current['daily']=[by_day[k] for k in sorted(by_day)]
    assert [x for x in current['daily'] if x['date']<'2026-10-29']==[x for x in historical if x['date']<'2026-10-29']
    invs=[x for x in current['daily'] if invitation_fields<=set(x)]
    assert [x['date'] for x in invs]==days('2026-09-15','2026-11-13')
    total={'sent':sum(x['invitationsSent'] for x in invs),'accepted':sum(x['invitationsAccepted'] for x in invs)}
    assert total=={'sent':600,'accepted':194}
    # Retain the October CSV vintage through October 28. The later October 28
    # tooltip differs; keep it as a separately dated restatement, not a second event.
    orig_segment=deepcopy(prior['invitationCoverage']['segments'][-1])
    prior_segments=deepcopy(prior['invitationCoverage']['segments'][:-1])
    for s in prior_segments:s['retainedFromPriorSource']=True
    orig_segment.update(end='2026-10-28',sourceDays=28,retainedFromPriorSource=True,finalDayPartial=False)
    prior_segments.append(orig_segment)
    prior_value=next(x for x in historical if x['date']=='2026-10-28')
    restatement={'date':'2026-10-28','retainedCsv':{k:prior_value[k] for k in invitation_fields},
        'laterAuthenticatedTooltip':{'invitationsSent':bridge['daily'][0]['sent'],'invitationsAccepted':bridge['daily'][0]['accepted']},
        'laterTooltipObservedAt':bridge['observedAt'],'retainedCsvCollectedAt':prior['invitationCollectedAt'],
        'appliedToRetainedSeries':False,
        'basis':'The latest view restated six additional acceptances for this historical source-day bucket. This bounded bridge does not reimport the earlier October series; the old CSV value is preserved. Neither vintage establishes exact acceptance-event dates.'}
    assert restatement['retainedCsv']=={'invitationsSent':73,'invitationsAccepted':19}
    assert restatement['laterAuthenticatedTooltip']=={'invitationsSent':73,'invitationsAccepted':25}
    month_summary=summary_segment(month['daily'],month['observedAt'],'Charles Home · This month',source_hash,True)
    bridge_summary=summary_segment(bridge['daily'][1:],bridge['observedAt'],'Charles Home · Last 30 days, verified bridge only',source_hash)
    stamp=bridge['observedAt']
    coverage={'start':'2026-09-15','end':'2026-11-13','complete':True,'sourceDays':len(invs),
        'zeroActivityDatesConfirmed':True,'currentDayPartial':True,'completeDaysThrough':'2026-11-12','sourceTimezone':None,
        'sourceDateBasis':'Historical CSV buckets through October 28; exact authenticated Home chart tooltips from October 29 through November 13. Dates are platform source labels, not Mountain-event timestamps. Accepted buckets may restate.',
        'accountEvidence':'New dates come from the authenticated Charles Solomon Home view, matched to linkedin.com/in/solomoncharles. Earlier CSV segments retain their original account attribution and clocks.',
        'collectedAt':stamp,'compositeSource':True,'segments':[*prior_segments,bridge_summary,month_summary]}
    review={'snapshotAt':stamp,'sourceType':'authenticated_home_chart_tooltips','latestExportSummary':month_summary,
        'bridgeSummary':bridge_summary,'mergedSeriesSummary':{'start':coverage['start'],'end':coverage['end'],'sourceDays':len(invs),**total},
        'overlapDays':1,'newSourceDays':15,'revisedDateBuckets':[],'separatelyObservedRestatements':[restatement],
        'retainedOlderSegments':prior_segments,
        'explicitZeroDates':[x['date'] for x in merged_new if x['sent']==x['accepted']==0],
        'homeReconciliation':{'start':month_summary['start'],'end':month_summary['end'],'allSourceDaysPresent':True,
            'sourceType':'authenticated_home_chart_tooltips','chart':metric_totals(month['daily']),'home':{'sent':month['totalSent'],'accepted':month['totalAccepted']},
            'sameNumericTotals':True,'combineWithHomeTotals':False,'homeCollectedAt':month['observedAt'],
            'note':'Direct chart tooltip buckets for the November source dates sum to the fixed Home totals; same source represented two ways, never added.'},
        'limits':['The CSV export control did not yield a new file; November date buckets were read directly from authenticated chart tooltips.','Distinct date and both counts were verified per tooltip; duplicate or omitted axis labels were not used.','The November 13 bucket is partial, and the source timezone is unavailable.','Earlier dates use separate CSV clocks. October 28’s later 73/25 tooltip does not revise this retained 73/19 CSV series.','Acceptance counts are source buckets and may be restated; no matched-cohort conversion is computed.']}
    current.update(invitationCoverage=coverage,invitationSummary={**total,'cohortAcceptanceRate':None,
        'basis':'Sum of composite source-day buckets; earlier retained CSV plus authenticated Home tooltip bridge. Not an invitation cohort.'},
        invitationCollectedAt=stamp,invitationImportReview=review)
    home=deepcopy(prior['accountAnalytics']);home_stamp=month['observedAt']
    home.update(snapshotAt=home_stamp,collectedAt=home_stamp,collectedOn='2026-11-13',reportingLocalDate='2026-11-13',
        preparedAt=stamp,sourceType='authenticated_browser_ui_fixed_window',collectionTimestampBasis='Authenticated Home observation timestamp; not upstream synchronization time.')
    home['sourceWindow'].update(preset=month['period'],displayedStartDate='2026-11-01',displayedEndDate='2026-11-13',finalDayPartial=True,sourceTimezone=None,
        exactStartTimestamp=None,exactEndTimestamp=None,dateBasis='November 1–13 chart source dates; final day partial. Source timezone unavailable; no Mountain rebucketing.')
    home['metrics']={'invitationActionsSent':month['totalSent'],'invitationAcceptancesReported':month['totalAccepted'],
        'messageActionsSent':month['messages'],'answeredMessagesReported':month['answers'],
        'profileVisitActionsSent':month['visits'],'profileFollowActionsSent':month['follows']}
    home['platformDisplayedRates'].update(acceptancePercent=month['displayedAcceptancePercent'],responsePercent=None,
        denominatorDefinitions=None,cohortRateEstablished=False,note='The 33.3% acceptance percentage is descriptive and supplied by Waalaxy. It is not an invitation-cohort conversion rate.')
    home['integration'].update(displayAs='Charles Waalaxy · November 1–13 (partial) · fixed source window',includeInSelectedPeriodTotals=False,
        mergeIntoDailySeries=False,existingDailyInvitationSource={'action':'Direct date tooltips normalized separately','scope':'No day is inferred from the Home total.'},
        mergeWithSelectedConnectedPeople=False,sourceOverlapsExistingDailyHistory=True,
        safeComparison='The November daily tooltip rows reconcile to this fixed aggregate, which is not added to daily or selected-person counts.',
        replacesAccountAccessGap='Charles identity and Home metrics directly verified; account-wide native message/reply and accepted event histories remain unavailable.')
    home['limits']=['November 13 is partial; the source timezone and upstream sync time are unavailable.','November source-date tooltips total 66 invitations and 22 reported acceptances, agreeing with this fixed aggregate; these are not additive.','Zero Waalaxy message or answered-message actions is not zero manual LinkedIn outreach or replies.','Acceptance bucket dates are not exact acceptance dates; the displayed rate is descriptive.','Connected-person worksheet flags are a separate selected population.']
    home['evidence']={'sourceSha256':source_hash,'readOnly':True,'minimalAggregateOnly':True}
    current['accountAnalytics']=home
    current['retainedEarlierAccountAnalytics']=[*current.get('retainedEarlierAccountAnalytics',[]),prior['accountAnalytics']]
    current.update(read(PRIVATE/'sheets/waalaxy_sheet_subset_patch.json'))
    current['notes']=[n for n in current.get('notes',[]) if not n.startswith(('Latest owner-supplied invitation CSV:','Invitation import contains'))]
    current['notes'].append('Authenticated Charles Home chart: 62 Sent / 22 Accepted in November 6–12 source buckets; November 13 partial is 4 / 0. Earlier retained CSV dates use their original clocks; no matched acceptance cohort or Mountain event attribution is inferred.')
    assert all(current[k]==prior[k] for k in ['snapshotAt','metrics','selectedExportSnapshot','historicalSnapshotAt'])
    write('waalaxy.json',current)
    write('invitation_patch.json',{k:current[k] for k in ['invitationCoverage','invitationSummary','invitationCollectedAt','invitationImportReview']}|{'invitationRows':new_rows})
    write('account_analytics_patch.json',home)
    write('summary.json',{'account':e['account'],'snapshotAt':stamp,'accountHomeObservedAt':home_stamp,
        'selectedCompleteSourceDays':{'start':'2026-11-06','end':'2026-11-12','sent':62,'accepted':22},
        'partialNovember13':{'sent':4,'accepted':0},'homeWindow':month_summary,
        'bridge':bridge_summary,'composite':coverage,'compositeTotals':total,'retainedSeparateRestatement':restatement,
        'selectedPersonSnapshotAt':current['sheetSubsetCollectedAt'],'sourceSha256':source_hash})
    print(json.dumps({'selectedSent':62,'selectedAccepted':22,'partialSent':4,'partialAccepted':0,'composite':total,'sourceDays':len(invs)}))


if __name__=='__main__':
    build()
