"""Christian-only Centripetal recording-time proxy; not attendance or billing."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/time'
TZ = ZoneInfo('America/Denver')


def read(name):
    return json.loads((PRIVATE / name).read_text())


def dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def build():
    manifest = read('manifest.json')
    subject = manifest['subjectEmail'].strip().lower()
    start, through = dt(manifest['start']), dt(manifest['through'])
    indexed = read('fireflies_metadata.json')
    details = {r['id']: r for r in read('fireflies_christian_metadata.json')['transcripts']}
    duplicate = read('oct9_duplicate_proof.json')
    assert duplicate['confidence'] == 'high'
    gram5 = next(r for r in duplicate['shingleMetrics'] if r['n'] == 5)
    assert gram5['shortContainment'] >= .85 and duplicate['alignment']['speakerAgreement'] == 1
    assert duplicate['alignment']['offsetSecondsP90'] - duplicate['alignment']['offsetSecondsP10'] < 2
    assert len(duplicate['normalizedTranscriptSha256']['short']) == 64
    assert len(duplicate['normalizedTranscriptSha256']['long']) == 64
    all_transcripts = {r['id']: r for r in indexed['transcripts']}
    associated = [r for r in all_transcripts.values()
                  if start.timestamp() * 1000 <= r['date'] <= through.timestamp() * 1000
                  and subject in {str(e).strip().lower() for e in r.get('participants', [])}]
    records = []
    excluded = []
    for r in associated:
        # Require a Centripetal organizer, rather than treating all Christian work as Centripetal.
        if not r.get('organizer_email', '').lower().endswith('@centripetaladvisors.com'):
            excluded.append({'id': r['id'], 'reason': 'Centripetal work scope not verified'})
            continue
        evidence = details.get(r['id'])
        assert evidence and subject in {str(e).strip().lower() for e in evidence.get('participants', [])}
        speaker_match = manifest['subjectName'].lower() in {s.lower() for s in evidence.get('speakerNames', [])}
        indexed_at = datetime.fromtimestamp(r['date']/1000, timezone.utc)
        duration = float(r['duration'])
        assert duration > 0 and manifest['firefliesDurationUnit'] == 'minutes'
        derived_end = indexed_at + timedelta(minutes=duration)
        clipped = max(0, (min(derived_end, through) - max(indexed_at, start)).total_seconds()/60)
        is_duplicate = r['id'] == duplicate['shortId']
        # Titles with participant names are replaced with minimal work labels.
        title = ('Centripetal workflow / GitHub huddle' if 'github' in r['title'].lower()
                 else 'Centripetal CRM coordination' if 'pipedrive' in r['title'].lower()
                 else 'Centripetal GTM')
        records.append({
            'id': 'fireflies:' + r['id'], 'title': title,
            'startAt': iso(indexed_at), 'endAt': iso(derived_end),
            'timeBasis': 'Fireflies transcript-date metadata; end is derived from audio duration, not verified meeting attendance.',
            'durationMinutes': round(duration, 5), 'ChristianMatchBasis': 'Exact subject email in participants' + (' and exact subject speaker label' if speaker_match else ''),
            'classification': 'excluded_duplicate_recording_segment' if is_duplicate else 'Centripetal_recording_associated_with_Christian',
            'countedMinutes': 0 if is_duplicate else round(clipped, 5),
            'sourceIds': {'fireflies': [r['id']], 'calendly': []},
            'evidenceLevel': 'recorded_meeting', 'attendanceMinutes': None,
            'duplicateOfId': 'fireflies:' + duplicate['longId'] if is_duplicate else None,
            'deduplicationBasis': 'High-confidence normalized transcript containment, matching speakers and stable sentence-offset alignment; private proof retained.' if is_duplicate else None,
            'notes': ['Participant association and speaker identity are supported. The full recording duration does not prove the subject attended for its full duration.',
                      'Calendar/recording metadata dates are proxies; actual meeting-start and individual join/leave timestamps are unavailable.'],
        })

    calendar = read('calendly_events.json')
    invitees = {r['eventId']: r['data'] for r in read('calendly_invitees.json')['events']}
    assert not calendar['pagination'].get('next_page_token')
    matching_calendly = []
    calendar_excluded = []
    for e in calendar['collection']:
        eid = e['uri'].rstrip('/').split('/')[-1]
        inv = invitees[eid]
        assert not inv['pagination'].get('next_page_token')
        active_match = [r for r in inv['collection']
                        if (r.get('email') or '').strip().lower() == subject and r['status'] == 'active']
        guest_match = any((g.get('email') or '').strip().lower() == subject for g in e.get('event_guests', []))
        if not active_match and not guest_match:
            calendar_excluded.append({'id': eid, 'reason': 'No exact subject invitee or guest email match'})
            continue
        if e['status'] != 'active' or dt(e['start_time']) > through:
            calendar_excluded.append({'id': eid, 'reason': 'Canceled or future occurrence'})
            continue
        if any(r.get('rescheduled') for r in active_match):
            calendar_excluded.append({'id': eid, 'reason': 'Rescheduled source; use replacement occurrence'})
            continue
        scheduled = max(0, (min(dt(e['end_time']), through)-max(dt(e['start_time']), start)).total_seconds()/60)
        matching_calendly.append({'id': 'calendly:' + eid, 'title': 'Centripetal scheduled meeting',
            'startAt': e['start_time'], 'endAt': e['end_time'], 'durationMinutes': scheduled,
            'ChristianMatchBasis': 'Exact subject invitee/guest email', 'classification': 'calendar_only_scheduled_time',
            'countedMinutes': scheduled, 'sourceIds': {'fireflies': [], 'calendly': [eid]},
            'evidenceLevel': 'calendar_only', 'attendanceMinutes': None,
            'notes': ['Scheduled duration only; not recording or attendance evidence.']})
    # The observed current source has no Christian match. Future nonzero calendar inputs
    # require explicit cross-source identity/time deduplication before combining sources.
    assert not matching_calendly, 'Review and prove cross-source deduplication for matching Calendly events'

    proof_path = PRIVATE / 'oct9_duplicate_proof.json'
    raw_minutes = sum(r['durationMinutes'] for r in records)
    counted = sum(r['countedMinutes'] for r in records)
    summary = {'rawAssociatedRecordingCount': len(records),
        'countedRecordingCount': sum(r['countedMinutes'] > 0 for r in records),
        'rawRecordingMinutes': round(raw_minutes, 2), 'recordedMinutes': round(counted, 2),
        'duplicateRecordingMinutesExcluded': round(raw_minutes-counted, 2),
        'calendarOnlyScheduledMinutes': 0, 'calendarOnlyMatchedEvents': 0,
        'actualChristianAttendanceMinutes': None,
        'recordingBasedMeetingProxyMinutes': {'low': round(counted, 2), 'high': round(counted, 2),
            'basis': 'Deduplicated audio-duration proxy after the shorter overlapping recording was verified as a duplicate segment; not an attendance-time range.'},
        'billableMinutes': None}
    files = ['manifest.json', 'fireflies_metadata.json', 'fireflies_christian_metadata.json',
             'oct9_duplicate_proof.json', 'calendly_events.json', 'calendly_invitees.json']
    out = {'snapshotAt': manifest['snapshotAt'],
        'subject': {'name': manifest['subjectName'], 'email': manifest['subjectEmail']},
        'timezone': manifest['timezone'], 'period': {'start': iso(start), 'through': iso(through), 'currentDayPartial': True},
        'sourceAsOf': {'fireflies': indexed['collectedAt'], 'calendly': manifest.get('calendlySnapshotAt', manifest['snapshotAt'])},
        'coverage': {'firefliesMetadataPages': indexed['pagination'], 'firefliesMetadataRecordsReviewed': len(all_transcripts),
            'firefliesMonthIndexedRecords': sum(start.timestamp()*1000 <= r['date'] <= through.timestamp()*1000 for r in all_transcripts.values()),
            'firefliesIndexedMonthCompleteWithinAccessibleList': manifest['firefliesPagesCompleteForIndexedMonth'],
            'calendlyAccountScope': manifest['calendlyAccount']['name'] + ' authenticated account only',
            'calendlyReviewedEvents': len(calendar['collection']), 'calendlyExactSubjectMatches': 0,
            'subjectOwnCalendarAvailable': False, 'failures': manifest['failures'],
            'gaps': ['Christian\'s own calendar and meetings absent from this accessible Fireflies account are not represented.',
                     'Fireflies date is a transcript creation/index timestamp, not a verified meeting start. Month coverage is therefore indexed-recording coverage.',
                     'Individual attendance duration and complete/non-meeting effort are not measured.'],
        }, 'events': sorted(records + matching_calendly, key=lambda r: r['startAt']), 'summary': summary,
        'deduplication': {'excludedSourceIds': [duplicate['shortId']], 'keptSourceIds': [duplicate['longId']],
            'confidence': 'high', 'method': 'Normalized transcript containment plus stable exact-sentence timestamp alignment and identical speaker roster',
            'short5WordSequenceContainment': gram5['shortContainment'],
            'exactAlignedSentenceMatches': duplicate['alignment']['uniqueLongSentenceMatches'],
            'medianRelativeOffsetSeconds': duplicate['alignment']['offsetSecondsMedian'],
            'privateProofSha256': hashlib.sha256(proof_path.read_bytes()).hexdigest()},
        'provenance': [{'path': 'data/private/time/'+name, 'sha256': hashlib.sha256((PRIVATE/name).read_bytes()).hexdigest()} for name in files],
        'references': [{'title': 'Fireflies Transcript Schema', 'url': manifest['durationUnitSource'],
            'supports': 'duration is audio minutes; date is transcript creation milliseconds UTC; participant emails differ from individual meeting-attendance records.'}],
        'notes': ['Centripetal work only, exact Christian subject identity only. No other team member\'s work time is included.',
                  'Recorded minutes describe associated audio, not exact attended, worked or billable time. Non-meeting estimates must remain a separate range.',
                  'Zero calendar-only minutes means zero matching invitees in Charles\'s scoped Calendly results, not zero Christian meetings across all calendars.',
                  f'{len(records)} associated recording records are retained for audit. One 33-minute duplicate segment has zero countedMinutes; {summary["countedRecordingCount"]} unique recording durations remain.',
                  'Prepared data contains no transcript text, summaries, other participant names/emails, join links or recording access links.'],
    }
    (ROOT / 'data/time_meetings.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'summary': summary, 'indexedMonthRecords': out['coverage']['firefliesMonthIndexedRecords'],
                      'calendarReviewedEvents': len(calendar['collection']), 'excludedScopeRecords': len(excluded)}, indent=2))


if __name__ == '__main__':
    build()
