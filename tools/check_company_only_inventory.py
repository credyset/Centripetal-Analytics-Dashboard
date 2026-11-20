"""Check separate company-only inventory without changing contact activity grain.

Runs the real normalizer in a temporary isolated directory. An optional snapshot
can also be checked with --snapshot; no current company-cohort count is assumed.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGET_FIELDS = {'sourceRow', 'company', 'status', 'action', 'score', 'rank', 'tier', 'stage'}


def check_inventory(video):
    targets = video['companyOnlyTargets']
    assert isinstance(targets, list)
    assert video['summary']['sourceRows'] == len(video['rows'])
    assert video['summary']['companyOnlyTargetRows'] == len(targets)
    assert video['summary']['allTargetRows'] == len(video['rows']) + len(targets)
    coverage = video['sourceCoverage']
    assert coverage['allTargetRows'] == len(video['rows']) + len(targets)
    assert coverage['mainReturnedRowsIncludingHeader'] == 1 + coverage['allTargetRows'] + coverage['excludedNonProspectPhysicalRows']
    physical_rows = [r['sourceRow'] for r in video['rows'] + targets]
    assert len(set(physical_rows)) == len(physical_rows), 'Company-only target duplicated a contact row'
    for target in targets:
        assert set(target) <= TARGET_FIELDS, 'Company-only target acquired person or activity fields'
        assert isinstance(target['sourceRow'], int)
        assert isinstance(target['company'], str) and target['company'].strip()
        assert target['company'].strip().casefold() != 'org'
        assert all(isinstance(value, str) for key, value in target.items() if key != 'sourceRow')


def check_fixture():
    header = ['org', 'contact', 'li', 'Status (CS Column)', 'Loom Link', 'Response Status',
              'Connected?', 'Connected At', 'DM Action', 'Follow-up Action', 'deal_id',
              'icp', 'rank', 'tier', 'stage']

    def source_row(**fields):
        return [fields.get(field, '') for field in header]

    company = source_row(**{'org': 'Research Only Co', 'contact': None, 'Status (CS Column)': 'Sent 9/25/26',
        'DM Action': 'Ready for video DM', 'Connected?': 'Connected', 'icp': '13.00',
        'rank': '01', 'tier': ' Warm ', 'stage': 'Seed'})
    raw = [header,
        source_row(**{'org': 'Alpha', 'contact': 'Amy', 'li': 'https://www.linkedin.com/in/amy/',
            'Status (CS Column)': 'Done', 'DM Action': 'Already sent/completed',
            'Follow-up Action': 'Follow-up Needed', 'Connected?': 'Connected', 'deal_id': '12',
            'Loom Link': 'https://www.loom.com/share/' + 'a' * 32}),
        company,
        [],
        header,
        source_row(**{'org': 'Beta', 'contact': 'Ben', 'li': 'https://www.linkedin.com/in/BEN/',
            'Status (CS Column)': 'Sent 9/10/26', 'DM Action': 'Ready for video DM'}),
        source_row(org='org'),
        source_row(contact='No company'),
        source_row(rank='9')]
    zero = deepcopy(raw)
    zero[2] = []
    with tempfile.TemporaryDirectory(prefix='video-company-only-') as directory:
        base = Path(directory)
        (base / 'tools').mkdir()
        private = base / 'data/private'
        private.mkdir(parents=True)
        history = base / 'data/history'
        history.mkdir()
        normalizer = base / 'tools/prepare_video.py'
        shutil.copyfile(ROOT / 'tools/prepare_video.py', normalizer)
        (private / 'video_connections.json').write_text(json.dumps({'values': [['linkedinUrl']]}))

        def normalize(grid, clock):
            (private / 'video_sheet.json').write_text(json.dumps({'values': grid}))
            (private / 'video_manifest.json').write_text(json.dumps({'snapshotAt': clock, 'complete': True}))
            completed = subprocess.run([sys.executable, str(normalizer)], capture_output=True, text=True)
            assert completed.returncode == 0, completed.stderr
            video = json.loads((base / 'data/video.json').read_text())
            check_inventory(video)
            return video

        before = normalize(zero, '2026-10-01T12:00:00Z')
        assert before['companyOnlyTargets'] == [] and before['summary']['allTargetRows'] == 2
        (history / 'video_before.json').write_text(json.dumps(before))
        current = normalize(raw, '2026-10-02T12:00:00Z')
        assert current['companyOnlyTargets'] == [{'sourceRow': 3, 'company': 'Research Only Co',
            'status': 'Sent 9/25/26', 'action': 'Ready for video DM', 'score': '13.00',
            'rank': '01', 'tier': ' Warm ', 'stage': 'Seed'}]
        assert current['summary']['sourceRows'] == current['summary']['uniqueProfiles'] == 2
        assert current['summary']['companyOnlyTargetRows'] == 1 and current['summary']['allTargetRows'] == 3
        assert current['summary']['readyRows'] == current['summary']['sheetCompletedRows'] == 1
        assert current['summary']['explicitSendStatusRows'] == current['summary']['followUpRows'] == 1
        assert current['summary']['connectedRows'] == current['summary']['rowsWithDealId'] == 1
        assert current['datedActions'] == [{'date': '2026-09-10', 'contactId': 'ben',
                                          'type': 'Send status', 'sourceRow': 6}]
        assert current['sourceCoverage']['excludedNonProspectPhysicalRows'] == 5
        assert current['rows'] == before['rows'] and current['datedActions'] == before['datedActions']
        for key in ('additionalRowsObserved', 'rowsNoLongerObserved', 'newProfileIdsObserved',
                    'removedProfileIdsObserved', 'statusChangesObserved',
                    'explicitSentDoneStatusChangesObserved', 'derivedActionClassificationChangesObserved'):
            assert current['snapshotDelta'][key] == 0, 'Company-only addition inflated contact history'
        (history / 'video_current.json').write_text(json.dumps(current))
        future = normalize(zero, '2026-10-03T12:00:00Z')
        assert future['companyOnlyTargets'] == []
        assert future['summary']['companyOnlyTargetRows'] == 0 and future['summary']['allTargetRows'] == 2
        assert future['rows'] == current['rows'] and future['datedActions'] == current['datedActions']
        assert future['snapshotDelta']['rowsNoLongerObserved'] == 0
        assert future['snapshotDelta']['removedProfileIdsObserved'] == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    check_fixture()
    if args.snapshot:
        data = json.loads(args.snapshot.read_text())
        check_inventory(data.get('video', data))
    print('Company-only inventory: isolated real-normalizer fixtures passed; contact counts, activities and profile deltas remain separate, including a future zero-target cohort.')


if __name__ == '__main__':
    main()
