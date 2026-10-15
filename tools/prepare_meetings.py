"""Prepare PII-minimized Calendly lifecycle evidence; never infer attendance."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private'
TZ = ZoneInfo('America/Denver')


def read(name):
    return json.loads((PRIVATE / name).read_text())


def ident(uri):
    return (uri or '').rstrip('/').split('/')[-1] or None


def event_from_invitee(uri):
    return uri.split('/scheduled_events/')[1].split('/')[0] if uri else None


def normalized_name(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower())


def localday(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(TZ).date().isoformat() if value else None


def build():
    manifest = read('calendly_manifest.json')
    raw = read('calendly_events.json')
    additional = read('calendly_events_after30.json')
    invites = read('calendly_invitees.json')
    assert not raw['pagination'].get('next_page_token'), 'Finish event pagination'
    assert not additional['pagination'].get('next_page_token'), 'Finish future pagination'
    # An additional future booking would require corresponding invitee collection.
    assert not additional['collection'], 'Collect invitees for additional future events before preparing'
    assert all(not i.get('error') and not i['data']['pagination'].get('next_page_token') for i in invites)
    by_id = {ident(e['uri']): e for e in raw['collection']}
    invitees = {i['eventId']: i['data']['collection'] for i in invites}
    assert set(by_id) == set(invitees)

    crm = read('pipedrive_deals.json')
    email_to_deals = defaultdict(set)
    crm_names = {}
    for d in crm:
        crm_names[d['id']] = normalized_name(d.get('person_name'))
        person = d.get('person_id') or {}
        if isinstance(person, dict):
            for item in person.get('email') or []:
                email = item.get('value') if isinstance(item, dict) else item
                if email:
                    email_to_deals[email.strip().lower()].add(d['id'])

    old_event = {}
    new_event = {}
    for eid, rows in invitees.items():
        olds = {event_from_invitee(r.get('old_invitee')) for r in rows if r.get('old_invitee')}
        news = {event_from_invitee(r.get('new_invitee')) for r in rows if r.get('new_invitee')}
        assert len(olds) <= 1 and len(news) <= 1, 'Review complex multi-invitee reschedule lifecycle'
        old_event[eid] = next(iter(olds), None)
        new_event[eid] = next(iter(news), None)

    def root_id(eid):
        seen = set()
        while old_event.get(eid):
            assert eid not in seen, 'Cycle in reschedule chain'
            seen.add(eid)
            eid = old_event[eid]
        return eid

    lead_path = PRIVATE / 'channels/ads_lead_dispositions.csv'
    with lead_path.open(newline='', encoding='utf-8-sig') as f:
        leads = {normalized_name(r['name']): r for r in csv.DictReader(f)}

    events = []
    verified_links = []
    private_joins = []
    for eid, e in by_id.items():
        rows = invitees[eid]
        root = root_id(eid)
        root_source = by_id.get(root)
        classification = 'excluded_interview_type' if 'interview' in e['name'].lower() else 'unclassified'
        matches = set()
        for r in rows:
            candidate = email_to_deals.get((r.get('email') or '').strip().lower(), set())
            exact = {did for did in candidate if normalized_name(r.get('name')) == crm_names.get(did)}
            matches.update(exact)
            if exact:
                private_joins.append({'eventId': eid, 'dealIds': sorted(exact),
                                      'inviteeMatch': 'exact_name_and_email',
                                      'inviteeSourceId': ident(r['uri'])})
            lead = leads.get(normalized_name(r.get('name')))
            if lead and exact:
                for did in sorted(exact):
                    verified_links.append({'dealId': did, 'eventId': eid,
                        'inviteeMatch': 'exact_name_and_email', 'company': lead['company'],
                        'bookingCreatedAt': e['created_at'], 'scheduledStartAt': e['start_time'],
                        'heldVerified': False, 'heldStatus': 'unverified',
                        'ownerQualification': 'qualified' if lead['disposition'] == 'qualified_warm' else lead['disposition'],
                        'ownerQualificationAsOf': lead['disposition_as_of'],
                        'note': 'Platform booking and identity corroborated; qualification remains the owner disposition, and attendance is unverified.'})
        source_hints = {r.get('tracking', {}).get('utm_source') for r in rows
                        if r.get('tracking', {}).get('utm_source')}
        item = {'id': eid, 'name': e['name'], 'status': e['status'],
                'createdAt': e['created_at'], 'startAt': e['start_time'], 'endAt': e['end_time'],
                'canceledAt': (e.get('cancellation') or {}).get('created_at'),
                'rescheduled': any(bool(r.get('rescheduled')) for r in rows),
                'rescheduledFromEventId': old_event[eid], 'rescheduledToEventId': new_event[eid],
                'bookingChainId': root,
                'bookingCreatedAt': root_source['created_at'] if root_source else None,
                'bookingChainComplete': bool(root_source),
                'isCurrentBooking': e['status'] == 'active' and not new_event[eid],
                'isRescheduleReplacement': bool(old_event[eid]),
                'source': 'Calendly', 'inviteeCount': len(rows),
                'activeInviteeCount': sum(r['status'] == 'active' for r in rows),
                'commercialClassification': classification,
                'heldVerified': False, 'heldStatus': 'unverified',
                'noShowRecorded': any(bool(r.get('no_show')) for r in rows),
                'matchedCrmDealIds': sorted(matches),
                'identityMatchBasis': 'exact_name_and_email' if matches else None,
                'hasCampaignTracking': bool(source_hints),
                'trackingSourceHints': sorted(source_hints),
                'trackingNote': 'Platform invitee UTM hints are supporting context, not proof of campaign causation or commercial fit.'}
        events.append(item)

    chains = {}
    for e in events:
        if e['bookingChainId'] not in chains or e['isCurrentBooking']:
            chains[e['bookingChainId']] = e
    generic = [e for e in chains.values() if e['commercialClassification'] == 'unclassified']
    today = manifest['today']
    complete_end = datetime.fromisoformat(manifest['completeEndExclusive'].replace('Z', '+00:00'))
    last30_start = (complete_end.astimezone(TZ).date()).toordinal() - 30
    in_last30 = lambda value: value and last30_start <= datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(TZ).date().toordinal() < complete_end.astimezone(TZ).date().toordinal()
    summary = {
        'rawScheduledEvents': len(events), 'statusCounts': dict(Counter(e['status'] for e in events)),
        'uniqueBookingChains': len(chains),
        'generic30MinuteBookingChains': len(generic),
        'excludedInterviewBookingChains': sum(e['commercialClassification'] == 'excluded_interview_type' for e in chains.values()),
        'rescheduleReplacementEvents': sum(e['isRescheduleReplacement'] for e in events),
        'upcomingGeneric30MinuteBookings': sum(e['isCurrentBooking'] and localday(e['startAt']) >= today for e in generic),
        'last30CompleteDaysGenericBookingCreations': sum(in_last30(e['bookingCreatedAt']) for e in generic),
        'verifiedCommercialCalls': None, 'verifiedHeldCalls': None,
    }
    source_names = ['calendly_manifest.json', 'calendly_events.json', 'calendly_events_after30.json',
                    'calendly_invitees.json', 'calendly_event_types.json', 'pipedrive_deals.json']
    out = {'snapshotAt': manifest['snapshotAt'], 'timezone': 'America/Denver',
        'coverage': {'start': localday(manifest['min']), 'end': localday(manifest['max']),
                     'endExclusive': True, 'complete': True, 'statuses': ['active', 'canceled'],
                     'scope': 'Authenticated user events by start time: last 90 complete Mountain days, current day, next 30 days; additional unbounded-future query returned no events.',
                     'eventStartMinInclusive': manifest['min'], 'eventStartMaxExclusive': manifest['max'],
                     'completeDaysThrough': str(datetime.fromordinal(complete_end.astimezone(TZ).date().toordinal()-1).date()),
                     'currentDayPartial': today, 'futureBeyond30DaysCount': len(additional['collection']),
                     'inviteePagesComplete': True,
                     'createdDateCoverageNote': 'Booking creation metrics describe retrieved event-start coverage, not a separate account-wide created-at API query. Rescheduled replacements retain original booking-chain creation time.'},
        'account': {'name': manifest['account']['name'], 'verifiedScope': 'Authenticated Charles Solomon Calendly account',
                    'sourceTimezone': manifest['account']['timezone']},
        'events': sorted(events, key=lambda e: e['startAt']), 'summary': summary,
        'verifiedLinks': verified_links,
        'provenance': [{'path': 'data/private/' + name, 'sha256': hashlib.sha256((PRIVATE/name).read_bytes()).hexdigest()}
                       for name in source_names] + [{'path': 'data/private/channels/ads_lead_dispositions.csv', 'sha256': hashlib.sha256(lead_path.read_bytes()).hexdigest()}],
        'notes': [
            'A Calendly booking verifies platform scheduling only. Generic 30-minute types are unclassified; they may include partners, recruiting or other non-sales conversations.',
            'Interview event types are kept for source reconciliation and excluded from business-call indicators until purpose is reviewed.',
            'Two lifecycle concepts remain separate: bookingCreatedAt is the original reschedule-chain creation date; startAt is the scheduled occurrence date.',
            'Canceled original events and replacement events are linked by bookingChainId. Count unique chains for booking creation, and only isCurrentBooking records for upcoming active bookings.',
            'An active event in the past is not attendance evidence. No-show absence, elapsed end time and CRM marked-done activity do not independently verify that a call was held.',
            'Exact name and email matches corroborate identity only. They do not establish channel attribution, qualified status, opportunity acceptance or revenue.',
            'Prepared records omit invitee names, email/phone, meeting notes, answers, locations and join/cancel/reschedule URLs; raw evidence remains local and excluded from Git.',
        ]}
    (ROOT / 'data/meetings.json').write_text(json.dumps(out, indent=2) + '\n')
    (PRIVATE / 'calendly_crm_join_manifest.json').write_text(json.dumps({'snapshotAt': manifest['snapshotAt'], 'method': 'exact normalized name and email', 'matches': private_joins}, indent=2) + '\n')
    assert len(events) == len({e['id'] for e in events})
    assert all(e['bookingChainComplete'] for e in events)
    print(json.dumps({'summary': summary, 'verifiedLeadLinkCount': len(verified_links),
                      'identityMatchedEventCount': sum(bool(e['matchedCrmDealIds']) for e in events)}, indent=2))


if __name__ == '__main__':
    build()
