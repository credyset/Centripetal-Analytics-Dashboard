"""Check the portable, curated reporting snapshot before sharing changes."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
source = ROOT/'data/shared-dashboard.json'
data = json.loads(source.read_text())
assert all(k in data for k in ('meta','ads','crm','video','waalaxy','content','referrals','time','sources'))
assert data['meta']['timezone'] == 'America/Denver'
for entity in ('deals','activities'):
    rows = data['crm'][entity]
    assert len(rows) == len({row['id'] for row in rows}), f'Duplicate CRM {entity} IDs'
assert len(data['video']['rows']) == data['video']['summary']['sourceRows']
assert abs(sum(row['spend'] for row in data['ads']['daily'])-data['ads']['totals']['spend']) < .02
if data.get('time'):
    effort = data['time']
    meetings = effort['meetings']
    assert abs(sum(e['countedMinutes'] for e in meetings['events'])-meetings['summary']['recordedMinutes']) < .001
    assert all(not e.get('duplicateOfId') or e['countedMinutes'] == 0 for e in meetings['events'])
    assert all(0 <= w['planningAllowance']['hoursLow'] <= w['planningAllowance']['hoursHigh'] for w in effort['workstreams'])

def inspect(value):
    if isinstance(value, dict):
        assert not {'provenance','sourcePath','sourceUrl'}.intersection(value), 'Private source reference'
        for child in value.values(): inspect(child)
    elif isinstance(value, list):
        for child in value: inspect(child)
    elif isinstance(value, str):
        assert '/Users/' not in value, 'Local filesystem path'
inspect(data)
print('Shared snapshot: JSON, source totals, record IDs, effort accounting and curation checks passed.')
