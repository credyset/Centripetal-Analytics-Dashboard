"""Integrate reviewed October 23 source families without refreshing older evidence.

The default CLI target is a private preview. Canonical shared files are written
only with --write-shared. Raw service responses are never accepted as patches.
"""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import copy
import json
import re

from prepare_shared_snapshot import curate_snapshot, preserve_newer_shared_sources
from import_waalaxy_actions_2026_10_22 import apply_invitation_patch

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_23'
SUPPORTED = {
    'videoInventory', 'recordingFieldReview', 'crmReconciliation',
    'waalaxySheetSubset', 'creator', 'crm', 'referrals', 'meetings', 'timeMeetings',
    'companyAnalytics', 'companyAvailabilityReview', 'adsLifecycleReview',
    'waalaxyAccountAnalytics', 'waalaxyInvitations', 'videoMessageDateReview',
    'sourceCards',
}


def clock(value):
    if isinstance(value, dict):
        value = value.get('snapshotAt') or value.get('collectedAt') or value.get('reviewedAt') or value.get('asOf')
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace(' UTC', 'Z').replace(' ', 'T').replace('Z', '+00:00'))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def require_current(incoming, existing, label):
    assert clock(incoming) > datetime.min.replace(tzinfo=timezone.utc), f'{label} has no collection clock'
    assert clock(incoming) >= clock(existing), f'Refusing older {label} patch'


def unwrap(value, key):
    return value[key] if isinstance(value, dict) and key in value else value


def worksheet_key(row):
    return (row.get('contactId') or row.get('profileId') or row.get('profile'), row.get('type'), row.get('date'))


def retain_worksheet_history(previous_video, new_video):
    """Archive source reports absent from the new ledger, without counting twice."""
    current_keys = {worksheet_key(r) for r in new_video.get('datedActions', [])}
    retained = {}
    for row in previous_video.get('retainedHistoricalWorksheetReports', []):
        if worksheet_key(row) not in current_keys:
            retained[worksheet_key(row)] = copy.deepcopy(row)
    for row in previous_video.get('datedActions', []):
        key = worksheet_key(row)
        if key not in current_keys:
            retained.setdefault(key, dict(copy.deepcopy(row),
                sourceInventorySnapshotAt=previous_video.get('snapshotAt'),
                historicalSourceRow=row.get('sourceRow'),
                historicalOnly=True,
                retentionBasis='Previously collected worksheet report no longer present in the current literal date fields; not a new activity or native-platform event.'))
    new_video['retainedHistoricalWorksheetReports'] = [retained[k] for k in sorted(retained, key=lambda k: tuple(str(v or '') for v in k))]


def event_key(event):
    if event.get('sourceMessageId'):
        return 'message:' + str(event['sourceMessageId'])
    profile = event.get('profileId') or event.get('profile')
    asset = event.get('assetId') or event.get('loomAssetId')
    direction = event.get('direction')
    when = event.get('date') or event.get('occurredAt')
    if profile and direction and when and (asset or event.get('dedupKey')):
        return '|'.join(str(v or '') for v in (profile, direction, when, asset or event.get('dedupKey')))
    assert event.get('observationId'), 'A platform observation needs a stable identity or explicit observation ID'
    return 'observation:' + str(event['observationId'])


def merge_nonempty_fields(previous, incoming):
    """A partial collector's empty containers are omissions, not deletions."""
    if isinstance(previous, dict) and isinstance(incoming, dict):
        result = copy.deepcopy(previous)
        for key, value in incoming.items():
            if key in result and isinstance(value, (dict, list)) and not value:
                continue
            result[key] = merge_nonempty_fields(result[key], value) if key in result else copy.deepcopy(value)
        return result
    if isinstance(previous, list) and isinstance(incoming, list):
        result = copy.deepcopy(previous)
        known = {json.dumps(v, sort_keys=True, ensure_ascii=False) for v in result}
        for value in incoming:
            ident = json.dumps(value, sort_keys=True, ensure_ascii=False)
            if ident not in known:
                result.append(copy.deepcopy(value))
                known.add(ident)
        return result
    return copy.deepcopy(incoming)


