"""Normalize retained Charles conversation observations without source writes.

Only matching profile/sender/asset evidence produces a sent-message observation.
Displayed local source days never become exact instants or dated read receipts.
"""
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import copy
import argparse
import hashlib
import json
import re

from apply_refresh_2026_10_23 import merge_message_review, event_key

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_23'
PROOF = PRIVATE / 'native_video'


def load(path):
    return json.loads(path.read_text())


def normalized_name(value):
    return ''.join(c for c in value.casefold() if c.isalnum())


def write(name, value):
    (PROOF / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def build(selected_profiles=None):
    baseline = load(PRIVATE / 'baseline_shared.json')
    prior = baseline['video']['messageDateReview']
    video = load(PRIVATE / 'sheets/video_inventory_patch.json')
    subset = load(PRIVATE / 'sheets/waalaxy_sheet_subset_patch.json')
    candidates = load(PRIVATE / 'sheets/new_video_native_review_candidates.json')
    candidates_by_profile = {r['id']: r for r in candidates}
    crm = load(PRIVATE / 'crm/video_crm_reconciliation_patch.json')
    crosswalk = {(r['profile'], r.get('sourceLoomAssetId')): r for r in crm['records']}
    events, records, checks, provenance = [], [], [], []
    latest = None
    for path in sorted(PROOF.glob('*_meta.json')):
        filename_profile = path.name.removesuffix('_meta.json')
        # Helper/export-attempt metadata can share this private directory. Only
        # exact requested profile filenames are eligible conversation proofs.
        if filename_profile not in candidates_by_profile:
            continue
        if selected_profiles and filename_profile not in selected_profiles:
            continue
        meta = load(path)
        profile = meta['profile']
        assert profile == filename_profile, 'Observation profile does not match its retained proof filename'
        candidate = candidates_by_profile[profile]
        raw_path = PROOF / (profile + '.txt')
        assert raw_path.exists(), f'Observation metadata has no retained UI proof: {profile}'
        raw = raw_path.read_text()
        assert 'Charles Solomon Me' in raw, f'Charles signed-in identity is absent: {profile}'
        assert normalized_name(candidate['contact']) in normalized_name(raw), f'Prospect identity is absent: {profile}'
        parties = re.findall(r'Open the options list in your conversation with\s+([^\n]+)', raw)
        assert any(normalized_name(candidate['contact']) in normalized_name(party) and 'charlessolomon' in normalized_name(party) for party in parties), f'Wrong or unverified conversation recipient: {profile}'
        assert meta.get('assetMatched') is not False, f'Capture was marked stale or mismatched; await a corrected proof: {profile}'
        observed = meta['observedAt']
        observed_time = datetime.fromisoformat(observed.replace('Z', '+00:00'))
        assert observed_time.tzinfo is not None
        observed_local_day = observed_time.astimezone(ZoneInfo('America/Denver')).date().isoformat()
        latest = max(filter(None, [latest, observed]), key=lambda v: datetime.fromisoformat(v.replace('Z', '+00:00')))
        asset = candidate['loomAssetId']
        asset_url = 'https://www.loom.com/share/' + asset
        asset_visible = bool(asset and re.search(r'https?://(?:www\.)?loom\.com/share/' + re.escape(asset), raw, re.I))
        matched = asset_visible and meta.get('status') != 'checked_unconfirmed'
        header = re.search(r'(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\s+Charles Solomon sent the following messages?', raw, re.I)
        shown_date = meta.get('displayedDate') or (header.group(1).upper() if header else None)
        when = meta.get('resolvedDate') if matched else None
        if matched and not when and shown_date:
            reported_day = date.fromisoformat(candidate['reportedVideoSentDate'])
            observed_day = observed_time.astimezone(ZoneInfo('America/Denver')).date()
            assert 0 <= (observed_day - reported_day).days < 7 and reported_day.strftime('%A').upper() == shown_date.upper(), 'Relative weekday cannot be resolved from this proof and corroborating source day'
            when = reported_day.isoformat()
        time_match = re.search(r'Charles Solomon sent the following messages? at\s+([0-9]{1,2}:[0-9]{2}\s*[AP]M)', raw, re.I)
        if matched:
            assert when and shown_date and time_match, f'Asset lacks a grounded sender/date/time observation: {profile}'
            date.fromisoformat(when)
            if shown_date.upper() in {'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'}:
                assert date.fromisoformat(when).strftime('%A').upper() == shown_date.upper()
            assert when == candidate['reportedVideoSentDate'], 'Platform source day does not corroborate the supplied worksheet date; review separately'
            assert (profile, asset) in crosswalk and crosswalk[(profile, asset)]['assetMatchVerified'] and crosswalk[(profile, asset)]['profileMatchVerified']
            linked = crosswalk[(profile, asset)]
            seen = bool(re.search(r'Seen by\s+', raw, re.I))
            event = {
                'observationId': f'linkedin-ui:{observed_local_day}:{profile}:outbound:{asset}',
                'dedupKey': '|'.join((profile, 'outbound', when, asset)),
                'sourceMessageId': None, 'sourceConversationId': None,
                'profileId': profile, 'company': candidate['company'], 'contact': candidate['contact'],
                'sourceRow': candidate['sourceRow'], 'sourceInventorySnapshotAt': video['snapshotAt'],
                'crmDealId': linked['crmDealId'], 'sourceNoteId': linked['crmNoteIds'][0],
                'sourceKind': 'native_linkedin_existing_conversation', 'date': when,
                'datePrecision': 'day', 'occurredAt': None, 'sourceTimezone': None,
                'displayedDateLabel': shown_date, 'displayedTime': time_match.group(1),
                'observedAsOfDate': observed_local_day,
                'dateBasis': meta.get('basis') or 'Displayed weekday resolved against the observation date; identical worksheet/CRM Loom asset corroborated. Source timezone and exact sending timestamp are unavailable.',
                'channel': 'linkedin_message', 'direction': 'outbound', 'sender': 'Charles Solomon',
                'videoIncluded': True, 'assetId': asset, 'assetLink': asset_url,
                'evidenceLink': candidate['linkedin'],
                'evidenceBasis': 'Correct Charles account and exact prospect; retained existing conversation shows the same outbound Loom asset. This establishes a sent platform message, not a dated delivery/view receipt, a prospect reply or a commercial outcome.',
                'observedAt': observed,
                'platformReadReceiptObserved': seen, 'readReceiptDate': None,
                'readReceiptBasis': 'A Seen marker is visible, but its calendar day is not supplied. It is not converted into a dated receipt or video-view event.' if seen else None,
            }
            events.append(event)
            records.append({'profileId': profile, 'sourceRow': candidate['sourceRow'], 'sourceRows': [candidate['sourceRow']],
                'company': candidate['company'], 'contact': candidate['contact'], 'linkedin': candidate['linkedin'],
                'matchedCrmDealId': linked['crmDealId'], 'platformSendDate': when,
                'platformVideoAttributionEstablished': True, 'platformCheckStatus': 'matched',
                'platformEvidenceCollectedAt': observed,
                'basis': 'Native observed send date belongs to the identical source Loom asset; worksheet reports and source person attributes remain separately labelled.'})
        checks.append({'profileId': profile, 'company': candidate['company'], 'sourceRow': candidate['sourceRow'],
            'crmDealId': crosswalk.get((profile, asset), {}).get('crmDealId'),
            'status': 'matched' if matched else 'checked_unconfirmed', 'assetId': asset,
            'platformSendDate': when, 'observedAt': observed, 'evidenceLink': candidate['linkedin'],
            'replyObservation': 'No new reply event is established from this bounded latest-thread asset check. Complete reply history is unavailable.',
            'basis': 'Matching Charles outbound asset and source day observed.' if matched else 'The requested profile was checked, but the matching asset was not established in the retained excerpt. No non-send or deletion is inferred.'})
        provenance.append({'profileId': profile, 'path': str(raw_path.relative_to(ROOT)),
            'sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(), 'observedAt': observed})
    assert latest, 'No completed native conversation observation is available'
    partial = {'snapshotAt': latest, 'reviewedAt': latest,
        'scope': {'videoSnapshotAt': video['snapshotAt'], 'nativeConversationReviewedAt': latest,
            'crmIdentityAssetReviewCollectedAt': crm['reviewedAt'],
            'nativeConversationProfilesReviewed': [r['profileId'] for r in checks]},
        'records': records, 'platformObservedEvents': events}
    review = merge_message_review(prior, partial, video, subset['sheetSubset'], subset['sheetSubsetCollectedAt'])
    all_checks = {r['profileId']: copy.deepcopy(r) for r in prior['nativePlatformCoverage']['profileChecks']}
    for check in checks:
        all_checks[check['profileId']] = check
    all_checks = list(all_checks.values())
    matched_checks = [r for r in all_checks if r['status'] == 'matched']
    unmatched_checks = [r for r in all_checks if r['status'] == 'checked_unconfirmed']
    pending = sorted(set(candidates_by_profile) - {r['profileId'] for r in checks})
    review['nativePlatformCoverage'] = {
        'snapshotAt': latest, 'reviewedAt': latest,
        'cohort': 'Retained October 21 asset-cohort checks plus independently collected October 22 worksheet-asset checks. Each observation retains its own collection date.',
        'cohortProfilesChecked': len(all_checks), 'cohortExactOutboundVideoMatches': len(matched_checks),
        'cohortPlatformSendsUnconfirmed': len(unmatched_checks),
        'additionalConversationProfilesChecked': prior['nativePlatformCoverage'].get('additionalConversationProfilesChecked', 0),
        'coverageCompleteForAccount': False,
        'sourceAccount': 'Charles Solomon via authenticated native Chrome profile Centreptal Advisors x RedySet',
        'platformMessageIdsAvailable': False, 'sourceTimezoneKnown': False,
        'profileChecks': all_checks, 'unconfirmedProfiles': [r['profileId'] for r in unmatched_checks],
        'incrementalCohort': {'sourceDate': '2026-10-22', 'requestedProfiles': len(candidates),
            'checkedProfiles': len(checks), 'matchedProfiles': len(events),
            'uncheckedProfiles': pending, 'completeWithinRequestedCohort': not pending,
            'replyHistoryComplete': False},
    }
    review['summary'].update(newVerifiedVideoSendEventsAdded=len(events), newVerifiedVideoReplyEventsAdded=0,
        previouslyReportedSendsCorroborated=len(matched_checks), additionalSendsAboveExistingReportedStatusCount=0)
    review['provenance'] = provenance
    review['notes'].append('Fresh October 22 video-asset checks corroborate existing worksheet reports; they are not added again to reported-send totals. Unchecked profiles remain pending, not verified zero or unconfirmed sends.')
    review['notes'] = list(dict.fromkeys(review['notes']))
    assert len(review['platformObservedEvents']) == len({event_key(e) for e in review['platformObservedEvents']})
    wrapper = {'replacementMode': 'complete_review_bundle', 'completeReviewBundle': True, 'review': review}
    write('video_message_review_patch.json', wrapper)
    source_card = {'id': 'video_message_dates', 'name': 'Video DM · observed message dates', 'asOf': latest,
        'checkedAt': '2026-10-23', 'status': 'Bounded native conversation asset checks; complete account history unavailable',
        'coverage': f"{len(all_checks)} asset profiles checked across separately dated October 21–22 cohorts; {len(matched_checks)} matching outbound videos observed. {len(pending)} newly requested profiles remain unchecked.",
        'method': 'Read-only Charles native LinkedIn conversations, exact worksheet/CRM asset and profile matches.',
        'note': 'Every observation retains its actual collection time and displayed source day. Native matches corroborate reported sends; no exact timestamp, dated read receipt, complete reply census or commercial outcome is inferred.'}
    write('source_card.json', source_card)
    write('normalization_summary.json', {'snapshotAt': latest, 'freshChecks': len(checks), 'freshMatches': len(events),
        'combinedChecks': len(all_checks), 'combinedMatches': len(matched_checks), 'pendingProfiles': pending,
        'historicalUnconfirmedProfiles': [r['profileId'] for r in unmatched_checks], 'accountWideCoverage': False})
    print(json.dumps({'freshChecks': len(checks), 'freshMatchedSends': len(events),
        'combinedMatchedSends': len(matched_checks), 'uncheckedProfiles': len(pending), 'sharedFilesWritten': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', action='append', default=[], help='Read only this completed profile proof; repeat to select several')
    args = parser.parse_args()
    build(set(args.profile) or None)
