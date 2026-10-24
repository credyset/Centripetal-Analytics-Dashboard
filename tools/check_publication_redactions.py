"""Verify employment-source identities cannot reappear through later imports."""
from copy import deepcopy
from pathlib import Path
import json

from publication_redactions import apply_publication_redactions,validate_publication_redactions,rules
from prepare_shared_snapshot import curate_snapshot

ROOT=Path(__file__).resolve().parents[1]
rule=rules()['01M5CWDYQKG89SJR4KZ07H7DQ3']
source_record={'id':rule['sourceId'],'title':'Excluded personal title','indexedAt':'2026-10-22T17:30:00Z',
    'durationMinutes':25.18,'classification':'recruiting_interview','classificationBasis':'Private employment assessment',
    'participantNames':['Employment candidate'],'originalTitle':'Excluded personal title',
    'recordingUrl':'https://example.invalid/private-recording',
    'metadata':{'title':'Excluded personal title','candidateName':'Employment candidate'},
    'speakerNames':['Employment candidate'],'jobAssessment':'Private hiring discussion'}
prospect={'id':'other-source','title':'Approved prospect conversation','contact':'Approved prospect'}
fixture={'nested':{'records':[deepcopy(source_record),deepcopy(prospect)]}}
original=deepcopy(fixture)
minimized=apply_publication_redactions(deepcopy(fixture))
assert fixture==original, 'Minimization must operate on a curated copy'
record=minimized['nested']['records'][0]
assert record['id']==source_record['id'] and record['indexedAt']==source_record['indexedAt']
assert record['durationMinutes']==source_record['durationMinutes']
assert record['title']==rule['safeTitle'] and set(record)<=set(rule['allowedFields'])
assert minimized['nested']['records'][1]==prospect, 'Non-target prospect data changed'
validate_publication_redactions(minimized)
for mutation in ['title','extra_context','missing_policy']:
    bad=deepcopy(minimized)
    target=bad['nested']['records'][0]
    if mutation=='title':target['title']='Restored personal title'
    elif mutation=='extra_context':target['candidateName']='Restored identity'
    else:target.pop('publicationPolicy')
    try:validate_publication_redactions(bad)
    except AssertionError:pass
    else:raise AssertionError('Unsafe employment mutation passed: '+mutation)

# Exercise the actual final curation hook, including nested metadata from a
# future source merger rather than only trusting a redaction marker in input.
source=json.loads((ROOT/'data/shared-dashboard.json').read_text())
source.setdefault('meetings',{}).setdefault('fireflies',{})['publicationHookTest']={'records':[deepcopy(source_record)]}
before=deepcopy(source)
public=curate_snapshot(source)
assert source==before, 'Curation modified raw input'
curated=public['meetings']['fireflies']['publicationHookTest']['records'][0]
assert curated['title']==rule['safeTitle'] and 'metadata' not in curated
assert curated['publicationPolicy']['candidateIdentityWithheld'] is True
assert public['outcomes']==source['outcomes'], 'Employment minimization altered commercial decisions'
assert public['time']['summary']['ownerEstimateRange']==source['time']['summary']['ownerEstimateRange']
validate_publication_redactions(public)
print('Publication redaction: opaque-source-ID minimization, nested metadata removal, unchanged business data and fail-closed validation passed.')
