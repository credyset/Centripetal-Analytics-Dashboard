"""Regress bounded mailbox context, privacy, clocks and commercial isolation."""
from pathlib import Path
import copy
import json

from apply_mailbox_review_2026_10_24 import apply_review, validate_review, COUNTERS
from prepare_shared_snapshot import preserve_newer_shared_sources

ROOT=Path(__file__).resolve().parents[1]


def fixture(clock='2026-10-24T06:43:06.514Z',thread=30330):
    return {'snapshotAt':clock,'reviewedAt':clock,
        'scope':{'kind':'targeted_inbox_review','mailboxKeysReviewed':['charles_team'],
            'foldersReviewed':['inbox'],'focusWindow':{'start':'2026-10-19','end':'2026-10-24'},
            'fullAccountCensus':False,'completeCommercialActivityCoverage':False,
            'selectionBasis':'Targeted business-correspondence context, including earlier relationship evidence.'},
        'accessContext':{'browserSessionUserLabel':'CW','mailboxes':[{'mailboxKey':'charles_team',
            'sourceMailboxId':'fixture-team-mailbox','mode':'team',
            'ownerLabel':'Charles','identityVerified':True}],
            'note':'Browser-session identity and selected mailbox ownership are separate from verified message senders.'},
        'sourceDisplayedAggregateConversationCount':9297,
        'aggregateCountScope':'Displayed aggregate inbox conversations; not selected-period activity or completeness evidence.',
        'records':[{'recordId':f'charles_team:thread:{thread}','mailboxKey':'charles_team','threadId':thread,
            'company':'Example business','dealIds':[],'observedAt':clock,'messageDate':'2026-10-23',
            'datePrecision':'day','occurredAt':None,'sourceTimezone':None,
            'sourceDisplayedDateLabel':'Oct23','messageDateBasis':'Displayed current-year source date; source timezone is unknown.',
            'direction':'inbound','senderVerified':True,'charlesInCorrespondenceObserved':True,
            'contextKind':'commercial_context_candidate',
            'summary':'An incoming business email references an earlier meeting and introduction support.',
            'remainingEvidenceNeeded':'Charles must review the sales-prospect role and any commercial decision.',
            'meetingReferenceObserved':True,'commercialOutcomeDecisionApplied':False,
            'evidenceUrl':f'https://centripetaladvisors.pipedrive.com/mail/search/thread/{thread}'}],
        'counterChanges':dict.fromkeys(COUNTERS,0),
        'notes':['A meeting reference is correspondence evidence; no commercial headline or Video DM event is added.']}


def rejected(patch):
    try:validate_review(patch)
    except (AssertionError,KeyError,ValueError):return
    raise AssertionError('Invalid mailbox context was accepted')


def main():
    actual=json.loads((ROOT/'data/shared-dashboard.json').read_text())
    if actual['crm'].get('mailboxReview'):
        validate_review(actual['crm']['mailboxReview'])
        assert next(c for c in actual['sources']if c['id']=='crm_inbox_context')['asOf']==actual['crm']['mailboxReview']['snapshotAt']
    baseline=copy.deepcopy(actual)
    baseline['crm'].pop('mailboxReview',None)
    baseline['sources']=[c for c in baseline['sources']if c['id']!='crm_inbox_context']
    raw=copy.deepcopy(baseline);patch=fixture();source_copy=copy.deepcopy(patch)
    result=apply_review(baseline,patch,'2026-10-24T07:00:00Z')
    assert baseline==raw and patch==source_copy, 'Applying context mutated input'
    for key in ('outcomes','time','video','ads','waalaxy','content','meetings','referrals'):
        assert result[key]==baseline[key],key
    for key,value in baseline['crm'].items():assert result['crm'][key]==value,key
    assert result['crm']['snapshotAt']==baseline['crm']['snapshotAt']
    assert result['crm']['mailboxReview']['sourceDisplayedAggregateConversationCount']==9297
    assert all(value==0 for value in result['crm']['mailboxReview']['counterChanges'].values())
    # A newer targeted selection keeps earlier thread/source clocks in a
    # separately labelled historical batch, rather than pretending to reread it.
    fresh=fixture('2026-10-24T07:01:00Z',thread=30331)
    updated=apply_review(result,fresh,'2026-10-24T07:02:00Z')
    history=updated['crm']['mailboxReview']['retainedPriorReviews']
    assert len(history)==1 and history[0]['records'][0]['threadId']==30330
    assert history[0]['records'][0]['observedAt']=='2026-10-24T06:43:06.514Z'
    assert updated['crm']['mailboxReview']['records'][0]['threadId']==30331
    repeated=apply_review(updated,fresh,'2026-10-24T07:03:00Z')
    assert repeated['crm']['mailboxReview']==updated['crm']['mailboxReview'], 'Replay duplicated history'
    try:apply_review(updated,patch,'2026-10-24T07:04:00Z')
    except AssertionError:pass
    else:raise AssertionError('Older independent source was allowed to overwrite newer review')
    # A future upstream CRM census must retain the independently dated review
    # and its source card even when it contains no mailbox supplement itself.
    upstream=copy.deepcopy(baseline);upstream['crm']['snapshotAt']='2026-10-25T00:00:00Z'
    preserved=preserve_newer_shared_sources(upstream,updated)
    assert preserved['crm']['mailboxReview']==updated['crm']['mailboxReview']
    card=next(c for c in preserved['sources']if c['id']=='crm_inbox_context')
    assert card['asOf']==fresh['snapshotAt'] and card['asOf']!=upstream['crm']['snapshotAt']
    # Whole-parent selection must not discard a newer child from the other
    # original input, even when that input's CRM inventory is older.
    older_parent_newer_child=copy.deepcopy(updated)
    older_parent_newer_child['crm']['snapshotAt']='2020-01-01T00:00:00Z'
    newer_parent_older_child=copy.deepcopy(result)
    newer_parent_older_child['crm']['snapshotAt']='2030-01-01T00:00:00Z'
    for source,prior in [(older_parent_newer_child,newer_parent_older_child),(newer_parent_older_child,older_parent_newer_child)]:
        joined=preserve_newer_shared_sources(source,prior)
        assert joined['crm']['snapshotAt']=='2030-01-01T00:00:00Z'
        assert joined['crm']['mailboxReview']==updated['crm']['mailboxReview']
        assert next(c for c in joined['sources']if c['id']=='crm_inbox_context')['asOf']==fresh['snapshotAt']
    for mutate in [
        lambda p:p['records'][0].update(body='Raw message content'),
        lambda p:p['records'][0].update(summary='Contact at private@example.org'),
        lambda p:p['records'][0].update(direction='inbound',senderVerified=False),
        lambda p:p['counterChanges'].update(heldProspectConversations=1),
        lambda p:p['scope'].update(fullAccountCensus=True),
        lambda p:p['records'][0].update(occurredAt='2026-10-23T12:00:00Z'),
        lambda p:p['records'].append(copy.deepcopy(p['records'][0])),
        lambda p:p['records'][0].update(commercialOutcomeDecisionApplied=True),
        lambda p:p['records'][0].update(heldMeetingInferred=True),
        lambda p:p['records'][0].update(scheduledEventDate='2026-02-30',bookingEvidence='accepted_invitation'),
    ]:
        bad=fixture();mutate(bad);rejected(bad)
    # Displaying a date without a timezone remains day-level source evidence.
    assert patch['records'][0]['occurredAt'] is None and patch['records'][0]['sourceTimezone'] is None
    print('Mailbox review: independent source/history preservation, aggregate isolation, sender/date guards, privacy and unchanged commercial outcomes passed.')


if __name__=='__main__':main()
