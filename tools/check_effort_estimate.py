"""Check dated owner increments without multiplying effort or measuring audio as work."""
from pathlib import Path
import copy
import json
from apply_effort_estimate import apply_effort_estimate, validate_effort_decision
from apply_effort_review_2026_10_22 import apply_review
from prepare_shared_snapshot import curate_snapshot
from prepare_meeting_refresh_2026_10_28 import owner_decision, apply_owner_preview, OWNER_INCREMENT_ID

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
# The October 23–28 answer was repeated under an unrelated question. One stable
# dated confirmation adds 3.5 hours once, without implying another increment or
# any commercial outcome. This fixture works before and after canonical write.
earlier=copy.deepcopy(decision)
earlier['increments']=[row for row in earlier['increments'] if row['coversThrough']<='2026-10-22']
earlier.update(hoursLow=earlier['baseline']['hoursLow']+sum(row['hours'] for row in earlier['increments']),
    hoursHigh=earlier['baseline']['hoursHigh']+sum(row['hours'] for row in earlier['increments']),
    coversThrough='2026-10-22',confirmedOn='2026-10-22')
fresh=owner_decision(earlier);fresh_copy=copy.deepcopy(fresh)
assert fresh['hoursLow']==21.75 and fresh['hoursHigh']==23.0 and fresh['coversThrough']=='2026-10-28'
assert owner_decision(fresh)==fresh
assert sum(row['id']==OWNER_INCREMENT_ID for row in fresh['increments'] if row.get('id'))==1
explicit=copy.deepcopy(data['time']);source_meetings=copy.deepcopy(explicit['meetings'])
for _ in range(3):
    apply_effort_estimate(explicit,decision=fresh)
    assert (explicit['summary']['nonMeetingEstimateHoursLow'],explicit['summary']['nonMeetingEstimateHoursHigh'])==(21.75,23.0)
    assert explicit['meetings']==source_meetings
assert fresh==fresh_copy, 'The caller-supplied decision was mutated'
preview,evidence=apply_owner_preview(copy.deepcopy(data['time']),fresh)
replayed,_=apply_owner_preview(preview,fresh)
assert replayed==preview, 'Owner evidence or total was duplicated on replay'
assert sum(row.get('id')==OWNER_INCREMENT_ID for row in next(w for w in preview['workstreams'] if w['id']=='dashboard')['evidence'])==1
assert not any(row['planningAllowance']['enabled'] for row in preview['workstreams'])
assert preview['meetings']==source_meetings and preview['trackedHumanMinutes'] is None
assert preview['summary']['combinedWorkedHours'] is None and preview['summary']['actualHumanTimeVerified'] is False
curated=curate_snapshot(copy.deepcopy(data),effort_decision=fresh)
assert curated['time']['summary']['ownerEstimateRange']['increments']==fresh['increments']
assert curated['outcomes']==data['outcomes'] and curated['time']['meetings']==data['time']['meetings']
for changed in ('duplicate','overlap','negative','incorrect_total'):
    bad=copy.deepcopy(fresh)
    if changed=='duplicate':bad['increments'].append(copy.deepcopy(bad['increments'][-1]))
    elif changed=='overlap':bad['increments'][-1]['periodStart']='2026-10-22'
    elif changed=='negative':bad['increments'][-1]['hours']=-3.5
    else:bad['hoursLow']+=3.5
    try:validate_effort_decision(bad)
    except (AssertionError,ValueError):pass
    else:raise AssertionError(f'Invalid owner decision accepted: {changed}')
print('Effort: dated owner increments, optional preview decision, one3.5-hour confirmation, idempotent evidence, negative guards and separate audio/actual time passed.')
