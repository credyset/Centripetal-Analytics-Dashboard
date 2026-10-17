"""Apply the owner's total estimate without inventing workstream allocations."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def apply_effort_estimate(effort):
    decision = json.loads((ROOT/'EFFORT_ESTIMATE.json').read_text())
    assert 0 <= decision['hoursLow'] <= decision['hoursHigh']
    summary=effort['summary']
    summary.update(nonMeetingEstimateHoursLow=decision['hoursLow'],
        nonMeetingEstimateHoursHigh=decision['hoursHigh'], ownerAdjustedEstimate=True,
        ownerEstimateRange={'low':decision['hoursLow'],'high':decision['hoursHigh'],
            'confirmedOn':decision['confirmedOn'],'basis':decision['basis']})
    summary.pop('ownerAdjustmentMultiplier',None)
    for row in effort['workstreams']:
        allowance=row['planningAllowance']
        allowance.update(enabled=False, supersededByOwnerTotalRange=True, ownerAdjustedEstimate=False,
            kind='Historical workstream assumption; superseded by owner total estimate')
        for bound in ('Low','High'):
            if 'baselineHours'+bound in allowance:
                allowance['hours'+bound]=allowance['baselineHours'+bound]
                allowance['minutes'+bound]=allowance['hours'+bound]*60
        allowance.pop('ownerAdjustmentMultiplier',None)
    for row in effort['workstreams']:
        for evidence in row.get('evidence',[]):
            if '35% nonmeeting estimate uplift' in evidence.get('label',''):
                evidence['label']='Owner reviewed source reconciliation and specified an overall nonmeeting estimate; this supports review scope, not measured duration.'
    effort['notes']=[n for n in effort.get('notes',[]) if '35%' not in n and 'Owner-specified nonmeeting estimate:' not in n]
    effort['notes'].append(f"Owner-specified nonmeeting estimate: {decision['hoursLow']}–{decision['hoursHigh']} hours. This replaces the prior percentage adjustment; no workstream allocation or measured actual-hour claim is made.")
    return effort
