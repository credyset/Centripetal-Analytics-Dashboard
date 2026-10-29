"""A canonical redirect may resolve identity, never assets, source dates or outcomes."""
import copy
from apply_crm_alias_review_2026_10_29 import apply_alias


def fixture():
    before = {'crm': {'snapshotAt': '2026-10-29T06:01:00Z', 'deals': [{'id': 411,
        'personId': 605, 'organizationId': 536, 'company': 'Apaluma', 'person': 'Alicia J. Keyes', 'status': 'open'}]},
        'outcomes': {'acceptedOpportunities': None}, 'time': {'ownerHours': [21.75, 23]},
        'video': {'snapshotAt': '2026-10-29T05:51:00Z', 'rows': [{'sourceRow': 140, 'id': 'aliciajkeyes505',
            'company': 'Apaluma', 'contact': 'Alicia J. Keyes', 'linkedin': 'https://www.linkedin.com/in/aliciajkeyes505/',
            'recordingAssetId': 'a'*32, 'dealId': None}], 'messageDateReview': {'platformObservedEvents': [{'date': '2026-10-28'}]},
            'crmReconciliation': {'snapshotAt': '2026-10-29T06:01:00Z', 'reviewedAt': '2026-10-29T06:01:00Z',
                'appliesToSnapshotAt': '2026-10-29T05:51:00Z', 'crmInventorySnapshotAt': '2026-10-29T06:01:00Z',
                'currentIdentityAssetReview': {'currentCrmRecordsEvidenced': 103, 'exactProfileMatches': 101,
                    'profileMatchedInPersonField': 79, 'profileMatchedInDealNote': 22, 'sourceLoomUrls': 71, 'sameAssetInCrmNotes': 65},
                'undatedStatusReview': {'currentCrmRecordsEvidenced': 1}, 'notes': [], 'specificLinkageGaps': [
                    {'sourceRow': 140, 'profile': 'aliciajkeyes505', 'sourceSheetDealId': None, 'matchedCrmDealId': None}]}}}
    proof = {'snapshotAt': '2026-10-29T06:31:49Z', 'method': 'authenticated_native_profile_redirect',
        'redirectObserved': True, 'identityVerified': True, 'sourceSystemWrites': 0,
        'sourceInventorySnapshotAt': before['video']['snapshotAt'], 'crmInventorySnapshotAt': before['crm']['snapshotAt'],
        'sourceRow': 140, 'profileId': 'aliciajkeyes505', 'contact': 'Alicia J. Keyes', 'company': 'Apaluma',
        'crmDealId': 411, 'crmPersonId': 605, 'crmOrganizationId': 536,
        'retainedCrmProfileUrl': 'https://www.linkedin.com/in/alicia-j-keyes-59722197/',
        'canonicalProfileUrl': 'https://www.linkedin.com/in/aliciajkeyes505/',
        'noteScopeReview': {'scopes': ['deal', 'person', 'organization'], 'completeReturnedPagination': True,
            'sourceAssetId': 'a'*32, 'sourceAssetMatches': [], 'distinctNoteIds': [1325, 1354], 'collectedAt': '2026-10-29T06:31:47Z'}}
    return before, proof


before, proof = fixture()
original = copy.deepcopy(before)
after = apply_alias(before, proof)
assert before == original
review = after['video']['crmReconciliation']
assert review['currentIdentityAssetReview']['currentCrmRecordsEvidenced'] == 104
assert review['currentIdentityAssetReview']['exactProfileMatches'] == 102
assert review['currentIdentityAssetReview']['profileMatchedInPersonField'] == 80
assert review['currentIdentityAssetReview']['sameAssetInCrmNotes'] == 65
assert review['undatedStatusReview']['currentCrmRecordsEvidenced'] == 2
assert review['specificLinkageGaps'][0]['matchedCrmDealId'] == 411
assert review['specificLinkageGaps'][0]['sourceSheetDealId'] is None
assert review['snapshotAt'] == before['video']['crmReconciliation']['snapshotAt']
assert after['video']['rows'] == before['video']['rows']
assert after['video']['messageDateReview'] == before['video']['messageDateReview']
assert after['crm'] == before['crm'] and after['outcomes'] == before['outcomes'] and after['time'] == before['time']
assert apply_alias(after, proof) == after, 'Replaying the same proof must not add another matched identity'
for mutate in [
    lambda p: p.update(redirectObserved=False),
    lambda p: p.update(identityVerified=False),
    lambda p: p.update(sourceSystemWrites=1),
    lambda p: p.update(sourceInventorySnapshotAt='2000-01-01T00:00:00Z'),
    lambda p: p.update(crmInventorySnapshotAt='2000-01-01T00:00:00Z'),
    lambda p: p.update(snapshotAt='2026-10-01T00:00:00Z'),
    lambda p: p.update(canonicalProfileUrl='https://www.linkedin.com/in/someone-else/'),
    lambda p: p.update(crmPersonId=606),
    lambda p: p.update(company='Different Company'),
    lambda p: p['noteScopeReview'].update(completeReturnedPagination=False),
    lambda p: p['noteScopeReview'].update(sourceAssetMatches=[1325]),
    lambda p: p['noteScopeReview'].update(sourceAssetId='b'*32),
]:
    invalid = copy.deepcopy(proof)
    mutate(invalid)
    try:
        apply_alias(before, invalid)
    except AssertionError:
        pass
    else:
        raise AssertionError('Unsupported alias/mismatched source was accepted')
print('CRM alias review: verified redirects resolve identity only; old URLs/IDs, assets, event proof, clocks, outcomes and hours are preserved.')
