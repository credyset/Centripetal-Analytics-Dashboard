"""Regression fixtures for lost serial dates and stale snapshot comparisons."""
from datetime import date, timedelta
import copy

from audit_sheet_reporting_2026_10_29 import audit, connection_diagnostics, export_overlap
from refresh_sheets_2026_10_28 import valid_date
from audit_native_receipts_2026_10_29 import selected_receipt
from apply_refresh_2026_10_23 import merge_message_review


def fails(callback):
    try:
        callback()
    except AssertionError:
        return
    raise AssertionError('Invalid source comparison was accepted')


def main():
    context = {'date_column': 'Connected At', 'reference_day': '2026-10-29'}
    assert valid_date('45687', **context) == '2025-01-30'
    assert valid_date(45687, **context) == '2025-01-30'
    assert valid_date('45687.0', **context) == '2025-01-30'
    assert valid_date('2025-01-30', **context) == '2025-01-30'
    for value in ('2026', '45687.5', '-45687', 'not a date', '99999', ''):
        assert valid_date(value, **context) is None
    assert valid_date('45687') is None
    assert valid_date('45687', date_column='rank', reference_day='2026-10-29') is None
    future_serial = str((date(2027,1,1)-date(1899,12,30)).days)
    assert valid_date(future_serial, **context) is None
    video = {'snapshotAt': '2026-10-29T05:00:00Z', 'rows': [
        {'id': 'fixture-alice', 'sourceRow': 2, 'company': 'Fixture company', 'contact': 'Alice Example',
         'connected': True, 'connectedAt': None, 'reportedVideoSentDate': None, 'reportedFollowUpSentDate': None,
         'recordingAssetId': None, 'linkedin': 'https://www.linkedin.com/in/fixture-alice/'}],
        'connectionDiagnostics': {'acceptedProfilesWithoutConnectedFlag': 0},
        'messageDateReview': {'platformObservedEvents': []}}
    subset = {'rows': [
        {'profileId': 'fixture-alice','connectedAt':'2025-01-30','matchedVideoProspect':True},
        {'profileId': 'sheet-only','connectedAt':None,'matchedVideoProspect':False}],
        'metrics': {'connectedProspects':2}}
    export = {'rows':[{'profileId':'fixture-alice'},{'profileId':'csv-only'}],
        'metrics':{'connectedProspects':2}, 'reviewedAt':'2026-10-22T01:00:00Z',
        'sourceObservationThrough':'2026-10-20', 'overlapWithSheet':{'sameProfiles':1,'onlyInExports':1,'onlyInSheet':0}}
    overlap = export_overlap(export, subset, video['snapshotAt'], '2026-10-29T06:00:00Z')
    assert (overlap['sameProfiles'],overlap['onlyInExports'],overlap['onlyInSheet']) == (1,1,1)
    assert overlap['appliesToSheetSnapshotAt'] == video['snapshotAt']
    assert overlap['newSourceDataCollected'] is False and overlap['actualMessageEventsAdded'] == 0
    broken = copy.deepcopy(subset); broken['rows'].append(broken['rows'][0])
    fails(lambda: export_overlap(export,broken,video['snapshotAt'],'2026-10-29T06:00:00Z'))
    headers = ['field-'+str(i) for i in range(29)]
    for index, label in ((1,'org'),(5,'contact'),(19,'Video Sent Date'),(20,'Follow-up Sent Date'),(22,'Connected At')):
        headers[index] = label
    raw = ['']*29; raw[1]='Fixture company'; raw[5]='Alice Example'; raw[22]='45687'
    snapshot = {'video':video,'waalaxy':{'sheetSubset':subset,'sheetSubsetCollectedAt':video['snapshotAt'],'selectedExportSnapshot':export}}
    patches, report = audit(snapshot,[headers,raw],'2026-10-29T06:00:00Z')
    assert patches['videoRows'][0]['connectedAt'] == '2025-01-30'
    assert video['rows'][0]['connectedAt'] is None, 'Audit mutated its input'
    assert patches['waalaxySelectedExportSnapshot']['reviewedAt'] == export['reviewedAt']
    old = patches['waalaxySelectedExportSnapshot']['retainedPriorOverlapReviews'][0]
    assert old['onlyInSheet'] == 0 and old['originalComparisonSheetClockUnreported'] is True
    assert report['nativeSourceOverlap']['newNativeEventsAddedByThisAudit'] == 0
    assert report['issuesResolved']['decodedConnectionDateRows'] == 1
    assert patches['videoConnectionDiagnostics']['acceptedProfilesWithoutConnectedFlagMissingDate'] == 0
    already_fixed = copy.deepcopy(snapshot)
    already_fixed['video']['rows'] = patches['videoRows']
    again, again_report = audit(already_fixed,[headers,raw],'2026-10-29T07:00:00Z')
    assert not again['videoConnectionDateCorrections']['changes']
    assert again['videoConnectionDiagnostics']['serialConnectionDatesDecodedAndCorroborated'] == 1
    assert again_report['issuesResolved']['decodedConnectionDateRows'] == 0
    # A plausible serial alone is insufficient for an automatic correction:
    # exact accepted-profile date corroboration is required as a second source.
    conflicting = copy.deepcopy(snapshot)
    conflicting['waalaxy']['sheetSubset']['rows'][0]['connectedAt'] = '2025-01-31'
    fails(lambda: audit(conflicting,[headers,raw],'2026-10-29T06:00:00Z'))
    no_flag = copy.deepcopy(video)
    no_flag['rows'][0]['connected'] = False
    assert connection_diagnostics(no_flag,subset)['acceptedProfilesWithoutConnectedFlagMissingDate'] == 0
    missing_date = copy.deepcopy(subset); missing_date['rows'][0]['connectedAt'] = None
    assert connection_diagnostics(no_flag,missing_date)['acceptedProfilesWithoutConnectedFlagMissingDate'] == 1
    receipt_meta = {'profile':'fixture-alice','contact':'Alice Example','account':'Charles Solomon',
        'profileIdentityVerified':True,'observedAt':'2026-10-29T06:00:00Z'}
    receipt_raw = '\n'.join([
        'button Open the options list in your conversation with Charles Solomon and Alice Example',
        'content list','text OCT 21','link View Charles’ profile Charles Solomon, Value: fixture',
        'text • 9:00 AM','text Earlier video https://www.loom.com/share/'+'a'*32,
        'image Seen by Alice Example at 10:00 AM.',
        'text MONDAY','link View Charles’ profile Charles Solomon, Value: fixture',
        'text • 8:30 AM','text What did you think of the video?',
        'text entry area Write a message'])
    selected = {'dateLabel':'MONDAY','time':'8:30 AM','direction':'outbound','date':'2026-10-26','kind':'video_follow_up'}
    fails(lambda: selected_receipt(receipt_raw,receipt_meta,selected))
    own = receipt_raw.replace('text entry area','image Seen by Alice Example at 8:31 PM.\ntext entry area')
    block, marker = selected_receipt(own,receipt_meta,selected)
    assert marker['recipient']=='Alice Example' and block['displayedDateLabel']=='MONDAY'
    wrong = own.replace('image Seen by Alice Example at 8:31 PM.','image Seen by Another Person at 8:31 PM.')
    fails(lambda: selected_receipt(wrong,receipt_meta,selected))
    # The displayed clock has no receipt day; it must never become a timestamp.
    assert marker['displayedTimeWithoutDate']=='8:31 PM' and 'date' not in marker
    # A later excerpt that does not establish a marker must retain known Seen
    # evidence for the same exact message, with its original receipt clock.
    original_event = {'observationId':'fixture-original','profileId':'fixture-alice','direction':'outbound',
        'date':'2026-10-28','assetId':'a'*32,'videoIncluded':True,'dedupKey':'fixture-alice|outbound|2026-10-28|'+'a'*32,
        'observedAt':'2026-10-29T06:00:00Z','displayedTime':'12:00 PM','contentFingerprint':'b'*64,
        'platformReadReceiptObserved':True,'readReceiptDate':None,'readReceiptBasis':'Explicit own-message undated Seen marker',
        'readReceiptSourceObservedAt':'2026-10-29T06:00:00Z','readReceiptValidatedAt':'2026-10-29T06:30:00Z',
        'readReceiptAppliesTo':'linkedin_message_only','loomVideoViewedEstablished':False}
    original_review = {'snapshotAt':'2026-10-29T06:00:00Z','scope':{},'records':[],
        'platformObservedEvents':[original_event],'summary':{},'notes':[]}
    reobserved = copy.deepcopy(original_event)
    for key in ('readReceiptSourceObservedAt','readReceiptValidatedAt','readReceiptBasis'):
        reobserved.pop(key)
    reobserved.update(observationId='fixture-later',observedAt='2026-10-29T07:00:00Z',platformReadReceiptObserved=False)
    partial = {'snapshotAt':'2026-10-29T07:00:00Z','platformObservedEvents':[reobserved]}
    merged = merge_message_review(original_review,partial,video,subset,video['snapshotAt'])
    retained = merged['platformObservedEvents'][0]
    assert retained['observedAt']=='2026-10-29T07:00:00Z' and retained['platformReadReceiptObserved'] is True
    assert retained['readReceiptSourceObservedAt']=='2026-10-29T06:00:00Z'
    assert retained['readReceiptValidatedAt']=='2026-10-29T06:30:00Z'
    assert retained['readReceiptDate'] is None and retained['loomVideoViewedEstablished'] is False
    different_block = copy.deepcopy(partial)
    different_block['platformObservedEvents'][0]['contentFingerprint']='c'*64
    unborrowed = merge_message_review(original_review,different_block,video,subset,video['snapshotAt'])
    assert unborrowed['platformObservedEvents'][0]['platformReadReceiptObserved'] is False
    different_message = copy.deepcopy(partial)
    different_message['platformObservedEvents'][0].update(assetId='d'*32,dedupKey='fixture-alice|outbound|2026-10-28|'+'d'*32)
    distinct = merge_message_review(original_review,different_message,video,subset,video['snapshotAt'])
    assert len(distinct['platformObservedEvents'])==2
    assert next(e for e in distinct['platformObservedEvents'] if e['assetId']=='d'*32)['platformReadReceiptObserved'] is False
    print('Sheet reporting audit: explicit serial dates, corroboration, snapshot overlap, missing-date diagnostics and same-message Seen-marker retention without borrowing passed.')


if __name__ == '__main__':
    main()
