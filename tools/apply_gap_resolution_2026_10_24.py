"""Apply independently dated, curated October 24 gap reviews.

The normal CLI writes a private preview. Canonical files require --write-shared.
No worksheet inventory or CRM census is re-dated by a focused verification.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import copy
import json

from apply_refresh_2026_10_23 import (apply_patches as apply_source_patches, clock,
    require_current, assert_curated, event_key)
from prepare_shared_snapshot import preserve_newer_shared_sources, curate_snapshot

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/gap_resolution_2026_10_24'
FAMILIES = {'nativeMessageReview', 'sheetFreshnessReview', 'crmIncrementalReview', 'gapResolutionReview', 'sourceCards'}


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def apply_patches(before, patches, reporting_as_of='2026-10-24', generated_at=None):
    assert not set(patches) - FAMILIES, 'Unknown focused patch family'
    assert reporting_as_of >= before['meta']['reportingAsOfDate'], 'Reporting frame cannot move backward'
    base_patches = {}
    if patches.get('nativeMessageReview'):
        base_patches['videoMessageDateReview'] = patches['nativeMessageReview']
    result = apply_source_patches(before, base_patches, reporting_as_of, generated_at)
    targets = [('sheetFreshnessReview','video','sourceFreshnessReview','appliesToSnapshotAt'),
        ('gapResolutionReview','video','gapResolutionReview','appliesToVideoInventorySnapshotAt'),
        ('crmIncrementalReview','crm','incrementalReview','baselineSnapshotAt')]
    for family, parent, child, scope_key in targets:
        if family not in patches:
            continue
        incoming = copy.deepcopy(patches[family])
        # Explicit child clocks are required; a parent's old inventory age is
        # never used as a substitute for a new verification's collection time.
        assert incoming.get('snapshotAt') and incoming.get('reviewedAt'), f'{family} needs explicit source clocks'
        require_current(incoming, before.get(parent, {}).get(child), family)
        assert incoming.get(scope_key) == before[parent]['snapshotAt'], f'{family} has stale inventory scope'
        result[parent][child] = incoming
    gap = result.get('video', {}).get('gapResolutionReview')
    if gap and 'gapResolutionReview' in patches:
        valid = {(r['sourceRow'], r['id']) for r in result['video']['rows']}
        for row in gap.get('records', []):
            if row.get('sourceRow') and row.get('profileId'):
                assert (row['sourceRow'], row['profileId']) in valid, 'Focused gap row/profile join is stale'
        # One verified wording correction only. This is not a new CRM crosswalk
        # or a claim that Chromie's empty recording cell matches an asset.
        for correction in gap.get('specificLinkageWordingCorrections', []):
            for row in result['video'].get('crmReconciliation', {}).get('specificLinkageGaps', []):
                if row.get('sourceSheetDealId') == correction['sourceSheetDealId']:
                    row['gap'] = correction['replacement']
                    row['wordingCorrectedAt'] = correction['reviewedAt']
                    row['wordingCorrectionBasis'] = 'Separately dated focused CRM review; original crosswalk collection clock and source ID are unchanged.'
    cards = {c['id']: copy.deepcopy(c) for c in result.get('sources', [])}
    for incoming in patches.get('sourceCards', []):
        old = cards.get(incoming['id'])
        if old:
            assert clock(incoming.get('asOf')) >= clock(old.get('asOf')), 'Source card cannot move backward'
        cards[incoming['id']] = copy.deepcopy(incoming)
    result['sources'] = list(cards.values())
    revised = generated_at or datetime.now(timezone.utc).isoformat()
    result['meta'].update(generatedAt=revised, analyticsRevisedAt=revised, localReviewOn=reporting_as_of,
        asOfDate=reporting_as_of, reportingAsOfDate=reporting_as_of,
        defaultReportingThrough=reporting_as_of, defaultCompleteReportingThrough='2026-10-23',
        currentDayPartial=True, revision='October 24 focused Video DM and CRM gap resolution',
        publicationReview='GAP_RESOLUTION_2026-10-24.md',
        lastRevisionNote='Focused source checks add historical native-message evidence and clarify CRM/identity/date gaps. Parent inventory clocks, commercial outcomes and owner effort estimates retain their separate evidence dates.')
    result = curate_snapshot(preserve_newer_shared_sources(result, before))
    assert result['outcomes'] == before['outcomes'], 'Commercial decisions changed'
    assert result['time'] == before['time'], 'Owner effort or meeting evidence changed'
    for parent in ('content','ads','waalaxy','meetings','referrals'):
        assert result[parent] == before[parent], f'Unrequested source change: {parent}'
    for key in ('snapshotAt','rows','summary','datedActions','snapshotDelta','sourceCoverage'):
        assert result['video'].get(key) == before['video'].get(key), f'Video inventory was modified: {key}'
    for key in before['crm']:
        if key != 'incrementalReview':
            assert result['crm'].get(key) == before['crm'].get(key), f'CRM inventory was modified: {key}'
    prior_events = {event_key(e):e for e in before['video']['messageDateReview']['platformObservedEvents']}
    events = {event_key(e):e for e in result['video']['messageDateReview']['platformObservedEvents']}
    assert prior_events.keys() <= events.keys(), 'Prior observed messages disappeared'
    for key, prior in prior_events.items():
        assert events[key]['observedAt'] == prior['observedAt'], 'An un-reobserved historical message was re-dated'
    assert_curated(result)
    return result


def prepare(private=PRIVATE, baseline=None):
    """Create public-safe patch families from retained private reviewed evidence."""
    before = baseline or load(ROOT / 'data/shared-dashboard.json')
    sheet = load(private / 'sheets/freshness_review_patch.json')
    identity = load(private / 'sheets/identity_date_gap_review_patch.json')
    appearance = load(private / 'sheets/source_appearance_review_patch.json')
    crm = load(private / 'crm/crm_gap_review_patch.json')
    native = load(private / 'native/native_message_review_patch.json')
    checks = {r['profileId']: r for r in native['review']['focusedNativeReviews']['profileChecks']}
    rows = {r['id']: r for r in before['video']['rows']}
    review_time = max(sheet['reviewedAt'], crm['reviewedAt'], native['review']['reviewedAt'],
        load(private / 'native/cast_meta.json')['observedAt'], appearance['reviewedAt'])
    records = []

    def record(profile, status, findings, **extra):
        row = rows[profile]
        item = {'profileId': profile, 'sourceRow': row['sourceRow'], 'company': row['company'],
            'contact': row['contact'], 'status': status, 'findings': findings,
            'crmDealId': int(row['dealId']) if str(row.get('dealId') or '').isdigit() else None, 'sourceInventorySnapshotAt': before['video']['snapshotAt']}
        if profile in checks:
            check = checks[profile]
            item.update(nativeReviewedAt=check['observedAt'], nativeEvidenceLink=check['evidenceLink'],
                platformSendDate=check.get('platformSendDate'), platformReplyDate=check.get('platformReplyDate'),
                sendAssetObserved=check.get('assetObserved'), sourceEvidenceBasis='native_direct')
        item.update(extra)
        records.append(item)
        return item

    record('alejandro-castellano', 'Native send and declined reply verified; CRM asset-note gap remains', [
        'Charles sent the exact worksheet Loom asset on September 10; a September 16 reply directly declined the explicit same-day video follow-up.',
        'These are historical September events. They add no October send or reply and establish no qualification or opportunity outcome.',
        'Pipedrive deal 428 exists with the exact current profile. The two distinct notes returned across deal/person/organization scopes do not contain this source Loom asset.',
        'The displayed month/day year uses the observed current-year label convention with moderate confidence; source timezone and exact instants are unavailable.'],
        crmDealId=428, platformReplyVideoAttributionEstablished=True,
        replyMeaning='declined', nativeAssetId='c8e600cc63794bb99d49b23a03df2251')
    record('nadav-cornberg', 'Historical native video send verified; worksheet/CRM linkage incomplete', [
        'Charles sent a matching Eve Security Loom video on September 25 and followed up October 13. The same thread explicitly distinguishes earlier 2025 messages from current-year labels.',
        'The source recording cell, literal video date and explicit CRM ID remain blank; native evidence is kept separately without filling those source fields.',
        'No accessible CRM profile/name/organization/native-asset search match was returned. Expected automation eligibility or a failed sync is not established.',
        'No incoming reply is visible in the bounded excerpt; full thread coverage is not claimed.'],
        nativeAssetId='028cf476dec54073922b204e5359ef61', crmRecordMatchEstablished=False)
    record('saganschultz', 'Native video reference verified; exact asset remains unconfirmed', [
        'A September 1 Charles message explicitly references a video and contains a shortened link. Its destination was not verified, so this is not counted as an exact-asset video send.',
        'Native follow-up is displayed September 9 at 9:17 PM; worksheet follow-up reports September 10. Unknown source timezone prevents declaring either source day incorrect.',
        'Pipedrive deal 425 and exact profile are present; the source Loom asset is absent from the two returned distinct notes.',
        'Month/day labels use the observed current-year convention with moderate confidence.'],
        crmDealId=425, platformVideoReferenceDate='2026-09-01', platformFollowUpDate='2026-09-09',
        shortLinkDestinationVerified=False)
    record('jirka-bachel', 'October conversation observed as general text', [
        'October 21 latest sequence contains Charles general text, an incoming agreement to connect and a Charles scheduling response; no video asset appears in that bounded sequence.',
        'The incoming response is a general LinkedIn reply, not an attributed video reply, held meeting or qualified prospect.',
        'Worksheet October 21 Video Sent report remains a separately labelled source report. No accessible CRM match was returned; automation eligibility is unverified.'],
        platformReplyVideoAttributionEstablished=False, sourceReportContentClassification='general_text_observed_no_video_in_bounded_sequence')
    record('noeljthomas', 'October message observed as general text', [
        'The October 21 latest Charles message is general text with no video asset in that bounded sequence.',
        'The older April incoming response is separate and does not establish an October reply.',
        'Worksheet October 21 Video Sent report remains a source report. No accessible CRM match was returned; automation eligibility is unverified.'],
        sourceReportContentClassification='general_text_observed_no_video_in_bounded_sequence')
    record('alexchantavy', 'Matching October asset remains unconfirmed', [
        'The exact Charles/Alex conversation was rechecked, but the matching October Loom asset was not established in the bounded visible excerpt.',
        'This preserves the original unconfirmed result; it does not prove a non-send, deletion or automation failure.'])
    record('ottocm', 'Stale CRM profile URL identified; alias equivalence unverified', [
        'Pipedrive deal 429 exists. Its older LinkedIn profile URL returns a LinkedIn 404; the current ottocm profile shows Otávio (Otto) Costa Miranda.',
        'No immutable profile-ID equivalence or old-to-new redirect was established, so name/company consistency does not become an exact profile match.',
        'The current source recording cell is empty. Source cleanup would require an owner-approved CRM profile correction.'], crmDealId=429,
        nativeReviewedAt=load(private / 'native/cast_meta.json')['observedAt'], profileAliasEquivalenceEstablished=False)
    record('xavierdegracia', 'Explicit CRM record present; exact profile missing', [
        'Pipedrive deal 224 is open and accessible through its explicit worksheet ID.',
        'Current CRM profile field is empty and exact-profile/note searches did not supply a verified profile link. This establishes record presence only.'], crmDealId=224)
    record('douglas-ford-304279b5', 'Deleted original and related live CRM record distinguished', [
        'Original worksheet ID 322 points to a deleted CRM record and remains source provenance.',
        'Live deal 836 has the exact current LinkedIn profile. The worksheet recording cell is empty, so no source-asset match is claimed.',
        'Formal merge/replacement intent is not verified; this is not evidence of a new prospect, new send or accepted opportunity.'],
        crmDealId=836, sourceSheetDealId=322, sourceRecordDeleted=True)
    record('mac-dougherty', 'Undated status has unresolved channel classification', [
        'The row reports Video Sent but has no literal video date or recording asset. Its source note describes email activity.',
        'A standardized status is insufficient to establish a LinkedIn video send, actual date or channel.'])
    record('marcsayoub', 'Historical video and follow-up dates independently verified', [
        'The September 1 Charles message contains a short link with a visible native Loom preview matching the exact worksheet asset. This establishes one historical September video send.',
        'An explicit video follow-up is displayed September 9 at 9:20 PM. The worksheet literal date fields remain blank and are not populated by this review.',
        'Current-year omitted month/day labels use the separately observed authenticated account convention with moderate confidence. Source timezone and exact instants remain unknown.'],
        crmDealId=427, platformFollowUpDate='2026-09-09', nativeAssetId='dbbdf32725da4cab951ad71804187308')
    record('ashishmandavia', 'October general follow-up date independently verified', [
        'The October 21 Charles message at 10:18 AM is general text asking to reconnect; it has no video asset in the current-period sequence.',
        'This supplies a native observed follow-up day separately from the blank worksheet follow-up date. No video send, current reply or held call is inferred.',
        'Earlier replies are explicitly dated February 2025 and remain separate from the October sequence.'],
        platformFollowUpDate='2026-10-21')
    # Company-level contact candidates are not substitutions for source identities.
    identity_candidates = [
        {'company':'TurboLaw','sourceRow':211,'status':'Official company identities resolved; intended recipient still needs selection',
         'findings':['Official TurboLaw about page names Jay Sarmaz (co-founder/CEO) and Ozgur Gevrek (co-founder/CTO). The source row combines misspelled names without an exact profile.',
             'Public profiles are contact candidates only; choosing one or two recipients requires source-owner direction. No source row was changed.'],
         'candidates':[{'name':'Jay Sarmaz','linkedin':'https://www.linkedin.com/in/jaysarmaz/'},
             {'name':'Ozgur Bora Gevrek','linkedin':'https://www.linkedin.com/in/ozgurbora/'}],
         'evidenceLinks':['https://turbolaw.ai/about']},
        {'company':'Corca Research','sourceRow':223,'status':'Official company contact identified; exact intended profile unresolved',
         'findings':['Official Corca documentation identifies Anton Gladkoborodov as CEO of Corca Research.',
             'The source says Co-founders without an exact profile. The intended recipient and exact LinkedIn identity remain unresolved; no automatic identity substitution was made.'],
         'candidates':[{'name':'Anton Gladkoborodov','role':'CEO'}],
         'evidenceLinks':['https://corca.app/doc/45KghvqDJatmDv7T_MGhq/what-is-corca']},
    ]
    records.extend(identity_candidates)
    minimal_crm = []
    for row in crm['recordReviews']:
        minimal_crm.append({key: copy.deepcopy(row.get(key)) for key in ('sourceRow','profile','company','sourceSheetDealId','crmDealId','crmPersonId','crmOrganizationId','dealStatus','dealDeleted','explicitRecordPresence','exactCurrentProfileFieldMatch','sourceLoomAssetId','matchingAssetNoteIds','distinctNoteIds','reviewedAt','actualSendOrReplyInferred')})
    minimal_unmatched = [{key:copy.deepcopy(row.get(key)) for key in ('sourceRow','profile','company','sourceSheetDealId','sourceReportedVideoSentDate','reviewedAt','matchedCrmDealId','currentAccessibleSearchMatches','expectedAutomationWriteEstablished','note')} for row in crm['unmatchedRecordReviews']]
    correction = crm['recommendedCorrections'][0]
    gap = {'snapshotAt':review_time,'reviewedAt':review_time,'reportingAsOfDate':'2026-10-24',
        'appliesToVideoInventorySnapshotAt':before['video']['snapshotAt'],
        'crmInventorySnapshotAt':before['crm']['snapshotAt'],
        'summary':{'description':'Focused native conversations, exact CRM record/asset searches, full unchanged Sheet reread and identity/date diagnostics resolve specific gaps while keeping source reports separate from actual observed messages.',
            'nativeProfilesReviewed':8,'newHistoricalSeptemberVideoSends':3,'newHistoricalSeptemberAttributedReplies':1,
            'newOctoberObservedVideoSends':0,'newOctoberAttributedVideoReplies':0,
            'sourceRowsChanged':0,'commercialOutcomesChanged':False,'ownerHoursChanged':False},
        'records':records,'crmRecordReviews':minimal_crm,'crmUnmatchedRecordReviews':minimal_unmatched,
        'crmSearchReview':{'reviewedAt':crm['reviewedAt'],'scopedSearches':len(crm['searches']),
            'currentAccessibleAccountOnly':True,'zeroResultsDoNotProveGlobalAbsence':True,'automationFailureEstablished':False},
        'identityDateReview':{'snapshotAt':identity['snapshotAt'],'reviewedAt':identity['reviewedAt'],
            'appliesToSnapshotAt':identity['appliesToSnapshotAt'],'summary':identity['summary'],
            'duplicateGroups':identity['duplicateGroups'],'analyticalTreatment':identity['analyticalTreatment']},
        'companyIdentityCandidates':identity_candidates,
        'sourceAppearanceReview':appearance,
        'specificLinkageWordingCorrections':[{'sourceSheetDealId':322,'replacement':correction['replacement'],'reviewedAt':crm['reviewedAt']}],
        'notes':['No source records, worksheets, messages, notes or automations were changed.',
            'Native evidence retains displayed day precision and unknown source timezone. Source date/status reports, person-history attributes, native observations and CRM note inventories are distinct evidence families.',
            'Worksheet inventory remains at its original collection clock because every full-range value was unchanged during the fresh read.',
            'Revision 1253 to 1290 bounds 40 new stable source identities between October 21 14:42 and October 22 15:59 Mountain time; this is a weekly source first-appearance minimum, not exact row-added or sending timestamps.',
            'Profile duplicates are recognized for unique-person diagnostics; six duplicate groups add no message events. Two duplicate Connected flags explain 115 source flags versus 113 distinct profiles.',
            'Exact commercial qualification, held-call completeness, opportunity acceptance and first-time wins remain reserved for Charles.']}
    increment = copy.deepcopy(crm['crmIncrementalReview'])
    increment.pop('sourceManifest', None)
    increment.update(snapshotAt=increment['reviewedAt'], baselineSnapshotAt=before['crm']['snapshotAt'])
    cards = [
        {'id':'video_source_freshness','name':'Video DM · full-range unchanged-source verification','asOf':sheet['reviewedAt'],
         'status':'Fresh read; source inventory unchanged','coverage':'; '.join(sheet['sourceRanges']),
         'method':'Read-only full allocated ranges, literal-date/formula inspection and source revision metadata/content access',
         'note':'All current values match the retained October 23 source. Inventory remains 468 rows / 460 unique profiles, with 22 literal video dates and 44 follow-up dates; original collection clock is preserved. File/revision timestamps do not establish message sending or exact row-added timestamps.'},
        {'id':'video_gap_resolution','name':'Video DM · targeted native/CRM/identity gap resolution','asOf':review_time,
         'status':'Focused evidence; complete activity history remains unavailable','coverage':'Eight native thread checks, stale profile review, six explicit CRM record checks, three unmatched-profile reviews and unchanged full Sheet ranges.',
         'method':'Independent native message blocks, current CRM record/note/search scopes and exact source-profile joins',
         'note':'Three September sends and one September declined video reply are newly verified. October native video sends remain 18; Navigara/Dark Watch current messages are general text. Source reports and commercial outcomes are unchanged.'},
        {'id':'crm_incremental','name':'Pipedrive · independent incremental state review','asOf':increment['reviewedAt'],
         'status':'Independently dated delta checks; full inventory clock retained',
         'coverage':increment.get('effectiveCoverage') or increment.get('scope'),
         'method':'Read-only overlapping change queries and bounded record verification; see guarded state bridge where verified',
         'note':increment.get('result','The full CRM inventory retains its original source clock; no new commercial decision is inferred.')},
        {'id':'video_message_dates','name':'Video DM · source dates and observed message proof','asOf':native['review']['reviewedAt'],
         'status':'Targeted native observations plus retained historical proof',
         'coverage':'Current literal source dates and 34 separately observed messages; 21 exact-asset video sends, including 18 in October and 3 historical September sends. Not an account-wide message census.',
         'method':'Exact profile plus sender/date/time/asset within each relevant native message block',
         'note':'The legacy 19-profile October cohort retains its original source clock. The focused October 24 eight-profile review is separate. One attributed declined reply is September 16; no new October video reply is inferred.'},
    ]
    manifest = {'reportingAsOfDate':'2026-10-24','patches':{
        'nativeMessageReview':'data/private/gap_resolution_2026_10_24/native/native_message_review_patch.json',
        'sheetFreshnessReview':'data/private/gap_resolution_2026_10_24/sheets/freshness_review_patch.json',
        'crmIncrementalReview':'data/private/gap_resolution_2026_10_24/crm/crm_incremental_review_public_patch.json',
        'gapResolutionReview':'data/private/gap_resolution_2026_10_24/gap_resolution_review_patch.json',
        'sourceCards':'data/private/gap_resolution_2026_10_24/source_cards_patch.json'}}
    save(private / 'gap_resolution_review_patch.json', gap)
    save(private / 'crm/crm_incremental_review_public_patch.json', increment)
    save(private / 'source_cards_patch.json', cards)
    save(private / 'integration_manifest.json', manifest)
    if not (private / 'baseline_shared.json').exists():
        save(private / 'baseline_shared.json', before)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',help='Prepare public-safe focused patches and manifest from private reviewed evidence')
    parser.add_argument('--manifest',type=Path,default=PRIVATE/'integration_manifest.json')
    parser.add_argument('--input',type=Path,default=ROOT/'data/shared-dashboard.json')
    parser.add_argument('--output',type=Path,default=PRIVATE/'integrated_dashboard_preview.json')
    parser.add_argument('--write-shared',action='store_true')
    args=parser.parse_args()
    before=load(args.input)
    manifest=prepare(baseline=before) if args.prepare else load(args.manifest)
    patches={}
    for family,value in manifest['patches'].items():
        path=Path(value) if isinstance(value,str) else None
        patches[family]=load(path if path.is_absolute() else ROOT/path) if path else copy.deepcopy(value)
    result=apply_patches(before,patches,manifest.get('reportingAsOfDate','2026-10-24'),manifest.get('generatedAt'))
    for path in ([ROOT/'data/shared-dashboard.json',ROOT/'data/dashboard.json'] if args.write_shared else [args.output]):
        save(path,result)
    print(json.dumps({'preview':str(args.output),'sharedFilesWritten':args.write_shared,'generatedAt':result['meta']['generatedAt'],
        'events':len(result['video']['messageDateReview']['platformObservedEvents']),
        'verifiedVideoSends':result['video']['messageDateReview']['summary']['retainedObservedVideoSendEvents'],
        'verifiedVideoReplies':result['video']['messageDateReview']['summary']['retainedObservedVideoReplyEvents'],
        'CRMInventoryClock':result['crm']['snapshotAt'],'videoInventoryClock':result['video']['snapshotAt']}))


if __name__=='__main__':
    main()
