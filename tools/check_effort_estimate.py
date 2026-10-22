"""Check dated owner increments without multiplying effort or measuring audio as work."""
from pathlib import Path
import copy
import json
from apply_effort_estimate import apply_effort_estimate
from apply_effort_review_2026_10_22 import apply_review
from prepare_shared_snapshot import curate_snapshot

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'data/shared-dashboard.json').read_text())
decision=json.loads((ROOT/'EFFORT_ESTIMATE.json').read_text())
expected=(decision['hoursLow'],decision['hoursHigh'])
effort=copy.deepcopy(data['time']);original_meetings=copy.deepcopy(effort['meetings'])
for _ in range(3):
    apply_effort_estimate(effort)
    assert (effort['summary']['nonMeetingEstimateHoursLow'],effort['summary']['nonMeetingEstimateHoursHigh'])==expected
assert effort['summary']['ownerEstimateConfirmed'] is True
assert effort['summary']['actualHumanTimeVerified'] is False
assert effort['trackedHumanMinutes'] is None and effort['summary']['combinedWorkedHours'] is None
assert effort['meetings']==original_meetings
assert not any(row['planningAllowance']['enabled'] for row in effort['workstreams'])
range_=effort['summary']['ownerEstimateRange']
assert range_['coversThrough']==decision['coversThrough']
assert range_['baseline']==decision['baseline'] and range_['increments']==decision['increments']
increment=sum(row['hours'] for row in range_['increments'])
assert expected==(range_['baseline']['hoursLow']+increment,range_['baseline']['hoursHigh']+increment)
# Older imports reapply the current total instead of retaining the stale range.
older=copy.deepcopy(data);older['time']['summary'].update(nonMeetingEstimateHoursLow=14.5,nonMeetingEstimateHoursHigh=15.75)
assert curate_snapshot(older)['time']['summary']['ownerEstimateRange']==range_
first=apply_review(copy.deepcopy(data),'2026-10-22T13:00:00Z')
second=apply_review(copy.deepcopy(first),'2026-10-22T13:00:00Z')
assert first==second, 'Replaying this review duplicated evidence, notes or hours.'
assert len(first['time']['notes'])==len(set(first['time']['notes']))
assert first['time']['meetings']==original_meetings
print('Effort: dated owner increment, idempotent total/evidence, unallocated workstreams and separate audio/actual time passed.')
