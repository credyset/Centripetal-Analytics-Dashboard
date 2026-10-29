"""Public synthetic fixtures for recipient/block/date and retained-clock safety."""
from pathlib import Path
import copy
import json
import tempfile

from normalize_native_refresh_2026_10_28 import (blocks_for, build, guarded_excerpt,
    make_event, resolve_selection_day, selected_block, event_key)

ASSET = 'a' * 32
CONTACT = 'Alice Example'
META = {'profile': 'fixture-alice', 'contact': CONTACT, 'company': 'Fixture company',
    'account': 'Charles Solomon', 'profileIdentityVerified': True,
    'observedAt': '2026-10-29T05:30:00Z', 'selections': []}
ROW = {'id': 'fixture-alice', 'sourceRow': 2, 'company': 'Fixture company', 'contact': CONTACT,
    'linkedin': 'https://www.linkedin.com/in/fixture-alice/', 'recordingAssetId': ASSET,
    'hasRecordingLink': True, 'reportedVideoSentDate': None}
VIDEO = {'snapshotAt': '2026-10-29T05:00:00Z', 'rows': [ROW]}


def fails(callback):
    try:
        callback()
    except (AssertionError, ValueError):
        return
    raise AssertionError('Invalid native evidence was accepted')


def raw(parties='Charles Solomon and Alice Example', label='WEDNESDAY', content=None, compose=False):
    heading = ('heading New message, Value: 2\nbutton Remove Alice Example\ntext Enter message recipients\n'
        if compose else 'button Open the options list in your conversation with ' + parties + '\n')
    return heading + 'content list\ntext ' + label + '\nlink View Charles’ profile Charles Solomon, Value: example\ntext • 12:00 PM\ntext ' + (content or 'A personal video https://www.loom.com/share/' + ASSET) + '\ntext entry area Write a message\n'


def selection(**kwargs):
    return dict({'dateLabel': 'WEDNESDAY', 'time': '12:00 PM', 'direction': 'outbound',
        'date': '2026-10-28', 'kind': 'video', 'asset': ASSET}, **kwargs)


def fixture_before():
    return {'video': dict(copy.deepcopy(VIDEO), messageDateReview={
        'snapshotAt': '2026-10-24T06:00:00Z', 'reviewedAt': '2026-10-24T06:00:00Z',
        'scope': {'videoSnapshotAt': '2026-10-24T05:00:00Z'}, 'summary': {}, 'records': [],
        'platformObservedEvents': [], 'explicitReplyReports': [], 'separateEmailContext': [],
        'nativePlatformCoverage': {'snapshotAt': '2026-10-24T06:00:00Z'}, 'notes': []}),
        'waalaxy': {'sheetSubset': {'rows': []}, 'sheetSubsetCollectedAt': VIDEO['snapshotAt']}}


