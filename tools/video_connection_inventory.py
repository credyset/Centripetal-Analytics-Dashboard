"""Validate a separately dated current-state Video DM helper inventory.

The review is a projection over an unchanged source inventory. It never changes
worksheet/native events, appearance dates, or period-connection metrics.
"""
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timedelta
import re

FIELDS = {'connected', 'connectedAt', 'action', 'connectionMatchCount'}
SOURCE_FIELDS = {'Connected?', 'Connected At', 'DM Action', 'Connection Match Count'}
ACTIONS = {'Ready for video DM', 'Awaiting connection', 'Review', 'Skip', 'Already sent/completed'}
LABELS = {'Connected', 'Not connected', 'Verify connection', 'Review duplicate', 'Check URL'}
ACTION_COUNTERS = {'readyRows': 'Ready for video DM', 'reviewRows': 'Review',
                   'awaitingConnectionRows': 'Awaiting connection'}


def _instant(value, label):
    assert isinstance(value, str) and re.search(r'T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$', value), label + ' requires an explicit timestamp'
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise AssertionError(label + ' is not a valid timestamp') from error
    assert result.utcoffset() is not None
    return result


def _day(value):
    if value is None:
        return None
    assert isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value), 'Connection dates retain an ISO source day'
    try:
        assert date.fromisoformat(value).isoformat() == value
    except ValueError as error:
        raise AssertionError('Invalid source connection day') from error
    return value


def _literal_day(value):
    if value in ('', None):
        return None
    if isinstance(value, str) and value.isdigit():
        return (date(1899, 12, 30) + timedelta(days=int(value))).isoformat()
    return _day(value)


def _state(state):
    assert isinstance(state, dict) and set(state) == FIELDS, 'Current helper changes have an exact field allowlist'
    assert type(state['connected']) is bool
    _day(state['connectedAt'])
    assert state['action'] in ACTIONS
    assert type(state['connectionMatchCount']) is int and state['connectionMatchCount'] >= 0


def _totals(rows):
    actions = Counter(row.get('action') for row in rows)
    labels = Counter(row.get('sourceConnectionLabel', row.get('connectionLabel')) for row in rows)
    return {**{key: actions[action] for key, action in ACTION_COUNTERS.items()},
            'connectedRows': sum(row.get('connected') is True for row in rows),
            'verifyConnectionRows': labels['Verify connection'], 'notConnectedRows': labels['Not connected']}, actions, labels


def _assert_integer_counters(counters):
    assert isinstance(counters, dict)
    assert all(type(value) is int and value >= 0 for value in counters.values()), 'Helper counters must be nonnegative integers'


