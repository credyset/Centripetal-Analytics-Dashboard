"""Build isolated Video DM/selected-person data from the November 13 read-only refresh."""
from collections import Counter, defaultdict
from copy import deepcopy
from html import unescape
from pathlib import Path
import csv
import hashlib
import io
import json
import re

from recording_evidence import recording_evidence_fields
from refresh_sheet_2026_10_21 import people, population
from refresh_sheets_2026_10_28 import profile, valid_date

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_11_13/sheets'
ID = '1_Vq5-hM3POad1V14rZjX6gfaUojUnnTvxjjSv1zDJ8M'
START, END, PARTIAL = '2026-11-06', '2026-11-12', '2026-11-13'


def read(path):
    return json.loads(path.read_text())


def load(name):
    return read(PRIVATE / name)


def write(name, value):
    p = PRIVATE / name
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    p.chmod(0o600)


def source(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def ranges(prefix):
    return sorted(p for p in PRIVATE.glob(f'{prefix}_*.json') if re.fullmatch(rf'{prefix}_\d{{4}}\.json', p.name))


def row_dicts(rows):
    return [(n, dict(zip(rows[0], r))) for n, r in enumerate(rows[1:], 2)]


def stable(row):
    return row['id'], row['company'].casefold().strip(), row['contact'].casefold().strip()


def revision_appearances(current_rows, stamp, review_clock):
    def revision(ident):
        file = load(f'revision_{ident}.json')
        assert file['revisionId'] == ident and file['fileId'] == ID
        grid = list(csv.reader(io.StringIO(file['content'])))
        assert len(grid) == 5000 and grid[0][1] == 'org' and grid[0][5] == 'contact' and grid[0][7] == 'li'
        keys = []
        for raw in grid[1:]:
            if len(raw)<8: continue
            company, contact = raw[1].strip(), raw[5].strip()
            if not company or not contact or (company.casefold(),contact.casefold())==('org','contact'):
                continue
            ident = profile(raw[7]) or hashlib.sha256(f'{company}|{contact}'.lower().encode()).hexdigest()[:16]
            keys.append((ident,company.casefold(),contact.casefold()))
        return file['revisionModifiedTime'], Counter(keys)
    from_clock, before = revision('1560')
    through_clock, after = revision('1652')
    mid_clock, mid = revision('1649')
    second_clock, second = revision('1651')
    partial_clock, partial = revision('1653')
    current_clock, retained_head = revision('1654')
    now = Counter(map(stable,current_rows))
    assert retained_head == now and not (before-after) and not (after-now)
    added=after-before
    novel={key for key in added if key not in before}
    evidence=[]
    seen=set()
    for r in current_rows:
        k=stable(r)
        if k in novel and k not in seen:
            seen.add(k)
            evidence.append({'profileId':r['id'],'company':r['company'],'contact':r['contact'],'currentSourceRow':r['sourceRow'],
                'firstAppearedAfter':from_clock,'firstAppearedBy':through_clock,'recordOccurrencesAdded':added[k]})
    assert seen==novel and len(evidence)==len({r['profileId'] for r in evidence})==88
    intervals=[]
    snapshots=[('1560',from_clock,before),('1649',mid_clock,mid),('1651',second_clock,second),('1652',through_clock,after),('1653',partial_clock,partial),('1654',current_clock,now)]
    for (lid,lo,left),(rid,hi,right) in zip(snapshots,snapshots[1:]):
        assert not (left-right)
        more=right-left
        intervals.append({'baselineRevisionId':lid,'laterRevisionId':rid,'firstAppearedAfter':lo,'firstAppearedBy':hi,
            'addedRowOccurrences':sum(more.values()),'newStableIdentities':sum(k not in left for k in more),
            'removedRowOccurrences':0,'bucket':'completed_window' if int(rid)<=1652 else 'unassigned_midnight_boundary' if rid=='1653' else 'partial_day'})
    assert sum(i['newStableIdentities'] for i in intervals if i['bucket']=='completed_window')==88
    assert intervals[-2]['newStableIdentities']==1 and intervals[-1]['newStableIdentities']==6
    return {'reviewedAt':review_clock,'appliesToSnapshotAt':stamp,'baselineRevisionId':'1560','laterRevisionId':'1652','currentRevisionId':'1654',
        'firstAppearedAfter':from_clock,'firstAppearedBy':through_clock,'currentRevisionAt':current_clock,
        'baselineValidSourceRows':sum(before.values()),'laterValidSourceRows':sum(after.values()),'currentValidSourceRows':sum(now.values()),
        'sourceRecordsRemoved':0,'retainedPriorStableIdentities':len(before),'retainedPriorRowOccurrences':sum(before.values()),
        'newStableSourceRecordsMinimum':len(evidence),'newUniqueProfilesMinimum':len({r['profileId'] for r in evidence}),
        'rowOccurrencesAdded':sum(added.values()),'extraOccurrencesBeyondDistinctNewIdentities':sum(added.values())-len(evidence),
        'additionalRowOccurrencesAfterLaterRevision':sum((now-after).values()),'records':evidence,'intervals':intervals,
        'partialDay':PARTIAL,'partialDayDistinctMinimum':intervals[-1]['newStableIdentities'],
        'unassignedBoundaryRows':intervals[-2]['addedRowOccurrences'],
        'revisionComparisonComplete':True,'stableIdentityComparisonVerified':True,'currentHeadMatchesLiveRows':True,
        'basis':'Complete main-tab CSV revisions. Lower-bound distinct stable source identities first seen inside the interval; exact creation date not supplied. Adjacent revisions isolate six distinct first appearances within partial Nov13; one midnight-straddling appearance is unassigned.'}


def evaluate_crm(rows):
    evidence = []
    raw = load('crm_notes_candidates.json')
    for item in raw:
        notes = item['result']
        assert notes['additional_data']['pagination']['more_items_in_collection'] is False
        for note in notes['data']:
            content = unescape(note['content'])
            urls = {p for url in re.findall(r'https?://[^\s"<>]+', content) if (p := profile(url))}
            assets = set(re.findall(r'loom\.com/share/([a-fA-F0-9]{32})', content))
            matches = [r for r in rows if r['id'] in urls and r['recordingAssetId'] in assets]
            assert len(matches) == 1
            r = matches[0]
            assert r['reportedFollowUpSentDate'] == '2026-11-09' and r['reportedVideoSentDate'] == '2026-11-05'
            assert 'Video DM Context (from Google Sheet' in content and 'Video Sent' in content
            r.update(matchedCrmDealId=item['dealId'], matchedCrmPersonId=note.get('person_id'),
                     crmMatchBasis='Exact profile and Loom asset in a November 5 deal note copied from the worksheet. No current follow-up or reply proof.')
            evidence.append({'sourceRow': r['sourceRow'], 'profile': r['id'], 'company': r['company'],
                'contact': r['contact'], 'crmDealId': item['dealId'], 'crmPersonId': note.get('person_id'),
                'crmNoteId': note['id'], 'crmNoteAddedAt': note['add_time'],
                'reportedVideoSentDate': r['reportedVideoSentDate'], 'reportedFollowUpSentDate': r['reportedFollowUpSentDate'],
                'recordingFieldKind': r['recordingFieldKind'], 'assetId': r['recordingAssetId'],
                'exactProfileAndAsset': True, 'noteCopiesWorksheetContext': True,
                'followUpCorroborated': False, 'replyCorroborated': False})
    return evidence


def build():
    manifest = load('collection_manifest.json')
    stamp = manifest['collectedAt']
    review_clock = manifest['supplementalReviewCompletedAt']
    meta = load('spreadsheet_metadata.json')
    before, after = load('drive_file_before.json'), load('drive_file_after.json')
    assert before['modified_time'] == after['modified_time']
    assert meta['properties']['timeZone'] == 'America/Los_Angeles'
    main_files, accepted_files = ranges('main'), ranges('accepted')
    assert len(main_files) == 10 and len(accepted_files) == 3
    main = [r for f in main_files for r in read(f).get('values', [])]
    accepted = [r for f in accepted_files for r in read(f).get('values', [])]
    assert len(main) == 5000 and len(main[0]) == 29 and len(accepted[0]) == 44
    prior = read(ROOT / 'data/shared-dashboard.json')
    assert prior['video']['snapshotAt'].startswith('2026-10-29'), 'Use an unmodified October 29 baseline.'
    old = prior['video']
    current = deepcopy(old)
    rows, dated, invalid = [], [], []
    groups = defaultdict(list)
    for line, item in row_dicts(main):
        company, contact = (str(item.get(k) or '').strip() for k in ['org','contact'])
        if not company or not contact or (company.casefold(),contact.casefold()) == ('org','contact'):
            continue
        key = profile(item.get('li'))
        ident = key or hashlib.sha256(f'{company}|{contact}'.lower().encode()).hexdigest()[:16]
        status = str(item.get('Status (CS Column)') or '').strip() or 'Blank'
        response = str(item.get('Response Status') or '').strip() or None
        conn = str(item.get('Connected?') or '').strip()
        video_day = valid_date(item.get('Video Sent Date'),date_column='Video Sent Date',reference_day=PARTIAL)
        follow_day = valid_date(item.get('Follow-up Sent Date'),date_column='Follow-up Sent Date',reference_day=PARTIAL)
        if video_day and video_day > PARTIAL: video_day = None
        if follow_day and follow_day > PARTIAL: follow_day = None
        recording = recording_evidence_fields(item.get('Loom Link'))
        asset_match = re.search(r'/share/([a-fA-F0-9]{32})',str(item.get('Loom Link') or ''))
        row = {'id':ident,'sourceRow':line,'company':company,'contact':contact,
            'linkedin':f'https://www.linkedin.com/in/{key}/' if key else '', 'status':status, **recording,
            'recordingAssetId':asset_match.group(1).lower() if asset_match and recording['recordingFieldKind']=='loom_url' else None,
            'hasResponseStatus':bool(response),'responseStatus':response,'connected':conn=='Connected',
            'connectedAt':valid_date(item.get('Connected At'),date_column='Connected At',reference_day=PARTIAL),
            'connectionLabel':conn,'action':item.get('DM Action') or '', 'followUp':item.get('Follow-up Action') or '',
            'dealId':item.get('deal_id') or None,'explicitSendStatus':status.casefold() in {'sent','done'},
            'reportedVideoSentStatus':status.casefold()=='video sent','datedSendStatus':bool(video_day),
            'reportedVideoSentDate':video_day,'reportedFollowUpSentDate':follow_day,
            'sourceDateBasis':'Literal worksheet date fields; activity reports, not native send/delivery proof.',
            'syncedToPipedriveFlag':str(item.get('Synced to Pipedrive') or '').strip().casefold() in {'true','yes'}}
        rows.append(row)
        if key: groups[key].append(row)
        for when,kind,field,content in [(video_day,'Send status','Video Sent Date','video'),(follow_day,'Follow-up status','Follow-up Sent Date','unspecified')]:
            if when:
                dated.append({'date':when,'contactId':ident,'sourceRow':line,'type':kind,'sourceField':field,
                    'channel':'unspecified','contentType':content,'datePrecision':'day','sourceTimezone':None,
                    'basis':'Self-reported literal worksheet date; exact send time and delivery are unverified.'})
            elif item.get(field):
                invalid.append({'sourceRow':line,'profileId':ident,'field':field,'reason':'Non-date value excluded; raw text retained privately.'})
    sheet_people = people(row_dicts(accepted), set(groups))
    accepted_by = {r['profileId']:r for r in sheet_people}
    exact_conn = [r for r in rows if r['connectedAt']]
    assert all(r['connected'] and accepted_by.get(r['id'],{}).get('connectedAt') == r['connectedAt'] for r in exact_conn)
    for row in exact_conn:
        row.update(connectedAtDatePrecision='day',connectedAtSourceTimezone=None,
            connectedAtEvidenceBasis='Connected At helper matched the exact accepted-profile date attribute; timezone and event instant unknown.')
    prior_profiles = {r['profileId']:r for r in prior['waalaxy']['sheetSubset']['rows']}
    subset = population(sheet_people,set(prior_profiles))
    subset.update(sourceSpreadsheetId=ID,sourceTabId=1939678986,sourceTab='Accepted Connections (Video Prospects)',
        returnedDataRows=len(accepted)-1,scope='Selected connected Video DM and Pulley prospect lists, not account-wide Waalaxy coverage.',
        dateBasis='Date-only first/last prospect attributes. Workbook timezone America/Los_Angeles; upstream event timezone unreported. Not a complete event history.',
        collectionCompleteWithinTab=True,upstreamExportCompleteForAccount=False)
    subset_patch={'sheetSubset':subset,'sheetSubsetCollectedAt':stamp,'sheetSubsetUpstreamSyncAt':None,
        'sheetSubsetAccountVerification':{'senderAccountId':None,'independentlyVerified':False,
            'basis':'User-identified Charles workflow; workbook does not carry the native sender account ID.'}}
    actions=Counter(r['action'] for r in rows)
    duplicates=[{'profile':k,'rows':[r['sourceRow'] for r in vals], 'actions':sorted({r['action'] for r in vals}),
                 'statuses':sorted({r['status'] for r in vals})} for k,vals in groups.items() if len(vals)>1]
    summary={'sourceRows':len(rows),'uniqueProfiles':len(groups),'rowsMissingProfile':sum(not r['linkedin'] for r in rows),
        'readyRows':actions['Ready for video DM'],'sheetCompletedRows':actions['Already sent/completed'],
        'explicitSendStatusRows':sum(r['explicitSendStatus'] for r in rows),'reportedVideoSentStatusRows':sum(r['reportedVideoSentStatus'] for r in rows),
        'datedSendStatusRows':sum(r['datedSendStatus'] for r in rows),'reportedFollowUpDateRows':sum(bool(r['reportedFollowUpSentDate']) for r in rows),
        'followUpRows':sum(r['followUp']=='Follow-up Needed' for r in rows),'manualCheckRows':sum(r['followUp']=='Manual Check' for r in rows),
        'reviewRows':actions['Review'],'awaitingConnectionRows':actions['Awaiting connection'],'skipRows':actions['Skip'],
        'duplicates':len(duplicates),'duplicateExtraRows':sum(len(d['rows'])-1 for d in duplicates),
        'conflictingProfiles':sum(len(d['actions'])>1 for d in duplicates),'acceptedConnectionRecords':len(accepted)-1,
        'connectedRows':sum(r['connected'] for r in rows),'rowsWithDealId':sum(bool(r['dealId']) for r in rows),
        'syncedToPipedriveFlagRows':sum(r['syncedToPipedriveFlag'] for r in rows),'recordingLinkRows':sum(r['hasRecordingLink'] for r in rows),
        'recordingFieldNonemptyRows':sum(r['hasRecordingFieldContent'] for r in rows),
        'recordingFieldNonUrlNotes':sum(r['recordingFieldKind']=='non_url_note' for r in rows),'newRowsInPeriod':None}
    before_ids, after_ids = Counter(map(stable,old['rows'])), Counter(map(stable,rows))
    before_profiles = {r['id'] for r in old['rows'] if r['linkedin']}
    delta={'basis':'First observed between source snapshots; not row creation timestamps or message dates.',
        'fromSnapshotAt':old['snapshotAt'],'toSnapshotAt':stamp,'additionalRowsObserved':sum((after_ids-before_ids).values()),
        'rowsNoLongerObserved':sum((before_ids-after_ids).values()),'netSourceRows':len(rows)-len(old['rows']),
        'newUniqueProfilesObserved':len(set(groups)-before_profiles), 'uniqueProfilesNoLongerObserved':len(before_profiles-set(groups)),
        'summaryChanges':{k:v-old['summary'][k] for k,v in summary.items() if isinstance(v,int) and isinstance(old['summary'].get(k),int)},
        'note':'Both snapshots span more than the selected reporting period. Differences must not be treated as period additions, sends or replies.'}
    # The later sheet can overwrite a reported date. Preserve any prior report
    # whose typed profile/date pair is absent; keep archive outside current KPIs.
    current_keys={(a['contactId'],a['type'],a['date']) for a in dated}
    archived=deepcopy(old.get('retainedHistoricalWorksheetReports') or [])
    archive_keys={(a.get('contactId') or a.get('profileId') or a.get('profile'),a['type'],a['date']) for a in archived}
    older_by_row={r['sourceRow']:r for r in old['rows']}
    historical_new=0
    for a in old['datedActions']:
        k=(a['contactId'],a['type'],a['date'])
        if k not in current_keys and k not in archive_keys:
            previous=older_by_row.get(a['sourceRow'],{})
            archived.append({**a,'company':previous.get('company'),'contact':previous.get('contact'),
                'historicalSourceRow':a['sourceRow'],'sourceInventorySnapshotAt':old['snapshotAt']})
            archive_keys.add(k); historical_new+=1
    accepted_raw=[r for _,r in row_dicts(accepted)]
    date_cells=load('date_and_helper_cells.json')
    date_data=date_cells['sheets'][0]['data'][0]
    assert date_data['startColumn']==19 and not any(c.get('userEnteredValue',{}).get('formulaValue') for row in date_data['rowData'] for c in row.get('values',[]))
    cell_dates={(n,i):c.get('formattedValue') for n,row in enumerate(date_data['rowData'],1) for i,c in enumerate(row.get('values',[]),19)}
    assert all(cell_dates[a['sourceRow'],19 if a['type']=='Send status' else 20] == a['date'] for a in dated)
    crm_matches=evaluate_crm(rows)
    current.update(snapshotAt=stamp,status='available',upstreamSyncAt=None,sourceUrl=f'https://docs.google.com/spreadsheets/d/{ID}/edit',
        coverage='Complete current worksheet inventory and selected connection tab; literal source dates remain separate from native send/reply evidence.',
        summary=summary,snapshotDelta=delta,rows=rows,datedActions=sorted(dated,key=lambda a:(a['date'],a['sourceRow'],a['type'])),
        duplicateProfiles=duplicates,retainedHistoricalWorksheetReports=archived,
        sourceCoverage={'mainRange':'A1:AC5000','acceptedRange':'A1:AR1011','mainReturnedRowsIncludingHeader':len(main),
            'acceptedReturnedRowsIncludingHeader':len(accepted),'excludedNonProspectPhysicalRows':len(main)-1-len(rows),
            'completeWithinWorkbook':True,'spreadsheetTimezone':'America/Los_Angeles','upstreamSyncAt':None,
            'sourceModifiedAtBeforeAndAfter':after['modified_time'],'fileUnchangedAcrossRead':True,
            'collectionMethod':'Read-only Centripetal Google Sheets connector, bounded chunks with independent Drive clock check.'},
        connectionDiagnostics={'connectedFlagRows':summary['connectedRows'],'verifyConnectionRows':sum(r['connectionLabel']=='Verify connection' for r in rows),
            'reviewDuplicateRows':sum(r['connectionLabel']=='Review duplicate' for r in rows),
            'acceptedProfilesMatchedMain':sum(r['matchedVideoProspect'] for r in sheet_people),
            'acceptedProfilesWithoutConnectedFlag':sum(r['matchedVideoProspect'] and not any(v['connected'] for v in groups[r['profileId']]) for r in sheet_people),
            'acceptedProfilesWithoutConnectedFlagMissingDate':sum(r['matchedVideoProspect'] and not any(v['connected'] for v in groups[r['profileId']]) and not r['connectedAt'] for r in sheet_people),
            'serialConnectionDatesDecodedAndCorroborated':len(exact_conn),'helperRuleVerified':True,
            'helperRuleBasis':'Current helper formulas read. Exact accepted-profile date cross-check applied; duplicate handling and manual overrides may affect Connected flags.',
            'manualOverrideRows':sum(bool(str(r.get('Manual Connection Override') or '').strip()) for r in accepted_raw)},
        recordingFieldReview={'snapshotAt':stamp,'reviewedAt':stamp,'appliesToSnapshotAt':stamp,
            'nonemptyCells':summary['recordingFieldNonemptyRows'],'recordingUrlCells':summary['recordingLinkRows'],
            'validLoomUrls':sum(r['recordingFieldKind']=='loom_url' for r in rows),'nonUrlNotes':summary['recordingFieldNonUrlNotes'],
            'records':[{'sourceRow':r['sourceRow'],'profile':r['id'],**{k:r[k] for k in ['hasRecordingFieldContent','hasRecordingLink','recordingFieldKind','recordingFieldNote']}} for r in rows if r['hasRecordingFieldContent']],
            'basis':'Current worksheet recording-field classification; asset presence does not establish delivery.'})
    current['notes']=[
        'November 13 workbook inventory and literal date reports are current to the recorded collection timestamp. Both tab ranges were exhausted. Workbook revision clock was stable across the read.',
        'Rows first observed since the October 29 inventory cannot be dated to the selected reporting period from this comparison. No exact row-creation timestamps are supplied.',
        'Current reported send/follow-up dates are owner-reported, date-only and timezone unspecified. Worksheet completion, assets, response labels and CRM sync flags are not independent evidence of sending, delivery, receipt, viewing, replies or qualification.',
        'Selected accepted-connection attributes do not provide account-wide Waalaxy totals, and no source-timezone shift is invented for date-only values.',
        'Earlier native conversation observations and technical/CRM reviews preserve their original scope and clocks. Earlier worksheet reports absent from the current date fields are archived separately.'
    ]
    current['periodCrmCrosswalk']={'snapshotAt':review_clock,'appliesToSnapshotAt':stamp,'cohortDate':'2026-11-09','records':crm_matches,
        'basis':'Bounded deal-note checks on the nine reported follow-up profiles; eight exact profile and Loom asset matches in earlier copied worksheet context, not follow-up or reply proof.'}
    current['sourceAppearanceRefresh']=revision_appearances(rows,stamp,review_clock)
    current['notes'].append('Bounded Drive revisions independently establish at least 88 distinct new stable source identities (93 additional row occurrences) after November 9 12:22 Mountain and by November 12 22:50 Mountain. Six further distinct appearances are bounded to partial November 13. One midnight-straddling appearance is unassigned. Exact creation dates are not supplied.')
    current['provenance']=[source(p) for p in [*main_files,*accepted_files,PRIVATE/'drive_file_before.json',PRIVATE/'drive_file_after.json',PRIVATE/'date_and_helper_cells.json']]
    assert current['messageDateReview']==old['messageDateReview']
    assert len(rows)==len({r['sourceRow'] for r in rows}) and len(dated)==summary['datedSendStatusRows']+summary['reportedFollowUpDateRows']
    assert len(crm_matches)==8
    window=[a for a in dated if START<=a['date']<=END]
    partial=[a for a in dated if a['date']==PARTIAL]
    report={'snapshotAt':stamp,'priorSnapshotAt':old['snapshotAt'],'period':{'start':START,'end':END,'partialDate':PARTIAL,'displayTimezone':'America/Denver','worksheetSourceDateTimezone':None},
        'summary':summary,'delta':delta,'acceptedSubsetMetrics':subset['metrics'],
        'periodWorksheetReports':dict(Counter(a['type'] for a in window)),
        'partialWorksheetReports':dict(Counter(a['type'] for a in partial)),
        'periodSelectedPersonAttributes':dict(Counter(field for r in sheet_people for field in ['connectedAt','connectionRequestDate','importDate','firstMessageAt','lastMessageAt','lastReplyAt'] if r[field] and START<=r[field]<=END)),
        'historicalWorksheetReportsPreserved':len(archived),'newlyArchivedHistoricalWorksheetReports':historical_new,
        'boundedAppearanceReview':{k:v for k,v in current['sourceAppearanceRefresh'].items() if k!='records'},
        'nativePlatformEventsCarriedForward':len(old['messageDateReview']['platformObservedEvents']),'nativePlatformEventsAddedByWorkbook':0,
        'invalidLiteralDateFields':invalid,'crmFollowUpAssetContextMatches':len(crm_matches),'crmPeriodFollowUpCorroborations':0,
        'warnings':current['notes']}
    write('video.json',current)
    write('waalaxy_sheet_subset_patch.json',subset_patch)
    write('summary.json',report)
    write('crm_worksheet_crosswalk.json',current['periodCrmCrosswalk'])
    write('source_appearance_refresh.json',current['sourceAppearanceRefresh'])
    print(json.dumps(report,indent=2,ensure_ascii=False))


if __name__=='__main__':
    build()
