"""Curate Christian's October evidence; keep recorded audio and assumed effort separate."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'

def build():
    meetings = json.loads((DATA / 'time_meetings.json').read_text())
    work = json.loads((DATA / 'time_work_evidence.json').read_text())
    now = datetime.now(timezone.utc)
    # These are explicitly unconfirmed allowances, never measurements. Scoped
    # project reviews refine two defaults; no task versions or agent runtime add hours.
    overrides = {
        'pulley': (1.5, 3.0, 'Project review: assumed asynchronous direction, access/upload coordination and review across three milestones.'),
        'website': (2.0, 4.0, 'Project review: assumed asynchronous website direction and visual review; meetings and shared analytics review excluded.'),
    }
    streams = []
    for row in work['workstreams']:
        allowance = dict(row['planningAllowance'])
        lo, hi, basis = overrides.get(row['id'], (allowance['hoursLow'], allowance['hoursHigh'], allowance['scope']))
        allowance.update(enabled=True, ownerConfirmed=False, hoursLow=lo, hoursHigh=hi,
                         minutesLow=lo*60, minutesHigh=hi*60, scope=basis,
                         kind='Draft asynchronous review and coordination estimate')
        # Do not imply the original round formula still defines refined estimates.
        if row['id'] in overrides:
            for key in ('assumedReviewRounds', 'minutesPerRoundLow', 'minutesPerRoundHigh'):
                allowance.pop(key, None)
        streams.append({key: row[key] for key in ('id','title','evidenceDates','humanInvolvementBasis')})
        streams[-1].update(planningAllowance=allowance, evidence=[
            {'date': a['evidenceDate'], 'label': a['establishes']}
            for a in row['artifacts'] if a.get('evidenceDate')
        ])
    # Publish minimum necessary evidence, not source paths, hashes, transcripts,
    # inferred end times, or other attendees' identities.
    meetings.pop('provenance', None)
    meetings.pop('deduplication', None)
    meetings['subject'] = {'name': 'Christian Wutz'}
    for event in meetings['events']:
        event.pop('endAt', None)
        event['timeBasis'] = 'Fireflies indexed date; actual meeting start and individual attendance are unverified.'
    result = {
        'snapshotAt': now.isoformat(), 'subject': 'Christian Wutz', 'timezone':'America/Denver',
        'period': {'start':'2026-10-01','end':now.astimezone(ZoneInfo('America/Denver')).date().isoformat(),
                   'currentDayPartial':True},
        'meetings':meetings, 'workstreams':streams, 'trackedHumanMinutes':None,
        'summary': {'nonMeetingEstimateHoursLow':sum(s['planningAllowance']['hoursLow'] for s in streams),
                    'nonMeetingEstimateHoursHigh':sum(s['planningAllowance']['hoursHigh'] for s in streams),
                    'confidence':'low', 'ownerConfirmed':False, 'combinedWorkedHours':None},
        'notes': [
            'Christian only. Other team members and automated research, coding, export and publication runtime are excluded.',
            'Meeting evidence measures deduplicated audio associated with Christian; exact attendance remains unknown.',
            'Nonmeeting estimates cover assumed asynchronous direction, review and coordination only. Actual work may fall outside the range.',
            'No combined worked-hour total is asserted: individual attendance and overlap with review work require confirmation.',
            'Newsletter/publication approvals are grouped under dashboard; repeated artifacts and mirrored publications are not extra work.',
            'These figures are a draft reconstruction, not a timesheet or billing record.'
        ]
    }
    assert abs(sum(e['countedMinutes'] for e in meetings['events']) - meetings['summary']['recordedMinutes']) < .001
    assert all(0 <= s['planningAllowance']['hoursLow'] <= s['planningAllowance']['hoursHigh'] for s in streams)
    assert result['summary']['combinedWorkedHours'] is None
    out = DATA / 'time.json'
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'output':str(out),'recordedMinutes':meetings['summary']['recordedMinutes'],**result['summary']}))

if __name__ == '__main__':
    build()
