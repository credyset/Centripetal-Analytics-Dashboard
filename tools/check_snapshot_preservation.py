"""Regression checks for importing old sources after a newer reviewed snapshot."""
import copy
import json
from pathlib import Path
from prepare_shared_snapshot import curate_snapshot, preserve_newer_shared_sources, publication_policy

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
# Simulate older complete exports, not just missing browser supplements.
for key in ('crm','referrals','meetings','time'):
    older[key]['snapshotAt']='2026-10-17T00:52:01Z' if key!='meetings' else '2026-10-15T02:58:42Z'
older['crm']['deals']=[d for d in older['crm']['deals'] if d['id']<832]
older['meetings'].pop('fireflies',None)
older['ads']['snapshotAt']='2026-10-17T00:51:00Z'
older['ads']['daily']=[r for r in older['ads']['daily'] if r['date']<='2026-10-16']
older['content'].pop('companyAnalytics',None)
older['waalaxy'].pop('accountAnalytics',None)
older['sources']=[s for s in older['sources'] if s['id'] not in ('content_company','waalaxy_account')]
for src in older['sources']:
    if src['id'] in ('crm','referrals','meetings','time','fireflies'):src['asOf']='2026-10-15T02:58:42Z'
# A later account snapshot may omit independently dated Sheet/CSV supplements.
older['waalaxy']['snapshotAt']='2026-10-23T00:00:00Z'
for key in ('sheetSubset','sheetSubsetCollectedAt','sheetSubsetAccountVerification','sheetSubsetUpstreamSyncAt','selectedExportSnapshot'):
    older['waalaxy'].pop(key,None)
restored=curate_snapshot(preserve_newer_shared_sources(older,current))
assert restored['content']['creatorAnalytics']==current['content']['creatorAnalytics']
assert restored['crm']['browserReview']==current['crm']['browserReview']
for key in ('crm','referrals','meetings','time'):
    assert restored[key]['snapshotAt']==current[key]['snapshotAt'], f'Newer {key} source lost'
assert restored['crm']['deals']==current['crm']['deals']
assert restored['ads']['daily']==current['ads']['daily']
for parent,child,source_id in (('content','companyAnalytics','content_company'),('waalaxy','accountAnalytics','waalaxy_account')):
    if child in current[parent]:
        assert restored[parent][child]==current[parent][child]
        assert any(s['id']==source_id for s in restored['sources'])
assert restored['meetings']['fireflies']==current['meetings']['fireflies']
assert next(s for s in restored['sources'] if s['id']=='fireflies')['asOf']==next(s for s in current['sources'] if s['id']=='fireflies')['asOf']
assert any(s['id']=='crm_browser' for s in restored['sources'])
if current['ads'].get('browserReview'):
    assert restored['ads']['browserReview']==current['ads']['browserReview']
    assert any(s['id']=='ads_browser' for s in restored['sources'])
assert restored['waalaxy']['sheetSubset']==current['waalaxy']['sheetSubset']
assert restored['waalaxy']['selectedExportSnapshot']==current['waalaxy']['selectedExportSnapshot']
assert restored['time']['period']==current['time']['period']
for key in ('reportingAsOfDate','defaultReportingThrough','defaultCompleteReportingThrough','defaultDatePreset'):
    assert restored['meta'][key]==current['meta'][key]
if publication_policy().get('mode')=='local_only':
    assert restored['meta']['publicationStatus']=='local_only'
    assert restored['meta']['public'] is False
    # Even a caller's old approval flag cannot override the canonical local hold.
    approved_flag=curate_snapshot(preserve_newer_shared_sources(older,current,publication_approved=True))
    assert approved_flag['meta']['publicationStatus']=='local_only'
    assert approved_flag['meta']['public'] is False
elif current['meta'].get('publicationStatus') in ('pending_owner_approval','local_only'):
    assert restored['meta']['publicationStatus']==current['meta']['publicationStatus']
    assert restored['meta']['public'] is False
print('Snapshot preservation: source supplements, reporting scope and publication hold passed.')
