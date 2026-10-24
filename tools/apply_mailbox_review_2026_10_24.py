"""Apply a bounded, independently dated Sales Inbox context review.

The CLI writes only a private preview. Raw subjects, bodies, addresses and
credentials are not valid fields. Context never updates commercial decisions.
"""
from datetime import datetime, timezone, date
from pathlib import Path
import argparse
import copy
import json
import re

from apply_refresh_2026_10_23 import assert_curated
from prepare_shared_snapshot import curate_snapshot, preserve_newer_shared_sources

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/gap_resolution_2026_10_24/inbox'
COUNTERS = {'heldProspectConversations', 'qualifiedProspectCompanies', 'acceptedOpportunities',
    'firstClientWins', 'videoSends', 'videoReplies', 'referralEvents', 'humanHours'}
TOP = {'snapshotAt','reviewedAt','scope','accessContext','sourceDisplayedAggregateConversationCount',
    'aggregateCountScope','records','counterChanges','notes','retainedPriorReviews'}
SCOPE = {'kind','mailboxKeysReviewed','foldersReviewed','focusWindow','fullAccountCensus',
    'completeCommercialActivityCoverage','selectionBasis','listPagesReviewed'}
ACCESS = {'browserSessionUserLabel','mailboxes','note'}
MAILBOX = {'mailboxKey','sourceMailboxId','mode','ownerLabel','identityVerified'}
RECORD = {'recordId','mailboxKey','threadId','company','contact','dealIds','observedAt',
    'messageDate','datePrecision','occurredAt','sourceTimezone','sourceDisplayedDateLabel',
    'messageDateBasis','direction','senderVerified','charlesInCorrespondenceObserved',
    'contextKind','summary','remainingEvidenceNeeded','commercialOutcomeDecisionApplied',
    'meetingReferenceObserved','evidenceUrl','notes','messageDateRange','scheduledEventDate',
    'scheduledEventTimezone','bookingEvidence','heldMeetingInferred','relatedThreadIds'}


def instant(value):
    result = datetime.fromisoformat(value.replace('Z','+00:00'))
    assert result.tzinfo is not None, 'Observation clock needs an explicit offset'
    return result


def unknown_fields(value, allowed, label):
    assert not set(value) - allowed, f'Unexpected {label} fields: {sorted(set(value)-allowed)}'


