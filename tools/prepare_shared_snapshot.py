"""Write the approved, curated reporting snapshot shared through GitHub."""
from pathlib import Path
import copy
import json
import re

ROOT = Path(__file__).resolve().parents[1]

def curate_snapshot(source):
    public = copy.deepcopy(source)
    public['meta'].update(public=True, publicDataPolicy='Owner-approved detailed snapshot including prospect identities and available business record links.')
    public['meta']['note'] = 'Published snapshot; source coverage varies. Automatic refresh is not enabled.'
    for name in ('ads', 'waalaxy', 'content'):
        public.get(name, {}).pop('sources', None)
    def scrub(value):
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()
                    if key not in ('provenance', 'sourceUrl', 'sourcePath')}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, str):
            return re.sub(r'/Users/[^\s]+', '[local source]', value)
        return value
    public = scrub(public)
    for item in public.get('sources', []):
        if item['id'] == 'waalaxy':
            item['note'] = 'Historical Charles-only person flags, not period message totals. Current campaign analytics remain unavailable.'
    return public

def write_shared(source):
    snapshot = curate_snapshot(source)
    target = ROOT / 'data/shared-dashboard.json'
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+'\n')
    return target

if __name__ == '__main__':
    source = json.loads((ROOT/'data/dashboard.json').read_text())
    print(write_shared(source))
