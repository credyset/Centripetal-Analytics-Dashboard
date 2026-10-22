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
    sources['meetings'].update(checkedAt='2026-10-21',status='Retained calendar source; current refresh needed')
    sources['fireflies'].update(checkedAt='2026-10-21',status='Retained reviewed recording evidence; current refresh needed')
    current['sources']=list(sources.values())
    current['meta'].update(generatedAt=datetime.now(timezone.utc).isoformat(),
        asOfDate='2026-10-21',reportingAsOfDate='2026-10-21',
        defaultReportingThrough='2026-10-21',defaultCompleteReportingThrough='2026-10-20',
        defaultDatePreset='week',currentDayPartial=True,
        publicationStatus='pending_owner_approval',
        revision='October 21 local source refresh and Charles-only outcome register; publication pending')
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
