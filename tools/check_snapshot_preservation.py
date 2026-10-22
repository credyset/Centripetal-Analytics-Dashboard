"""Regression checks for importing old sources after a newer reviewed snapshot."""
import copy
import json
from pathlib import Path
from prepare_shared_snapshot import curate_snapshot, preserve_newer_shared_sources

ROOT=Path(__file__).resolve().parents[1]
current=json.loads((ROOT/'data/shared-dashboard.json').read_text())
older=copy.deepcopy(current)
for key in ('publicationStatus','reportingAsOfDate','defaultCompleteReportingThrough','defaultDatePreset','currentDayPartial'):
    older['meta'].pop(key,None)
older['meta'].update(public=True,asOfDate='2026-10-16',generatedAt='2026-10-17T00:52:01Z',defaultReportingThrough='2026-10-15')
older['content'].pop('creatorAnalytics',None)
older['content']['snapshotAt']='2026-09-11T00:00:00Z'
older['content']['daily']=[]
for key in ('crm','referrals','ads'):older[key].pop('browserReview',None)
older['sources']=[s for s in older['sources'] if s['id'] not in ('crm_browser','ads_browser')]
older['time'].pop('reviewedAsOf',None)
older['time']['period']['end']='2026-10-16'
# A later account snapshot may omit independently dated Sheet/CSV supplements.
older['waalaxy']['snapshotAt']='2026-10-23T00:00:00Z'
for key in ('sheetSubset','sheetSubsetCollectedAt','sheetSubsetAccountVerification','sheetSubsetUpstreamSyncAt','selectedExportSnapshot'):
    older['waalaxy'].pop(key,None)
restored=curate_snapshot(preserve_newer_shared_sources(older,current))
assert restored['content']['creatorAnalytics']==current['content']['creatorAnalytics']
assert restored['crm']['browserReview']==current['crm']['browserReview']
assert any(s['id']=='crm_browser' for s in restored['sources'])
if current['ads'].get('browserReview'):
    assert restored['ads']['browserReview']==current['ads']['browserReview']
    assert any(s['id']=='ads_browser' for s in restored['sources'])
assert restored['waalaxy']['sheetSubset']==current['waalaxy']['sheetSubset']
assert restored['waalaxy']['selectedExportSnapshot']==current['waalaxy']['selectedExportSnapshot']
assert restored['time']['period']==current['time']['period']
for key in ('reportingAsOfDate','defaultReportingThrough','defaultCompleteReportingThrough','defaultDatePreset'):
    assert restored['meta'][key]==current['meta'][key]
if current['meta'].get('publicationStatus')=='pending_owner_approval':
    assert restored['meta']['publicationStatus']=='pending_owner_approval'
    assert restored['meta']['public'] is False
print('Snapshot preservation: source supplements, reporting scope and publication hold passed.')
