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
    ledger['ownerDecisionsAsOf'] = max(filter(None, [r.get('confirmedOn') for r in ledger['heldCalls'] + ledger.get('opportunityAcceptances', []) + ledger.get('clientWins', [])]), default=None)
    data['outcomes'] = ledger
    return data