def validate_video_connection_inventory(video):
    """Return True for a valid child, raising before any untrusted overlay is used."""
    if not video.get('connectionInventoryReview'):
        return True
    review = video['connectionInventoryReview']
    assert review.get('schemaVersion') == 1
    assert review.get('status') == 'current_bounded_helper_inventory'
    assert review.get('appliesToSnapshotAt') == video.get('snapshotAt'), 'Connection helpers apply to a different inventory'
    assert review.get('parentVideoInventorySnapshotAt') == video.get('snapshotAt')
    reviewed_at = _instant(review.get('reviewedAt'), 'Helper reviewedAt')
    assert review.get('snapshotAt') == review.get('reviewedAt')
    assert _instant(video.get('snapshotAt'), 'Base video snapshotAt') <= reviewed_at
    assert set(review.get('rowChangeAllowlist', [])) == FIELDS and len(review['rowChangeAllowlist']) == len(FIELDS)
    assert set(review.get('literalSourceColumnAllowlist', [])) == SOURCE_FIELDS and len(review['literalSourceColumnAllowlist']) == len(SOURCE_FIELDS)
    assert review.get('atomicSnapshot') is False
    coverage = review.get('coverage') or {}
    assert coverage.get('completeCurrentMainAndLedgerValues') is True
    assert coverage.get('completeConnectionEventStream') is False
    assert coverage.get('sourceRecordedDatesIndependentlyVerifiedAsAcceptanceEvents') is False
    assert coverage.get('reportingPeriodConnectionsAdded') == 0

    base_rows = video.get('rows') or []
    by_source = {row['sourceRow']: row for row in base_rows}
    assert len(by_source) == len(base_rows), 'Base source rows are not unique'
    projected = {key: deepcopy(row) for key, row in by_source.items()}
    records = review.get('records')
    assert isinstance(records, list) and records
    seen = set()
    ledger = {}
    source_counts = Counter()
    source_cell_count = 0
    for record in records:
        source_row, ident = record.get('sourceRow'), record.get('id')
        assert type(source_row) is int and source_row in by_source, 'Current helper source row is absent'
        assert source_row not in seen, 'Current helper source row occurs more than once'
        seen.add(source_row)
        row = by_source[source_row]
        assert all(record.get(key) == row.get(key) for key in ('id', 'company', 'contact')), 'Current helper identity differs from its base row'
        assert isinstance(ident, str) and ident
        before, after = record.get('before'), record.get('after')
        _state(before); _state(after)
        for field in ('connected', 'connectedAt', 'action'):
            assert before[field] == row.get(field), 'Current helper before value differs from the base row: ' + field
        if 'connectionMatchCount' in row:
            assert before['connectionMatchCount'] == row['connectionMatchCount'], 'Current helper before match count differs from the base row'
        label = record.get('sourceConnectionLabel')
        assert label in LABELS
        assert record.get('ledgerProfileId') == ident
        ledger_row = record.get('ledgerSourceRow')
        assert type(ledger_row) is int and ledger_row > 1
        ledger_date = _day(record.get('ledgerRecordedDate'))
        ledger_identity = (ident, ledger_date)
        assert ledger_row not in ledger or ledger[ledger_row] == ledger_identity, 'One ledger row was joined to different profiles or dates'
        ledger[ledger_row] = ledger_identity
        assert record.get('eventTimezone') is None and record.get('heldCallConfirmed') is None
        assert record.get('heldStatus') == 'Not established by this helper review'
        if label == 'Connected':
            assert after['connected'] is True and after['connectedAt'] == ledger_date and ledger_date
            assert record.get('datePrecision') == 'day'
        elif label in ('Verify connection', 'Review duplicate'):
            assert after['connected'] is False and after['connectedAt'] is None and after['action'] == 'Review', 'Unverified/duplicate identities must stay on review hold'
            assert record.get('datePrecision') == 'unknown'
            if label == 'Verify connection':
                assert ledger_date is None, 'Verify connection row unexpectedly has a dated ledger acceptance'
        else:
            assert after['connected'] is False
        raw = record.get('sourceFieldChanges')
        assert isinstance(raw, dict) and raw and set(raw) <= SOURCE_FIELDS
        for field, change in raw.items():
            assert set(change) == {'before', 'after'} and change['before'] != change['after']
            if field == 'Connected?':
                assert change['before'] == row.get('connectionLabel') and change['after'] == label
                assert (change['before'] == 'Connected') is before['connected']
                assert (change['after'] == 'Connected') is after['connected']
            elif field == 'Connected At':
                assert _literal_day(change['before']) == before['connectedAt']
                assert _literal_day(change['after']) == after['connectedAt']
            elif field == 'DM Action':
                assert change['before'] == before['action'] and change['after'] == after['action']
            else:
                assert int(change['before']) == before['connectionMatchCount'] and int(change['after']) == after['connectionMatchCount']
        if 'Connected?' not in raw:
            assert label == row.get('connectionLabel'), 'Unchanged source connection label was reclassified'
        for normalized, literal in [('connected', 'Connected?'), ('connectedAt', 'Connected At'), ('action', 'DM Action'), ('connectionMatchCount', 'Connection Match Count')]:
            assert not (before[normalized] != after[normalized]) or literal in raw, 'A normalized helper change lacks literal source evidence'
            if normalized != 'connected':
                assert (before[normalized] != after[normalized]) == (literal in raw), 'Literal and normalized helper changes disagree'
        projected[source_row].update(deepcopy(after), sourceConnectionLabel=label)
        source_counts.update(raw.keys())
        source_cell_count += len(raw)

    base_summary, current_summary = review.get('baseSummary'), review.get('newSummary')
    _assert_integer_counters(base_summary); _assert_integer_counters(current_summary)
    assert set(base_summary) == set(current_summary)
    base_counts, base_actions, base_labels = _totals(base_rows)
    new_counts, new_actions, new_labels = _totals(list(projected.values()))
    for key, value in base_counts.items():
        assert base_summary[key] == value, 'Base helper counter does not match its rows: ' + key
        assert current_summary[key] == new_counts[key], 'Current helper counter does not match its rows: ' + key
    for key in ('readyRows', 'connectedRows', 'reviewRows', 'awaitingConnectionRows'):
        assert base_summary[key] == video['summary'][key], 'Base helper summary contradicts historical inventory'
    assert base_summary['currentLedgerRows'] == video['summary']['acceptedConnectionRecords']
    for key in ('verifyConnectionRows', 'acceptedProfilesMatchedMain', 'acceptedProfilesWithoutConnectedFlag', 'acceptedProfilesWithoutConnectedFlagMissingDate', 'serialConnectionDatesDecodedAndCorroborated'):
        assert base_summary[key] == video['connectionDiagnostics'][key]
    summary = review.get('summary') or {}
    assert summary.get('inventoryDeltaOnly') is True and summary.get('newConnectionRecordsArePeriodConnections') is False
    old_ledger, new_ledger = base_summary['currentLedgerRows'], current_summary['currentLedgerRows']
    assert summary.get('priorLedgerRows') == old_ledger and summary.get('currentLedgerRows') == new_ledger
    assert new_ledger >= old_ledger and summary.get('newConnectionRecords') == new_ledger - old_ledger == len(ledger)
    assert set(ledger) == set(range(old_ledger + 2, new_ledger + 2)), 'Ledger append rows are not contiguous or complete'
    assert len({ident for ident, day in ledger.values()}) == len(ledger), 'Ledger append repeats a profile identity'
    added_dated = sum(day is not None for ident, day in ledger.values())
    added_undated = len(ledger) - added_dated
    assert summary.get('newLedgerRowsWithRecordedDate') == added_dated
    assert summary.get('newLedgerRowsWithoutRecordedDate') == added_undated
    assert current_summary['ledgerHelperConnectedRows'] - base_summary['ledgerHelperConnectedRows'] == added_dated
    assert current_summary['ledgerHelperVerifyRows'] - base_summary['ledgerHelperVerifyRows'] == added_undated
    for counters in (base_summary, current_summary):
        assert counters['ledgerHelperConnectedRows'] + counters['ledgerHelperVerifyRows'] == counters['currentLedgerRows']
    assert summary.get('ledgerRowsWithRecordedDate') == current_summary['ledgerHelperConnectedRows']
    assert summary.get('ledgerRowsWithoutRecordedDate') == current_summary['ledgerHelperVerifyRows']
    assert summary.get('ledgerHelperVerificationCounts') == {'Connected': current_summary['ledgerHelperConnectedRows'], 'Verify connection': current_summary['ledgerHelperVerifyRows']}
    assert summary.get('changedContactRows') == len(records)
    assert summary.get('changedHelperCells') == source_cell_count and summary.get('changedSourceColumnCounts') == dict(source_counts)
    for name, rows, actions, labels in [('prior', base_rows, base_actions, base_labels), ('current', list(projected.values()), new_actions, new_labels)]:
        values = summary.get(name) or {}
        assert values.get('contactRows') == len(base_rows) == len(rows)
        assert values.get('readyRows') == actions['Ready for video DM'] and values.get('connectedRows') == labels['Connected']
        assert values.get('connectionLabels') == dict(labels) and values.get('actionCounts') == dict(actions)
        assert values.get('uniqueProfiles') == video['summary']['uniqueProfiles']
        assert values.get('allTargetRows') == values['contactRows'] + values['companyOnlyTargetRows']
        if 'companyOnlyTargets' in video:
            assert values['companyOnlyTargetRows'] == len(video['companyOnlyTargets'])
    # Appended profiles that remain unverified or duplicated do not become
    # verified current connections, even when a dated ledger row exists.
    unverified_ledger = {record['ledgerSourceRow'] for record in records if not record['after']['connected']}
    assert current_summary['acceptedProfilesMatchedMain'] - base_summary['acceptedProfilesMatchedMain'] == len(ledger)
    assert current_summary['acceptedProfilesWithoutConnectedFlag'] - base_summary['acceptedProfilesWithoutConnectedFlag'] == len(unverified_ledger)
    assert current_summary['acceptedProfilesWithoutConnectedFlagMissingDate'] - base_summary['acceptedProfilesWithoutConnectedFlagMissingDate'] == added_undated
    assert current_summary['serialConnectionDatesDecodedAndCorroborated'] == new_counts['connectedRows']
    for key in ('acceptedProfilesMatchedMain', 'acceptedProfilesWithoutConnectedFlag', 'acceptedProfilesWithoutConnectedFlagMissingDate', 'serialConnectionDatesDecodedAndCorroborated'):
        assert summary.get(key) == current_summary[key]

    captures = review.get('sourceCaptures')
    assert isinstance(captures, list) and len(captures) >= 6
    assert len({capture.get('file') for capture in captures}) == len(captures)
    for capture in captures:
        assert re.fullmatch(r'[^/\\]+\.json', capture.get('file', ''))
        assert re.fullmatch(r'[0-9a-f]{64}', capture.get('sha256', ''))
        assert type(capture.get('returnedRowsIncludingHeader')) is int and capture['returnedRowsIncludingHeader'] > 0
        assert isinstance(capture.get('range'), str) and '!' in capture['range']
        assert isinstance(capture.get('captureClockBasis'), str) and capture['captureClockBasis']
        if capture.get('capturedAt') is not None:
            assert _instant(capture['capturedAt'], 'Source capturedAt') <= reviewed_at
    current_captures = [capture for capture in captures if capture.get('capturedAt')]
    assert any(re.search(r'!A1:AC\d+$', capture['range']) and capture['returnedRowsIncludingHeader'] >= len(base_rows) + 1 for capture in current_captures)
    assert any(re.search(r'!A1:AN\d+$', capture['range']) and capture['returnedRowsIncludingHeader'] == new_ledger + 1 for capture in current_captures)
    assert any(re.search(r'!AO1:AR\d+$', capture['range']) and capture['returnedRowsIncludingHeader'] == new_ledger + 1 for capture in current_captures)
    assert any(re.search(r'!A1:AR\d+$', capture['range']) and capture['returnedRowsIncludingHeader'] == old_ledger + 1 for capture in captures if not capture.get('capturedAt'))
    return True
