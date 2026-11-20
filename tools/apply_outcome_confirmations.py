"""Build the Charles-only outcome ledger from owner and reviewed source evidence.

Source snapshots must never manufacture commercial acceptance or attendance.
Call this after assembling the dashboard and again during shared curation so
imports cannot erase confirmed business outcomes. No source service is changed.
"""
import copy
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def explicit_timestamp(value, field):
    """Require an actual source instant; a date or naive clock is insufficient."""
    assert isinstance(value, str) and re.search(r'T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$', value), f'{field} needs an explicit offset timestamp'
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise AssertionError(f'{field} needs a valid source timestamp') from error
    assert parsed.utcoffset() is not None, f'{field} needs an explicit offset'
    return parsed


def apply_opportunity_state_reviews(observed, data):
    """Overlay source closure without rewriting historical acceptance evidence."""
    deals = {row['id']: row for row in data.get('crm', {}).get('deals', [])}
    reviewed = set()
    historical = ('documentedBy', 'lastDocumentedAt', 'originalAcceptedAt',
                  'originalAcceptanceDateVerified', 'acceptedBeforeOctober')
    for review in data.get('meetings', {}).get('sourceObservedOpportunityStateReviews', []):
        ident = review.get('opportunityId')
        assert ident in observed and ident not in reviewed, 'State review needs one existing opportunity ID'
        reviewed.add(ident)
        row = observed[ident]
        deal_id = review.get('dealId')
        assert type(deal_id) is int and deal_id == row.get('dealId'), 'State review deal does not match opportunity'
        deal = deals.get(deal_id)
        assert deal and deal.get('status') == 'lost', 'State review needs an actual CRM lost status'
        assert review.get('sourceStatus') == 'lost', 'Only explicit source lost status is supported'
        assert review.get('sourceStatusField') == 'Pipedrive deal.status', 'Stage labels cannot establish status'
        assert re.fullmatch(r'pipedrive:dealChange:\d+', review.get('sourceStatusChangedEventId', '')), 'Source status change identity is required'
        if review.get('companyKey') is not None:
            assert review['companyKey'] == row.get('companyKey'), 'State review company does not match opportunity'
        closed_at = explicit_timestamp(review.get('sourceClosedAt'), 'sourceClosedAt')
        reviewed_at = explicit_timestamp(review.get('lastReviewedAt'), 'lastReviewedAt')
        snapshot_at = explicit_timestamp(review.get('sourceSnapshotAt'), 'sourceSnapshotAt')
        assert closed_at <= snapshot_at and closed_at <= reviewed_at, 'Closure must precede source collection and review'
        assert deal.get('lostAt') and explicit_timestamp(deal['lostAt'], 'CRM lostAt') == closed_at, 'Source closure must match the retained actual lost timestamp'
        evidence = review.get('closureEvidence') or {}
        assert evidence.get('sourceSystem') == 'pipedrive_mail', 'Closure needs primary source evidence'
        assert type(evidence.get('sourceMessageId')) is int and evidence['sourceMessageId'] > 0
        assert evidence.get('sourceTimestampField') == 'mailMessage.message_time'
        assert evidence.get('summary') and evidence.get('evidenceUrl', '').startswith('https://centripetaladvisors.pipedrive.com/mail/'), 'Closure needs an evidence summary and source link'
        assert explicit_timestamp(evidence.get('occurredAt'), 'closureEvidence.occurredAt') <= reviewed_at
        assert review.get('nextStep') is None and review.get('currentNextStepStatus') == 'no_active_agreed_next_step_verified'
        assert review.get('currentState') in ('source_closed_lost', 'closed_lost')
        for key, value in review.get('preserveHistoricalFields', {}).items():
            assert key in historical and row.get(key) == value, 'State review cannot rewrite historical evidence'
        prior_step = row.get('historicalNextStep') or row.get('nextStep')
        assert prior_step and review.get('historicalNextStep') == prior_step, 'Historical next step must retain its original wording'
        # Copy an explicit allowlist only. Collection/review dates never become
        # active documentation or original acceptance dates.
        for key in ('sourceStatus', 'sourceClosedAt', 'sourceStatusField',
                    'sourceStatusChangedEventId', 'sourceSnapshotAt', 'lastReviewedAt',
                    'currentNextStepStatus', 'closureEvidence'):
            row[key] = copy.deepcopy(review[key])
        row.update(historicalNextStep=prior_step, nextStep=None, currentState='closed_lost')
    return observed