def merge_independent_records(previous, incoming, identity):
    result = {}
    for item in previous + incoming:
        key = identity(item)
        result[key] = merge_nonempty_fields(result.get(key, {}), item)
    return list(result.values())


def normalize_message_patch(incoming):
    """Intentional context-family replacement requires a complete review bundle."""
    if not incoming:
        return {}, False
    if 'replacementMode' not in incoming:
        return incoming, False
    assert incoming.get('replacementMode') == 'complete_review_bundle' and incoming.get('completeReviewBundle') is True, 'Invalid complete message-review wrapper'
    review = incoming.get('review')
    required = {'snapshotAt', 'reviewedAt', 'scope', 'summary', 'records', 'platformObservedEvents',
        'separateEmailContext', 'explicitReplyReports', 'nativePlatformCoverage', 'notes'}
    assert isinstance(review, dict) and required <= set(review), 'Complete message-review bundle is missing independent evidence families'
    return review, True


def archive_mismatched_row_reviews(snapshot, previous):
    """Generic source preservation may retain older proof, but never activate it."""
    video = snapshot.get('video') or {}
    current_snapshot = video.get('snapshotAt')
    valid_rows = {(r['sourceRow'], r['id']) for r in video.get('rows', [])}
    history = {}
    for item in (previous.get('video') or {}).get('historicalRowScopedReviews', []) + video.get('historicalRowScopedReviews', []):
        proof = item.get('review') or {}
        ident = (item.get('reviewKind'), proof.get('appliesToSnapshotAt'), clock(proof).isoformat())
        history[ident] = copy.deepcopy(item)
    archived = []
    for key in ('recordingFieldReview', 'crmReconciliation'):
        review = video.get(key)
        if not review:
            continue
        valid_scope = review.get('appliesToSnapshotAt') == current_snapshot
        valid_join = all((r['sourceRow'], r.get('profile') or r.get('profileId')) in valid_rows for r in review.get('records', []))
        if valid_scope and valid_join:
            continue
        history[(key, review.get('appliesToSnapshotAt'), clock(review).isoformat())] = {
            'reviewKind': key, 'review': copy.deepcopy(review), 'historicalOnly': True,
            'archivedForInventorySnapshotAt': current_snapshot,
            'reason': 'Original row-scoped review belongs to a different inventory snapshot or row/profile map. Its proof and collection clocks are retained only as historical evidence.'}
        archived.append(key)
        video.pop(key, None)
    if history:
        video['historicalRowScopedReviews'] = list(history.values())
    if archived:
        cards = {c['id']: c for c in snapshot.get('sources', [])}
        card = cards.setdefault('video_crm_reconciliation', {'id': 'video_crm_reconciliation', 'name': 'Video DM recording fields and CRM crosswalk'})
        active = [key for key in ('recordingFieldReview', 'crmReconciliation') if video.get(key)]
        if not active:
            proofs = [item['review'] for item in history.values()]
            latest = max(proofs, key=clock)
            card.update(asOf=latest.get('snapshotAt') or latest.get('collectedAt') or latest.get('reviewedAt'),
                status='Historical row-scoped evidence; no compatible current recording/CRM review',
                coverage='Earlier recording-field and CRM row reviews retain their original inventory scope and collection dates.',
                note='The current inventory was collected separately. Historical row-scoped reviews are archived and are not applied to current rows. A compatible current recording-field/CRM crosswalk is not available in this import.')
        else:
            latest = max((video[key] for key in active), key=clock)
            card.update(asOf=latest.get('snapshotAt') or latest.get('collectedAt') or latest.get('reviewedAt'),
                status='Current ' + ', '.join(active) + '; other row-scoped review is historical',
                note='Only compatible current row-scoped evidence is active. Other independently dated row reviews are archived with their original proof and collection clocks.')
        snapshot['sources'] = list(cards.values())
    return snapshot


