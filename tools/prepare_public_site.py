"""Package a public reporting snapshot without prospect identities or private links.

The internal application/data remain unchanged. Only the allowlisted public dist
directory is passed to Sites. Public source retains anonymous calculation rows so
existing date and pipeline filters can reproduce the actual aggregate metrics.
"""
from pathlib import Path
import copy
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'public_site'
DIST = SITE / 'dist'


def pick(record, fields):
    return {key: copy.deepcopy(record[key]) for key in fields if key in record}


def build():
    source = json.loads((ROOT / 'data/dashboard.json').read_text())
    public = copy.deepcopy(source)
    public['meta'].update(public=True, publicDataPolicy='Aggregate reporting; prospect identities and private record links omitted.')
    public['meta']['note'] = 'Published snapshot; source coverage varies. Automatic refresh is not enabled.'
    for name in ('ads', 'waalaxy', 'content'):
        public[name].pop('sources', None)
    public['ads']['leads'] = [dict(pick(row, ('date', 'disposition', 'campaign', 'qualificationAsOf', 'meetingBooked', 'meetingHeld')),
                                  company='Identity withheld') for row in source['ads']['leads']]
    for row in public['ads']['campaigns']:
        row['name'] = 'Campaign ' + row['code']
        row.pop('id', None)
    public['waalaxy']['lists'] = []
    public['content']['posts'] = []  # Ranked post register is outside public aggregate scope.

    crm = public['crm']
    owners = sorted({str(row.get('owner')) for row in source['crm']['deals'] + source['crm']['activities'] if row.get('owner')})
    owner_labels = {name: f'Owner {index+1}' for index, name in enumerate(owners)}
    deal_ids = {row['id']: index+1 for index, row in enumerate(source['crm']['deals'])}
    deal_fields = ('pipelineId', 'stageId', 'status', 'value', 'currency', 'createdAt', 'updatedAt', 'stageChangedAt',
                   'wonAt', 'lostAt', 'nextActivityDate', 'lastActivityDate', 'isTest')
    crm['deals'] = [dict(pick(row, deal_fields), id=deal_ids[row['id']], owner=owner_labels.get(str(row.get('owner')), 'Unassigned'))
                    for row in source['crm']['deals']]
    activity_fields = ('type', 'done', 'isTest', 'createdAt', 'completedAt', 'dueDate')
    crm['activities'] = [dict(pick(row, activity_fields), id=index+1, dealId=deal_ids.get(row.get('dealId')),
                             owner=owner_labels.get(str(row.get('owner')), 'Unassigned'))
                         for index, row in enumerate(source['crm']['activities'])]
    crm['quality'].pop('testDealIds', None)
    crm['quality'].pop('testActivityIds', None)
    crm.pop('summary', None)  # Calculations use the retained anonymous rows.

    video = public['video']
    video.pop('sourceUrl', None)
    video.pop('duplicateProfiles', None)
    video['datedActions'] = []
    video['rows'] = [dict(pick(row, ('action', 'connected', 'connectedAt', 'explicitSendStatus')), id=index+1,
                         company='Identity withheld', contact='Identity withheld', linkedin='', loom='', reply='',
                         status='', followUp='', dealId=None)
                     for index, row in enumerate(source['video']['rows'])]
    # Free-text notes may refer to a qualified company's name or local collection paths.
    def scrub(value):
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()
                    if key not in ('provenance', 'sourceUrl', 'sourcePath')}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, str):
            value = re.sub(r'NuVee', 'the qualified lead', value, flags=re.I)
            value = re.sub(r'/Users/[^\s]+', '[local source]', value)
        return value
    public = scrub(public)
    for item in public['sources']:
        if item['id'] == 'waalaxy':
            item['note'] = 'Historical Charles-only person flags, not period message totals. Current campaign analytics remain unavailable.'

    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / 'data').mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'assets', DIST / 'assets', dirs_exist_ok=True)
    shutil.copy2(ROOT / 'styles.css', DIST / 'styles.css')
    html = (ROOT / 'index.html').read_text().replace('Internal analytics · Local concept', 'Public analytics · Dated snapshot').replace('INTERNAL / CONCEPT 01', 'PUBLIC / SNAPSHOT')
    html = html.replace('<meta name="color-scheme"', '<meta name="robots" content="noindex, nofollow">\n  <meta name="color-scheme"')
    (DIST / 'index.html').write_text(html)
    app = (ROOT / 'app.js').read_text()
    app = re.sub(r'NuVee', 'the qualified lead', app, flags=re.I)
    app = app.replace('function table(id,title,rows,cols,note=\'\'){',
        'function table(id,title,rows,cols,note=\'\'){if(["ads-leads","content-posts","crm-deals","crm-overdue","video-prospects"].includes(id))return panel(title,\'<p class="definition-note">Individual records and private links are omitted from this public view. Aggregate reporting appears above.</p>\');')
    app = app.replace('local concept', 'published snapshot').replace('Local concept', 'Published snapshot')
    app = app.replace('A working concept, with actual source data.', 'A published snapshot, with actual source data.')
    (DIST / 'app.js').write_text(app)
    (DIST / 'data/dashboard.json').write_text(json.dumps(public, ensure_ascii=False) + '\n')
    shutil.copy2(ROOT / 'data/empty.json', DIST / 'data/empty.json')
    manifest_path = SITE / '.openai/hosting.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['static'] = {'directory': 'dist'}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    # Do not permit record identities, contacts, internal links or filesystem paths.
    payload = (DIST / 'data/dashboard.json').read_text()
    assert not re.search(r'/Users/|linkedin\.com/in/|pipedrive\.com/deal/|loom\.com/|docs\.google\.com|[\w.+-]+@[\w.-]+\.[a-z]{2,}', payload, re.I)
    for row in source['crm']['deals']:
        assert 'title' not in public['crm']['deals'][deal_ids[row['id']]-1]
    assert len(public['crm']['deals']) == len(source['crm']['deals'])
    assert len(public['video']['rows']) == len(source['video']['rows'])
    print(json.dumps({'dist': str(DIST), 'sources': len(public['sources']), 'identitiesRemoved': True,
                      'anonymousDealCalculationRows': len(crm['deals']), 'sourceGeneratedAt': public['meta']['generatedAt']}))


if __name__ == '__main__':
    build()
