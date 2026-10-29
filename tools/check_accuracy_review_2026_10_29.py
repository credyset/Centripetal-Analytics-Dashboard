"""Regression fixtures for keyed accuracy changes and independent evidence clocks.

Uses only the tracked snapshot, never ignored source exports or credentials.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import tempfile

from apply_accuracy_review_2026_10_29 import (CONNECTION_FIELDS, integrate, load_bundle)
from apply_refresh_2026_10_23 import event_key

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--snapshot', type=Path, default=ROOT/'data/shared-dashboard.json')
args = parser.parse_args()


def fixture():
    before = json.loads(args.snapshot.read_text())
    # The synthetic one-row audit starts before its own corrections, even when
    # the tracked snapshot already contains the complete published audit.
    before['video'].pop('sourceFieldAuditReview', None)
    row = next(r for r in before['video']['rows'] if r['id'] == 'mac-dougherty')
    row['connectedAt'] = None
    for key in CONNECTION_FIELDS-{'connectedAt'}:
        row.pop(key, None)
    event = next(e for e in before['video']['messageDateReview']['platformObservedEvents'] if e['profileId'] == 'aliciajkeyes505' and e['direction'] == 'outbound' and e['videoIncluded'] is True)
    event['platformReadReceiptObserved'] = False;event['readReceiptDate'] = None
    for key in ['readReceiptBasis', 'readReceiptSourceObservedAt', 'readReceiptValidatedAt', 'readReceiptAppliesTo', 'loomVideoViewedEstablished']:
        event.pop(key, None)
    later = datetime.fromisoformat(before['meta']['generatedAt'].replace('Z','+00:00'))+timedelta(minutes=5)
    stamp = later.isoformat();generated = (later+timedelta(minutes=1)).isoformat()
    alias = {'snapshotAt': stamp, 'method': 'authenticated_native_profile_redirect', 'redirectObserved': True,
        'identityVerified': True, 'sourceSystemWrites': 0, 'sourceInventorySnapshotAt': before['video']['snapshotAt'],
        'crmInventorySnapshotAt': before['crm']['snapshotAt'], 'sourceRow': 140, 'profileId': 'aliciajkeyes505',
        'contact': 'Alicia J. Keyes', 'company': 'Apaluma', 'crmDealId': 411, 'crmPersonId': 605, 'crmOrganizationId': 536,
        'retainedCrmProfileUrl': 'https://www.linkedin.com/in/alicia-j-keyes-59722197/',
        'canonicalProfileUrl': 'https://www.linkedin.com/in/aliciajkeyes505/',
        'noteScopeReview': {'scopes': ['deal','person','organization'], 'completeReturnedPagination': True,
            'sourceAssetId': event['assetId'], 'sourceAssetMatches': [], 'distinctNoteIds': [1325,1354], 'collectedAt': stamp}}
    fields = {'connectedAt': '2025-01-30', 'connectedAtDatePrecision': 'day', 'connectedAtSourceTimezone': None,
        'connectedAtEvidenceBasis': 'Explicit source serial date corroborated to the exact accepted profile; not an acceptance event.'}
    connections = {'appliesToVideoInventorySnapshotAt': before['video']['snapshotAt'], 'reviewedAt': stamp,
        'sourceValueCollectionClockPreserved': True, 'changes': [{'sourceRow': row['sourceRow'], 'profileId': row['id'], 'previousConnectedAt': None, 'fields': fields}]}
    corrections = {'reviewedAt': stamp, 'changes': [{'observationId': event['observationId'], 'eventKey': event_key(event),
        'profileId': event['profileId'], 'date': event['date'], 'originalObservedAt': event['observedAt'], 'contentFingerprint': event['contentFingerprint'],
        'fields': {'platformReadReceiptObserved': True, 'readReceiptDate': None, 'readReceiptBasis': 'Own exact selected outbound message has an undated Seen marker.',
            'readReceiptSourceObservedAt': event['observedAt'], 'readReceiptValidatedAt': stamp,
            'readReceiptAppliesTo': 'linkedin_message_only', 'loomVideoViewedEstablished': False}}]}
    audit = {'snapshotAt': stamp, 'reviewedAt': stamp, 'appliesToVideoInventorySnapshotAt': before['video']['snapshotAt'],
        'sourceCollectionClockPreserved': True, 'connectionDateRowsRecovered': 1,
        'records': [{'sourceRow': row['sourceRow'], 'profileId': row['id'], 'date': fields['connectedAt'], 'exactAcceptedProfileDateMatch': True}],
        'nativeSeenMarkerReview': {'snapshotAt': stamp, 'reviewedAt': stamp, 'appliesToVideoInventorySnapshotAt': before['video']['snapshotAt'],
            'observedMarkerCorrections': 1, 'records': [{'messageObservationId': event['observationId']}],
            'readReceiptDatesAdded': 0, 'videoPlayEventsAdded': 0, 'nativeMessageEventsAdded': 0, 'replyEventsAdded': 0, 'commercialOutcomesAdded': 0}}
    selected = deepcopy(before['waalaxy']['selectedExportSnapshot'])
    selected['overlapWithSheet'] = {'sameProfiles': 167, 'onlyInExports': 39, 'onlyInSheet': 6,
        'reviewedAt': stamp, 'appliesToSheetSnapshotAt': before['video']['snapshotAt'],
        'exportParentReviewedAt': selected['reviewedAt'], 'exportSourceObservationThrough': selected['sourceObservationThrough'],
        'exportUniqueProfiles': 206, 'sheetUniqueProfiles': 173, 'newSourceDataCollected': False, 'actualMessageEventsAdded': 0}
    ids = before['ads']['review']['sourceScope']
    ads = {'snapshotAt': stamp, 'reviewedAt': stamp, 'accountId': '515259390', 'identityVerified': True,
        'reviewKind': 'authenticated_ui_aggregate_zero', 'coverage': {'start': '2026-10-22', 'end': '2026-10-29',
            'sourceTimezone': 'UTC', 'finalDayPartial': True, 'completeDaysThrough': '2026-10-28'},
        'metrics': {'spend': 0, 'impressions': 0, 'clicks': 0, 'rawLeads': 0}, 'sourceDailyRowsAdded': 0,
        'scope': {'adSetIds': ids['exportedAdSetIds']+ids['uiOnlyZeroDeliveryAdSetIds'], 'adSetsReviewed': 7,
            'matchesRetainedAdSetScope': True, 'accountWideCompleteCampaignCoverage': False, 'viewFilterCleared': True,
            'allVisibleCurrentAdSetsVerified': True, 'unfilteredAdSetCount': 7, 'parentCampaignCountIsSeparateGrain': True}}
    card = {'id': 'ads_zero_delivery', 'asOf': stamp, 'coverage': deepcopy(ads['coverage'])}
    bundle = {'manifest': {'appliesToVideoInventorySnapshotAt': before['video']['snapshotAt']}, 'connections': connections,
        'replacements': {('video','connectionDiagnostics'): deepcopy(before['video']['connectionDiagnostics']),
            ('waalaxy','selectedExportSnapshot'): selected, ('video','sourceFieldAuditReview'): audit},
        'seen': corrections, 'alias': alias, 'ads': ads, 'adsCard': card}
    return before, bundle, generated


before, bundle, generated = fixture()
original = deepcopy(before)
after = integrate(before, bundle, reviewed_at=generated)
assert before == original, 'Integration mutated caller input'
assert integrate(after, bundle, reviewed_at=generated) == after, 'Replaying corrections changed counts/history or duplicated proof'
assert after['video']['snapshotAt'] == before['video']['snapshotAt']
assert after['video']['crmReconciliation']['snapshotAt'] == before['video']['crmReconciliation']['snapshotAt']
assert after['crm'] == before['crm'] and after['outcomes'] == before['outcomes'] and after['time'] == before['time']
assert after['ads']['daily'] == before['ads']['daily'] and after['ads']['coverage'] == before['ads']['coverage']
assert after['waalaxy']['selectedExportSnapshot']['reviewedAt'] == before['waalaxy']['selectedExportSnapshot']['reviewedAt']
old_events = before['video']['messageDateReview']['platformObservedEvents'];new_events = after['video']['messageDateReview']['platformObservedEvents']
assert len(new_events) == len(old_events) == 60
assert [event_key(e) for e in new_events] == [event_key(e) for e in old_events]
assert [(e['date'],e['observedAt']) for e in new_events] == [(e['date'],e['observedAt']) for e in old_events]
seen_id = bundle['seen']['changes'][0]['observationId']
seen_event = next(e for e in new_events if e['observationId'] == seen_id)
assert seen_event['platformReadReceiptObserved'] is True and seen_event['readReceiptDate'] is None
assert seen_event['loomVideoViewedEstablished'] is False
assert next(c for c in after['sources'] if c['id']=='video_connection_dates')['asOf'] == before['video']['snapshotAt']
assert next(c for c in after['sources'] if c['id']=='ads_zero_delivery')['asOf'] == bundle['ads']['snapshotAt']

# Optional old manifests without Seen corrections preserve every native field.
without_seen = deepcopy(bundle);without_seen['seen'] = None
without_seen['replacements'][('video','sourceFieldAuditReview')].pop('nativeSeenMarkerReview')
optional = integrate(before, without_seen, reviewed_at=generated)
assert optional['video']['messageDateReview'] == before['video']['messageDateReview']

# Each mismatch must fail closed before it can shift proof to another row,
# date, account, message block, whole inventory clock, or business outcome.
for mutate in [
    lambda b: b['connections'].update(appliesToVideoInventorySnapshotAt='2000-01-01T00:00:00Z'),
    lambda b: b['connections']['changes'][0].update(sourceRow=-1),
    lambda b: b['connections']['changes'][0].update(profileId='wrong-profile'),
    lambda b: b['connections']['changes'].append(deepcopy(b['connections']['changes'][0])),
    lambda b: b['connections']['changes'][0]['fields'].update(reportedVideoSentDate='2026-10-29'),
    lambda b: b['seen']['changes'][0].update(contentFingerprint='wrong-message'),
    lambda b: b['seen']['changes'][0].update(eventKey='wrong-key'),
    lambda b: b['seen']['changes'][0].update(date='2026-10-27'),
    lambda b: b['seen']['changes'][0].update(originalObservedAt='2026-10-29T00:00:00Z'),
    lambda b: b['seen']['changes'][0]['fields'].update(readReceiptDate='2026-10-29'),
    lambda b: b['seen']['changes'][0]['fields'].update(loomVideoViewedEstablished=True),
    lambda b: b['seen']['changes'][0]['fields'].update(date='2026-10-29'),
    lambda b: b['replacements'][('waalaxy','selectedExportSnapshot')].update(reviewedAt=generated),
    lambda b: b['replacements'][('waalaxy','selectedExportSnapshot')]['overlapWithSheet'].update(onlyInSheet=1),
    lambda b: b['ads']['metrics'].update(videoViews=0),
    lambda b: b['ads']['scope']['adSetIds'].pop(),
    lambda b: b['ads']['scope'].update(viewFilterCleared=False),
    lambda b: b['ads'].update(sourceDailyRowsAdded=1),
    lambda b: b['adsCard'].update(asOf=generated),
]:
    invalid = deepcopy(bundle);mutate(invalid)
    try:
        integrate(before, invalid, reviewed_at=generated)
    except (AssertionError, StopIteration):
        pass
    else:
        raise AssertionError('A stale, broadened or mismatched accuracy correction was accepted')
conflicting = deepcopy(before)
next(r for r in conflicting['video']['rows'] if r['id']=='mac-dougherty')['connectedAt']='1999-01-01'
try:
    integrate(conflicting, bundle, reviewed_at=generated)
except AssertionError:
    pass
else:
    raise AssertionError('An independently populated conflicting date was overwritten')

# Manifest paths are constrained to declared families and local bundle files;
# optional native correction keys can be omitted without inventing events.
with tempfile.TemporaryDirectory() as folder:
    directory = Path(folder)
    def put(name, value):
        (directory/name).write_text(json.dumps(value))
    for name, value in [('alias.json', bundle['alias']), ('ads.json', bundle['ads']), ('card.json', bundle['adsCard']),
                        ('connections.json', bundle['connections']), ('seen.json', bundle['seen'])]:
        put(name, value)
    replacements = []
    for n, (key, value) in enumerate(bundle['replacements'].items()):
        name = f'replacement-{n}.json';put(name, value)
        replacements.append({'path': list(key), 'file': name})
    manifest = {'appliesToVideoInventorySnapshotAt': before['video']['snapshotAt'],
        'fieldCorrections': {'file': 'connections.json', 'target': ['video','rows'],
            'joinKeys': ['sourceRow','id=profileId'], 'mergeFieldsOnly': True, 'expectedPriorConnectedAt': None},
        'replacements': replacements,
        'existingNativeEventCorrections': {'file': 'seen.json', 'target': ['video','messageDateReview','platformObservedEvents'],
            'joinKeys': ['observationId','eventKey','profileId','date','contentFingerprint'],
            'mergeFieldsOnly': True, 'expectedPriorPlatformReadReceiptObserved': False}}
    def load(value):
        put('manifest.json', value)
        return load_bundle(directory/'manifest.json',directory/'alias.json',directory/'ads.json',directory/'card.json')
    loaded = load(manifest)
    assert loaded['seen'] == bundle['seen'] and loaded['replacements'] == bundle['replacements']
    optional_manifest = deepcopy(manifest);optional_manifest.pop('existingNativeEventCorrections')
    assert load(optional_manifest)['seen'] is None
    for mutate in [lambda m:m['fieldCorrections'].update(file='../outside.json'),
                   lambda m:m['fieldCorrections'].update(target=['outcomes']),
                   lambda m:m['replacements'][0].update(path=['crm','deals']),
                   lambda m:m['existingNativeEventCorrections'].update(target=['video','datedActions'])]:
        invalid = deepcopy(manifest);mutate(invalid)
        try:
            load(invalid)
        except AssertionError:
            pass
        else:
            raise AssertionError('A broad or escaping manifest path was accepted')
print('Accuracy integration: keyed scopes, idempotent replay, optional corrections, Seen boundaries and protected clocks/events/outcomes/effort passed.')
