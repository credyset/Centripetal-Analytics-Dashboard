"""Package the shared dashboard for the existing Sites project."""
from pathlib import Path
import json
from build_static_site import build

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'public_site'

if __name__ == '__main__':
    manifest_path = SITE / '.openai/hosting.json'
    manifest = json.loads(manifest_path.read_text())
    build(SITE / 'dist')
    manifest['static'] = {'directory': 'dist'}
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
