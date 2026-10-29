"""Prepare bounded read-only Calendly/Fireflies and dated owner-effort patches.

Raw responses and outputs stay private. No shared file or source service is
written. Public integration uses independently dated source families.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import re
from apply_effort_estimate import apply_effort_estimate

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_28/meetings'
PRIOR = ROOT / 'data/private/refresh_2026_10_23/meetings'
TZ = ZoneInfo('America/Denver')
SUBJECT = 'christian@redyset.io'
REPORTING_DATE = '2026-10-29'
OWNER_INCREMENT_ID = 'owner-nonmeeting-oct23-through-oct28-2026'


def read(path):
    data = json.loads(path.read_text())
    if isinstance(data, dict) and 'result' in data:
        data = data['result']
    if isinstance(data, dict) and isinstance(data.get('content'), list):
        data = json.loads('\n'.join(x['text'] for x in data['content'] if x['type'] == 'text'))
    return data


def dump(name, data):
    (PRIVATE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def stamp(path):
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace('+00:00', 'Z')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def local_day(value):
    return dt(value).astimezone(TZ).date()


def iso_ms(value):
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat().replace('+00:00', 'Z')


def norm(value):
    return re.sub(r'[^a-z0-9]', '', str(value or '').lower())


def ident(value):
    return value.rstrip('/').split('/')[-1] if value else None


def owner_decision(previous):
    """Return a total-based decision; repeating the same confirmation adds once."""
    decision = deepcopy(previous)
    increments = [row for row in decision.get('increments', []) if row.get('id') != OWNER_INCREMENT_ID]
    matching = [row for row in increments if row.get('periodStart') == '2026-10-23' and row.get('coversThrough') == '2026-10-28']
    assert not matching, 'The same dated owner period already has another confirmation; reconcile before adding.'
    increments.append({'id': OWNER_INCREMENT_ID, 'periodStart': '2026-10-23',
        'coversThrough': '2026-10-28', 'hours': 3.5, 'confirmedOn': '2026-10-28',
        'basis': 'Christian directly confirmed 3.5 additional non-meeting hours for October 23–28 in this dashboard task. The repeated answer under an unrelated question is the same confirmation, counted once; it establishes no commercial outcome.'})
    added = sum(row['hours'] for row in increments)
    decision.update(hoursLow=decision['baseline']['hoursLow'] + added,
        hoursHigh=decision['baseline']['hoursHigh'] + added, confirmedOn='2026-10-28',
        coversThrough='2026-10-28', increments=increments,
        basis='Christian confirmed the original 14.5–15.75-hour October 1–16 baseline, 3.75 additional non-meeting hours for October 17–22, and 3.5 additional hours for October 23–28. The overall owner estimate is 21.75–23.0 hours through October 28. Each dated increment is counted once. This is not independently measured time and no workstream allocation was supplied.')
    assert (decision['hoursLow'], decision['hoursHigh']) == (21.75, 23.0)
    return decision


def apply_owner_preview(effort, decision):
    """Pure preview of the canonical total decision and one stable evidence row."""
    value = deepcopy(effort)
    apply_effort_estimate(value, decision=decision)
    dashboard = next(row for row in value['workstreams'] if row['id'] == 'dashboard')
    evidence = {'id': OWNER_INCREMENT_ID, 'date': '2026-10-28',
        'label': 'Christian confirmed one additional 3.5-hour non-meeting increment covering October 23–28 while directing the live dashboard refresh. It is included once in the overall Centripetal estimate; no hours are allocated to this workstream.'}
    dashboard['evidence'] = [row for row in dashboard.get('evidence', []) if row.get('id') != OWNER_INCREMENT_ID] + [evidence]
    dashboard['evidenceDates'] = sorted(set(dashboard.get('evidenceDates', [])) | {'2026-10-28'})
    assert value['meetings'] == effort['meetings']
    assert value['trackedHumanMinutes'] is None and value['summary']['combinedWorkedHours'] is None
    return value, evidence


CLASSES = {
    '01M5DYZ4JE84D6G6GD4CRZVE59': ('Investor/referral relationship — Updata', 'investor_referral_relationship', 'Charles and the external investor discuss sharing relevant company referrals, introductions and possible educational collaboration. This is relationship development, not a buyer engagement or completed referral introduction.'),
    '01M5WA9CGDKN2VFESB276QGY6H': ('Existing-client investor discussion — OneFlo', 'existing_client_investor_discussion', 'Actual dialogue concerns investor materials and financing support for an existing client. A client fundraising conversation does not establish a new Centripetal client or accepted sales opportunity.'),
    '01M5FY6AR77MGME0GWJH3Q54X8': ('Existing-client investor discussion — Megadata', 'existing_client_investor_discussion', 'Charles discusses an existing client with an investor. This is client/investor relationship work; it is not a prospect buying a Centripetal engagement.'),
    '01M5YY361SXXV1JR2P1SWZBNVJ': ('Internal client-work automation review', 'internal_client_work_review', 'The internal team reviews existing-client reporting and automation priorities. A parallel source recording has the same indexed start and overlapping dialogue; these IDs are not asserted to be distinct meetings.'),
    '01M5QBAQ1S4N3ZN4JFQEE4PE6S': ('Internal client-work automation review', 'internal_client_work_review', 'Internal staff discuss reporting and automation work. A same-start parallel transcript remains an overlap candidate; no additional human time or sales conversation is inferred.'),
    '01M5SYK0GXC6Z4D726KJXV2AAM': ('Fragmentary internal-contact recording', 'insufficient_dialogue_for_business_purpose', 'Only a brief greeting fragment is available. The complete purpose, attendance duration and any commercial meaning are unestablished.'),
    '01M5SYJ9N41SYBCC1MBNCWXGBQ': ('Fragmentary internal finance coordination', 'insufficient_dialogue_for_full_business_purpose', 'A short fragment refers to closed historical accounting records. It does not establish a complete meeting purpose, a prospect conversation or a commercial outcome.'),
    '01M5YQ653R4Z0BD3J38N0FKKA5': ('Internal operations and automation review', 'internal_operations_review', 'Known internal staff review automation governance, operational priorities and go-to-market systems. The parallel same-start transcript is an overlap candidate, not an independently counted additional meeting.'),
    '01M5SYH0ZDZJP2VZSC4ZQ9SSA7': ('Internal operations and automation review', 'internal_operations_review', 'Internal operations and systems planning, with overlapping dialogue in a parallel record. No additional sales or human-hour count is inferred.'),
    '01M5CWDYGANENVXFXJRQ0EB9TY': ('Existing-client finance coordination', 'existing_client_finance_coordination', 'Dialogue concerns existing-client financial reporting and coordination. Private financial and employment details are withheld from the reporting summary.'),
    '01M5W8HXW4Q3TW84Q4WWGVRNX7': ('Existing-client financial preparation', 'existing_client_finance_delivery', 'Actual dialogue concerns existing-client financial and investor-document preparation. It does not establish a new Centripetal buyer or a first-client win.'),
    '01M5W6GE9KCYG0130Z43H1PZZ1': ('Internal Centripetal huddle', 'internal_team_coordination', 'Internal staff coordination and operational planning. Private personnel, client-financial and transaction details are not published. The same-start parallel record is an overlap candidate.'),
    '01M5CWDYFKDJK96XVWF1HM5DXR': ('Internal Centripetal huddle', 'internal_team_coordination', 'Internal team coordination. The parallel record has overlapping dialogue and is not automatically another meeting; private internal details remain excluded.'),
}
PAIRS = [('01M5YY361SXXV1JR2P1SWZBNVJ', '01M5QBAQ1S4N3ZN4JFQEE4PE6S'),
    ('01M5YQ653R4Z0BD3J38N0FKKA5', '01M5SYH0ZDZJP2VZSC4ZQ9SSA7'),
    ('01M5W6GE9KCYG0130Z43H1PZZ1', '01M5CWDYFKDJK96XVWF1HM5DXR')]


def build():
    PRIVATE.mkdir(parents=True, exist_ok=True)
    base_path = PRIVATE / 'baseline_shared.json'
    if not base_path.exists():
        base_path.write_bytes((ROOT / 'data/shared-dashboard.json').read_bytes())
    base = read(base_path)
    pages = [PRIVATE / f'fireflies_page_{skip:03}.json' for skip in (0, 50, 100)]
    metadata = [row for path in pages for row in read(path)['transcripts']]
    assert len(metadata) == len({row['id'] for row in metadata}) == 150
    assert all(metadata[i]['date'] >= metadata[i+1]['date'] for i in range(len(metadata)-1))
    metadata_at = max(map(stamp, pages))
    month_start = datetime(2026, 10, 1, tzinfo=TZ).timestamp() * 1000
    october = [row for row in metadata if month_start <= row['date'] <= dt(metadata_at).timestamp() * 1000]
    assert len(october) == 97 and min(row['date'] for row in metadata) < month_start
    old_metadata = [row for skip in (0, 50) for row in read(PRIOR / f'fireflies_page_{skip:03}.json')['transcripts']]
    old_october = {row['id']: row for row in old_metadata if row['date'] >= month_start}
    assert len(old_october) == 84 and set(old_october) <= {row['id'] for row in october}
    new = {row['id'] for row in october} - set(old_october)
    assert new == set(CLASSES), 'The manually reviewed batch differs from the metadata delta.'
    fields = ['id', 'title', 'date', 'duration', 'organizer_email', 'participants', 'transcript_url']
    changed = [row['id'] for row in october if row['id'] in old_october and any(row.get(k) != old_october[row['id']].get(k) for k in fields)]
    transcripts = {rid: (read(PRIVATE / f'fireflies_{rid}.json').get('transcript') or {}) for rid in new}
    assert all(transcripts[rid].get('id') == rid and transcripts[rid].get('sentences') for rid in new)
    body_at = max(stamp(PRIVATE / f'fireflies_{rid}.json') for rid in new)
    reviewed_at = max(metadata_at, body_at)
    pair_by_id = {rid: [other for other in pair if other != rid] for pair in PAIRS for rid in pair}
    records = []
    for row in october:
        rid = row['id']
        if rid not in new:
            continue
        title, classification, basis = CLASSES[rid]
        transcript = transcripts[rid]
        speaker_names = {s.get('speaker_name') for s in transcript['sentences']}
        assert 'Christian Wutz' not in speaker_names
        insufficient = classification.startswith('insufficient_')
        records.append({'id': rid, 'title': title, 'indexedAt': iso_ms(row['date']), 'occurredAt': None,
            'dateBasis': 'Fireflies transcript index metadata; an independently verified occurrence timestamp is unavailable.',
            'durationMinutes': round(float(row['duration']), 5), 'classification': classification,
            'classificationBasis': basis, 'reviewedDialogue': True,
            'purposeReviewStatus': 'dialogue_reviewed_insufficient_for_business_purpose' if insufficient else 'dialogue_reviewed_purpose_classified',
            'sentenceCount': len(transcript['sentences']), 'speakerCount': len(speaker_names),
            'charlesSpeakerConfirmed': 'Charles Solomon' in speaker_names,
            'christianSpeakerLabelObserved': False, 'charlesListedInParticipants': 'charles@centripetaladvisors.com' in row.get('participants', []),
            'evidenceCollectedAt': stamp(PRIVATE / f'fireflies_{rid}.json'),
            'sourceEvidenceSha256': sha(PRIVATE / f'fireflies_{rid}.json'),
            'commercialOutcomeDecisionApplied': False, 'qualificationDecisionApplied': False,
            'ownerReviewRequired': False, 'audioDurationIsAttendance': False, 'crmDealIds': [],
            'duplicateCandidateIds': pair_by_id.get(rid, []),
            'identityReviewNote': 'Exact professional email/name/organization searches returned no accessible CRM match; these are bounded searches, not proof of global absence.' if rid == '01M5DYZ4JE84D6G6GD4CRZVE59' else None})
    retry_register = read(ROOT / 'data/private/completion_audit_2026_10_22/commercial/october_76_triage_register.json')
    retries = []
    for row in retry_register['records']:
        if row['reviewStatus'] == 'dialogue_reviewed_purpose_classified':
            continue
        rid = row['recordingId']
        current = read(PRIVATE / f'fireflies_{rid}.json').get('transcript') or {}
        prior = read(PRIOR / f'fireflies_{rid}.json').get('transcript') or {}
        identical = current.get('sentences') == prior.get('sentences') and current.get('summary') == prior.get('summary')
        assert identical
        retries.append({'id': rid, 'priorSentenceCount': len(prior.get('sentences') or []),
            'currentSentenceCount': len(current.get('sentences') or []),
            'dialogueAndSummaryIdenticalToPriorResponse': True,
            'currentDisposition': 'Still empty or fragmentary; no newly sufficient business-purpose or outcome evidence.',
            'evidenceCollectedAt': stamp(PRIVATE / f'fireflies_{rid}.json')})
    assert len(retries) == 11
    reviewed_at = max(reviewed_at, *(row['evidenceCollectedAt'] for row in retries))

    meetings = deepcopy(base['meetings'])
    raw_events = []
    event_files = [PRIVATE / f'calendly_{status}_retained_000.json' for status in ('active', 'canceled')]
    for path in event_files:
        result = read(path)
        assert not result['pagination'].get('next_page_token')
        raw_events.extend(result['collection'])
    invitee_rows = read(PRIVATE / 'calendly_invitees.json')
    assert len(raw_events) == len(invitee_rows) == 29
    invitees = {row['eventId']: row['data']['collection'] for row in invitee_rows}
    assert all(not row['data']['pagination'].get('next_page_token') for row in invitee_rows)
    calendar_at = max(*(stamp(path) for path in event_files), *(row['collectedAt'] for row in invitee_rows))
    crm_records = [row for path in sorted((PRIVATE.parent / 'crm').glob('deals_[0-9]*.json')) for row in read(path)['data']]
    assert len(crm_records) == len({row['id'] for row in crm_records}) == 780
    crm_at = read(PRIVATE.parent / 'crm/collection_manifest.json')['collectionCompletedAt']
    by_email = defaultdict(set)
    names = {}
    for deal in crm_records:
        person = deal.get('person_id') or {}
        names[deal['id']] = norm(deal.get('person_name') or (person.get('name') if isinstance(person, dict) else ''))
        if isinstance(person, dict):
            for email in person.get('email') or []:
                value = email.get('value') if isinstance(email, dict) else email
                if value:
                    by_email[value.strip().lower()].add(deal['id'])
    prior_events = {row['id']: row for row in meetings['events']}
    current_events = []
    identity_links = []
    christian_calendar = []
    for event in raw_events:
        rid = ident(event['uri'])
        assert rid in prior_events, 'New calendar event needs explicit normalization and chain review.'
        current = deepcopy(prior_events[rid])
        rows = invitees[rid]
        matches = set()
        for row in rows:
            matched = {did for did in by_email.get((row.get('email') or '').strip().lower(), set()) if names[did] == norm(row.get('name'))}
            matches |= matched
            if matched:
                identity_links.append({'eventId': rid, 'dealIds': sorted(matched),
                    'basis': 'Exact normalized invitee name and email against freshly collected CRM deal/person fields',
                    'crmSourceCollectedAt': crm_at, 'inviteesCollectedAt': next(r['collectedAt'] for r in invitee_rows if r['eventId'] == rid)})
            if (row.get('email') or '').strip().lower() == SUBJECT:
                christian_calendar.append(rid)
        if any((row.get('email') or '').strip().lower() == SUBJECT for row in event.get('event_guests') or []):
            christian_calendar.append(rid)
        current.update(status=event['status'], createdAt=event['created_at'], updatedAt=event['updated_at'],
            startAt=event['start_time'], endAt=event['end_time'], canceledAt=(event.get('cancellation') or {}).get('created_at'),
            inviteeCount=len(rows), activeInviteeCount=sum(row['status'] == 'active' for row in rows),
            noShowRecorded=any(bool(row.get('no_show')) for row in rows), matchedCrmDealIds=sorted(matches),
            identityMatchBasis='exact_name_and_email' if matches else None)
        for field, source_key in [('rescheduledFromEventId', 'old_invitee'), ('rescheduledToEventId', 'new_invitee')]:
            refs = {value.split('/scheduled_events/')[1].split('/')[0] for row in rows if (value := row.get(source_key))}
            assert len(refs) <= 1
            current[field] = next(iter(refs), None)
        current['rescheduled'] = any(bool(row.get('rescheduled')) for row in rows)
        current['isCurrentBooking'] = event['status'] == 'active' and not current['rescheduledToEventId']
        current_events.append(current)
    assert not christian_calendar
    meetings.update(snapshotAt=calendar_at, events=sorted(current_events, key=lambda row: row['startAt']), identityLinks=identity_links)
    meetings['coverage'].update(completeDaysThrough='2026-10-28', currentDayPartial=REPORTING_DATE,
        observedThrough=REPORTING_DATE, currentDayPartialDate=REPORTING_DATE,
        eventsCollectedAt=max(map(stamp, event_files)), inviteesCollectionCompletedAt=max(row['collectedAt'] for row in invitee_rows),
        atomicSnapshot=False)
    chains = {}
    for row in current_events:
        key = row['bookingChainId']
        if key not in chains or row['isCurrentBooking']:
            chains[key] = row
    generic = [row for row in chains.values() if row['commercialClassification'] == 'unclassified']
    report_date = datetime.fromisoformat(REPORTING_DATE).date()
    meetings['summary'].update(rawScheduledEvents=len(current_events), statusCounts=dict(Counter(row['status'] for row in current_events)),
        uniqueBookingChains=len(chains), generic30MinuteBookingChains=len(generic),
        excludedInterviewBookingChains=sum(row['commercialClassification'] == 'excluded_interview_type' for row in chains.values()),
        rescheduleReplacementEvents=sum(row['isRescheduleReplacement'] for row in current_events),
        upcomingGeneric30MinuteBookings=sum(row['isCurrentBooking'] and row['startAt'] > calendar_at for row in generic),
        last30CompleteDaysGenericBookingCreations=sum(bool(row.get('bookingCreatedAt')) and report_date-timedelta(days=30) <= local_day(row['bookingCreatedAt']) < report_date for row in generic))
    lifecycle_keys = ['status', 'startAt', 'endAt', 'canceledAt', 'rescheduledFromEventId', 'rescheduledToEventId']
    meetings['snapshotComparison'] = {'baselineSnapshotAt': base['meetings']['snapshotAt'],
        'newScheduledEventIds': [], 'noLongerReturnedEventIds': [],
        'changedLifecycleEventIds': [row['id'] for row in current_events if any(row.get(k) != prior_events[row['id']].get(k) for k in lifecycle_keys)],
        'basis': 'Same retained July 16–November 13 scheduled-start scope; full active/canceled event and invitee pagination. Scheduling is not attendance.'}
    assert not meetings['snapshotComparison']['changedLifecycleEventIds']
    meetings['notes'].append('Latest lifecycle and all-invitee reread retains the same 29 events and 26 booking chains. Fresh CRM name/email identity joins are supporting links, not qualification or attendance decisions.')
    meetings['notes'] = list(dict.fromkeys(meetings['notes']))

    ff = deepcopy(base['meetings']['fireflies'])
    old_increment = deepcopy(ff['incrementalPurposeReview'])
    prior_incremental_records = {row['id']: row for row in old_increment.get('records', [])}
    combined = [*prior_incremental_records.values(), *records]
    assert len(combined) == len({row['id'] for row in combined}) == 21
    ff['snapshotAt'] = metadata_at
    week_start = report_date-timedelta(days=report_date.weekday())
    current_week = [row for row in october if week_start <= local_day(iso_ms(row['date'])) <= report_date]
    ff['coverage'].update(recordsScanned=len(metadata), sourcePages=[{'skip': skip, 'limit': 50, 'returned': 50,
        'collectedAt': stamp(path)} for skip, path in zip((0,50,100), pages)], oldestIndexedAt=iso_ms(min(row['date'] for row in metadata)),
        newestIndexedAt=iso_ms(max(row['date'] for row in metadata)), octoberIndexedRecords=len(october),
        currentWeekIndexedRecords=len(current_week), completeForIndexedOctoberWithinAccessibleList=True,
        completeForActualHeldMeetings=False, atomicSnapshot=False, knownOctoberMetadataChangedIds=changed,
        bodyVersionAvailable=False)
    ff['summary'].update(metadataRecordsScanned=len(metadata), octoberIndexedRecords=len(october), currentWeekIndexedRecords=len(current_week))
    prior_batches = old_increment.pop('retainedPriorReviews', [])
    ff['incrementalPurposeReview'] = {'snapshotAt': reviewed_at, 'reviewedAt': reviewed_at,
        'metadataInventorySnapshotAt': metadata_at, 'baselineRetainedOctoberRecords': 84,
        'newOctoberRecords': len(new), 'newRecordingIds': sorted(new), 'newRecordingsReviewed': len(records),
        'newPurposeClassifiedRecords': sum(row['purposeReviewStatus'] == 'dialogue_reviewed_purpose_classified' for row in records),
        'newInsufficientDialogueRecords': sum(row['purposeReviewStatus'] != 'dialogue_reviewed_purpose_classified' for row in records),
        'priorIncrementalRecordsRetained': len(prior_incremental_records), 'records': combined,
        'retainedPriorReviews': [*prior_batches, old_increment],
        'priorInsufficientRecordsRetried': len(retries), 'retryDetails': retries,
        'allNewResponsesHaveDialogue': True, 'newManualCommercialReviewCandidates': 0,
        'commercialOutcomeDecisionApplied': False, 'qualificationDecisionApplied': False,
        'bodyOnlyChangesDetectable': False, 'previousDetailedReviewPreserved': True,
        'completeActualHeldCallCoverage': False,
        'notes': ['Thirteen new records were read: eleven sufficiently support investor/referral, existing-client or internal purpose; two are fragmentary. Recording IDs do not equal distinct meetings.',
            'The register also retains eight prior incremental records with their original evidence clocks. Earlier purpose reviews remain independently dated; they were not all reread.',
            'All 84 previous October IDs remain visible with unchanged compared metadata. Eleven previously empty or insufficient responses were reread and remain identical; unchanged metadata does not prove every older body is unchanged.',
            'The newest Updata dialogue is referral-relationship development, not a buyer engagement or completed referral introduction. No commercial outcome decision or prospect-call addition is applied.',
            'Three same-start staff-recording pairs have overlapping dialogue and remain explicit overlap candidates. None contains a newly verified Christian participant/speaker match or contributes additional Christian hours.']}
    ff['currentWeekPurposeReview'] = {'start': str(week_start), 'end': REPORTING_DATE,
        'recordingsReviewed': len(current_week), 'priorWeekRecordsRetainedWithOriginalReviewAge': 0,
        'newWeekRecordsReviewed': len(current_week), 'additionalCharlesProspectCallsEstablished': 0,
        'ownerCommercialReviewCandidates': 0, 'completeActualMeetingCoverage': False,
        'note': 'All thirteen available October 26–28 indexed records were read; eleven support purpose classification and two are fragmentary. Investor/referral, existing-client and internal work remain separate from eligible prospect conversations. Three overlapping source pairs are not asserted to be unique meetings. October 29 is partial.'}
    ff['notes'].append('Latest metadata collection scans 150 records across October 1 and retains 97 October-indexed IDs. Thirteen new bodies and eleven prior insufficient responses were reviewed. Older body evidence keeps its original collection age; no new owner commercial decisions are applied.')
    ff['notes'] = list(dict.fromkeys(ff['notes']))
    meetings['fireflies'] = ff
    future = {status: read(PRIVATE / f'calendly_future_{status}.json') for status in ('active', 'canceled')}
    assert all(not row['collection'] and not row['pagination'].get('next_page_token') for row in future.values())
    meetings['metadataFreshnessCheck'] = {'snapshotAt': max(reviewed_at, calendar_at), 'reviewedAt': max(reviewed_at, calendar_at),
        'fireflies': {'latestAccessibleIds': 150, 'octoberIndexedIds': 97, 'newIds': 13,
            'changedMetadataIds': len(changed), 'bodyVersionAvailable': False,
            'scope': 'Three metadata pages cross October 1; thirteen new bodies and eleven prior insufficient responses were read. Older bodies retain their review age.'},
        'calendly': {'activeEvents': 26, 'canceledEvents': 3,
            'scope': {'minStartTime': '2026-07-16T06:00:00Z', 'maxStartTime': '2026-11-13T07:00:00Z'},
            'eventsAndInviteesPagesComplete': True, 'reviewedEvents': 29, 'ChristianExactSubjectMatches': 0,
            'additionalUnboundedFutureCheck': {'activeEvents': 0, 'canceledEvents': 0,
                'snapshotAt': max(stamp(PRIVATE / f'calendly_future_{status}.json') for status in future), 'complete': True}},
        'note': 'Source metadata, dialogue and scheduling provide bounded supporting evidence. Commercial decisions remain for Charles; no actual attendance or complete prospect-call roster is inferred.'}

    tm = deepcopy(base['time']['meetings'])
    prior_subject = {row['id'].split(':')[-1] for row in tm['events']}
    current_subject = [row for row in october if SUBJECT in {value.lower().strip() for value in row.get('participants') or []}
        and row.get('organizer_email', '').lower().endswith('@centripetaladvisors.com')]
    assert {row['id'] for row in current_subject} == prior_subject
    prior_events_time = {row['id'].split(':')[-1]: row for row in tm['events']}
    assert all(abs(float(row['duration'])-prior_events_time[row['id']]['durationMinutes']) < .0001 for row in current_subject)
    tm['snapshotAt'] = reviewed_at
    tm['period'].update(through=metadata_at, currentDayPartial=True)
    tm['sourceAsOf'].update(fireflies=metadata_at, calendly=calendar_at)
    tm['coverage'].update(firefliesMetadataPages={'pages': 3, 'pageSize': 50, 'skip': [0,50,100],
        'oldestIndexedAt': iso_ms(min(row['date'] for row in metadata)), 'crossedMonthStart': True},
        firefliesMetadataRecordsReviewed=150, firefliesMonthIndexedRecords=97,
        firefliesIndexedMonthCompleteWithinAccessibleList=True, calendlyReviewedEvents=29,
        calendlyExactSubjectMatches=0, latestNewRecordingBodiesReviewed=13,
        newExactChristianAssociatedRecordings=0, newChristianSpeakerLabelMatches=0)
    tm['notes'] = [note for note in tm.get('notes', []) if not note.startswith('No non-meeting estimate increase is inferred.')]
    tm['notes'].append('Latest source read retains the same seven exact-Christian associated recording records and prior duplicate exclusions: six counted durations and 324.77 associated audio minutes. None of the thirteen new recording dialogues adds an exact Christian participant or full-name speaker match.')
    tm['notes'].append('The separately maintained owner non-meeting estimate is not recomputed from audio. New human-hour increments require direct owner confirmation; recording metadata and unattended agent activity add no human hours.')
    tm['notes'] = list(dict.fromkeys(tm['notes']))
    assert tm['events'] == base['time']['meetings']['events'] and tm['summary'] == base['time']['meetings']['summary']
    assert meetings['ownerConfirmedHeldCalls'] == base['meetings']['ownerConfirmedHeldCalls']

    decision = owner_decision(read(ROOT / 'EFFORT_ESTIMATE.json'))
    owner_preview, evidence = apply_owner_preview(base['time'], decision)
    assert owner_decision(decision) == decision
    assert apply_owner_preview(owner_preview, decision)[0] == owner_preview
    dump('owner_effort_decision_patch.json', decision)
    dump('owner_effort_evidence_patch.json', {'confirmationId': OWNER_INCREMENT_ID,
        'ownerConfirmedOn': '2026-10-28', 'periodStart': '2026-10-23', 'coversThrough': '2026-10-28',
        'incrementHours': 3.5, 'totalRangeHours': {'low': 21.75, 'high': 23.0},
        'duplicateAnswerCountedTwice': False, 'commercialDecisionApplied': False,
        'workstream': 'dashboard', 'evidence': evidence,
        'integrationOrder': 'Write the reviewed canonical EFFORT_ESTIMATE decision before curation. Apply the stable evidence row once by confirmationId, and keep the separately prepared timeMeetings proxy independent.'})
    dump('time_owner_preview.json', owner_preview)
    dump('calendly_refresh_patch.json', meetings)
    dump('fireflies_refresh_patch.json', ff)
    dump('time_meetings_patch.json', tm)
    cards = []
    for key in ('meetings', 'fireflies', 'time'):
        card = deepcopy(next(row for row in base['sources'] if row['id'] == key))
        card['checkedAt'] = REPORTING_DATE
        if key == 'meetings':
            card.update(asOf=calendar_at, coverage=deepcopy(meetings['coverage']),
                status='Fresh complete retained scheduling scope; lifecycle state unchanged',
                method='Read-only authenticated Charles Calendly event/invitee pages plus fresh exact CRM name/email matching',
                note='29 source events /26 booking chains remain unchanged. Two October 29 bookings are scheduled; acceptance and CRM stages do not establish attendance. Source event and invitee collection clocks remain explicit.')
        elif key == 'fireflies':
            card.update(asOf=metadata_at, coverage=deepcopy(ff['coverage']),
                status='Current paginated metadata with thirteen new dialogue reviews',
                note='150 metadata records /97 October IDs. Thirteen new dialogues and eleven earlier insufficient responses were reviewed; older evidence keeps its original age. Investor/referral and existing-client discussions do not add eligible prospect-call or win decisions.')
        else:
            card.update(asOf=reviewed_at, coverage={'start': '2026-10-01', 'end': REPORTING_DATE,
                'currentDayPartial': True, 'ownerNonMeetingEstimateCoversThrough': '2026-10-28'},
                status='Current recording evidence and dated owner non-meeting estimate',
                note='Associated audio proxy remains 324.77 minutes. The owner separately supplied 3.5 additional non-meeting hours for October 23–28, counted once, bringing the overall estimate to 21.75–23.0 hours through October 28. October 29 is unmeasured; audio duration is not attendance or human work.')
        cards.append(card)
    cards.append({'id': 'fireflies_incremental_review', 'name': 'Fireflies · latest incremental dialogue review',
        'asOf': reviewed_at, 'checkedAt': REPORTING_DATE,
        'status': 'Thirteen new dialogues reviewed; earlier evidence retained separately',
        'coverage': 'Thirteen new October26–28 indexed records and eleven prior empty/fragmentary responses; eight prior incremental records and the earlier76-ID review retain their original evidence clocks.',
        'method': 'Read-only transcript requests; actual speaker/dialogue purpose classification; no commercial decision inference',
        'note': 'Eleven new records support investor/referral, existing-client or internal classification; two are fragmentary. Same-start parallel recordings are not automatically distinct meetings. No new exact Christian-associated recording or commercial headline is added.'})
    dump('source_cards_patch.json', cards)
    manifest = {'reportingAsOfMountain': REPORTING_DATE, 'completeDaysThroughMountain': '2026-10-28',
        'reviewedAt': max(reviewed_at, calendar_at), 'readOnly': True, 'sourceWrites': 0,
        'commercialDecisionsApplied': 0, 'ownerNonMeetingIncrementHours': 3.5,
        'calendly': {'snapshotAt': calendar_at, 'events': 29, 'active': 26, 'canceled': 3,
            'inviteeEvents': 29, 'completePagination': True, 'ChristianExactSubjectMatches': 0,
            'lifecycleDelta': meetings['snapshotComparison']},
        'fireflies': {'metadataSnapshotAt': metadata_at, 'recordsScanned': 150, 'octoberIndexedRecords': 97,
            'priorOctoberRecords': 84, 'newOctoberIds': sorted(new), 'changedPreviousMetadataIds': changed,
            'newBodiesRead': 13, 'newPurposeClassified': 11, 'newInsufficient': 2, 'priorInsufficientRetried': 11,
            'priorInsufficientResponsesIdentical': True, 'completeIndexedMonthWithinAccessibleList': True,
            'completeActualHeldMeetingRoster': False, 'bodyOnlyUpdatesDetectable': False},
        'time': {'recordingProxyMinutes': 324.77, 'newExactChristianRecordingIds': [],
            'actualAttendanceMinutes': None, 'ownerNonMeetingHours': {'low': 21.75, 'high': 23.0},
            'ownerEstimateCoversThrough': '2026-10-28', 'incrementCountedOnce': True},
        'patches': {'meetings': 'data/private/refresh_2026_10_28/meetings/calendly_refresh_patch.json',
            'timeMeetings': 'data/private/refresh_2026_10_28/meetings/time_meetings_patch.json',
            'sourceCards': 'data/private/refresh_2026_10_28/meetings/source_cards_patch.json'},
        'timestampBasis': 'Per-file immediate local retention clocks after connector responses; events, invitees, metadata and actual body reads retain separate dates.',
        'publication': 'Only curated source summaries are prepared. Raw transcripts, invitee answers, private financial/personnel details and recording access links remain private.'}
    dump('manifest.json', manifest)
    print(json.dumps({key: manifest[key] for key in ('calendly', 'fireflies', 'time')}, indent=2))


if __name__ == '__main__':
    build()
