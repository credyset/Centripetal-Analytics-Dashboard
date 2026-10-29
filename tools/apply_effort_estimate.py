"""Apply the owner's total estimate without inventing workstream allocations."""
import json
import copy
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_effort_decision(decision):
    def hours(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0
    assert hours(decision['hoursLow']) and hours(decision['hoursHigh'])
    assert 0 <= decision['hoursLow'] <= decision['hoursHigh']
    if decision.get('baseline'):
        baseline = decision['baseline']
        assert hours(baseline['hoursLow']) and hours(baseline['hoursHigh']) and baseline['hoursLow'] <= baseline['hoursHigh']
        previous_end = date.fromisoformat(baseline['coversThrough'])
        assert date.fromisoformat(baseline['periodStart']) <= previous_end
        ids, periods = set(), set()
        for row in decision.get('increments', []):
            start, end = date.fromisoformat(row['periodStart']), date.fromisoformat(row['coversThrough'])
            assert start <= end and start > previous_end, 'Owner increment periods overlap or are out of order'
            assert hours(row['hours']), 'An increment must be a finite nonnegative hour estimate'
            assert (start, end) not in periods, 'The same dated owner answer cannot be counted twice'
            periods.add((start, end))
            if row.get('id'):
                assert row['id'] not in ids, 'Owner confirmation ID is duplicated'
                ids.add(row['id'])
            previous_end = end
        added=sum(row['hours'] for row in decision['increments'])
        assert math.isclose(decision['hoursLow'],baseline['hoursLow']+added, abs_tol=1e-9)
        assert math.isclose(decision['hoursHigh'],baseline['hoursHigh']+added, abs_tol=1e-9)
        assert date.fromisoformat(decision['coversThrough']) == previous_end
    return decision


def apply_effort_estimate(effort, decision=None):
    decision = copy.deepcopy(decision) if decision is not None else json.loads((ROOT/'EFFORT_ESTIMATE.json').read_text())
    validate_effort_decision(decision)
    summary=effort['summary']
    summary.update(nonMeetingEstimateHoursLow=decision['hoursLow'],
        nonMeetingEstimateHoursHigh=decision['hoursHigh'], ownerAdjustedEstimate=True,
        ownerEstimateConfirmed=True, actualHumanTimeVerified=False,
        ownerEstimateRange={'low':decision['hoursLow'],'high':decision['hoursHigh'],
            'confirmedOn':decision['confirmedOn'],'basis':decision['basis'],
            'periodStart':decision.get('periodStart'), 'coversThrough':decision.get('coversThrough'),
            'baseline':copy.deepcopy(decision.get('baseline')),
            'increments':copy.deepcopy(decision.get('increments',[]))})
    summary.pop('ownerConfirmed',None)
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
    # The current decision is a total, not a multiplier or another increment.
    effort['notes'].append(f"Owner-specified nonmeeting estimate: {decision['hoursLow']}–{decision['hoursHigh']} hours through {decision.get('coversThrough',decision['confirmedOn'])}. No workstream allocation or independently measured-hour claim is made.")
    return effort
