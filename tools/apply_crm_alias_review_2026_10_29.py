"""Apply one independently observed CRM/profile alias without changing source clocks.

Only a compatible Video DM identity crosswalk is revised. The CRM URL, original
worksheet ID, asset-note evidence, native events, commercial decisions and hours
remain unchanged. The CLI writes private previews and a curated crosswalk patch.
"""
import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    assert result.tzinfo is not None
    return result


def profile(value):
    parsed = urlparse(value)
    assert parsed.scheme == 'https' and parsed.hostname in {'linkedin.com', 'www.linkedin.com'}
    parts = parsed.path.strip('/').split('/')
    assert len(parts) == 2 and parts[0] == 'in' and parts[1]
    assert not parsed.query and not parsed.fragment
    return parts[1].casefold()


def apply_alias(before, proof):
    allowed = {'snapshotAt', 'method', 'redirectObserved', 'identityVerified', 'sourceSystemWrites',
        'sourceInventorySnapshotAt', 'crmInventorySnapshotAt', 'sourceRow', 'profileId', 'contact', 'company',
        'crmDealId', 'crmPersonId', 'crmOrganizationId', 'retainedCrmProfileUrl', 'canonicalProfileUrl',
        'noteScopeReview', 'evidenceHashes'}
    assert set(proof) <= allowed
    assert not re.search(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', json.dumps(proof), re.I)
    video = before['video']
    current = video['crmReconciliation']
    assert proof['redirectObserved'] is True and proof['identityVerified'] is True
    assert proof['sourceSystemWrites'] == 0 and not isinstance(proof['sourceSystemWrites'], bool)
    assert proof['method'] == 'authenticated_native_profile_redirect'
    assert proof['sourceInventorySnapshotAt'] == video['snapshotAt'] == current['appliesToSnapshotAt']
    assert proof['crmInventorySnapshotAt'] == before['crm']['snapshotAt'] == current['crmInventorySnapshotAt']
    assert instant(proof['snapshotAt']) >= max(instant(video['snapshotAt']), instant(before['crm']['snapshotAt']))
    target = next(r for r in video['rows'] if r['sourceRow'] == proof['sourceRow'] and r['id'] == proof['profileId'])
    assert target['company'] == proof['company'] and target['contact'] == proof['contact']
    assert profile(target['linkedin']) == profile(proof['canonicalProfileUrl']) == proof['profileId']
    assert profile(proof['retainedCrmProfileUrl']) != proof['profileId']
    deal = next(r for r in before['crm']['deals'] if r['id'] == proof['crmDealId'])
    assert deal['personId'] == proof['crmPersonId'] and deal['organizationId'] == proof['crmOrganizationId']
    assert deal['company'] == proof['company'] and deal['person'].strip() == proof['contact']
    assert deal['status'] != 'deleted'
    notes = proof['noteScopeReview']
    assert set(notes) == {'scopes', 'completeReturnedPagination', 'sourceAssetId', 'sourceAssetMatches', 'distinctNoteIds', 'collectedAt'}
    assert set(notes['scopes']) == {'deal', 'person', 'organization'}
    assert notes['completeReturnedPagination'] is True
    assert notes['sourceAssetId'] == target['recordingAssetId']
    assert notes['sourceAssetMatches'] == []
    assert notes['distinctNoteIds'] == sorted(set(notes['distinctNoteIds']))
    assert instant(notes['collectedAt']) <= instant(proof['snapshotAt'])
    result = copy.deepcopy(before)
    review = result['video']['crmReconciliation']
    aliases = review.setdefault('profileAliasReviews', [])
    existing = next((r for r in aliases if r['profileId'] == proof['profileId']), None)
    gap = next(r for r in review['specificLinkageGaps'] if r['sourceRow'] == target['sourceRow'] and r['profile'] == target['id'])
    if existing:
        assert existing['crmDealId'] == proof['crmDealId']
        assert existing['retainedCrmProfileUrl'] == proof['retainedCrmProfileUrl']
        assert instant(proof['snapshotAt']) >= instant(existing['snapshotAt'])
        aliases[aliases.index(existing)] = copy.deepcopy(proof)
    else:
        assert gap['matchedCrmDealId'] is None, 'The identity counter already includes this match without the expected review'
        aliases.append(copy.deepcopy(proof))
        identity = review['currentIdentityAssetReview']
        identity['currentCrmRecordsEvidenced'] += 1
        identity['exactProfileMatches'] += 1
        # This is the retained person-field URL with an independently observed
        # canonical redirect, rather than an exact raw-string equality.
        identity['profileMatchedInPersonField'] += 1
        review['undatedStatusReview']['currentCrmRecordsEvidenced'] += 1
    identity = review['currentIdentityAssetReview']
    identity['verifiedCanonicalAliasMatches'] = len(aliases)
    identity['note'] = ('Current explicit-ID/asset rows retain their original CRM/person and note scopes. '
        'Person-field matches include one independently observed canonical LinkedIn redirect; '
        'the stored CRM URL is unchanged. Identity and asset evidence do not establish actual sending.')
    assert gap['sourceSheetDealId'] == target.get('dealId')
    gap.update(matchedCrmDealId=proof['crmDealId'], noteIdsReviewed=notes['distinctNoteIds'],
        gap=('Identity resolved: the retained CRM profile URL redirects to the exact current source profile. '
             'Current deal 411/person 605 is matched without altering the original worksheet ID or stored CRM URL. '
             'The source Loom asset is absent from the exhausted deal/person/organization notes; '
             'that remaining recording-linkage gap is separate from independently observed native sending.'),
        identityAliasReview=copy.deepcopy(proof))
    review['reviewedAt'] = max(review['reviewedAt'], proof['snapshotAt'])
    note = ('Apaluma identity was independently resolved by a native canonical-profile redirect. '
            'Its source asset remains absent from current scoped CRM notes. Original IDs and all native/commercial clocks are preserved.')
    if note not in review['notes']:
        review['notes'].append(note)
    assert review['snapshotAt'] == current['snapshotAt']
    assert review['crmInventorySnapshotAt'] == current['crmInventorySnapshotAt']
    assert identity['sameAssetInCrmNotes'] == current['currentIdentityAssetReview']['sameAssetInCrmNotes']
    assert identity['sourceLoomUrls'] == current['currentIdentityAssetReview']['sourceLoomUrls']
    for key in before:
        if key != 'video':
            assert result[key] == before[key], f'Alias review altered unrelated section {key}'
    for key in video:
        if key != 'crmReconciliation':
            assert result['video'][key] == video[key], f'Alias review altered unrelated Video evidence {key}'
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT/'data/shared-dashboard.json')
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--patch-output', type=Path, required=True)
    args = parser.parse_args()
    for out in [args.output, args.patch_output]:
        assert out.resolve().is_relative_to((ROOT/'data/private').resolve()), 'Private output required'
    result = apply_alias(json.loads(args.snapshot.read_text()), json.loads(args.proof.read_text()))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    args.patch_output.write_text(json.dumps(result['video']['crmReconciliation'], ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'preview': str(args.output), 'crosswalkPatch': str(args.patch_output),
                      'inventoryClocksPreserved': True, 'nativeEventsAndCommercialDecisionsChanged': False}))


if __name__ == '__main__':
    main()