def sync_review_source_cards(snapshot):
    cards = {c['id']: c for c in snapshot.get('sources', [])}
    meetings = snapshot.get('meetings') or {}
    if 'meetings' in cards and meetings.get('snapshotAt'):
        cards['meetings'].update(asOf=meetings['snapshotAt'], coverage=copy.deepcopy(meetings.get('coverage')))
    archive = snapshot.get('crm', {}).get('archiveReview') or {}
    if archive:
        card = cards.setdefault('crm_archived', {'id': 'crm_archived', 'name': 'Pipedrive · archived deals'})
        card.update(asOf=archive.get('snapshotAt') or archive.get('collectedAt'),
            coverage=archive.get('scope'), status='Independently dated dedicated archived-record review',
            method=archive.get('method'),
            note=f"{archive.get('archivedDealCount')} accessible archived deals returned over {archive.get('pagesExhausted')} exhausted page(s). This separate archived-endpoint review does not refresh the non-archived inventory or establish first-client wins.")
    snapshot['sources'] = list(cards.values())
    return snapshot


def merge_message_review(previous, incoming, video, sheet_subset, sheet_collected_at):
    """Preserve native proof by profile/asset; source rows retain historical meaning."""
    previous = previous or {}
    incoming, complete_replacement = normalize_message_patch(incoming)
    if incoming:
        require_current(incoming, previous, 'native message-date review')
    review = copy.deepcopy(incoming) if complete_replacement else merge_nonempty_fields(previous, incoming)
    if not review:
        return None
    if not complete_replacement:
        review['separateEmailContext'] = merge_independent_records(previous.get('separateEmailContext', []), incoming.get('separateEmailContext', []), lambda r: r.get('sourceMessageId') or r.get('eventId'))
        review['explicitReplyReports'] = merge_independent_records(previous.get('explicitReplyReports', []), incoming.get('explicitReplyReports', []), lambda r: r.get('eventId') or (r.get('profileId'), r.get('sourceNoteId'), r.get('reportedReplyDate')))
        old_native = previous.get('nativePlatformCoverage') or {}
        new_native = incoming.get('nativePlatformCoverage') or {}
        if old_native and new_native:
            for key in ('cohort', 'cohortProfilesChecked', 'cohortExactOutboundVideoMatches', 'cohortPlatformSendsUnconfirmed'):
                assert key not in new_native or new_native[key] == old_native.get(key), 'Replacing a native coverage cohort requires a complete message-review bundle'
            old_profiles = {r['profileId'] for r in old_native.get('profileChecks', [])}
            assert all(r['profileId'] in old_profiles for r in new_native.get('profileChecks', [])), 'Adding a coverage cohort requires a complete message-review bundle'
            native = merge_nonempty_fields(old_native, new_native)
            native['profileChecks'] = merge_independent_records(old_native.get('profileChecks', []), new_native.get('profileChecks', []), lambda r: r['profileId'])
            review['nativePlatformCoverage'] = native
    by_profile = defaultdict(list)
    for row in video.get('rows', []):
        by_profile[row['id']].append(row)
    events = {}
    source_events = [(event, previous.get('scope', {}).get('videoSnapshotAt')) for event in previous.get('platformObservedEvents', [])]
    source_events.extend((event, incoming.get('scope', {}).get('videoSnapshotAt') or video.get('snapshotAt')) for event in incoming.get('platformObservedEvents', []))
    for event, evidence_inventory_at in source_events:
        item = copy.deepcopy(event)
        item.setdefault('sourceInventorySnapshotAt', evidence_inventory_at)
        key = event_key(item)
        prior = events.get(key)
        if prior:
            # One observed message, even when the same asset is rechecked. Keep
            # every observation's provenance without adding another send.
            candidates = [prior, item]
            chosen = max(candidates, key=lambda e: clock(e.get('observedAt')))
            item = copy.deepcopy(chosen)
            # A collector's false means it did not establish a Seen marker in
            # its excerpt, not that the recipient became unread. Carry an
            # already verified marker only for this same authored message;
            # another displayed block must not borrow the receipt evidence.
            def same_receipt_message(a, b):
                if a.get('sourceMessageId') and b.get('sourceMessageId'):
                    return str(a['sourceMessageId']) == str(b['sourceMessageId'])
                fingerprint_a, fingerprint_b = a.get('contentFingerprint'), b.get('contentFingerprint')
                if fingerprint_a and fingerprint_b and fingerprint_a != fingerprint_b:
                    return False
                time_a = re.sub(r'\s+', '', str(a.get('displayedTime') or '')).upper()
                time_b = re.sub(r'\s+', '', str(b.get('displayedTime') or '')).upper()
                return bool(time_a and time_a == time_b)
            known_markers = [candidate for candidate in candidates if candidate.get('platformReadReceiptObserved') is True
                and same_receipt_message(candidate, chosen)]
            if known_markers and item.get('platformReadReceiptObserved') is not True:
                marker = max(known_markers, key=lambda e: clock(e.get('readReceiptValidatedAt') or e.get('readReceiptSourceObservedAt') or e.get('observedAt')))
                for receipt_field in ('platformReadReceiptObserved', 'readReceiptBasis', 'readReceiptDate',
                        'readReceiptSourceObservedAt', 'readReceiptValidatedAt', 'readReceiptAppliesTo', 'loomVideoViewedEstablished'):
                    if receipt_field in marker:
                        item[receipt_field] = copy.deepcopy(marker[receipt_field])
                if not item.get('readReceiptSourceObservedAt'):
                    item['readReceiptSourceObservedAt'] = marker.get('readReceiptSourceObservedAt') or marker.get('observedAt')
            observations = {}
            for candidate in candidates:
                for evidence in candidate.get('observationHistory', []) + [{k: candidate.get(k) for k in ('observationId', 'observedAt', 'sourceRow', 'evidenceBasis')}]:
                    observations[(evidence.get('observationId'), evidence.get('observedAt'))] = evidence
            item['observationHistory'] = list(observations.values())
            item['firstObservedAt'] = min((e.get('observedAt') for e in candidates if e.get('observedAt')), default=None)
        matches = by_profile.get(item.get('profileId') or item.get('profile'), [])
        asset = item.get('assetId') or item.get('loomAssetId')
        exact_assets = [r for r in matches if asset and r.get('recordingAssetId') == asset]
        item['currentInventorySnapshotAt'] = video.get('snapshotAt')
        if item.get('sourceEvidenceBasis') == 'native_direct':
            # Native message proof remains valid independently of the current
            # worksheet recording cell or an absent CRM note. Track profile and
            # asset joins separately on every future inventory-only replay.
            item['currentSourceRows'] = [r['sourceRow'] for r in matches]
            item['currentAssetSourceRows'] = [r['sourceRow'] for r in exact_assets]
            item['currentInventoryMatchBasis'] = ('Exact current worksheet profile; native message proof is independent of worksheet asset fields and CRM note contents.' if matches else
                'Profile absent from current inventory; historical native message proof retained independently.')
        else:
            item['currentSourceRows'] = [r['sourceRow'] for r in exact_assets if asset] if asset else [r['sourceRow'] for r in matches]
            item['currentInventoryMatchBasis'] = ('Exact profile and identical recording asset; historical observation row is unchanged.' if exact_assets else
                'Exact profile only; current inventory does not independently corroborate an identical asset.' if matches else
                'Profile absent from current inventory; historical observed message retained independently.')
        if item.get('sourceInventorySnapshotAt') != video.get('snapshotAt'):
            item.setdefault('historicalSourceSnapshotAt', item.get('sourceInventorySnapshotAt'))
            item['sourceRowBasis'] = 'Row number at the original observation; currentSourceRows is a separate current-inventory join.'
        events[key] = item
    review['platformObservedEvents'] = list(events.values())
    records = {}
    for row in previous.get('records', []) + incoming.get('records', []):
        records[row['profileId']] = merge_nonempty_fields(records.get(row['profileId'], {}), row)
    attributes = {r['profileId']: r for r in (sheet_subset or {}).get('rows', [])}
    interesting = set(records) | {r['id'] for r in video.get('rows', []) if r.get('reportedVideoSentDate')}
    for key in sorted(interesting):
        current = by_profile.get(key, [])
        item = records.setdefault(key, {'profileId': key})
        dates = sorted({r['reportedVideoSentDate'] for r in current if r.get('reportedVideoSentDate')})
        previous_reported_date = item.get('reportedSendDate')
        if previous_reported_date and previous_reported_date not in dates:
            item['historicalReportedSendDate'] = previous_reported_date
            item['historicalReportedSendDateBasis'] = item.get('reportedSendBasis') or 'Earlier worksheet source report; not native-platform proof.'
            item['historicalReportedSendDateSourceInventoryAt'] = previous.get('scope', {}).get('videoSnapshotAt')
        item['currentWorksheetReportedSendDates'] = dates
        item['reportedSendDate'] = dates[-1] if dates else None
        item['reportedSendBasis'] = ('Literal Video Sent Date in the refreshed worksheet; independently labelled source report, not native-platform proof.' if dates else None)
        if current:
            first = current[0]
            for field in ('company', 'contact', 'linkedin'):
                item.setdefault(field, first.get(field))
            item['currentSourceRows'] = [r['sourceRow'] for r in current]
            item.setdefault('sourceRow', first['sourceRow'])
            item.setdefault('sourceRows', [r['sourceRow'] for r in current])
            item['currentInventorySnapshotAt'] = video.get('snapshotAt')
            item['sourceRowBasis'] = 'Original evidence row retained; currentSourceRows independently identifies the refreshed inventory.'
            item['hasRecordingAssetReference'] = any(r.get('hasRecordingLink') for r in current)
        attribute = attributes.get(key)
        if attribute:
            for field, source_field in [('firstLinkedInMessageDate', 'firstMessageAt'), ('latestLinkedInMessageDate', 'lastMessageAt'), ('latestLinkedInReplyDate', 'lastReplyAt')]:
                item[field] = attribute.get(source_field)
            item['personHistoryCollectedAt'] = sheet_collected_at
            item.setdefault('historySource', 'Selected connected-person worksheet attributes via exact profile identity')
            item.setdefault('historyDatePrecision', 'day')
            item.setdefault('historySourceTimezone', None)
            item.setdefault('historySenderAccountId', None)
        item.setdefault('videoAttributionEstablished', False)
        outbound = [e for e in review['platformObservedEvents'] if e.get('profileId') == key and e.get('direction') == 'outbound' and e.get('videoIncluded')]
        inbound = [e for e in review['platformObservedEvents'] if e.get('profileId') == key and e.get('direction') == 'inbound']
        send_dates = [e.get('date') for e in outbound if e.get('date')]
        reply_dates = [e.get('date') for e in inbound if e.get('date')]
        if send_dates:
            item['platformSendDate'] = max(send_dates)
        if reply_dates:
            item['platformReplyDate'] = max(reply_dates)
    review['records'] = list(records.values())
    review.setdefault('scope', {}).update(currentVideoInventorySnapshotAt=video.get('snapshotAt'),
        currentPersonHistoryCollectedAt=sheet_collected_at,
        historicalNativeProofRetained=True,
        coverageCompleteForAllVideoDmMessages=False)
    review.setdefault('summary', {}).update(
        rowsWithReportedSendDate=sum(bool(r.get('reportedVideoSentDate')) for r in video.get('rows', [])),
        relatedActualOutboundEmails=len(review.get('separateEmailContext', [])),
        explicitCrmReplyDateReports=len(review.get('explicitReplyReports', [])),
        accountWideActualVideoSends=None, accountWideActualVideoReplies=None,
        retainedObservedVideoSendEvents=sum(e.get('direction') == 'outbound' and bool(e.get('videoIncluded')) for e in review['platformObservedEvents']),
        retainedObservedVideoReplyEvents=sum(e.get('direction') == 'inbound' and e.get('replyToVideoAttributionEstablished') is True for e in review['platformObservedEvents']))
    review['inventorySupplementCollectedAt'] = video.get('snapshotAt')
    note = 'Current worksheet inventory/date reports were refreshed independently. Every native observation retains its original observedAt, displayed day, precision and historical row; newer inventory collection does not re-date native proof.'
    if note not in review.setdefault('notes', []):
        review['notes'].append(note)
    return review


