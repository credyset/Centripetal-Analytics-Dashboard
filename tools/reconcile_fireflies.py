"""Build the reviewed recording ledger from sanitized read-only review evidence.

No transcript text, private participant rosters, recording URLs or source-system
mutations are used by this normalization step. Re-running preserves the captured
live-review timestamp rather than claiming a fresh collection.
"""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/fireflies_reconciliation.json'


def reconcile(evidence):
    records = []
    for item in evidence['reviewedRecordings']:
        assert item['durationMinutes'] >= 0
        assert item['classification'] != 'qualified_prospect'
        exact_crm = [m['dealId'] for m in item.get('identityMatches', []) if m['exactNameAndEmail']]
        calendar = [m['bookingChainId'] for m in item.get('verifiedCalendarJoins', [])]
        # The current connector omits the event IDs and join/leave fields needed
        # to promote indexed recording times into verified meeting occurrences.
        assert not calendar and not item.get('verifiedOccurredAt')
        dialogue = item['sentenceCount'] > 0 and item['speakerCount'] >= 2
        records.append({
            'id': item['id'], 'title': item['title'],
            'indexedAt': item['indexedAt'], 'occurredAt': None,
            'durationMinutes': round(item['durationMinutes'], 5),
            'classification': item['classification'],
            'classificationBasis': item['classificationBasis'],
            'evidenceStatus': 'recorded_conversation_unlinked' if dialogue else 'recording_metadata_only',
            'crmDealIds': sorted(exact_crm), 'bookingChainIds': calendar,
            'joinStatus': 'exact_crm_identity_only_no_calendar_join' if exact_crm else 'no_verified_crm_or_calendar_join',
            'joinBasis': 'Exact private participant email plus speaker name corroborates CRM contact identity only; it is not deal attribution.' if exact_crm else 'No reliable source-ID, participant-identity and occurrence evidence established a join.',
            'heldStatus': 'unverified_for_booked_call', 'qualifiedStatus': 'unverified',
            'priorClaimedDate': item['priorClaimedDate'],
            'indexedDateMatchesPrior': item['indexedAt'][:10] == item['priorClaimedDate'],
            'audioDurationIsAttendance': False,
            'sourceEvidenceSha256': item['metadataSha256'],
            'purposeReviewSha256': item['purposeReviewSha256'],
        })
    assert len(records) == len({r['id'] for r in records})
    counts = dict(Counter(r['classification'] for r in records))
    summary = {
        'reviewedRecordingCount': len(records),
        'reviewedAudioMinutes': round(sum(r['durationMinutes'] for r in records), 2),
        'classificationCounts': counts,
        'recordedConversationsWithDialogue': sum(r['evidenceStatus'] == 'recorded_conversation_unlinked' for r in records),
        'metadataOnlyRecordings': sum(r['evidenceStatus'] == 'recording_metadata_only' for r in records),
        'recordingsWithExactCrmIdentity': sum(bool(r['crmDealIds']) for r in records),
        'verifiedCalendarJoinedHeldCalls': 0,
        'verifiedQualifiedHeldCalls': None,
        'bookedToHeldRate': None,
        'indexedDateMismatches': sum(not r['indexedDateMatchesPrior'] for r in records),
        'priorAggregateClaimsVerified': False,
        'recordingCountIsUniqueMeetings': False,
    }
    return {
        'snapshotAt': evidence['reviewedLiveAt'], 'timezone': 'America/Denver',
        'coverage': {
            'reviewScope': 'Exact eight source IDs previously labelled BD/prospect; separate bounded index scan for known lead identity corroboration.',
            'reviewedIdsComplete': True,
            'indexedMetadataRecordsScanned': evidence['indexScan']['count'],
            'indexedMetadataNewestAt': evidence['indexScan']['newestAt'],
            'indexedMetadataOldestAt': evidence['indexScan']['oldestAt'],
            'metadataPagination': [{'skip': 0, 'limit': 50, 'returned': 50}, {'skip': 50, 'limit': 50, 'returned': 50}],
            'indexScanCompleteForAllHistory': False,
            'sourceWindowIsMeetingOccurrenceWindow': False,
            'accountScope': 'Accessible Centripetal Fireflies connector; selected records include Centripetal organizers. Authenticated-user metadata is not exposed by this connector.',
            'missingOccurrenceFields': ['calendar_id', 'cal_id', 'meeting_attendance', 'verified meeting start'],
            'failures': ['Fireflies keyword searches for four unrelated lead strings returned identical newest results; search filtering was not reliable and no absence inference uses these searches.'],
            'limits': ['Only eight of the claimed nineteen recordings had a supplied detailed source ledger. Counts of nineteen total, six client and five internal were not independently reconstructed.',
                       'Index scan is bounded and paginated, not an atomic account export. Missing matching recordings do not demonstrate that booked calls were not held.',
                       'A recording is not automatically a unique meeting. Broader duplicate reconciliation outside these eight IDs was not performed.'],
        },
        'records': sorted(records, key=lambda r: r['indexedAt'], reverse=True),
        'summary': summary,
        'priorUnsupportedClaims': evidence['priorClaims'],
        'leadBookingReviews': evidence['leadBookingReviews'],
        'references': [{'title': 'Fireflies Transcript Schema', 'url': 'https://docs.fireflies.ai/schema/transcript',
            'supports': 'duration is audio minutes; date is transcript creation milliseconds UTC; calendar identity and individual attendance are distinct fields.'}],
        'notes': [
            'Keep indexedAt for the source index and occurredAt null until occurrence evidence is verified. Do not use indexed dates as verified held-call dates.',
            'Classification comes from limited purpose review, not participant email domains. External speakers include reference checks, client delivery, recruiting and vendor/partner discussions.',
            'A commercial-discovery discussion does not by itself verify a qualified prospect, accepted opportunity, booked-call linkage or revenue.',
            'Recording audio minutes do not establish individual attendance duration or billable time.',
            'No transcript bodies, summaries, participant email rosters or recording-access URLs are retained in this prepared ledger. Christian effort data is unchanged.',
        ],
        'sourceEvidence': evidence,
    }


def main():
    supplied = sys.stdin.read().strip() if not sys.stdin.isatty() else ''
    evidence = json.loads(supplied) if supplied else json.loads(OUTPUT.read_text())['sourceEvidence']
    result = reconcile(evidence)
    OUTPUT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'summary': result['summary'], 'output': str(OUTPUT)}, indent=2))


if __name__ == '__main__':
    main()
