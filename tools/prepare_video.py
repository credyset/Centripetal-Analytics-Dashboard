"""Prepare a labelled Video DM snapshot; never infer delivery from a Loom link."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
from urllib.parse import unquote
import hashlib, json, re

BASE = Path(__file__).resolve().parent.parent
raw = json.loads((BASE / 'data/private/video_sheet.json').read_text())['values']
connection_raw = json.loads((BASE / 'data/private/video_connections.json').read_text())['values']
now = datetime.now(timezone.utc).isoformat()
header = raw[0]
rows = []
groups = defaultdict(list)
dated = []
for line, values in enumerate(raw[1:], 2):
    r = dict(zip(header, values))
    company, contact = str(r.get('org', '')).strip(), str(r.get('contact', '')).strip()
    if not company or not contact or (company == 'org' and contact == 'contact'):
        continue
    url = str(r.get('li', '')).strip()
    match = re.search(r'linkedin\.com/in/([^/?#]+)', unquote(url), re.I)
    key = match.group(1).lower().rstrip('/') if match else ''
    status = str(r.get('Status (CS Column)', '')).strip()
    item = {
        'id': key or hashlib.sha256((company+'|'+contact).lower().encode()).hexdigest()[:16],
        'sourceRow': line, 'company': company, 'contact': contact,
        'linkedin': 'https://www.linkedin.com/in/'+key+'/' if key else '',
        'status': status, 'loom': str(r.get('Loom Link', '')).strip(),
        'reply': str(r.get('Response Status', '')).strip(),
        'connected': str(r.get('Connected?', '')).lower() in ('true','yes','connected'),
        'connectedAt': r.get('Connected At', ''), 'action': r.get('DM Action', ''),
        'followUp': r.get('Follow-up Action', ''), 'dealId': r.get('deal_id', ''),
        'explicitSendStatus': status.lower() in ('sent','done'),
    }
    rows.append(item)
    if key: groups[key].append(item)
    dated_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', status)
    if dated_match:
        month, day, year = map(int, dated_match.groups()); year += 2000 if year < 100 else 0
        try: date = datetime(year, month, day).date().isoformat()
        except ValueError: continue
        action = 'Follow-up status' if re.match(r'f/?u|follow',status,re.I) else 'Send status'
        dated.append({'date': date, 'contactId': item['id'], 'type': action, 'sourceRow': line})

actions = Counter(r['action'] for r in rows)
duplicates = [{'profile': k, 'rows': [r['sourceRow'] for r in rs],
               'actions': sorted(set(r['action'] for r in rs))}
              for k, rs in groups.items() if len(rs) > 1]
conflicts = [d for d in duplicates if len(d['actions']) > 1]
conn_header = connection_raw[0]
connections = [dict(zip(conn_header,r)) for r in connection_raw[1:] if r]
result = {
    'snapshotAt': now, 'status': 'available',
    'coverage': 'Current status snapshot; row-added and video-sent dates are not consistently recorded',
    'sourceUrl': 'https://docs.google.com/spreadsheets/d/1_Vq5-hM3POad1V14rZjX6gfaUojUnnTvxjjSv1zDJ8M/edit',
    'rows': rows, 'datedActions': dated,
    'summary': {
        'sourceRows': len(rows), 'uniqueProfiles': len(groups),
        'rowsMissingProfile': sum(not r['linkedin'] for r in rows),
        'readyRows': actions['Ready for video DM'],
        'sheetCompletedRows': actions['Already sent/completed'],
        'explicitSendStatusRows': sum(r['explicitSendStatus'] for r in rows),
        'followUpRows': sum(r['followUp']=='Follow-up Needed' for r in rows),
        'manualCheckRows': sum(r['followUp']=='Manual Check' for r in rows),
        'reviewRows': actions['Review'], 'awaitingConnectionRows': actions['Awaiting connection'],
        'skipRows': actions['Skip'], 'duplicates': len(duplicates),
        'duplicateExtraRows': sum(len(d['rows'])-1 for d in duplicates),
        'conflictingProfiles': len(conflicts),
        'acceptedConnectionRecords': len(connections),
        'connectedRows': sum(r['connected'] for r in rows),
        'rowsWithDealId': sum(bool(r['dealId']) for r in rows),
        'newRowsInPeriod': None,
    },
    'duplicateProfiles': duplicates,
    'notes': [
        'Status totals count source rows. Unique profiles deduplicate valid normalized LinkedIn URLs; rows without a valid profile remain unresolved.',
        'Spreadsheet sent/completed includes a Loom link or exact Sent/Done status. A Loom link alone does not establish delivery.',
        'Explicit Sent/Done is a self-reported status, not independently verified delivery. Undated sends cannot be assigned to the selected period.',
        'Follow-up categories overlap the main status categories; do not add them to the prospect total.',
        'This first snapshot establishes the baseline. Newly added rows by period remain unavailable until a later comparable snapshot or trusted creation date exists.',
        'Connection dates and automation message dates are not Video DM send dates. The status snapshot is unaffected by the date filter.',
    ],
}
assert len(rows)==sum(actions.values())
assert len({r['sourceRow'] for r in rows})==len(rows)
(BASE/'data/video.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['summary'],indent=2))
