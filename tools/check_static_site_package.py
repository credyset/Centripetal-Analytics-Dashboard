"""Verify curated payload equality and fail-closed static build destinations."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from build_static_site import ROOT, build
from prepare_shared_snapshot import curate_snapshot


EXPECTED_FILES = {
    '.nojekyll', 'index.html', 'app.js', 'styles.css',
    'data/dashboard.json', 'data/empty.json',
    'assets/LICENSE-Lora.txt', 'assets/LICENSE-Roboto.txt',
    'assets/Lora-Regular.ttf', 'assets/Lora-SemiBold.ttf',
    'assets/Roboto-Bold.ttf', 'assets/Roboto-Medium.ttf',
    'assets/Roboto-Regular.ttf', 'assets/logo.png',
}


def quiet_build(destination, for_publication=False):
    with redirect_stdout(io.StringIO()):
        build(destination, for_publication=for_publication)


def contents(destination):
    return {path.relative_to(destination).as_posix(): path.read_bytes()
            for path in destination.rglob('*') if path.is_file()}


def rejected(destination, for_publication=False):
    try:
        quiet_build(destination, for_publication=for_publication)
    except RuntimeError:
        return
    raise AssertionError('Unsafe or held destination was accepted: ' + str(destination))


def verify_payload(destination, expected):
    packaged = contents(destination)
    assert set(packaged) == EXPECTED_FILES, set(packaged) ^ EXPECTED_FILES
    matches = re.findall(r'<script id="report-data" type="application/json">([\s\S]*?)</script>',
                         packaged['index.html'].decode())
    assert len(matches) == 1
    embedded = json.loads(matches[0])
    downloaded = json.loads(packaged['data/dashboard.json'])
    assert embedded == downloaded == expected
    assert packaged['data/empty.json'] == (ROOT / 'data/empty.json').read_bytes()
    return packaged


source = json.loads((ROOT / 'data/shared-dashboard.json').read_text())
expected = curate_snapshot(source)
with TemporaryDirectory(prefix='centripetal-static-package-') as temporary:
    base = Path(temporary)
    destination = base / 'dist'
    quiet_build(destination)
    initial = verify_payload(destination, expected)
    quiet_build(destination)
    assert verify_payload(destination, expected) == initial  # Known clean output can be rebuilt.

    # Files outside the public manifest must stop the build before any output
    # changes. Their removal is performed only by this test in its own temp dir.
    for relative in ('.env', 'data/private-export.json', 'data/shared-dashboard.json'):
        sentinel = destination / relative
        sentinel.write_text('STALE_PRIVATE_SENTINEL_DO_NOT_PUBLISH')
        before = contents(destination)
        rejected(destination)
        assert contents(destination) == before, 'Rejected output was modified: ' + relative
        sentinel.unlink()
        quiet_build(destination)
        assert verify_payload(destination, expected) == initial

    # An expected public data file may be stale, but a successful rebuild must
    # replace it with the exact same snapshot embedded in the current HTML.
    (destination / 'data/dashboard.json').write_text('{"stale": true}\n')
    quiet_build(destination)
    assert verify_payload(destination, expected) == initial
    unexpected_directory = destination / 'private'
    unexpected_directory.mkdir()
    rejected(destination)
    unexpected_directory.rmdir()

    # Reject checkout/source destinations, including ancestors and arbitrary
    # new folders inside the checkout. No directory is created by rejection.
    for unsafe in (ROOT, ROOT.parent, ROOT / 'data', ROOT / 'assets', ROOT / 'tools',
                   ROOT / 'public_site', ROOT / '_site/nested-output', ROOT / 'new-preview-output'):
        existed = unsafe.exists()
        rejected(unsafe)
        assert existed or not unsafe.exists()

    # Linked entries could otherwise turn an allowed filename into an overwrite
    # of a file outside the build directory; reject them before copying.
    secret = base / 'outside-sentinel'
    secret.write_text('UNCHANGED_OUTSIDE_OUTPUT')
    link_output = base / 'linked-output'
    link_output.mkdir()
    (link_output / 'app.js').symlink_to(secret)
    rejected(link_output)
    assert secret.read_text() == 'UNCHANGED_OUTSIDE_OUTPUT'
    alias = base / 'output-alias'
    alias.symlink_to(destination, target_is_directory=True)
    rejected(alias)
    hardlink_output = base / 'hardlinked-output'
    hardlink_output.mkdir()
    os.link(secret, hardlink_output / 'app.js')
    rejected(hardlink_output)
    assert secret.read_text() == 'UNCHANGED_OUTSIDE_OUTPUT'

    publication = base / 'publication'
    if expected.get('meta', {}).get('public') and expected['meta'].get('publicationStatus') not in ('local_only', 'pending_owner_approval'):
        quiet_build(publication, for_publication=True)
        verify_payload(publication, expected)
    else:
        rejected(publication, for_publication=True)
        assert not publication.exists()

print('Static package: exact embedded/downloaded curated payload, clean rebuilds, dirty-output rejection and source-directory protection passed.')