def main():
    for parties in ('Charles Solomon and Alice Example', 'Alice Example and Charles Solomon'):
        blocks, guard = blocks_for(raw(parties), META)
        event = make_event(META, selection(), selected_block(blocks, selection(), META), ROW, VIDEO)
        assert event['videoIncluded'] is True and event['date'] == '2026-10-28'
        assert event['occurredAt'] is None and event['sourceTimezone'] is None
        assert event['dateTimeAssetAnchoredWithinSameMessageBlock'] is True
    fails(lambda: guarded_excerpt(raw('Charles Solomon and Another Person'), META))
    fails(lambda: guarded_excerpt(raw(), dict(META, profileIdentityVerified=False)))
    compose_meta = dict(META, sourceLayout='existing_history_in_compose_view', recipientControlVerified=True)
    blocks_for(raw(compose=True), compose_meta)
    fails(lambda: blocks_for(raw(compose=True), META))
    fails(lambda: blocks_for(raw(compose=True).replace('content list', 'button Remove Another Person\ncontent list'), compose_meta))
    blocks, _ = blocks_for(raw(), META)
    fails(lambda: selected_block(blocks, selection(time='12:01 PM'), META))
    fails(lambda: selected_block(blocks, selection(asset='b' * 32), META))
    fails(lambda: selected_block(blocks, selection(direction='inbound'), META))
    assert resolve_selection_day('MONDAY','2026-10-26', META)[1] == 'high'
    fails(lambda: resolve_selection_day('MONDAY','2026-10-19', META))
    assert resolve_selection_day('SEP 24','2026-09-24', META)[1] == 'moderate'
    fails(lambda: resolve_selection_day('SEP 24','2025-09-24', META))
    for label, day in [('TODAY','2026-10-29'), ('YESTERDAY','2026-10-28')]:
        # Explicit browser-calendar reference may differ one day from the
        # Mountain observation day, but requires its own stated basis.
        relative_meta = dict(META, sourceReferenceDate='2026-10-29', sourceReferenceDateBasis='Fixture verified browser-calendar date')
        relative_blocks, _ = blocks_for(raw(label=label), relative_meta)
        assert relative_blocks[0]['displayedDateLabel'] == label
        assert resolve_selection_day(label, day, relative_meta)[1] == 'high'
    fails(lambda: resolve_selection_day('TODAY','2026-10-29', dict(META, sourceReferenceDate='2026-10-29')))
    with tempfile.TemporaryDirectory() as temporary:
        private = Path(temporary); native = private / 'native'; native.mkdir()
        meta = dict(META, selections=[selection()])
        (native/'fixture_meta.json').write_text(json.dumps(meta))
        (native/'fixture.txt').write_text(raw())
        before = fixture_before()
        first, _, report = build(before, VIDEO, private=private, require_all=True)
        assert report['newVideoSendEvents'] == 1
        before['video']['messageDateReview'] = first['review']
        event = first['review']['platformObservedEvents'][0]
        old_clock = event['observedAt']; old_key = event_key(event)
        # A later check of the same message is not another send and cannot
        # replace its first curated evidence clock.
        meta['observedAt'] = '2026-10-29T07:00:00Z'
        (native/'fixture_meta.json').write_text(json.dumps(meta))
        repeated, _, repeated_report = build(before, VIDEO, private=private, require_all=True)
        assert repeated_report['newEvents'] == 0 and repeated_report['reobservedPriorEvents'] == 1
        assert repeated['review']['platformObservedEvents'][0]['observedAt'] == old_clock
        assert event_key(repeated['review']['platformObservedEvents'][0]) == old_key
        assert repeated['review']['focusedNativeReviews']['retainedPriorReviews'][0]['profileChecks'][0]['observedAt'] == old_clock
        # Follow-up-only refreshes preserve prior exact video proof.
        before['video']['messageDateReview'] = repeated['review']
        follow = selection(dateLabel='MONDAY', date='2026-10-26', kind='video_follow_up')
        follow.pop('asset')
        meta.update(observedAt='2026-10-29T08:00:00Z', selections=[follow])
        (native/'fixture_meta.json').write_text(json.dumps(meta))
        (native/'fixture.txt').write_text(raw(label='MONDAY', content='What did you think of the video? Private cell 555-000-1234.'))
        final, _, final_report = build(before, VIDEO, private=private, require_all=True)
        assert final_report['newVideoFollowUpEvents'] == 1 and final_report['newVideoSendEvents'] == 0
        record = final['review']['records'][0]
        assert record['platformVideoAttributionEstablished'] is True and record['platformEvidenceCollectedAt'] == old_clock
        assert record['platformFollowUpDate'] == '2026-10-26'
        assert '555-000-1234' not in json.dumps(final) and 'privateContent' not in json.dumps(final)
        assert final['review']['nativePlatformCoverage'] == first['review']['nativePlatformCoverage']
        block = blocks_for(raw(label='MONDAY', content='What did you think of the video?'), meta)[0][0]
        fails(lambda: make_event(meta, dict(follow, replyToVideoAttributionEstablished=True), block, ROW, VIDEO))
    print('Native refresh fixtures: recipient controls, exact blocks, date convention, no raw bodies, follow-up separation and retained clocks passed.')


if __name__ == '__main__':
    main()
