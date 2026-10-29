"""Integrate bounded October 29 accuracy corrections into a private preview.

Source inventories, event identities/dates, owner outcomes and effort are locked.
Only explicit keyed date/Seen corrections and independently dated audit children
are accepted. Canonical snapshots change only with --write-shared.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

from apply_crm_alias_review_2026_10_29 import apply_alias
from apply_refresh_2026_10_23 import assert_curated, clock, event_key
from apply_refresh_2026_10_28 import replace_group, serialized
from prepare_shared_snapshot import curate_snapshot
from publication_redactions import validate_publication_redactions

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT/'data/private/accuracy_audit_2026_10_29'
SHEETS = ROOT/'data/private/published_gap_audit_2026_10_29/sheets'
CONFIDENCE = ROOT/'data/private/confidence_audit_2026_10_29'
CONNECTION_FIELDS = {'connectedAt', 'connectedAtDatePrecision', 'connectedAtSourceTimezone', 'connectedAtEvidenceBasis'}
RECEIPT_FIELDS = {'platformReadReceiptObserved', 'readReceiptDate', 'readReceiptBasis',
    'readReceiptSourceObservedAt', 'readReceiptValidatedAt', 'readReceiptAppliesTo', 'loomVideoViewedEstablished'}
REPLACEMENTS = {('video', 'connectionDiagnostics'), ('waalaxy', 'selectedExportSnapshot'), ('video', 'sourceFieldAuditReview')}
AUDIT_CARDS = {'video_connection_dates', 'waalaxy_snapshot_overlap', 'video_crm_alias', 'video_native_seen', 'ads_zero_delivery'}


def read(path):
    return json.loads(Path(path).read_text())


def manifest_file(parent, name):
    result = (parent/name).resolve()
    assert result.is_relative_to(parent.resolve()), 'Manifest file must stay within its source directory'
    return read(result)


def load_bundle(manifest_path, alias_path, ads_path, card_path):
    manifest_path = Path(manifest_path)
    manifest = read(manifest_path)
    field = manifest['fieldCorrections']
    assert field['target'] == ['video', 'rows'] and field['joinKeys'] == ['sourceRow', 'id=profileId']
    assert field['mergeFieldsOnly'] is True and field['expectedPriorConnectedAt'] is None
    replacements = {}
    for entry in manifest['replacements']:
        key = tuple(entry['path'])
        assert key in REPLACEMENTS and key not in replacements, 'Unknown/duplicate replacement path'
        replacements[key] = manifest_file(manifest_path.parent, entry['file'])
    assert set(replacements) == REPLACEMENTS
    native = manifest.get('existingNativeEventCorrections')
    if native:
        assert native['target'] == ['video', 'messageDateReview', 'platformObservedEvents']
        assert native['joinKeys'] == ['observationId', 'eventKey', 'profileId', 'date', 'contentFingerprint']
        assert native['mergeFieldsOnly'] is True and native['expectedPriorPlatformReadReceiptObserved'] is False
    return {'manifest': manifest, 'connections': manifest_file(manifest_path.parent, field['file']),
        'replacements': replacements, 'seen': manifest_file(manifest_path.parent, native['file']) if native else None,
        'alias': read(alias_path), 'ads': read(ads_path), 'adsCard': read(card_path)}


def apply_connection_fields(result, bundle):
    video = result['video'];patch = bundle['connections']
    assert bundle['manifest']['appliesToVideoInventorySnapshotAt'] == patch['appliesToVideoInventorySnapshotAt'] == video['snapshotAt']
    assert patch['sourceValueCollectionClockPreserved'] is True
    rows = {(r['sourceRow'], r['id']): r for r in video['rows']}
    assert len(rows) == len(video['rows'])
    seen = set()
    for change in patch['changes']:
        key = (change['sourceRow'], change['profileId'])
        assert key in rows and key not in seen, 'Duplicate or stale connection row/profile'
        seen.add(key);row = rows[key];fields = change['fields']
        assert set(fields) == CONNECTION_FIELDS and change['previousConnectedAt'] is None
        date.fromisoformat(fields['connectedAt'])
        assert fields['connectedAtDatePrecision'] == 'day' and fields['connectedAtSourceTimezone'] is None
        assert fields['connectedAtEvidenceBasis'] and row['connected'] is True
        assert row.get('connectedAt') in (None, fields['connectedAt']), 'Conflicting existing connection date'
        if row.get('connectedAt') is not None:
            assert all(row.get(k) == v for k, v in fields.items()), 'Replay differs from the earlier correction'
        row.update(deepcopy(fields))
    audit = bundle['replacements'][('video', 'sourceFieldAuditReview')]
    assert audit['appliesToVideoInventorySnapshotAt'] == video['snapshotAt']
    assert audit['sourceCollectionClockPreserved'] is True
    proof = {(r['sourceRow'], r['profileId']): r for r in audit['records']}
    assert len(proof) == len(audit['records']) == audit['connectionDateRowsRecovered'] == len(seen)
    assert set(proof) == seen
    for key, record in proof.items():
        assert record['exactAcceptedProfileDateMatch'] is True and record['date'] == rows[key]['connectedAt']
    for (section, key), incoming in bundle['replacements'].items():
        old = result[section].get(key)
        if key == 'selectedExportSnapshot':
            # Only the overlap comparison and its historical archive are new.
            for field in set(old) | set(incoming):
                if field not in {'overlapWithSheet', 'retainedPriorOverlapReviews'}:
                    assert old.get(field) == incoming.get(field), 'Overlap review rewrote older selected-person source'
            overlap = incoming['overlapWithSheet']
            assert overlap['appliesToSheetSnapshotAt'] == video['snapshotAt']
            assert overlap['exportParentReviewedAt'] == old['reviewedAt']
            assert overlap['exportSourceObservationThrough'] == old['sourceObservationThrough']
            assert overlap['newSourceDataCollected'] is False and overlap['actualMessageEventsAdded'] == 0
            assert overlap['sameProfiles']+overlap['onlyInExports'] == overlap['exportUniqueProfiles']
            assert overlap['sameProfiles']+overlap['onlyInSheet'] == overlap['sheetUniqueProfiles']
            assert clock(overlap['reviewedAt']) >= clock((old.get('overlapWithSheet') or {}).get('reviewedAt'))
        elif key == 'sourceFieldAuditReview' and old:
            assert clock(incoming['reviewedAt']) >= clock(old.get('reviewedAt'))
            if old.get('nativeSeenMarkerReview'):
                assert incoming.get('nativeSeenMarkerReview'), 'Later independent Seen review would be lost'
                assert clock(incoming['nativeSeenMarkerReview']['reviewedAt']) >= clock(old['nativeSeenMarkerReview']['reviewedAt'])
        result[section][key] = deepcopy(incoming)


def apply_seen_fields(result, patch):
    if patch is None:
        return
    events = result['video']['messageDateReview']['platformObservedEvents']
    indexed = {e['observationId']: e for e in events}
    assert len(indexed) == len(events), 'Duplicate native observation IDs'
    changed = set()
    for change in patch['changes']:
        ident = change['observationId']
        assert ident in indexed and ident not in changed, 'Unknown or repeated Seen-event key'
        changed.add(ident);event = indexed[ident];fields = change['fields']
        assert event_key(event) == change['eventKey']
        assert event['profileId'] == change['profileId'] and event['date'] == change['date']
        assert event['contentFingerprint'] == change['contentFingerprint']
        assert event['observedAt'] == change['originalObservedAt']
        assert event['direction'] == 'outbound', 'Own-message Seen evidence cannot be borrowed from an inbound block'
        assert set(fields) == RECEIPT_FIELDS
        assert fields['platformReadReceiptObserved'] is True and fields['readReceiptDate'] is None
        assert fields['readReceiptSourceObservedAt'] == event['observedAt']
        assert fields['readReceiptValidatedAt'] == patch['reviewedAt']
        assert clock(fields['readReceiptValidatedAt']) >= clock(event['observedAt'])
        assert fields['readReceiptAppliesTo'] == 'linkedin_message_only' and fields['loomVideoViewedEstablished'] is False
        assert isinstance(fields['readReceiptBasis'], str) and fields['readReceiptBasis']
        assert event.get('readReceiptDate') is None
        if event.get('platformReadReceiptObserved') is True:
            assert all(event.get(k) == v for k, v in fields.items()), 'Seen replay conflicts with existing evidence'
        else:
            assert event.get('platformReadReceiptObserved') is False
        event.update(deepcopy(fields))
    child = result['video']['sourceFieldAuditReview']['nativeSeenMarkerReview']
    assert child['appliesToVideoInventorySnapshotAt'] == result['video']['snapshotAt']
    assert child['observedMarkerCorrections'] == len(changed) == len(child['records'])
    assert {r['messageObservationId'] for r in child['records']} == changed
    assert all(child[k] == 0 for k in ['readReceiptDatesAdded', 'videoPlayEventsAdded', 'nativeMessageEventsAdded', 'replyEventsAdded', 'commercialOutcomesAdded'])


def apply_ads_review(result, review, card):
    ads = result['ads'];scope = review['scope'];coverage = review['coverage']
    assert review['reviewKind'] == 'authenticated_ui_aggregate_zero' and review['identityVerified'] is True
    assert review['accountId'] == ads['lifecycleReview']['accountId'] == '515259390'
    expected = set(ads['review']['sourceScope']['exportedAdSetIds']) | set(ads['review']['sourceScope']['uiOnlyZeroDeliveryAdSetIds'])
    assert set(scope['adSetIds']) == expected and len(scope['adSetIds']) == len(expected) == scope['adSetsReviewed']
    assert scope['matchesRetainedAdSetScope'] is True and scope['accountWideCompleteCampaignCoverage'] is False
    assert scope['viewFilterCleared'] is True and scope['allVisibleCurrentAdSetsVerified'] is True
    assert scope['unfilteredAdSetCount'] == 7 and scope['parentCampaignCountIsSeparateGrain'] is True
    assert review['sourceDailyRowsAdded'] == 0
    assert set(review['metrics']) == {'spend', 'impressions', 'clicks', 'rawLeads'}
    assert all(v == 0 and not isinstance(v, bool) for v in review['metrics'].values())
    assert coverage['sourceTimezone'] == 'UTC' and coverage['finalDayPartial'] is True
    assert (coverage['start'], coverage['end'], coverage['completeDaysThrough']) == ('2026-10-22', '2026-10-29', '2026-10-28')
    assert clock(review['reviewedAt']) >= clock(review['snapshotAt']) >= clock(ads.get('zeroDeliveryReview'))
    assert card['id'] == 'ads_zero_delivery' and card['asOf'] == review['snapshotAt'] and card['coverage'] == coverage
    ads['zeroDeliveryReview'] = deepcopy(review)


def audit_cards(result, bundle):
    video = result['video'];proof = bundle['alias'];audit = video['sourceFieldAuditReview']
    overlap = result['waalaxy']['selectedExportSnapshot']['overlapWithSheet']
    cards = {c['id']: deepcopy(c) for c in result['sources']}
    cards['video_connection_dates'] = {'id': 'video_connection_dates', 'name': 'Video DM · connection-date normalization audit',
        'asOf': video['snapshotAt'], 'reviewedAt': audit['reviewedAt'], 'status': 'Explicit retained source dates recovered; no new acceptance events',
        'coverage': f"{audit['connectionDateRowsRecovered']} keyed Connected At attributes corroborated to accepted profiles; source inventory clock preserved.",
        'note': 'Date-only source attributes have unknown event timezone. Normalization does not establish when an invitation was accepted.'}
    cards['waalaxy_snapshot_overlap'] = {'id': 'waalaxy_snapshot_overlap', 'name': 'Waalaxy · independently dated snapshot overlap',
        'asOf': video['snapshotAt'], 'reviewedAt': overlap['reviewedAt'], 'status': 'Current worksheet compared with retained selected-person exports',
        'coverage': deepcopy(overlap), 'note': 'The older CSV retains its source date and sender limitations. These overlapping populations are never summed.'}
    cards['video_crm_alias'] = {'id': 'video_crm_alias', 'name': 'Video DM · verified canonical CRM/profile alias',
        'asOf': proof['snapshotAt'], 'reviewedAt': proof['snapshotAt'], 'status': 'Apaluma identity resolved; source asset-note gap remains',
        'coverage': {'videoInventorySnapshotAt': video['snapshotAt'], 'crmInventorySnapshotAt': result['crm']['snapshotAt'], 'company': proof['company'], 'crmDealId': proof['crmDealId']},
        'note': 'Independently observed native redirect resolves identity only. Original CRM URL, worksheet ID, inventory and native proof clocks remain unchanged.'}
    seen = bundle.get('seen')
    if seen:
        cards['video_native_seen'] = {'id': 'video_native_seen', 'name': 'Video DM · undated Seen marker review',
            'asOf': max(c['originalObservedAt'] for c in seen['changes']), 'reviewedAt': seen['reviewedAt'],
            'status': 'Own-message markers verified; no receipt dates or video views inferred',
            'coverage': f"{len(seen['changes'])} existing exact native message blocks; no new message, reply or commercial event.",
            'note': 'Each marker keeps its original source capture and separate validation clock; it applies to the LinkedIn message, not proof a video was played.'}
    cards['ads_zero_delivery'] = deepcopy(bundle['adsCard'])
    cards['ads_zero_delivery']['reviewedAt'] = bundle['ads']['reviewedAt']
    result['sources'] = list(cards.values())


def validate_result(before, result, bundle):
    for name in ['crm', 'referrals', 'outcomes', 'time', 'content', 'meetings']:
        assert result[name] == before[name], f'Accuracy corrections altered protected {name}'
    owner = result['time']['summary']['ownerEstimateRange']
    assert (owner['low'], owner['high'], owner['coversThrough']) == (21.75, 23.0, '2026-10-28')
    for key in before['ads']:
        if key != 'zeroDeliveryReview':
            assert result['ads'][key] == before['ads'][key], f'Ads review altered older source {key}'
    for key in before['waalaxy']:
        if key != 'selectedExportSnapshot':
            assert result['waalaxy'][key] == before['waalaxy'][key], f'Waalaxy overlap altered {key}'
    original_rows = {(r['sourceRow'], r['id']): r for r in before['video']['rows']}
    revised_rows = {(r['sourceRow'], r['id']): r for r in result['video']['rows']}
    assert set(original_rows) == set(revised_rows)
    for key, old in original_rows.items():
        new = revised_rows[key]
        assert {k:v for k,v in new.items() if k not in CONNECTION_FIELDS} == {k:v for k,v in old.items() if k not in CONNECTION_FIELDS}
    old_review = before['video']['messageDateReview'];new_review = result['video']['messageDateReview']
    assert {k:v for k,v in old_review.items() if k != 'platformObservedEvents'} == {k:v for k,v in new_review.items() if k != 'platformObservedEvents'}
    old_events = old_review['platformObservedEvents'];new_events = new_review['platformObservedEvents']
    assert len(old_events) == len(new_events) == 60
    for old, new in zip(old_events, new_events):
        assert {k:v for k,v in old.items() if k not in RECEIPT_FIELDS} == {k:v for k,v in new.items() if k not in RECEIPT_FIELDS}, 'Native event identity/date/source clock changed'
    for key in before['video']:
        if key not in {'rows', 'connectionDiagnostics', 'sourceFieldAuditReview', 'crmReconciliation', 'gapResolutionReview', 'messageDateReview'}:
            assert result['video'][key] == before['video'][key], f'Video audit altered {key}'
    assert result['video']['crmReconciliation']['snapshotAt'] == before['video']['crmReconciliation']['snapshotAt']
    assert result['video']['crmReconciliation']['crmInventorySnapshotAt'] == before['video']['crmReconciliation']['crmInventorySnapshotAt']
    assert result['meta']['reportingAsOfDate'] == '2026-10-29' and result['meta']['defaultCompleteReportingThrough'] == '2026-10-28'
    assert result['meta']['currentDayPartial'] is True
    assert {c['id']:c for c in result['sources'] if c['id'] not in AUDIT_CARDS} == {c['id']:c for c in before['sources'] if c['id'] not in AUDIT_CARDS}, 'Audit relabelled another source card or clock'
    assert_curated(result);validate_publication_redactions(result)


def integrate(before, bundle, reviewed_at=None):
    result = apply_alias(before, bundle['alias'])
    apply_connection_fields(result, bundle)
    apply_seen_fields(result, bundle.get('seen'))
    apply_ads_review(result, bundle['ads'], bundle['adsCard'])
    # Current wording can change only with its own independently dated proof;
    # earlier source findings and native sending evidence are not rewritten.
    gap = next(r for r in result['video']['gapResolutionReview']['records'] if r['profileId'] == bundle['alias']['profileId'])
    gap['crmDealId'] = bundle['alias']['crmDealId']
    gap['status'] = 'Exact native video and current CRM identity verified; source asset-note gap remains'
    gap['identityAliasReview'] = deepcopy(bundle['alias'])
    finding = 'Later independent native-profile redirect resolves this source/CRM identity alias; the original CRM URL and worksheet ID are retained. The source asset remains absent from current scoped CRM notes.'
    if finding not in gap['findings']:
        gap['findings'].append(finding)
    audit_cards(result, bundle)
    reviewed_at = reviewed_at or datetime.now(timezone.utc).isoformat()
    assert clock(reviewed_at) >= max(clock(bundle['ads']['reviewedAt']), clock(bundle['alias']['snapshotAt']), clock(bundle['connections']['reviewedAt']), clock((bundle.get('seen') or {}).get('reviewedAt')))
    assert clock(reviewed_at) >= clock(before['meta'].get('accuracyAuditReviewedAt')), 'Accuracy review clock cannot move backwards'
    result['meta'].update(generatedAt=reviewed_at, analyticsRevisedAt=reviewed_at, accuracyAuditReviewedAt=reviewed_at,
        publicationReview='ACCURACY_REVIEW_2026-10-29.md', revision='October 29 published-dashboard accuracy review',
        lastRevisionNote='Bounded Ads aggregate zero, retained connection-date normalization, corrected snapshot overlap, canonical CRM alias and own-message Seen markers have independent evidence clocks. Inventory, native message dates/IDs, commercial owner decisions and Christian’s 21.75–23.0-hour estimate through October28 remain unchanged; October29 is partial.')
    result = curate_snapshot(result)
    validate_result(before, result, bundle)
    return result


def write_shared(result, expected_snapshot, expected_effort):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    lock = PRIVATE/'canonical-write.lock';fd = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
    try:
        assert read(ROOT/'data/shared-dashboard.json') == expected_snapshot, 'Canonical data changed; integrate the newer input'
        assert read(ROOT/'EFFORT_ESTIMATE.json') == expected_effort, 'Owner effort policy changed during review'
        replace_group({ROOT/'data/dashboard.json': serialized(result), ROOT/'data/shared-dashboard.json': serialized(result)})
    finally:
        os.close(fd);lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'data/shared-dashboard.json')
    parser.add_argument('--output', type=Path, default=PRIVATE/'integrated_accuracy_preview.json')
    parser.add_argument('--manifest', type=Path, default=SHEETS/'integration_manifest.json')
    parser.add_argument('--alias-proof', type=Path, default=PRIVATE/'crm/apaluma_alias_public_proof.json')
    parser.add_argument('--ads-review', type=Path, default=CONFIDENCE/'ads_zero_delivery_review_patch.json')
    parser.add_argument('--ads-card', type=Path, default=CONFIDENCE/'ads_zero_delivery_source_card.json')
    parser.add_argument('--write-shared', action='store_true', help='Explicitly replace both canonical snapshots after private validation; owner policy is never written')
    args = parser.parse_args()
    assert args.output.resolve().is_relative_to((ROOT/'data/private').resolve()), 'Preview must stay private'
    canonical, effort = read(ROOT/'data/shared-dashboard.json'), read(ROOT/'EFFORT_ESTIMATE.json')
    before = read(args.input);bundle = load_bundle(args.manifest, args.alias_proof, args.ads_review, args.ads_card)
    if args.write_shared:
        assert before == canonical, 'Canonical publication must start from the current shared input'
    result = integrate(before, bundle)
    args.output.parent.mkdir(parents=True, exist_ok=True);args.output.write_bytes(serialized(result))
    for checker in ['check_shared_snapshot.py', 'check_video_reconciliation.py', 'check_independent_channels.py']:
        subprocess.run([sys.executable, str(ROOT/'tools'/checker), '--snapshot', str(args.output)], check=True)
    if args.write_shared:
        write_shared(result, canonical, effort)
    print(json.dumps({'privatePreview': str(args.output), 'canonicalFilesWritten': args.write_shared,
        'connectionDateCorrections': len(bundle['connections']['changes']), 'seenMarkerCorrections': len((bundle.get('seen') or {}).get('changes', [])),
        'nativeEvents': len(result['video']['messageDateReview']['platformObservedEvents']), 'ownerHours': [21.75,23.0],
        'sourceClocksAndCommercialDecisionsPreserved': True}))


if __name__ == '__main__':
    main()
