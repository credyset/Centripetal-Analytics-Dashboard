"""Package the owner-approved detailed dashboard for the existing public Site.

Publication of prospect identities and available business details was explicitly
approved by the owner on October 14, 2026. Use only the curated dashboard JSON;
never copy raw exports, credentials, environment files or the internal checkout.
"""
from pathlib import Path
import json
import shutil
from prepare_shared_snapshot import curate_snapshot

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'public_site'
DIST = SITE / 'dist'


def build():
    # The same tracked snapshot drives GitHub clones and the hosted dashboard.
    snapshot_path = ROOT / 'data/shared-dashboard.json'
    if not snapshot_path.exists():
        snapshot_path = ROOT / 'data/dashboard.json'
    source = json.loads(snapshot_path.read_text())
    public = curate_snapshot(source)

    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / 'data').mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'assets', DIST / 'assets', dirs_exist_ok=True)
    shutil.copy2(ROOT / 'styles.css', DIST / 'styles.css')
    html = (ROOT / 'index.html').read_text().replace('Internal analytics · Local concept', 'Public analytics · Dated snapshot').replace('INTERNAL / CONCEPT 01', 'PUBLIC / SNAPSHOT')
    html = html.replace('<meta name="color-scheme"', '<meta name="robots" content="noindex, nofollow">\n  <meta name="color-scheme"')
    (DIST / 'index.html').write_text(html)
    payload = json.dumps(public, ensure_ascii=False) + '\n'
    app = (ROOT / 'app.js').read_text()
    app = app.replace('local concept', 'published snapshot').replace('Local concept', 'Published snapshot')
    app = app.replace('A working concept, with actual source data.', 'A published snapshot, with actual source data.')
    (DIST / 'app.js').write_text(app)
    (DIST / 'data/dashboard.json').write_text(payload)
    # Keep the published interface and source snapshot in one response. This
    # avoids old asset/data caches and blocked auxiliary script requests.
    start = app.index('try{const res=await fetch(')
    end = app.index('S.data.meta=S.data.meta||{};', start)
    app = app[:start] + "try{S.data=JSON.parse(document.getElementById('report-data').textContent);" + app[end:]
    safe_payload = payload.replace('<', '\\u003c')
    html = html.replace('  <script src="app.js" defer></script>\n', '')
    html = html.replace('</body>', '<script id="report-data" type="application/json">' + safe_payload + '</script>\n<script>' + app + '</script>\n</body>')
    (DIST / 'index.html').write_text(html)
    shutil.copy2(ROOT / 'data/empty.json', DIST / 'data/empty.json')
    manifest_path = SITE / '.openai/hosting.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['static'] = {'directory': 'dist'}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')

    # Confirm identities, source IDs and business links survive the package step.
    assert public['crm']['deals'] == source['crm']['deals']
    assert public['crm']['activities'] == source['crm']['activities']
    assert public['video']['rows'] == source['video']['rows']
    assert public['ads']['leads'] == source['ads']['leads']
    assert public['content']['posts'] == source['content']['posts']
    assert '/Users/' not in json.dumps(public)
    print(json.dumps({'dist': str(DIST), 'sources': len(public['sources']), 'identitiesIncluded': True,
                      'dealRecords': len(public['crm']['deals']), 'videoRows': len(public['video']['rows']),
                      'sourceGeneratedAt': public['meta']['generatedAt']}))


if __name__ == '__main__':
    build()
