"""Independent evidence survives unrelated parent refreshes and stale replays."""
from copy import deepcopy
import json
from pathlib import Path
from prepare_shared_snapshot import (curate_snapshot, merge_review_rows,
                                     preserve_newer_shared_sources)

ROOT=Path(__file__).resolve().parents[1]
baseline=curate_snapshot(json.loads((ROOT/'data/shared-dashboard.json').read_text()))
later='2026-12-01T06:00:00Z'

# Calendar-only imports omit commercial source decisions, not their evidence.
incoming=deepcopy(baseline)
incoming['meetings']['snapshotAt']=later
for child in ('sourceVerifiedHeldCalls','sourceObservedOpportunities',
              'sourceObservedOpportunityStateReviews','businessContextReview'):
    incoming['meetings'].pop(child,None)
after=curate_snapshot(preserve_newer_shared_sources(incoming,baseline))
for child in ('sourceVerifiedHeldCalls','sourceObservedOpportunities',
              'sourceObservedOpportunityStateReviews','businessContextReview'):
    if child in baseline['meetings']:
        assert after['meetings'][child]==baseline['meetings'][child],child
assert after['outcomes']==baseline['outcomes']
assert after['meetings']['snapshotAt']==later

# October preparation cannot erase separately collected November audio.
incoming=deepcopy(baseline)
incoming['time']['snapshotAt']=later
incoming['time'].pop('novemberRecordingReview',None)
after=curate_snapshot(preserve_newer_shared_sources(incoming,baseline))
assert after['time']['novemberRecordingReview']==baseline['time']['novemberRecordingReview']
assert after['time']['snapshotAt']==later
assert next(s for s in after['sources'] if s['id']=='time_november')==next(s for s in baseline['sources'] if s['id']=='time_november')

# Independently newer workbook wins in both input orders, preserving the UI.
incoming=deepcopy(baseline)
incoming['content']['snapshotAt']=later
incoming['content']['creatorAnalytics']['snapshotAt']=later
workbook=incoming['content']['creatorAnalytics']['exportAnalytics']
workbook['snapshotAt']=workbook['collectedAt']='2026-10-01T06:00:00Z'
workbook['daily']=workbook['daily'][:1]
for source,previous in ((incoming,baseline),(baseline,incoming)):
    after=preserve_newer_shared_sources(source,previous)
    assert after['content']['creatorAnalytics']['snapshotAt']==later
    assert after['content']['creatorAnalytics']['exportAnalytics']==baseline['content']['creatorAnalytics']['exportAnalytics']
    card=next(s for s in after['sources'] if s['id']=='content_creator_export')
    assert card['asOf']==baseline['content']['creatorAnalytics']['exportAnalytics']['snapshotAt']
    assert card['coverage']==baseline['content']['creatorAnalytics']['exportAnalytics']['coverage']

# Different source IDs survive partial row reviews; a later explicit decision
# supersedes its identity, while an ambiguous same-clock conflict fails closed.
first={'conversationId':'source:a','reviewedAt':'2026-11-01T00:00:00Z','heldAt':'2026-10-30'}
second=dict(first,reviewedAt='2026-11-02T00:00:00Z',heldAt='2026-10-31')
other=dict(first,conversationId='source:b')
old={'meetings':{'sourceVerifiedHeldCalls':[first,other]}}
new={'meetings':{'sourceVerifiedHeldCalls':[second]}}
for source,previous in ((new,old),(old,new)):
    merged=merge_review_rows(source,previous,'sourceVerifiedHeldCalls','conversationId')
    assert {r['conversationId']:r for r in merged}=={'source:a':second,'source:b':other}
for invalid in ([dict(first,heldAt='2026-10-29')],[first,first],[dict(first,reviewedAt=None)]):
    try:merge_review_rows({'meetings':{'sourceVerifiedHeldCalls':invalid}},old,'sourceVerifiedHeldCalls','conversationId')
    except AssertionError:pass
    else:raise AssertionError('Invalid source decision accepted')

incoming=deepcopy(baseline)
incoming['content']['creatorAnalytics']['exportAnalytics']['daily'][0]['impressions']+=1
try:preserve_newer_shared_sources(incoming,baseline)
except AssertionError as error:assert 'collection clock' in str(error)
else:raise AssertionError('Conflicting equal-clock workbook accepted')

assert curate_snapshot(preserve_newer_shared_sources(after,after))==curate_snapshot(after)
print('Independent review preservation: calendar decisions/closure, November audio, creator workbook, partial stable-ID reviews and equal-clock conflict guards passed.')