def apply_outcome_confirmations(data, root=ROOT):
    root = Path(root)
    decisions = json.loads((root / 'OUTCOME_CONFIRMATIONS.json').read_text())
    assert decisions['scope'] == 'charles_only'
    assert decisions['timezone'] == 'America/Denver'
    legacy = json.loads((root / 'OWNER_CONFIRMATIONS.json').read_text())
    ledger = copy.deepcopy(decisions)
    calls = {r['conversationId']: copy.deepcopy(r) for r in decisions.get('heldCalls', [])}
    for row in legacy.get('heldCalls', []):
        key = 'calendly:' + row['bookingChainId']
        disposition = row.get('ownerQualification', '')
        calls.setdefault(key, {
            'conversationId': key,
            'companyKey': 'company:' + re.sub(r'[^a-z0-9]+', '-', row['company'].lower()).strip('-'),
            'company': row['company'],
            'dealId': row['dealId'],
            'bookingChainId': row['bookingChainId'],
            'heldAt': row['heldAt'],
            'dateBasis': row.get('occurrenceDateBasis'),
            'charlesParticipated': True,
            'prospectMeeting': True,
            'heldConfirmed': True,
            'qualification': 'unqualified' if disposition == 'unqualified' else 'qualified' if disposition.startswith('qualified') else 'unknown',
            'qualificationDetail': disposition.replace('_', ' '),
            'qualificationConfirmedOn': legacy.get('confirmedOn'),
            'evidenceBasis': 'Dashboard owner confirmation of the linked Charles prospect call',
            'confirmedOn': legacy.get('confirmedOn'),
        })
    ledger['heldCalls'] = list(calls.values())
    # Preserve the owner's held-call decision while correcting a date inferred
    # from a booking that newer correspondence shows was rescheduled.
    date_reviews={r['dealId']:r for r in ledger['heldCalls'] if r.get('heldDateRange') and r.get('dealId')}
    if date_reviews:
        meetings=data.get('meetings',{})
        for rows in (meetings.get('ownerConfirmedHeldCalls',[]),meetings.get('verifiedLinks',[]),
                     meetings.get('fireflies',{}).get('leadBookingReviews',[])):
            for row in rows:
                review=date_reviews.get(row.get('dealId',row.get('crmDealId')))
                if review:
                    row.update(heldAt=None,heldDateRange=copy.deepcopy(review['heldDateRange']),
                               heldDateBasis=review['dateBasis'],heldStatus='Owner-confirmed held; exact date unresolved')
        for row in meetings.get('events',[]):
            review=next((r for r in date_reviews.values() if r.get('bookingChainId')==row.get('bookingChainId')),None)
            if review and row.get('heldVerified'):
                row.update(heldAt=None,heldDateRange=copy.deepcopy(review['heldDateRange']),heldDateBasis=review['dateBasis'])
        for row in data.get('ads',{}).get('leads',[]):
            review=next((r for r in date_reviews.values() if r['company'].lower()==row.get('company','').lower()),None)
            if review:
                for item in (row,row.get('bookingCorroboration',{})):
                    item.update(heldAt=None,heldDateRange=copy.deepcopy(review['heldDateRange']),heldDateBasis=review['dateBasis'])
        meetings['notes']=[n for n in meetings.get('notes',[]) if not n.startswith('The owner confirmed NuVee (October 6) and Venus')]
        note='The owner confirmed the linked NuVee and Venus calls were held. New inbox evidence shows the Venus October 15 booking was rescheduled to an accepted October 16 invitation; its exact occurrence day remains unresolved. Its held confirmation counts once when a selected period includes both candidate dates. NuVee remains the only qualified paid lead under the latest explicit owner decision.'
        if note not in meetings['notes']:meetings['notes'].append(note)
    ledger['ownerDecisionsAsOf'] = max(filter(None, [r.get('confirmedOn') for r in ledger['heldCalls'] + ledger.get('opportunityAcceptances', []) + ledger.get('clientWins', [])]), default=None)
    # Independently verified conversations can establish a held-call minimum.
    # Preserve the owner ledger and its historical booking-date corrections.
    for row in data.get('meetings', {}).get('sourceVerifiedHeldCalls', []):
        assert row['heldConfirmed'] is True and row['prospectMeeting'] is True and row['charlesParticipated'] is True
        qualification = row['qualification']
        assert qualification in ('unknown', 'qualified', 'unqualified')
        if qualification == 'unknown':
            assert not row.get('qualificationConfirmedOn')
        else:
            assert row.get('sourceQualificationVerified') is True
            assert row.get('qualificationEvidenceBasis') == 'direct_charles_commercial_approval'
            assert row.get('qualificationConfirmedOn') and row.get('qualificationDetail')
            assert row.get('evidenceBasis') and row.get('reviewedAt')
        assert row.get('heldAt') or row.get('heldDateRange')
        calls.setdefault(row['conversationId'], copy.deepcopy(row))
    ledger['heldCalls'] = list(calls.values())
    observed = {r['opportunityId']: copy.deepcopy(r) for r in ledger.get('observedOpportunities', [])}
    for row in data.get('meetings', {}).get('sourceObservedOpportunities', []):
        # A documented proposal establishes current pipeline evidence. Without
        # the original acceptance date it cannot establish a new acceptance.
        assert row.get('originalAcceptanceDateVerified') is False
        assert row.get('originalAcceptedAt') is None
        assert row.get('documentedBy') and row.get('lastDocumentedAt')
        assert row.get('companyKey') and row.get('dealId')
        assert row.get('nextStep') and row.get('evidenceBasis') and row.get('reviewedAt')
        observed.setdefault(row['opportunityId'], copy.deepcopy(row))
    apply_opportunity_state_reviews(observed, data)
    ledger['observedOpportunities'] = list(observed.values())
    data['outcomes'] = ledger
    return data