def validate_review(review, historical=False):
    unknown_fields(review, TOP, 'mailbox-review')
    observed, reviewed = instant(review['snapshotAt']), instant(review['reviewedAt'])
    assert reviewed >= observed
    scope = review['scope']; unknown_fields(scope, SCOPE, 'scope')
    assert scope['kind'] == 'targeted_inbox_review'
    assert scope['fullAccountCensus'] is False
    assert scope['completeCommercialActivityCoverage'] is False
    assert isinstance(scope['mailboxKeysReviewed'], list) and scope['mailboxKeysReviewed']
    assert isinstance(scope['foldersReviewed'], list) and scope['foldersReviewed']
    window = scope['focusWindow']; assert set(window) == {'start','end'}
    assert date.fromisoformat(window['start']) <= date.fromisoformat(window['end'])
    access = review['accessContext']; unknown_fields(access, ACCESS, 'access-context')
    assert isinstance(access['browserSessionUserLabel'], str) and access['browserSessionUserLabel']
    mailboxes = access['mailboxes']; assert mailboxes
    keys = set()
    for mailbox in mailboxes:
        unknown_fields(mailbox, MAILBOX, 'mailbox')
        assert mailbox['mailboxKey'] not in keys; keys.add(mailbox['mailboxKey'])
        assert mailbox['mode'] in {'team','personal'}
        assert mailbox['identityVerified'] is True
        assert mailbox['ownerLabel']
    assert set(scope['mailboxKeysReviewed']) <= keys
    count = review['sourceDisplayedAggregateConversationCount']
    assert count is None or (isinstance(count,int) and not isinstance(count,bool) and count >= 0)
    assert isinstance(review['aggregateCountScope'], str) and review['aggregateCountScope']
    assert set(review['counterChanges']) == COUNTERS
    assert all(value == 0 and not isinstance(value,bool) for value in review['counterChanges'].values())
    record_keys = set()
    for row in review['records']:
        unknown_fields(row, RECORD, 'mailbox-record')
        assert row['mailboxKey'] in scope['mailboxKeysReviewed']
        assert isinstance(row['threadId'], int) and row['threadId'] > 0
        key = f"{row['mailboxKey']}:thread:{row['threadId']}"
        assert row['recordId'] == key and key not in record_keys; record_keys.add(key)
        assert instant(row['observedAt']) <= observed
        assert row['commercialOutcomeDecisionApplied'] is False
        assert row['direction'] in {'inbound','outbound','mixed','unconfirmed'}
        assert isinstance(row['senderVerified'],bool)
        if not row['senderVerified']:
            assert row['direction'] == 'unconfirmed', 'Mailbox/folder membership does not verify sender direction'
        assert row['contextKind'] and row['summary'] and row['remainingEvidenceNeeded']
        assert isinstance(row['dealIds'],list) and len(row['dealIds']) == len(set(row['dealIds']))
        assert all(isinstance(value,int) and value > 0 for value in row['dealIds'])
        precision = row['datePrecision']; assert precision in {'day','timestamp','unknown'}
        if precision == 'day':
            date.fromisoformat(row['messageDate']); assert row['occurredAt'] is None
        elif precision == 'timestamp':
            instant(row['occurredAt']); assert row['sourceTimezone'], 'An exact source instant needs explicit source-time context'
            date.fromisoformat(row['messageDate'])
        else:
            assert row['messageDate'] is None and row['occurredAt'] is None
        if row.get('messageDateRange'):
            bounds=row['messageDateRange']; assert set(bounds)=={'start','end'}
            assert date.fromisoformat(bounds['start']) <= date.fromisoformat(row['messageDate']) <= date.fromisoformat(bounds['end'])
        if row.get('scheduledEventDate'):
            date.fromisoformat(row['scheduledEventDate'])
            assert row.get('bookingEvidence') in {'scheduling_correspondence','accepted_invitation'}
        if 'heldMeetingInferred' in row:
            assert row['heldMeetingInferred'] is False
        if row.get('relatedThreadIds'):
            assert len(set(row['relatedThreadIds']))==len(row['relatedThreadIds'])
            assert all(isinstance(value,int) and value>0 for value in row['relatedThreadIds'])
        if row.get('evidenceUrl'):
            assert row['evidenceUrl'] == f"https://centripetaladvisors.pipedrive.com/mail/search/thread/{row['threadId']}"
    # A bounded review may mention prospect names/companies, but never include
    # raw mail content or addresses hidden in an unexpected nested field.
    assert not re.search(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', json.dumps(review), re.I), 'Use mailbox labels and curated summaries; raw addresses stay private'
    for prior in review.get('retainedPriorReviews', []):
        assert not prior.get('retainedPriorReviews'), 'Review history must be flat'
        validate_review(prior, historical=True)
        assert instant(prior['reviewedAt']) <= reviewed
    assert_curated(review)
    return review


def apply_review(before, incoming, generated_at=None):
    validate_review(incoming)
    result = copy.deepcopy(before)
    previous = before.get('crm', {}).get('mailboxReview')
    current = copy.deepcopy(incoming)
    if previous:
        validate_review(previous)
        assert instant(current['snapshotAt']) >= instant(previous['snapshotAt']), 'Mailbox source collection cannot move backward'
        assert instant(current['reviewedAt']) >= instant(previous['reviewedAt']), 'Mailbox review cannot move backward'
        old = copy.deepcopy(previous); old_history = old.pop('retainedPriorReviews', [])
        existing = list(current.pop('retainedPriorReviews', []))
        if old != current:
            existing.extend(old_history + [old])
        else:
            existing.extend(old_history)
        unique = {json.dumps(row,sort_keys=True):row for row in existing}
        if unique:
            current['retainedPriorReviews'] = sorted(unique.values(),key=lambda r:instant(r['reviewedAt']))
    result['crm']['mailboxReview'] = current
    cards = {card['id']:copy.deepcopy(card) for card in result.get('sources',[])}
    cards['crm_inbox_context'] = {'id':'crm_inbox_context','name':'Pipedrive · targeted Charles mailbox context',
        'asOf':current['snapshotAt'],'status':'Independent bounded correspondence review',
        'coverage':copy.deepcopy(current['scope']),
        'method':'Read-only Sales Inbox browser review; selected mailbox and individual sender/date evidence verified separately',
        'note':'Curated correspondence context only. The displayed inbox aggregate is not selected-period activity or completeness evidence. Original CRM inventory and commercial decisions retain their own sources and clocks.'}
    result['sources'] = list(cards.values())
    generated = generated_at or datetime.now(timezone.utc).isoformat()
    assert instant(generated) >= instant(current['reviewedAt']), 'Generation clock predates the independent review'
    result['meta'].update(generatedAt=generated,analyticsRevisedAt=generated)
    result = curate_snapshot(preserve_newer_shared_sources(result,before))
    validate_review(result['crm']['mailboxReview'])
    for key in before:
        if key not in {'crm','sources','meta'}:
            assert result[key] == before[key], f'Mailbox context altered unrelated source: {key}'
    for key in before['crm']:
        if key != 'mailboxReview':
            assert result['crm'][key] == before['crm'][key], f'Mailbox context altered CRM source: {key}'
    assert result['outcomes'] == before['outcomes'], 'Mailbox context altered commercial decisions'
    assert result['time'] == before['time'], 'Mailbox context altered owner hours'
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'data/shared-dashboard.json')
    parser.add_argument('--patch',type=Path,default=PRIVATE/'mailbox_review_public_patch.json')
    parser.add_argument('--output',type=Path,default=PRIVATE/'integrated_mailbox_preview.json')
    args=parser.parse_args()
    result=apply_review(json.loads(args.input.read_text()),json.loads(args.patch.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'preview':str(args.output),'sourceCollectedAt':result['crm']['mailboxReview']['snapshotAt'],
        'currentReviewedThreads':len(result['crm']['mailboxReview']['records']),'commercialOutcomeChanges':0,'sharedFilesWritten':False}))


if __name__=='__main__':main()
