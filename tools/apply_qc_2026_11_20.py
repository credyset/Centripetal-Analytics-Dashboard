"""Apply bounded source-backed QC corrections to a private dashboard preview.

Original source snapshots and the reporting window stay fixed. A QC review
clock does not refresh a source census or establish complete business coverage.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from apply_refresh_2026_10_23 import assert_curated, event_key, merge_message_review
from prepare_shared_snapshot import curate_snapshot
from publication_redactions import validate_publication_redactions
from video_connection_inventory import validate_video_connection_inventory

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/qc_2026_11_20'
INCREASE_ALPHA_DATE_BASIS = (
    'November 17 occurrence is supported by the actual prospective-services dialogue and '
    'independently dated accepted November 17 3pm Eastern reschedule/correspondence. '
    'The November 10 note1815 and Kayla confirmation are pre-call rescheduling context; '
    'CRM activity1178 is separate completion metadata, not independent attendance proof.')


def read(path):
    return json.loads(path.read_text())


def integrate(before, crm_patch, native_patch, prepared_at, business_context=None, company_targets=None, connection_inventory=None):
    result = deepcopy(before)
    result['meetings']['sourceObservedOpportunityStateReviews'] = deepcopy(crm_patch['opportunityLifecycleUpdates'])
    for row in result['meetings'].get('sourceVerifiedHeldCalls', []):
        if row.get('conversationId') == 'fireflies:01M70QH78WZ9WKDEGAR485G7AY':
            assert row['dealId'] == 821 and row['heldAt'] == '2026-11-17'
            row['dateBasis'] = INCREASE_ALPHA_DATE_BASIS
    if business_context:
        event_ids = {event['id'] for event in result['meetings']['events']}
        assert len(business_context['records']) == len({row['eventId'] for row in business_context['records']})
        assert all(row['eventId'] in event_ids for row in business_context['records'])
        result['meetings']['businessContextReview'] = deepcopy(business_context)
        card = dict(id='calendly_business_context', name='Calendly business intake and cancellation context',
                    asOf=business_context['reviewedAt'], checkedAt='2026-11-20',
                    status='Current bounded metadata review', coverage=business_context['scope'],
                    method='Keyed event and invitee source review; business context only',
                    note='Self-reported booking intake and concise cancellation context. Original calendar source clocks and commercial decisions remain separate.')
        result['sources'] = [old for old in result['sources'] if old['id'] != card['id']] + [card]
    review = result['referrals']['eventReview']
    prior_note = {k: deepcopy(review[k]) for k in ('snapshotAt', 'reviewedAt', 'note', 'coverage')}
    history = review.setdefault('retainedPriorReviews', [])
    if prior_note['reviewedAt'] != crm_patch['reviewedAt'] and prior_note not in history:
        history.append(prior_note)
    events = {r['eventId']: r for r in review['events']}
    for row in crm_patch['referralRequestEvents']:
        assert row['type'] == 'request' and row['communicationCount'] == 1
        if row['eventId'] in events:
            assert events[row['eventId']] == row
        events[row['eventId']] = deepcopy(row)
    review['events'] = list(events.values())
    review['reviewedAt'] = crm_patch['reviewedAt']
    counts = Counter(r['type'] for r in review['events'])
    review['note'] = (
        f"The retained evidence includes {counts['request']} request communications, "
        f"{counts['introduction']} inbound introductions and {counts['follow_up']} outbound follow-ups "
        "across their separate dated source windows. A multi-target request counts once by source message, "
        "not once per target. Coverage remains incomplete; these records do not establish held calls, "
        "qualification, accepted opportunities or wins. Current referral-stage inventory remains separate.")
    assert review['coverage']['status'] == 'incomplete'

    video = result['video']
    if company_targets:
        assert company_targets['appliesToVideoSnapshotAt'] == video['snapshotAt']
        summary = company_targets['summary']
        assert summary['contactRows'] == len(video['rows']) == video['summary']['sourceRows']
        assert summary['uniqueLinkedInProfiles'] == video['summary']['uniqueProfiles']
        assert summary['companyOnlyTargetRows'] == len(company_targets['records'])
        assert summary['allTargetRows'] == summary['contactRows'] + summary['companyOnlyTargetRows']
        video['companyOnlyTargets'] = deepcopy(company_targets['records'])
        video['summary'].update(companyOnlyTargetRows=summary['companyOnlyTargetRows'],
                                allTargetRows=summary['allTargetRows'])
        video['sourceCoverage'].update(deepcopy(company_targets['sourceCoveragePatch']))
        video['companyOnlyTargetReview'] = dict(
            appliesToVideoSnapshotAt=video['snapshotAt'],
            historicalPresence=deepcopy(company_targets['historicalPresenceReview']),
            notes=deepcopy(company_targets['notes']))
        video['coverage'] = ('Complete named-target worksheet inventory: contact prospect rows and a separate '
                             'company-only preparation cohort. Dated contact reports and independently dated '
                             'native conversation evidence retain their own scope.')
    video['messageDateReview'] = merge_message_review(
        video['messageDateReview'], native_patch, video,
        result['waalaxy']['sheetSubset'], result['waalaxy']['sheetSubsetCollectedAt'])
    if native_patch.get('focusedNativeReviews'):
        # A new scoped group carries previous groups separately, not as extra
        # current profileChecks with an incompatible denominator.
        video['messageDateReview']['focusedNativeReviews'] = deepcopy(native_patch['focusedNativeReviews'])
    if connection_inventory:
        child = deepcopy(connection_inventory.get('childSupplement', connection_inventory))
        base_video = deepcopy(video)
        video['connectionInventoryReview'] = child
        validate_video_connection_inventory(video)
        assert {key: value for key, value in video.items() if key != 'connectionInventoryReview'} == {
            key: value for key, value in base_video.items() if key != 'connectionInventoryReview'}, 'Helper review changed the base video inventory'
        card = dict(id='video_connection_inventory', name='Video DM · current connection and preparation helpers',
                    asOf=child['snapshotAt'], reviewedAt=child['reviewedAt'], checkedAt='2026-11-20',
                    status='Current bounded helper inventory', coverage=child['scope'],
                    method='Read-only main and connection-ledger values; exact source-row/profile join',
                    note='Current ledger rows include unverified records. Helper queues retain their own review clock; ledger additions do not establish period connections, sends, replies or commercial outcomes.')
        result['sources'] = [old for old in result['sources'] if old['id'] != card['id']] + [card]
    for card in result['sources']:
        if card['id'] == 'referral_events':
            card.update(reviewedAt=crm_patch['reviewedAt'], asOf=crm_patch['reviewedAt'],
                        checkedAt='2026-11-20', note=review['note'])
        elif card['id'] == 'video_message_dates':
            card.update(reviewedAt=native_patch['reviewedAt'], asOf=native_patch['reviewedAt'],
                        checkedAt='2026-11-20',
                        note='Bounded native conversation evidence, including separately dated historical replies. Original message and observation dates are preserved. Complete account-wide sends and replies remain unknown.')
        elif card['id'] == 'video' and company_targets:
            card.update(coverage=video['coverage'],
                        note=f"{summary['contactRows']} contact prospect rows plus {summary['companyOnlyTargetRows']} company-only targets, "
                             f"{summary['allTargetRows']} total target rows. Company-only targets are not contacts, sends, replies or qualified opportunities. Original inventory clock retained.")
    result['meta']['generatedAt'] = prepared_at
    result['meta']['qualityReviewedAt'] = prepared_at
    result = curate_snapshot(result)

    for section in ('ads', 'content', 'waalaxy', 'crm', 'time'):
        assert result[section] == before[section], f'QC unexpectedly changed {section} source values'
    prior_calls = deepcopy(before['outcomes']['heldCalls'])
    for row in prior_calls:
        if row.get('conversationId') == 'fireflies:01M70QH78WZ9WKDEGAR485G7AY':
            row['dateBasis'] = INCREASE_ALPHA_DATE_BASIS
    assert result['outcomes']['heldCalls'] == prior_calls, 'QC changed a held-call fact beyond the reviewed date-basis correction'
    for key in ('opportunityAcceptances', 'clientWins', 'coverage'):
        assert result['outcomes'][key] == before['outcomes'][key], f'QC changed commercial {key}'
    for key in ('defaultDatePreset', 'defaultCompleteReportingThrough', 'reportingAsOfDate', 'defaultReportingThrough'):
        assert result['meta'][key] == before['meta'][key], 'QC moved the reporting period'
    old_events = {event_key(e): e for e in before['video']['messageDateReview']['platformObservedEvents']}
    new_events = {event_key(e): e for e in result['video']['messageDateReview']['platformObservedEvents']}
    assert old_events.keys() <= new_events.keys()
    for key, old in old_events.items():
        assert new_events[key]['date'] == old['date']
        assert new_events[key]['observedAt'] == old['observedAt'], 'QC re-dated original native proof'
    assert_curated(result)
    validate_publication_redactions(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=PRIVATE / 'baseline.json')
    parser.add_argument('--output', type=Path, default=PRIVATE / 'dashboard_preview.json')
    parser.add_argument('--connection-inventory', type=Path, default=PRIVATE / 'video/connection_inventory_patch.json', help='Optional separately dated current-helper child; omit the file to retain only the base inventory')
    args = parser.parse_args()
    result = integrate(read(args.baseline), read(PRIVATE / 'crm/durable_source_patch.json'),
                       read(PRIVATE / 'video/native_historical_patch.json'), datetime.now(timezone.utc).isoformat(),
                       read(PRIVATE / 'meeting_context/businessContextReview.json'),
                       read(PRIVATE / 'video/company_only_targets_patch.json'),
                       read(args.connection_inventory) if args.connection_inventory.exists() else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    args.output.chmod(0o600)
    print('Prepared private November 20 QC preview; original reporting bounds preserved')


if __name__ == '__main__':
    main()
