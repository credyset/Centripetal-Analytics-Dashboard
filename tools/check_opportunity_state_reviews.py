"""Exercise source closure guards without altering original opportunity events."""
import copy
import json
import tempfile
from pathlib import Path
from apply_outcome_confirmations import apply_outcome_confirmations

closed_at = '2026-11-17T17:54:57Z'
original = {
    'opportunityId': 'commercial:example', 'companyKey': 'company:example',
    'company': 'Example', 'dealId': 10, 'documentedBy': '2026-09-24',
    'lastDocumentedAt': '2026-10-15', 'originalAcceptedAt': None,
    'originalAcceptanceDateVerified': False, 'acceptedBeforeOctober': True,
    'nextStep': 'Review the scoped proposal', 'evidenceBasis': 'Dated commercial dialogue',
    'reviewedAt': '2026-10-22T12:00:00Z',
}
review = {
    'opportunityId': original['opportunityId'], 'companyKey': original['companyKey'],
    'dealId': 10, 'sourceStatus': 'lost', 'sourceClosedAt': closed_at,
    'sourceStatusField': 'Pipedrive deal.status',
    'sourceStatusChangedEventId': 'pipedrive:dealChange:123',
    'sourceSnapshotAt': '2026-11-20T05:20:00Z',
    'lastReviewedAt': '2026-11-20T08:02:20Z',
    'historicalNextStep': original['nextStep'], 'nextStep': None,
    'currentState': 'source_closed_lost',
    'currentNextStepStatus': 'no_active_agreed_next_step_verified',
    'closureEvidence': {
        'sourceSystem': 'pipedrive_mail', 'sourceMessageId': 123,
        'sourceTimestampField': 'mailMessage.message_time',
        'occurredAt': '2026-11-17T17:54:18Z',
        'evidenceUrl': 'https://centripetaladvisors.pipedrive.com/mail/search/thread/123',
        'summary': 'Charles sent a final step-back message.',
    },
    'preserveHistoricalFields': {key: original[key] for key in (
        'documentedBy', 'lastDocumentedAt', 'originalAcceptedAt',
       'originalAcceptanceDateVerified', 'acceptedBeforeOctober')},
}
decisions = {
    'scope': 'charles_only', 'timezone': 'America/Denver', 'heldCalls': [],
    'observedOpportunities': [original],
    'opportunityAcceptances': [{'opportunityId': 'untouched-event', 'confirmedOn': '2026-09-24'}],
    'clientWins': [{'companyKey': 'untouched-client'}],
    'coverage': {'opportunityAcceptances': {'status': 'incomplete'}},
}
base = {
    'crm': {'deals': [{'id': 10, 'status': 'lost', 'lostAt': closed_at}]},
    'meetings': {'sourceObservedOpportunityStateReviews': [review]},
}

