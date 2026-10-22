"""Regression checks for URL-vs-note evidence and scoped CRM reconciliation."""
from pathlib import Path
import copy
import json
from recording_evidence import recording_evidence_fields, apply_video_evidence_reviews
from prepare_shared_snapshot import curate_snapshot

ROOT=Path(__file__).resolve().parents[1]
for value in ('LI DM - had already connected on LI','Sent a video DM without loom',
              'javascript:alert(1)','https://[bad'):
    fields=recording_evidence_fields(value)
    assert fields['hasRecordingLink'] is False and fields['recordingFieldKind']=='non_url_note'
assert recording_evidence_fields(None)['recordingFieldKind']=='empty'
assert recording_evidence_fields('https://www.loom.com/share/'+'a'*32)['recordingFieldKind']=='loom_url'
assert recording_evidence_fields('https://loom.com.example.org/share/'+'a'*32)['recordingFieldKind']=='other_url'
assert apply_video_evidence_reviews({})=={}

data=json.loads((ROOT/'data/shared-dashboard.json').read_text())
video=data['video']; review=video['crmReconciliation']; rows=video['rows']
assert len(rows)==428 and sum(bool(r.get('hasRecordingLink')) for r in rows)==57
note_rows={r['sourceRow'] for r in rows if r.get('recordingFieldKind')=='non_url_note'}
assert note_rows=={310,1064,1068}
assert review['selfReportedSentRows']==12 and review['messageNoteWithoutAssetRows']==2
assert review['validVideoAssetRows']==review['videoAssetCohortCrmMatches']==10
assert review['expectedVideoCrmMissing']==0
assert len([r for r in review['records'] if r.get('crmDealId')])==10
assert len([r for r in rows if r.get('dealId')])==82
assert len([r for r in rows if r.get('matchedCrmDealId')])==10
assert len(video['datedActions'])==33
assert video['sourceVerification']['verifiedVideoDmSends'] is None

# An older normalizer for exactly this source snapshot must not recreate
# phantom asset links or erase the independently verified CRM join.
incorrect=copy.deepcopy(data)
original_ids={r['sourceRow']:r.get('dealId') for r in rows}
for row in incorrect['video']['rows']:
    if row['sourceRow'] in note_rows:
        row['hasRecordingLink']=True
        row.pop('recordingFieldKind',None)
        row.pop('recordingFieldNote',None)
fixed=curate_snapshot(incorrect)
assert all(not r['hasRecordingLink'] for r in fixed['video']['rows'] if r['sourceRow'] in note_rows)
assert original_ids=={r['sourceRow']:r.get('dealId') for r in fixed['video']['rows']}

# Historical reviews cannot overwrite changed values in a newer Sheet read.
newer=copy.deepcopy(video)
newer['snapshotAt']='2026-10-23T12:00:00Z'
target=next(r for r in newer['rows'] if r['sourceRow']==1064)
target.update(hasRecordingLink=True,recordingFieldKind='loom_url',recordingFieldNote=None)
apply_video_evidence_reviews(newer)
assert target['hasRecordingLink'] is True
print('Video reconciliation:57 URLs/3 notes, scoped10/10 CRM matches, original IDs, source-time guards and delivery limits passed.')
