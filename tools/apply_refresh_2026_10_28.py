"""Integrate the reviewed October 28/29 source refresh into a private preview.

Every source keeps its own collection clock and reporting coverage. The approved
dated owner-effort decision is applied in memory only after source integration.
Canonical files change only with the explicit --write-shared switch. That switch
stages all three files and rolls back replacements if a controlled write fails;
it does not claim a multi-file transaction across a process or power failure.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import tempfile

from apply_refresh_2026_10_23 import (SUPPORTED, apply_patches, assert_curated,
    clock, event_key, normalize_message_patch, require_current)
from apply_effort_estimate import validate_effort_decision
from prepare_meeting_refresh_2026_10_28 import apply_owner_preview, OWNER_INCREMENT_ID
from prepare_shared_snapshot import curate_snapshot
from publication_redactions import validate_publication_redactions

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_28'
REPORTING_DATE = '2026-10-29'
COMPLETE_THROUGH = '2026-10-28'
MANIFESTS = ('crm/contribution_manifest.json', 'sheets/integration_manifest.json',
    'meetings/manifest.json', 'ads/manifest_entries.json')
EXTRA_FAMILIES = {'profileAnalytics', 'adsInventory'}
CHILD_FAMILIES = {'video.gapResolutionReview', 'video.sourceFreshnessReview'}


def read(path):
    return json.loads(Path(path).read_text())


def resolve(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def load_value(value):
    return read(resolve(value)) if isinstance(value, str) else deepcopy(value)


def combine_source_cards(groups):
    cards = {}
    for group in groups:
        assert isinstance(group, list), 'Source cards must be a curated list'
        for incoming in group:
            ident = incoming['id']
            assert incoming.get('asOf'), f'Source card has no independent clock: {ident}'
            old = cards.get(ident)
            if old:
                if clock(incoming['asOf']) == clock(old['asOf']):
                    assert incoming == old, f'Conflicting source cards at the same clock: {ident}'
                    continue
                if clock(incoming['asOf']) < clock(old['asOf']):
                    continue
            cards[ident] = deepcopy(incoming)
    return list(cards.values())


def native_child_overrides(children, native_patch, manifest_path):
    """Read native-derived closures only with their explicit message bundle."""
    result = deepcopy(children)
    manifest = read(manifest_path)
    declared = manifest.get('patches', {}).get('videoMessageDateReview')
    assert declared, 'Native manifest does not declare its reviewed message bundle'
    declared_path = manifest_path.parent / declared
    assert read(declared_path) == read(native_patch), 'Native child manifest belongs to a different message bundle'
    for entry in manifest.get('independentChildren', []):
        family = '.'.join(entry['path'])
        assert family in CHILD_FAMILIES, f'Unexpected native child review: {family}'
        incoming = read(manifest_path.parent / entry['file'])
        require_current(incoming, result.get(family), family)
        result[family] = incoming
    return result


def load_manifests(private=PRIVATE, native_patch=None):
    patches, extras, children, card_groups = {}, {}, {}, []
    for relative in MANIFESTS:
        manifest = read(private / relative)
        date = manifest.get('reportingAsOfDate') or manifest.get('reportingAsOfMountain')
        assert date in (None, REPORTING_DATE), f'Unexpected reporting frame in {relative}'
        families = manifest.get('patches', manifest)
        for family, value in families.items():
            assert family in SUPPORTED | EXTRA_FAMILIES, f'Unknown patch family: {family}'
            data = load_value(value)
            if family == 'sourceCards':
                card_groups.append(data)
                continue
            target = extras if family in EXTRA_FAMILIES else patches
            assert family not in target, f'Duplicate independently owned patch family: {family}'
            target[family] = data
        for family, value in manifest.get('independentChildPatches', {}).items():
            assert family in CHILD_FAMILIES and family not in children, f'Unknown or duplicate child review: {family}'
            children[family] = load_value(value)
    patches['sourceCards'] = combine_source_cards(card_groups)
    assert {'crm', 'referrals', 'creator', 'waalaxyAccountAnalytics', 'videoInventory',
        'recordingFieldReview', 'crmReconciliation', 'waalaxySheetSubset',
        'waalaxyInvitations', 'meetings', 'timeMeetings', 'adsLifecycleReview'} <= set(patches)
    assert set(extras) == EXTRA_FAMILIES and set(children) == CHILD_FAMILIES
    native_manifest = private / 'native/integration_manifest.json'
    if native_patch is not None and native_manifest.exists():
        children = native_child_overrides(children, native_patch, native_manifest)
    return patches, extras, children


def ads_source_cards(ads, lifecycle):
    return [{'id': 'ads', 'name': 'LinkedIn Ads · refreshed authenticated exports',
        'asOf': ads['collectedAt'], 'checkedAt': REPORTING_DATE,
        'status': 'Fresh exported totals; daily source rows end October 21',
        'coverage': deepcopy(ads['coverage']),
        'method': 'Authenticated Ad Set and Ad performance exports reconciled independently at both grains',
        'note': 'Report generation and file collection retain separate clocks. The wider requested window contains no exported October 22–29 daily rows; missing dates are unavailable, not measured zero. Individual lead dispositions retain their own evidence dates.'},
        {'id': 'ads_lifecycle', 'name': 'LinkedIn Ads · independent account status review',
        'asOf': lifecycle['snapshotAt'], 'checkedAt': REPORTING_DATE,
        'status': 'Seven selected ad sets Completed; no active selected ad set',
        'coverage': deepcopy(lifecycle['reportingWindow']),
        'method': 'Read-only authenticated account UI status and control totals',
        'note': 'Status observation precedes the later export generation and download. Each source retains its actual clock. No exact conclusion time or missing daily zero is inferred.'}]


def apply_child_reviews(snapshot, before, children):
    video = snapshot['video']
    valid_rows = {(r['sourceRow'], r['id']) for r in video['rows']}
    for family, incoming in children.items():
        parent, child = family.split('.')
        assert parent == 'video' and family in CHILD_FAMILIES
        require_current(incoming, before.get(parent, {}).get(child), family)
        assert incoming.get('reviewedAt') and clock(incoming['reviewedAt']) >= clock(incoming), f'{family} has an invalid review clock'
        scope = incoming.get('appliesToSnapshotAt') or incoming.get('appliesToVideoInventorySnapshotAt')
        assert scope == video['snapshotAt'], f'{family} belongs to a different inventory'
        for record in incoming.get('records', []):
            assert (record['sourceRow'], record['profileId']) in valid_rows, f'{family} has a stale row/profile join'
        video[child] = deepcopy(incoming)


def sync_video_review_cards(snapshot):
    """Describe the selected evidence, independently of parent inventory dates."""
    video = snapshot['video']
    cards = {card['id']: deepcopy(card) for card in snapshot.get('sources', [])}
    review = video.get('messageDateReview') or {}
    if review:
        events = review.get('platformObservedEvents', [])
        sends = [event for event in events if event.get('direction') == 'outbound' and event.get('videoIncluded') is True]
        october = sum(str(event.get('date', '')).startswith('2026-10-') for event in sends)
        september = sum(str(event.get('date', '')).startswith('2026-09-') for event in sends)
        focused = review.get('focusedNativeReviews') or {}
        profiles = focused.get('profilesChecked')
        followups = review.get('summary', {}).get('newObservedVideoFollowUpEventsAdded', 0)
        latest = (f' The latest targeted review covers {profiles} profiles and {followups} newly observed video follow-up texts.'
            if profiles is not None else '')
        card = cards.setdefault('video_message_dates', {'id': 'video_message_dates'})
        card.update(name='Video DM · source dates and observed message proof',
            asOf=review.get('reviewedAt') or review['snapshotAt'], checkedAt=REPORTING_DATE,
            status='Current bounded native observations; all prior proof retains its original clocks',
            coverage=f"{len(events)} separately observed messages; {len(sends)} exact-asset video sends, including {october} in October and {september} historical September sends." + latest + ' Not an account-wide message census.',
            method='Exact recipient/profile, sender and date/time/asset within each selected native message block',
            note='Historical cohorts and individual observations retain their original evidence clocks. Follow-up texts are separate from initial video sends. Day-only labels do not establish exact timestamps, complete reply history or commercial outcomes.')
    freshness = video.get('sourceFreshnessReview') or {}
    if freshness:
        changed = freshness.get('inventoryChanged') is True
        count = freshness.get('changedPhysicalRows', 0)
        card = cards.setdefault('video_source_freshness', {'id': 'video_source_freshness'})
        card.update(name='Video DM · complete source-value freshness review',
            asOf=freshness['snapshotAt'], checkedAt=REPORTING_DATE,
            status='Current full source read; source values changed' if changed else 'Current full source read; source values unchanged',
            coverage=f"{count} changed physical rows ({freshness.get('changedMainPhysicalRows', 0)} main; {freshness.get('changedAcceptedPhysicalRows', 0)} accepted). Complete allocated source ranges were reread.",
            method='Complete source ranges, literal dates/helper fields and dated revision comparisons',
            note=f"Current inventory was collected separately at {video['snapshotAt']}. " + ('Source values changed while the valid company/contact population stayed stable. ' if changed else 'The full reviewed source values match the retained inventory. ') + 'File/revision times and source-field changes do not establish actual messages or row-added timestamps; historical native proof keeps its own dates.')
    gap = video.get('gapResolutionReview') or {}
    if gap:
        closure = gap.get('nativeClosureReview') or {}
        summary = gap.get('summary') or {}
        card = cards.setdefault('video_gap_resolution', {'id': 'video_gap_resolution'})
        if closure:
            profiles = len(closure.get('priorityProfilesWithExactNativeVideoProof', []))
            followups = len(closure.get('nativeFollowUps', []))
            coverage = f'{profiles} priority source sending gaps closed by exact native video proof; {followups} source-reported follow-up dates corroborated by native message-day observations.'
            status = 'Current native sending closures; CRM note and identity gaps remain separate'
            note = 'Source fields, native messages and current CRM records retain separate clocks. Absent CRM notes or unresolved aliases are not closed by a native send; no held call, qualification, accepted opportunity or win is inferred.'
        else:
            coverage = f"{summary.get('newSourceRecordingAssets', 0)} added recording fields, {summary.get('changedSourceVideoDates', 0)} changed video date and {summary.get('newSourceFollowUpDateReports', 0)} added source follow-up date reports."
            status = 'Current source-field review; actual native sending is independently reviewed'
            note = 'Source fields and historical source appearances are separate from native messages, CRM note coverage and owner commercial decisions.'
        card.update(name='Video DM · current source/native/CRM gap review',
            asOf=gap.get('reviewedAt') or gap['snapshotAt'], checkedAt=REPORTING_DATE,
            status=status, coverage=coverage,
            method='Exact current source-profile joins, dated source revisions and separately observed native message proof', note=note)
    snapshot['sources'] = list(cards.values())


def assert_native_retained(before, result, incoming=None):
    old = before.get('video', {}).get('messageDateReview') or {}
    new = result.get('video', {}).get('messageDateReview') or {}
    prior = {event_key(e): e for e in old.get('platformObservedEvents', [])}
    current = {event_key(e): e for e in new.get('platformObservedEvents', [])}
    normalized, _ = normalize_message_patch(incoming)
    reobserved = {event_key(e): e for e in normalized.get('platformObservedEvents', [])}
    assert len(current) == len(new.get('platformObservedEvents', [])), 'Duplicate native event identities'
    assert set(prior) <= set(current), 'Previously observed native messages were lost'
    immutable = ('date', 'occurredAt', 'datePrecision', 'sourceTimezone', 'direction',
        'assetId', 'loomAssetId', 'sourceMessageId', 'profileId', 'videoIncluded')
    for ident, event in prior.items():
        updated = current[ident]
        for field in immutable:
            if field in event:
                assert updated.get(field) == event[field], f'Historical native event fact changed: {field}'
        if updated.get('observedAt') != event.get('observedAt'):
            assert ident in reobserved, 'Fresh inventory cannot re-date an old native observation'
            dates = {row.get('observedAt') for row in updated.get('observationHistory', [])}
            dates.add(updated.get('firstObservedAt'))
            assert event.get('observedAt') in dates, 'Original native observation clock was lost'


def assert_historical_reviews(before, result):
    old = before.get('meetings', {}).get('fireflies') or {}
    new = result.get('meetings', {}).get('fireflies') or {}
    # The earlier 76-ID review and eight incremental records are separately dated
    # evidence. A newer metadata census must not refresh those dialogue clocks.
    for field in ('records', 'reviewedAt'):
        if field in old:
            assert new.get(field) == old[field], f'Original transcript review changed: {field}'
    prior = old.get('incrementalPurposeReview') or {}
    current = new.get('incrementalPurposeReview') or {}
    indexed = {row.get('id', row.get('recordingId')): row for row in current.get('records', [])}
    for row in prior.get('records', []):
        assert indexed.get(row.get('id', row.get('recordingId'))) == row, 'Prior dialogue evidence or clock was overwritten'


def validate_integrated(before, result, decision, native_patch=None):
    assert result['outcomes'] == before['outcomes'], 'Commercial outcome decisions changed'
    assert result.get('meetings', {}).get('ownerConfirmedHeldCalls') == before.get('meetings', {}).get('ownerConfirmedHeldCalls'), 'Owner-confirmed held calls changed'
    assert_native_retained(before, result, native_patch)
    assert_historical_reviews(before, result)
    effort = result['time']
    owner = effort['summary']['ownerEstimateRange']
    assert (owner['low'], owner['high']) == (decision['hoursLow'], decision['hoursHigh']) == (21.75, 23.0)
    assert owner['coversThrough'] == '2026-10-28'
    assert len([row for row in owner['increments'] if row.get('id') == OWNER_INCREMENT_ID]) == 1
    assert effort['summary']['combinedWorkedHours'] is None and effort['trackedHumanMinutes'] is None
    assert effort['meetings']['events'] == before['time']['meetings']['events'], 'No newly associated Christian recording was established in this refresh'
    assert effort['meetings']['summary'] == before['time']['meetings']['summary'], 'Audio proxy cannot become human attendance'
    assert result['meta']['reportingAsOfDate'] == REPORTING_DATE
    assert result['meta']['defaultCompleteReportingThrough'] == COMPLETE_THROUGH
    assert result['meta']['currentDayPartial'] is True
    ads = result['ads']
    assert ads['coverage'].get('syntheticDailyRowsAdded', 0) == 0
    assert not (set(ads['coverage'].get('missingRequestedDates', [])) & {r['date'] for r in ads['daily']}), 'Missing dates were fabricated as daily rows'
    assert_curated(result)
    validate_publication_redactions(result)


def integrate(before, patches, extras, children, decision, native_patch=None, generated_at=None):
    """Pure two-phase integration; never write the canonical owner decision here."""
    validate_effort_decision(decision)
    # Reconcile an input with current canonical policy before base integration.
    # On the first refresh that is the old 18.25–19.5 decision; after publication
    # it is 21.75–23.0. This makes replay safe without changing policy prematurely.
    baseline = curate_snapshot(before)
    assert baseline['outcomes'] == before['outcomes']
    sources = deepcopy(patches)
    inventory = deepcopy(extras.get('adsInventory'))
    if inventory:
        require_current(inventory, baseline.get('ads'), 'authenticated Ads export')
        baseline['ads'] = inventory
        sources['sourceCards'] = combine_source_cards([sources.get('sourceCards', []),
            ads_source_cards(inventory, sources['adsLifecycleReview'])])
    if native_patch is not None:
        assert 'videoMessageDateReview' not in sources, 'Native review supplied twice'
        sources['videoMessageDateReview'] = deepcopy(native_patch)
    result = apply_patches(baseline, sources, reporting_as_of=REPORTING_DATE, generated_at=generated_at)
    profile = extras.get('profileAnalytics')
    if profile:
        existing = result['content']['creatorAnalytics'].get('profileAnalytics')
        require_current(profile, existing, 'Charles personal profile analytics')
        assert profile['account'].get('identityVerified') and profile['account'].get('name') == 'Charles Solomon'
        result['content']['creatorAnalytics']['profileAnalytics'] = deepcopy(profile)
    apply_child_reviews(result, before, children)
    sync_video_review_cards(result)
    result['time'], _ = apply_owner_preview(result['time'], decision)
    revision_time = generated_at or datetime.now(timezone.utc).isoformat()
    result['meta'].update(generatedAt=revision_time, analyticsRevisedAt=revision_time,
        asOfDate=REPORTING_DATE, reportingAsOfDate=REPORTING_DATE,
        defaultReportingThrough=REPORTING_DATE, defaultCompleteReportingThrough=COMPLETE_THROUGH,
        currentDayPartial=True, localReviewOn=REPORTING_DATE,
        publicationReview='REFRESH_2026-10-29.md', revision='October 29 independent live-source refresh',
        lastRevisionNote='Current source inventories, personal creator/profile analytics and separately dated native evidence retain their actual clocks. October 29 is partial. Commercial outcomes remain owner-reviewed. Christian confirmed one additional 3.5-hour non-meeting increment for October 23–28, bringing the estimate to 21.75–23.0 hours through October 28; associated audio remains separate.')
    result = curate_snapshot(result, effort_decision=decision)
    validate_integrated(before, result, decision, native_patch)
    return result


def serialized(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def replace_group(payloads, replace=os.replace):
    """Stage same-filesystem files; restore originals on a controlled failure."""
    staged, originals, changed = {}, {}, []
    try:
        for target, contents in payloads.items():
            target = Path(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            originals[target] = target.read_bytes() if target.exists() else None
            fd, temporary = tempfile.mkstemp(prefix='.' + target.name + '.', dir=target.parent)
            staged[target] = Path(temporary)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(contents)
                stream.flush()
                os.fsync(stream.fileno())
        for target, temporary in staged.items():
            replace(temporary, target)
            changed.append(target)
    except BaseException:
        for target in reversed(changed):
            previous = originals[target]
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                fd, temporary = tempfile.mkstemp(prefix='.' + target.name + '.rollback.', dir=target.parent)
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(previous)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def write_reviewed_group(result, decision, expected_snapshot=None, expected_decision=None):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    lock = PRIVATE / 'canonical-write.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(fd, f'{os.getpid()}\n'.encode())
        if expected_snapshot is not None:
            assert read(ROOT / 'data/shared-dashboard.json') == expected_snapshot, 'Canonical shared data changed during review; integrate the newer revision first'
        if expected_decision is not None:
            assert read(ROOT / 'EFFORT_ESTIMATE.json') == expected_decision, 'Canonical owner decision changed during review; reconcile it before writing'
        replace_group({ROOT / 'EFFORT_ESTIMATE.json': serialized(decision),
            ROOT / 'data/dashboard.json': serialized(result),
            ROOT / 'data/shared-dashboard.json': serialized(result)})
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', type=Path, default=PRIVATE)
    parser.add_argument('--input', type=Path, default=ROOT / 'data/shared-dashboard.json')
    parser.add_argument('--output', type=Path, default=PRIVATE / 'integrated_dashboard_preview.json')
    parser.add_argument('--effort-decision', type=Path, default=PRIVATE / 'meetings/owner_effort_decision_patch.json')
    parser.add_argument('--native-patch', type=Path, help='Optional reviewed complete native-message bundle; raw bodies are rejected')
    parser.add_argument('--write-shared', action='store_true', help='Explicitly replace the reviewed canonical effort decision and both dashboard snapshots')
    args = parser.parse_args()
    protected = {ROOT / 'EFFORT_ESTIMATE.json', ROOT / 'data/dashboard.json', ROOT / 'data/shared-dashboard.json'}
    assert args.output.resolve() not in {path.resolve() for path in protected}, 'The preview output must not target a canonical file; use --write-shared for reviewed publication'
    canonical_before = read(ROOT / 'data/shared-dashboard.json')
    policy_before = read(ROOT / 'EFFORT_ESTIMATE.json')
    patches, extras, children = load_manifests(args.private_root, native_patch=args.native_patch)
    before, decision = read(args.input), read(args.effort_decision)
    native = read(args.native_patch) if args.native_patch else None
    result = integrate(before, patches, extras, children, decision, native)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(serialized(result))
    if args.write_shared:
        write_reviewed_group(result, decision, expected_snapshot=canonical_before, expected_decision=policy_before)
    print(json.dumps({'privatePreview': str(args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output),
        'canonicalFilesWritten': args.write_shared, 'commercialOutcomesUnchanged': True,
        'reportingAsOfDate': REPORTING_DATE, 'completeDaysThrough': COMPLETE_THROUGH,
        'ownerNonMeetingEstimate': [decision['hoursLow'], decision['hoursHigh']],
        'ownerEstimateCoversThrough': decision['coversThrough'],
        'videoRows': len(result['video']['rows']),
        'nativeObservedEvents': len(result['video'].get('messageDateReview', {}).get('platformObservedEvents', [])),
        'sourceCards': len(result['sources'])}))


if __name__ == '__main__':
    main()