with tempfile.TemporaryDirectory(prefix='centripetal-opportunity-state-') as folder:
    root = Path(folder)
    (root / 'OWNER_CONFIRMATIONS.json').write_text(json.dumps({'heldCalls': []}))
    (root / 'OUTCOME_CONFIRMATIONS.json').write_text(json.dumps(decisions))
    first = apply_outcome_confirmations(copy.deepcopy(base), root)
    closed = first['outcomes']['observedOpportunities'][0]
    for key, value in original.items():
        if key != 'nextStep':
            assert closed[key] == value, f'Historical {key} changed'
    assert closed['historicalNextStep'] == original['nextStep'] and closed['nextStep'] is None
    assert closed['currentState'] == 'closed_lost' and closed['sourceStatus'] == 'lost'
    assert apply_outcome_confirmations(copy.deepcopy(first), root) == first, 'Repeated curation changed closure'
    for key in ('heldCalls', 'opportunityAcceptances', 'clientWins', 'coverage'):
        assert first['outcomes'][key] == decisions[key], f'Closure changed {key}'

    def reject(change):
        candidate = copy.deepcopy(base)
        change(candidate, candidate['meetings']['sourceObservedOpportunityStateReviews'][0])
        try:
            apply_outcome_confirmations(candidate, root)
        except AssertionError:
            return
        raise AssertionError('Invalid lifecycle source review was accepted')

    for change in (
        lambda d, r: r.update(opportunityId='not-an-existing-opportunity'),
        lambda d, r: r.update(dealId=11),
        lambda d, r: r.pop('sourceStatus'),
        lambda d, r: r.update(sourceStatus='open'),
        lambda d, r: d['crm']['deals'][0].update(status='open'),
        lambda d, r: r.pop('sourceClosedAt'),
        lambda d, r: r.update(sourceClosedAt='2026-11-17'),
        lambda d, r: r.update(sourceClosedAt='2026-11-17T17:54:57'),
        lambda d, r: r.pop('lastReviewedAt'),
        lambda d, r: r.update(sourceStatusField='Pipedrive stage.name'),
        lambda d, r: r['closureEvidence'].pop('sourceMessageId'),
        lambda d, r: r.update(historicalNextStep='A different proposal step'),
        lambda d, r: r['preserveHistoricalFields'].update(lastDocumentedAt='2026-11-17'),
        lambda d, r: r.update(sourceClosedAt='2026-11-20T09:00:00Z'),
    ):
        reject(change)

    # A source-observed opportunity is merged before its state review too.
    source_only = copy.deepcopy(base)
    source_only['meetings']['sourceObservedOpportunities'] = [copy.deepcopy(original)]
    without_owner_observed = copy.deepcopy(decisions)
    without_owner_observed['observedOpportunities'] = []
    (root / 'OUTCOME_CONFIRMATIONS.json').write_text(json.dumps(without_owner_observed))
    assert apply_outcome_confirmations(source_only, root)['outcomes']['observedOpportunities'][0] == closed

print('Opportunity state review checks passed: stable original evidence, idempotence, source-only merge and 14 invalid review rejections')

# Exercise the real snapshot validator with a source-linked request whose
# referring contact is outside the Referral Pipeline. It is still an action,
# while introduction/follow-up records retain their stricter referral join.
import subprocess
import sys
root = Path(__file__).resolve().parents[1]
snapshot = json.loads((root / 'data/shared-dashboard.json').read_text())
contact = next(row for row in snapshot['crm']['deals'] if not row.get('isTest'))
request = {
    'eventId': 'validator:request:999999999', 'type': 'request',
    'direction': 'outbound', 'verified': True, 'charlesIncluded': True,
    'sentByCharles': True, 'sourceSystem': 'pipedrive_mail',
    'sourceMessageId': 999999999, 'sourceContactDealId': contact['id'],
    'referralDealId': None, 'prospectDealId': None,
    'communicationCount': 1,
    'requestedCompanies': [{'company': contact['title'], 'prospectDealId': contact['id']}],
    'date': '2026-11-17', 'occurredAt': '2026-11-17T12:00:00Z',
    'datePrecision': 'timestamp', 'sourceTimezone': 'UTC',
    'heldCallConfirmed': None, 'acceptedOpportunityConfirmed': None,
    'firstClientWinConfirmed': None,
}
with tempfile.TemporaryDirectory(prefix='centripetal-referral-request-') as folder:
    path = Path(folder) / 'snapshot.json'

    def validate_request(change=None, expected=True):
        candidate = copy.deepcopy(snapshot)
        event = copy.deepcopy(request)
        if change:
            change(event)
        candidate['referrals']['eventReview']['events'].append(event)
        path.write_text(json.dumps(candidate))
        result = subprocess.run([sys.executable, str(root / 'tools/check_shared_snapshot.py'), '--snapshot', str(path)], capture_output=True, text=True)
        assert (result.returncode == 0) is expected, result.stdout + result.stderr

    validate_request()
    for change in (
        lambda r: r.update(sourceContactDealId=-1),
        lambda r: r.update(type='follow_up'),
        lambda r: r.update(communicationCount=3),
        lambda r: r.update(communicationCount=True),
        lambda r: r['requestedCompanies'][0].update(prospectDealId=-1),
        lambda r: r['requestedCompanies'][0].update(company='Different company identity'),
        lambda r: r['requestedCompanies'].append(copy.deepcopy(r['requestedCompanies'][0])),
        lambda r: r.update(heldCallConfirmed=True),
    ):
        validate_request(change, expected=False)
print('Referral request checks passed: valid non-referral contact join and 8 invalid request rejections')
