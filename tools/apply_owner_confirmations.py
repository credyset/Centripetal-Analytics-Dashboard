"""Retain explicit owner outcomes across independent source refreshes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply_owner_confirmations(snapshot):
    decision = json.loads((ROOT / 'OWNER_CONFIRMATIONS.json').read_text())
    meetings = snapshot.setdefault('meetings', {})
    confirmations = decision['heldCalls']
    by_deal = {r['dealId']: r for r in confirmations}
    by_chain = {r['bookingChainId']: r for r in confirmations}

    def update(row, proof):
        row.update(heldVerified=True, heldStatus='Owner-confirmed held',
                   heldAt=proof['heldAt'], heldConfirmedOn=decision['confirmedOn'],
                   heldEvidenceSource=decision['source'],
                   heldDateBasis=proof['occurrenceDateBasis'])

    for row in meetings.get('verifiedLinks', []):
        if proof := by_deal.get(row['dealId']):
            update(row, proof)
            row['note'] = 'Platform booking and identity corroborated. Owner separately confirms the call was held; qualification remains the prior owner disposition. Exact attendance duration is unknown.'
    for row in meetings.get('events', []):
        if row.get('isCurrentBooking') and (proof := by_chain.get(row.get('bookingChainId'))):
            update(row, proof)
    for row in snapshot.get('ads', {}).get('leads', []):
        proof = next((p for p in confirmations if p['company'].lower() == row['company'].lower()), None)
        if proof:
            row['meetingHeld'] = True
            update(row, proof)
            calendar_link = next((p for p in meetings.get('verifiedLinks', []) if p['dealId']==proof['dealId']), None)
            if calendar_link:
                row['meetingBooked'] = True
                row['bookingCorroboration'] = dict(calendar_link, source='Calendly', verifiedAt=meetings['snapshotAt'])
            if row.get('bookingCorroboration'):
                update(row['bookingCorroboration'], proof)
                row['bookingCorroboration']['note'] = 'Calendly corroborates booking and identity. Attendance was separately confirmed by the owner October 16; exact duration is unavailable.'
    # The bounded recording scan did not provide this evidence. Keep its negative
    # identity match result and add the separate owner confirmation explicitly.
    for row in meetings.get('fireflies', {}).get('leadBookingReviews', []):
        if proof := by_deal.get(row['crmDealId']):
            update(row, proof)
            row['limit'] = 'No exact recording identity match in the earlier bounded scan. Held status is from the separate October 16 owner confirmation, not from Fireflies.'
    meetings['ownerConfirmedHeldCalls'] = [dict(p, confirmedOn=decision['confirmedOn'], evidenceSource=decision['source']) for p in confirmations]
    meetings.setdefault('summary', {}).update(ownerConfirmedLinkedHeldCalls=len(confirmations),
        ownerConfirmedQualifiedLinkedHeldCalls=sum(p['ownerQualification']=='qualified_warm' for p in confirmations))
    meetings['notes'] = [n for n in meetings.get('notes', []) if 'Attendance remains unverified for all' not in n]
    note = 'The owner confirmed NuVee (October 6) and Venus Ai Consulting (October 15) as held on October 16. These two linked calls are a bounded confirmed set, not complete account-wide held-call coverage. NuVee remains the only qualified paid lead; Venus remains unqualified.'
    if note not in meetings['notes']:
        meetings['notes'].append(note)
    return snapshot
