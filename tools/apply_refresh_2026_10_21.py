"""Assemble reviewed October 21 source evidence for local review.

No collection or publication occurs here. Older complete exports remain dated;
partial browser observations are attached separately. Re-running starts from a
preserved baseline and never compounds the owner's non-meeting estimate.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import json
from prepare_shared_snapshot import curate_snapshot

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_21'


def read(name):
    return json.loads((PRIVATE/name).read_text())


def apply_fresh_recording_review(current, sources):
    path=PRIVATE/'outcome_investigation/fireflies_current_patch.json'
    if not path.exists():return
    review=json.loads(path.read_text())
    metadata={}
    for file in (PRIVATE/'outcome_investigation').glob('fireflies_current_page*.json'):
        response=json.loads(file.read_text())['result']
        if 'content' in response:
            response=next(json.loads(c['text']) for c in response['content'] if c.get('type')=='text')
        metadata.update({r['id']:r for r in response['transcripts']})
    ff=current.setdefault('meetings',{}).setdefault('fireflies',{})
    records={r['id']:r for r in ff.get('records',[])}
    for row in review['currentWeekPurposeReview']:
        meta=metadata[row['id']]
        records[row['id']]={k:copy.deepcopy(row[k]) for k in ('id','indexedAt','classification','classificationBasis','reviewedDialogue','charlesSpeakerConfirmed','countAsCharlesProspectCall','evidenceCollectedAt')}
        records[row['id']].update(title=meta['title'],durationMinutes=meta['duration'],occurredAt=None,
            evidenceStatus='actual_dialogue_reviewed',heldStatus='excluded_from_Charles_prospect_calls',
            joinStatus='prospect_purpose_or_Charles_participation_not_established',crmDealIds=[])
    for row in review['independentlyReviewedRecordings']:
        proof=next(p for p in review['reviewedHeldSourceProofs'] if p['sourceRecordingId']==row['id'])
        meta=metadata[row['id']]
        records[row['id']]={k:copy.deepcopy(row[k]) for k in ('id','indexedAt','company','classification','charlesSpeakerConfirmed','evidenceCollectedAt')}
        records[row['id']].update(title=meta['title'],durationMinutes=meta['duration'],
            # The scheduled invitation time corroborates the day, not exact
            # attendance start. Keep only verified date precision.
            occurredAt=proof['heldAt'],occurrenceDatePrecision='day',
            classificationBasis=proof['dateBasis'],evidenceStatus='actual_dialogue_and_independent_date_corroboration',
            heldStatus='source_corroborated',joinStatus='actual_dialogue_plus_invitation_and_correspondence',
            crmDealIds=proof['crmDealIds'])
    ff.update(snapshotAt=review['snapshotAt'],records=list(records.values()),
        coverage={**review['metadataCoverage'],'limits':review['limits']},
        currentWeekPurposeReview={
            'start':'2026-10-19','end':'2026-10-21','recordingsReviewed':11,
            'additionalCharlesProspectCallsEstablished':0,'completeActualMeetingCoverage':False,
            'note':'All eleven available indexed recordings were reviewed for purpose. Client delivery, internal discussions and vendor feedback were excluded. Missing/unrecorded calls remain outside this source.'},
        summary={'metadataRecordsScanned':100,'octoberIndexedRecords':76,'currentWeekIndexedRecords':11,
            'reviewedSourceCorroboratedHeldCalls':2,'recordingCountIsUniqueMeetings':False},
        notes=['Fresh read uses the configured Centripetal Fireflies MCP; no browser terms acceptance or sign-in was needed.',
            'One hundred metadata records cross October 1; 76 are indexed in October. This is complete indexed-October coverage within the accessible list, not complete actual-meeting or attendance coverage.',
            'The minimized detailed register combines earlier retained reviews with fresh dialogue reviews; it is not the entire metadata list and overlapping recording segments are not automatically unique meetings.',
            'Nicolette October 12 and DEXIQ October 2 have actual Charles dialogue and independently corroborated occurrence days. Exact meeting-start and individual attendance times remain unknown.',
            'The eleven October 19–21 recordings establish no additional Charles prospect calls. This bounded absence is not an account-wide zero.',
            'Conditional internal discussion of future XCaliber/Venus engagements does not establish signed client wins.'])
    sources['fireflies'].update(asOf=review['snapshotAt'],checkedAt='2026-10-21',
        status='Current configured MCP metadata and scoped dialogue review',coverage=ff['coverage'],
        method='Configured Centripetal Fireflies MCP; paginated metadata plus actual speaker/dialogue reviews and independent Inbox corroboration',
        note='100 metadata records scanned / 76 October-indexed. All 11 October 19–21 recordings reviewed; none establishes an additional Charles prospect call. Nicolette and DEXIQ held days are independently corroborated. Actual meeting coverage and commercial decisions remain incomplete.')
    effort=current['time']
    meeting_patch=read('outcome_investigation/fireflies_time_meetings_patch.json')
    meeting_patch.pop('provenance',None)
    meeting_patch.pop('deduplication',None)
    meeting_patch['subject']={'name':'Christian Wutz'}
    if current.get('meetings',{}).get('snapshotAt'):
        meeting_patch['sourceAsOf']['calendly']=current['meetings']['snapshotAt']
        meeting_patch['coverage'].update(calendlyReviewedEvents=27,calendlyExactSubjectMatches=0,
            calendlyAccountScope='Charles Solomon authenticated account, July 16–November 13; all returned invitees/guests checked for the exact Christian email. Not Christian’s own calendar.')
    for event in meeting_patch['events']:
        event.pop('endAt',None)
        event['timeBasis']='Fireflies indexed date; actual meeting start and individual attendance are unverified.'
    effort.update(meetings=meeting_patch,snapshotAt=review['snapshotAt'],evidenceCollectionThrough=review['snapshotAt'])
    effort['notes']=[n for n in effort.get('notes',[]) if not n.startswith('October 21 refresh review:')]
    effort['notes'].append('October 21 refresh review: a fresh metadata scan and actual Christian speaker checks confirm the same six associated recordings, five after duplicate removal, totaling 228.58 audio minutes. No newer matching recording was found in the accessible indexed list. Audio duration is not attendance or worked time. The owner’s 14.5–15.75-hour non-meeting estimate remains unchanged.')
    sources['time'].update(asOf=review['snapshotAt'],status='Current recording review; owner nonmeeting estimate',
        note='Christian only, reporting through October 21. Fresh metadata and speaker reviews retain five deduplicated recordings / 228.58 audio minutes; no additional matching source recording was found. The separate 14.5–15.75-hour owner estimate remains unchanged. Actual human hours and own-calendar coverage remain unknown.')


def build():
    baseline=PRIVATE/'dashboard_before_refresh.json'
    if not baseline.exists():
        baseline.write_bytes((ROOT/'data/shared-dashboard.json').read_bytes())
    current=json.loads(baseline.read_text())
    sources={s['id']:s for s in current['sources']}
    creator=read('creator_patch.json')
    current['content']=creator['content']
    sources['content']=creator['source']
    current['video']=read('sheets_video_patch.json')
    current['waalaxy'].update(read('waalaxy_patch.json'))
    sources['video'].update(asOf=current['video']['snapshotAt'],checkedAt='2026-10-21',
        coverage='428 valid prospect rows; full current main and accepted-connections tabs',
        note='45 ready rows, 41 follow-up rows, 29 exact Sent/Done statuses. Separate dated source-status evidence includes 12 October 21 send statuses; delivery and video content are unverified. Blank rows are excluded. Upstream sync time remains unknown.')
    sources['waalaxy'].update(asOf=current['waalaxy']['sheetSubsetCollectedAt'],checkedAt='2026-10-21',
        status='Current selected-person snapshots; invitation export ends October 15',
        coverage='October 21 live Sheet: 168 connected people; separate October 20 selected CSVs: 206 people; invitation actions September 15–October 15',
        method='Connected Google Sheets read, retained selected-list CSVs and historical invitation/person exports')
    browser=read('crm_browser_patch.json')
    current['crm']['browserReview']=browser
    current['referrals']['browserReview']={**copy.deepcopy(browser),
        'pipelines':[p for p in browser['pipelines'] if p['pipelineId']==4],
        'visibleRecords':[r for r in browser['visibleRecords'] if r['pipelineId']==4]}
    sources['crm'].update(checkedAt='2026-10-21',status='Retained complete October 16 snapshot; current partial browser supplement',
        note='The complete deal/activity source retains its October 16 collection and October 15 complete reporting cutoff. October 21 browser observations are a separate open-stage inventory supplement. Export download was blocked by Chrome; this week’s created/updated/completed totals remain unavailable.')
    sources['referrals'].update(checkedAt='2026-10-21',status='Retained reconciled referral snapshot; current raw-stage supplement',
        note='The cleaned 60-record business partition retains its complete October 16 source date. October 21 raw open-stage observations are separate and include tests; current stages do not establish dated introductions, qualification or acceptance.')
    sources['crm_browser']={'id':'crm_browser','name':'Pipedrive · current browser observations',
        'status':'Partial current browser supplement','asOf':browser['collectedAt'],
        'checkedAt':'2026-10-21','coverage':browser['coverage'],
        'method':'Read-only visible open-stage browser views',
        'note':'377 Leads, 42 Sales and 348 Referral source-view records, sampled separately. Tests and duplicates remain included; not a full deal/activity export or a won/held/accepted opportunity ledger.'}
    # The configured MCP became available after the bounded browser review.
    # Prefer the newer complete returned inventory; retain the earlier board
    # observation only as clearly superseded provenance.
    fresh_crm=PRIVATE/'crm_mcp_patch.json'
    if fresh_crm.exists():
        current['crm']=read('crm_mcp_patch.json')
        current['crm']['browserReview']={**browser,'supersededByFullSnapshotAt':current['crm']['snapshotAt']}
        old_ref_browser=current['referrals'].get('browserReview')
        current['referrals']=read('referrals_mcp_patch.json')
        if old_ref_browser:current['referrals']['browserReview']={**old_ref_browser,'supersededByFullSnapshotAt':current['crm']['snapshotAt']}
        sources['crm'].update(asOf=current['crm']['snapshotAt'],checkedAt='2026-10-21',
            status='Current paginated read-only MCP snapshot',coverage=current['crm']['coverage'],
            method='Configured Pipedrive read-only MCP; all returned non-deleted deals and all-owner done/undone activities, all pages',
            note='769 returned deals / 924 activities; 765 and 919 after explicit test-title exclusions. Observed through October 21, partial; complete reporting days through October 20. Archived-inclusive completeness is unverified. New/updated CRM records are not new accepted opportunities; current stages are not wins. Record 203 remains flagged for a test-labelled organization and is separately reviewable.')
        sources['referrals'].update(asOf=current['referrals']['snapshotAt'],checkedAt='2026-10-21',
            status='Current reconciled referral inventory from same CRM read',coverage=current['referrals']['coverage'],
            method='Local Pipeline 4 partition of the same current paginated Pipedrive MCP source',
            note='348 raw referral records; 60 active, 245 Office Hours, 40 Graveyard/Newsletter and three explicit tests. The same-source inventory overlaps the CRM; dated introductions, qualification and automation execution remain incomplete.')
        sources['crm_browser'].update(name='Pipedrive · earlier browser cross-check',
            status='Historical browser observation superseded by full MCP inventory',
            note='Earlier open-board counts reconcile with the fresh source: 377 open Leads plus one won and one lost equals 379 total Leads. Sales 42 and Referrals 348. The newer full returned MCP inventory supplies the current dashboard metrics.')
    ads_path=PRIVATE/'ads_patch.json'
    if ads_path.exists():
        ads=read('ads_patch.json')
        current['ads']=ads['ads']
        sources['ads']=ads['source']
    else:
        ad_review=read('ads_browser_patch.json')
        current['ads']['browserReview']=ad_review
        sources['ads'].update(checkedAt='2026-10-21',status='Retained daily export; current fixed-window browser supplement',
            note='Daily campaign/creative exports remain dated through October 16 UTC. A separate October 21 browser aggregate covers September 4–October 22 UTC, final day partial. The configured daily export download stalled; source-reported conversions/appointments do not establish held calls or accepted opportunities.')
        sources['ads_browser']={'id':'ads_browser','name':'LinkedIn Ads · current browser aggregate',
            'status':'Current fixed-window browser supplement','asOf':ad_review['collectedAt'],
            'checkedAt':'2026-10-21','coverage':ad_review['coverage'],
            'method':ad_review['method'],
            'note':'All seven ad sets in the reporting view; $3,592.31 spend, 25,055 impressions, 106 clicks, four source-reported submissions and 62 form opens. Daily source buckets and submission detail remain separately incomplete.'}
    # Reporting scope may reach today; unchanged meeting evidence does not.
    effort=current['time']
    effort['period'].update(end='2026-10-21',currentDayPartial=True)
    effort['reviewedAsOf']='2026-10-21'
    effort['evidenceCollectionThrough']=effort['snapshotAt']
    effort['notes']=[n for n in effort.get('notes',[]) if not n.startswith('October 21 refresh review:')]
    effort['notes'].append('October 21 refresh review: the reporting scope extends through today, but no newer meeting or attendance evidence was accessible. The five deduplicated recordings and their original collection dates remain unchanged. The owner’s 14.5–15.75-hour overall non-meeting estimate is carried forward unchanged, with no inferred incremental hours after October 16.')
    sources['time'].update(coverage=effort['period'],checkedAt='2026-10-21',
        status='Retained meeting evidence; owner nonmeeting estimate',
        note='Christian only, October 1–21 reporting scope, today partial. Evidence last collected October 16: five deduplicated recordings / 228.58 audio minutes. No newer attendance/time log was collected. The separate 14.5–15.75-hour owner estimate is unchanged; actual human hours are unknown.')
    calendar_patch=PRIVATE/'calendly/calendly_refresh_patch.json'
    if calendar_patch.exists():
        current.setdefault('meetings',{}).update(read('calendly/calendly_refresh_patch.json'))
        current['meetings']['coverage'].update(observedThrough='2026-10-21',
            currentDayPartial=True,currentDayPartialDate='2026-10-21')
        sources['meetings'].update(asOf=current['meetings']['snapshotAt'],checkedAt='2026-10-21',
            status='Current authenticated Charles Calendly snapshot',coverage=current['meetings']['coverage'],
            method='Configured Calendly MCP; explicit active/canceled events and all invitee pages within the retained window',
            note='27 event records / 25 booking chains, same IDs as the prior source. October bookings: NuVee October 6, original Venus October 15 and Quantex October 22. No October 19–21 Calendly starts were returned, which does not establish zero held calls. The original Venus booking conflicts with an accepted October 16 reschedule in Inbox.')
    else:sources['meetings'].update(checkedAt='2026-10-21',status='Retained calendar source; current refresh needed')
    sources['fireflies'].update(checkedAt='2026-10-21',status='Retained reviewed recording evidence; current refresh needed')
    apply_fresh_recording_review(current,sources)
    current['sources']=list(sources.values())
    current['meta'].update(generatedAt=datetime.now(timezone.utc).isoformat(),
        asOfDate='2026-10-21',reportingAsOfDate='2026-10-21',
        defaultReportingThrough='2026-10-21',defaultCompleteReportingThrough='2026-10-20',
        defaultDatePreset='week',currentDayPartial=True,
        publicationStatus='local_only',
        revision='October 21 source refresh, configured MCP reconciliation and Charles-only outcome register; owner-directed local only')
    result=curate_snapshot(current)
    payload=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (ROOT/'data/shared-dashboard.json').write_text(payload)
    (ROOT/'data/dashboard.json').write_text(payload)
    print(json.dumps({'asOf':result['meta']['asOfDate'],'publicationStatus':result['meta']['publicationStatus'],
        'videoRows':result['video']['summary']['sourceRows'],
        'sheetPeople':result['waalaxy']['sheetSubset']['metrics']['connectedProspects'],
        'creatorImpressions':result['content']['creatorAnalytics']['summary']['impressions'],
        'heldEvidence':len(result['outcomes']['heldCalls']),
        'crmFullSnapshotAt':result['crm']['snapshotAt']}))


if __name__=='__main__':build()