def assert_curated(snapshot):
    email = re.compile(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', re.I)
    prohibited = {'emailBody', 'messageBody', 'rawBody', 'rawResponse', 'sentences', 'transcript'}
    def visit(value, path=''):
        if isinstance(value, dict):
            for key, item in value.items():
                assert key not in prohibited or not item, f'Raw content field rejected: {path}/{key}'
                visit(item, path + '/' + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, path + '/' + str(index))
        elif isinstance(value, str):
            assert not email.search(value), f'Raw email identity rejected: {path}'
            assert '/Users/' not in value and 'file:///' not in value, f'Local personal path rejected: {path}'
    visit(snapshot)


def apply_patches(before, patches, reporting_as_of='2026-10-23', generated_at=None):
    assert not set(patches) - SUPPORTED, f'Unknown patch families: {set(patches) - SUPPORTED}'
    assert reporting_as_of >= before.get('meta', {}).get('reportingAsOfDate', ''), 'Refusing an older reporting frame'
    result = copy.deepcopy(before)
    cards = {c['id']: copy.deepcopy(c) for c in before.get('sources', [])}

    def card(ident, section, status=None):
        existing = cards.setdefault(ident, {'id': ident, 'name': ident})
        existing.update(asOf=section.get('snapshotAt') or section.get('collectedAt') or section.get('reviewedAt'), checkedAt=reporting_as_of)
        if section.get('coverage') is not None:
            existing['coverage'] = copy.deepcopy(section['coverage'])
        if status:
            existing['status'] = status

    for key in ('crm', 'referrals', 'meetings'):
        if key in patches:
            incoming = unwrap(patches[key], key)
            require_current(incoming, result.get(key), key)
            result[key] = copy.deepcopy(incoming)
            if key == 'meetings':
                result[key].setdefault('coverage', {}).update(observedThrough=reporting_as_of, currentDayPartialDate=reporting_as_of)
            card(key, incoming, 'Current independently collected source inventory; commercial outcomes remain owner-reviewed')

    if 'videoInventory' in patches:
        incoming = unwrap(patches['videoInventory'], 'videoInventory')
        require_current(incoming, before.get('video'), 'Video DM inventory')
        video = copy.deepcopy(incoming)
        # Preserve independently dated proof/review families, not stale row joins.
        for key in ('sourceVerification', 'automationReview', 'metadataFreshnessCheck', 'datedStatusReview'):
            if before.get('video', {}).get(key):
                video[key] = copy.deepcopy(before['video'][key])
        retain_worksheet_history(before.get('video', {}), video)
        result['video'] = video
        card('video', video, 'Current complete worksheet inventory; literal source dates separated from observed message proof')

    for key in ('recordingFieldReview', 'crmReconciliation'):
        if key in patches:
            incoming = unwrap(patches[key], key)
            require_current(incoming, before.get('video', {}).get(key), key)
            assert incoming.get('appliesToSnapshotAt') == result['video']['snapshotAt'], f'{key} is scoped to a different Video DM inventory'
            valid_rows = {(r['sourceRow'], r['id']) for r in result['video']['rows']}
            for row in incoming.get('records', []):
                assert (row['sourceRow'], row.get('profile') or row.get('profileId')) in valid_rows, f'{key} has a stale row/profile join'
            result['video'][key] = copy.deepcopy(incoming)
            card('video_crm_reconciliation', incoming, 'Current exact-identity/asset reconciliation; source rows independently verified')

    if 'waalaxySheetSubset' in patches:
        incoming = patches['waalaxySheetSubset']
        require_current({'snapshotAt': incoming['sheetSubsetCollectedAt']}, {'snapshotAt': before.get('waalaxy', {}).get('sheetSubsetCollectedAt')}, 'Waalaxy selected-person worksheet')
        for key in ('sheetSubset', 'sheetSubsetCollectedAt', 'sheetSubsetUpstreamSyncAt', 'sheetSubsetAccountVerification'):
            result['waalaxy'][key] = copy.deepcopy(incoming[key])
        card('waalaxy', {'snapshotAt': incoming['sheetSubsetCollectedAt'], 'coverage': incoming['sheetSubset']['scope']}, 'Current selected-person worksheet; account/invitation sources retain independent dates')

    if 'waalaxyInvitations' in patches:
        result['waalaxy'] = apply_invitation_patch(result['waalaxy'], patches['waalaxyInvitations'])
        if patches['waalaxyInvitations'].get('sourceCard'):
            cards['waalaxy_invitations'] = copy.deepcopy(patches['waalaxyInvitations']['sourceCard'])

    supplements = [('creator', 'content', 'creatorAnalytics', 'content'),
        ('companyAnalytics', 'content', 'companyAnalytics', 'content_company'),
        ('companyAvailabilityReview', 'content', 'companyAvailabilityReview', 'content_company_availability'),
        ('adsLifecycleReview', 'ads', 'lifecycleReview', 'ads_lifecycle'),
        ('waalaxyAccountAnalytics', 'waalaxy', 'accountAnalytics', 'waalaxy_account')]
    for family, parent, child, ident in supplements:
        if family not in patches:
            continue
        wrapper = patches[family]
        incoming = unwrap(wrapper, child)
        require_current(incoming, before.get(parent, {}).get(child), family)
        if family == 'creator':
            assert wrapper.get('validation', {}).get('allSourceCountsReconciled'), 'Creator counts do not reconcile'
            assert incoming['coverage']['sourceTimezone'] == 'UTC'
            assert incoming['coverage']['completeDaysThrough'] < incoming['coverage']['end']
            incoming = copy.deepcopy(incoming)
            prior_profile = before.get('content', {}).get('creatorAnalytics', {}).get('profileAnalytics')
            incoming_profile = incoming.get('profileAnalytics')
            if prior_profile and (not incoming_profile or clock(prior_profile) > clock(incoming_profile)):
                incoming['profileAnalytics'] = copy.deepcopy(prior_profile)
        result.setdefault(parent, {})[child] = copy.deepcopy(incoming)
        card(ident, incoming, 'Current independently dated reviewed source supplement')

    if 'timeMeetings' in patches:
        incoming = unwrap(patches['timeMeetings'], 'timeMeetings')
        require_current(incoming, before.get('time', {}).get('meetings'), 'Christian meeting-duration proxy')
        assert incoming.get('subject', {}).get('name', 'Christian Wutz') == 'Christian Wutz'
        assert incoming.get('summary', {}).get('actualChristianAttendanceMinutes') is None
        assert incoming.get('summary', {}).get('billableMinutes') is None
        result['time']['meetings'] = copy.deepcopy(incoming)
        result['time']['snapshotAt'] = incoming['snapshotAt']
        result['time']['evidenceCollectionThrough'] = incoming['snapshotAt']
        result['time']['reviewedAsOf'] = reporting_as_of
        result['time']['period'].update(end=reporting_as_of, currentDayPartial=True)
        card('time', result['time'], 'Current recording-duration proxy; owner non-meeting estimate retains October 22 cutoff')

    if 'videoInventory' in patches or 'videoMessageDateReview' in patches:
        review = merge_message_review(before.get('video', {}).get('messageDateReview'),
            patches.get('videoMessageDateReview'), result['video'], result.get('waalaxy', {}).get('sheetSubset'),
            result.get('waalaxy', {}).get('sheetSubsetCollectedAt'))
        if review:
            result['video']['messageDateReview'] = review
            if patches.get('videoMessageDateReview'):
                card('video_message_dates', review, 'Current bounded conversation observations; original historical proof retained')

    for incoming in patches.get('sourceCards', []):
        old = cards.get(incoming['id']) or {}
        if incoming.get('asOf') and old.get('asOf'):
            assert clock(incoming['asOf']) >= clock(old['asOf']), f"Older source card: {incoming['id']}"
        cards[incoming['id']] = copy.deepcopy(incoming)
    result['sources'] = list(cards.values())
    revision_time=generated_at or datetime.now(timezone.utc).isoformat()
    result['meta'].update(generatedAt=revision_time, analyticsRevisedAt=revision_time,
        localReviewOn=reporting_as_of, publicationReview='REFRESH_REVIEW_2026-10-23.md',
        asOfDate=reporting_as_of, reportingAsOfDate=reporting_as_of,
        defaultReportingThrough=reporting_as_of, defaultCompleteReportingThrough='2026-10-22',
        currentDayPartial=True, revision='October 23 independent live-source refresh',
        lastRevisionNote='Independently collected source families refreshed with separate source clocks. Commercial outcomes and the owner non-meeting estimate are unchanged.')
    result = preserve_newer_shared_sources(result, before)
    archive_mismatched_row_reviews(result, before)
    sync_review_source_cards(result)
    result = curate_snapshot(result)
    assert result['outcomes'] == before['outcomes'], 'Commercial outcomes must remain owner-reviewed and unchanged'
    for key in ('nonMeetingEstimateHoursLow', 'nonMeetingEstimateHoursHigh', 'ownerEstimateRange', 'combinedWorkedHours'):
        assert result['time']['summary'].get(key) == before['time']['summary'].get(key), f'Owner effort evidence changed: {key}'
    assert result['time']['workstreams'] == before['time']['workstreams'], 'Do not reallocate the owner non-meeting estimate'
    if 'waalaxyInvitations' not in patches:
        for key in ('invitationCollectedAt', 'invitationCoverage', 'invitationSummary', 'invitationImportReview'):
            assert result['waalaxy'].get(key) == before['waalaxy'].get(key), f'Unrequested invitation evidence change: {key}'
        invitation_fields = lambda w: [(r['date'], r.get('invitationsSent'), r.get('invitationsAccepted')) for r in w.get('daily', []) if 'invitationsSent' in r or 'invitationsAccepted' in r]
        assert invitation_fields(result['waalaxy']) == invitation_fields(before['waalaxy'])
    prior_native = {event_key(e) for e in before.get('video', {}).get('messageDateReview', {}).get('platformObservedEvents', [])}
    current_native = {event_key(e) for e in result.get('video', {}).get('messageDateReview', {}).get('platformObservedEvents', [])}
    assert prior_native <= current_native, 'Historical native message proof was lost'
    assert_curated(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path, help='Private JSON {patches:{family:path},reportingAsOfDate,generatedAt?}')
    parser.add_argument('--input', type=Path, default=ROOT / 'data/shared-dashboard.json')
    parser.add_argument('--output', type=Path, default=PRIVATE / 'integrated_dashboard_preview.json')
    parser.add_argument('--write-shared', action='store_true', help='Explicitly write canonical shared and local dashboard snapshots')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    patches = {}
    for family, value in manifest['patches'].items():
        if isinstance(value, str):
            path = Path(value)
            if not path.is_absolute():
                path = ROOT / path
            patches[family] = json.loads(path.read_text())
        else:
            patches[family] = copy.deepcopy(value)
    before = json.loads(args.input.read_text())
    result = apply_patches(before, patches, manifest.get('reportingAsOfDate', '2026-10-23'), manifest.get('generatedAt'))
    targets = [ROOT / 'data/shared-dashboard.json', ROOT / 'data/dashboard.json'] if args.write_shared else [args.output]
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    for path in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized)
    print(json.dumps({'patchFamilies': sorted(patches), 'reportingAsOfDate': result['meta']['reportingAsOfDate'],
        'sharedFilesWritten': args.write_shared, 'commercialOutcomesUnchanged': True,
        'ownerNonMeetingEstimateUnchanged': True, 'videoRows': len(result['video']['rows']),
        'nativeObservationsRetained': len(result['video'].get('messageDateReview', {}).get('platformObservedEvents', []))}))


if __name__ == '__main__':
    main()
