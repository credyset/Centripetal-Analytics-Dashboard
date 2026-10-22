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
for parent,child in (('crm','archiveReview'),('video','sourceVerification'),('waalaxy','workflowReview'),('crm','commercialContextReview'),('waalaxy','replyContextReview'),('referrals','eventReview'),('referrals','legacyCaptureReview'),('time','workEvidence')):
    if child in current[parent]:assert restored[parent][child]==current[parent][child]
# A newer source container can omit an independently dated context/event
# supplement; preserve the evidence without re-dating the new parent inventory.
supplements=[('crm','commercialContextReview','commercial_context'),('waalaxy','replyContextReview','commercial_context'),('referrals','eventReview','referral_events')]
incoming=copy.deepcopy(current)
for parent,child,source_id in supplements:
    incoming[parent]['snapshotAt']='2026-10-23T12:00:00Z'
    incoming[parent].pop(child,None)
incoming['sources']=[s for s in incoming['sources'] if s['id'] not in {'commercial_context','referral_events'}]
kept=preserve_newer_shared_sources(incoming,current)
for parent,child,source_id in supplements:
    if child in current[parent]:
        assert kept[parent][child]==current[parent][child]
        assert kept[parent]['snapshotAt']=='2026-10-23T12:00:00Z'
        assert any(s['id']==source_id for s in kept['sources'])
assert restored['meetings']['fireflies']==current['meetings']['fireflies']
assert next(s for s in restored['sources'] if s['id']=='fireflies')['asOf']==next(s for s in current['sources'] if s['id']=='fireflies')['asOf']
assert any(s['id']=='crm_browser' for s in restored['sources'])
if current['ads'].get('browserReview'):
    assert restored['ads']['browserReview']==current['ads']['browserReview']
    assert any(s['id']=='ads_browser' for s in restored['sources'])
assert restored['waalaxy']['sheetSubset']==current['waalaxy']['sheetSubset']
assert restored['waalaxy']['selectedExportSnapshot']==current['waalaxy']['selectedExportSnapshot']
# A newer bounded metadata import may omit independently reviewed recordings.
# Keep the dialogue evidence without falsely claiming new metadata presence.
prior_ff=current['meetings'].get('fireflies') or {}
reviewed_ids={r['id'] for r in prior_ff.get('records',[]) if r.get('lastPurposeReviewedAt')}
if reviewed_ids:
    incoming=copy.deepcopy(current)
    incoming['meetings']['snapshotAt']='2026-10-23T12:00:00Z'
    incoming['meetings']['fireflies']={'snapshotAt':'2026-10-23T12:00:00Z','records':[]}
    incoming['sources']=[s for s in incoming['sources'] if s['id'] not in ('fireflies_purpose','fireflies_october_review')]
    kept=preserve_newer_shared_sources(incoming,current)
    rows=kept['meetings']['fireflies']['records']
    assert reviewed_ids<={r['id'] for r in rows}
    assert all(r.get('retainedForPurposeEvidenceOnly') for r in rows if r['id'] in reviewed_ids)
    assert any(s['id']=='fireflies_purpose' for s in kept['sources'])
    if prior_ff.get('octoberPurposeReview'):
        assert kept['meetings']['fireflies']['octoberPurposeReview']==prior_ff['octoberPurposeReview']
        assert any(s['id']=='fireflies_october_review' for s in kept['sources'])
        prior_by_id={r['id']:r for r in prior_ff['records']}
        for row in rows:
            if row['id'] in reviewed_ids:
                for key in ('purposeReviewStatus','sentenceCount','charlesSpeakerEvidence','duplicateCandidateIds'):
                    assert row.get(key)==prior_by_id[row['id']].get(key), f'Lost recording purpose field {key}'
# Matching IDs in a newer metadata-only import must preserve separately
# corroborated occurrence dates, held status and CRM joins too.
corroborated={r['id']:r for r in prior_ff.get('records',[]) if r.get('heldStatus')=='source_corroborated'}
if corroborated:
    incoming=copy.deepcopy(current)
    incoming_ff=incoming['meetings']['fireflies']
    incoming_ff['snapshotAt']='2026-10-23T12:00:00Z'
    incoming_ff['records']=[{k:r[k] for k in ('id','title','indexedAt','durationMinutes') if k in r}
                            for r in prior_ff['records']]
    kept=curate_snapshot(preserve_newer_shared_sources(incoming,current))
    rows={r['id']:r for r in kept['meetings']['fireflies']['records']}
    for ident,record in corroborated.items():
        for key in ('heldStatus','occurredAt','occurrenceDatePrecision','crmDealIds','joinStatus','evidenceStatus'):
            assert rows[ident].get(key)==record.get(key), f'Lost independently corroborated recording field {key}'
    # A later explicit, dated review may still retract a prior occurrence claim.
    ident=next(iter(corroborated))
    newer=copy.deepcopy(incoming)
    decision=next(r for r in newer['meetings']['fireflies']['records'] if r['id']==ident)
    decision.update(corroborationReviewedAt='2026-10-24T12:00:00Z',heldStatus='retracted_by_review',
                    occurredAt=None,crmDealIds=[],joinStatus='reviewed_join_retracted')
    decision=next(r for r in preserve_newer_shared_sources(newer,current)['meetings']['fireflies']['records'] if r['id']==ident)
    assert decision['heldStatus']=='retracted_by_review' and decision['occurredAt'] is None
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
