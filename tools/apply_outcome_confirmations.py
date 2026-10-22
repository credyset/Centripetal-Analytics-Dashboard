"""Build the Charles-only outcome ledger from explicit owner confirmations.

Source snapshots must never manufacture commercial acceptance or attendance.
Call this after assembling the dashboard and again during shared curation so
imports cannot erase confirmed business outcomes. No source service is changed.
"""
import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    data['outcomes'] = ledger
    return data
