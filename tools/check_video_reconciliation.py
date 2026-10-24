"""Regression checks for recording evidence, current source dates and scoped CRM joins."""
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import copy
import json
from recording_evidence import recording_evidence_fields, apply_video_evidence_reviews
from prepare_shared_snapshot import curate_snapshot

ROOT=Path(__file__).resolve().parents[1]


def row_key(row):
    return (row['sourceRow'], row.get('id') or row.get('profile'))


def check_video_reconciliation(data):
    video=data['video'];review=video['crmReconciliation'];rows=video['rows'];summary=video['summary']
    by_key={row_key(r):r for r in rows}
    assert len(by_key)==len(rows)==summary['sourceRows'], 'Repeated source row/profile identity'
    assert len({r['sourceRow'] for r in rows})==len(rows)
    fields=video['recordingFieldReview']
    assert fields['appliesToSnapshotAt']==review['appliesToSnapshotAt']==video['snapshotAt'], 'Stale recording/CRM crosswalk'
    evidence={row_key(r):r for r in fields['records']}
    assert len(evidence)==len(fields['records']) and set(evidence)<=set(by_key)
    for key,proof in evidence.items():
        for field in ('hasRecordingFieldContent','hasRecordingLink','recordingFieldKind','recordingFieldNote'):
            assert by_key[key].get(field)==proof[field], 'Current recording classification differs from scoped evidence'
    assert fields['nonemptyCells']==sum(bool(r.get('hasRecordingFieldContent')) for r in rows)
    assert fields['validLoomUrls']==sum(r.get('recordingFieldKind')=='loom_url' for r in rows)
    assert fields['nonUrlNotes']==summary['recordingFieldNonUrlNotes']==sum(r.get('recordingFieldKind')=='non_url_note' for r in rows)
    assert summary['recordingLinkRows']==sum(bool(r.get('hasRecordingLink')) for r in rows)
    for row in rows:
        kind=row.get('recordingFieldKind','empty')
        assert row['hasRecordingLink']==(kind in ('loom_url','other_url'))
        assert bool(row.get('hasRecordingFieldContent'))==(kind!='empty')
        if kind=='non_url_note':assert row['recordingFieldNote']
        else:assert row.get('recordingFieldNote') is None
    start=review.get('cohortStartDate') or review['cohortDate']
    end=review.get('cohortEndDate') or review['cohortDate']
    assert start<=end
    if any('reportedVideoSentDate' in r for r in rows):
        cohort={row_key(r):r for r in rows if r.get('reportedVideoSentDate') and start<=r['reportedVideoSentDate']<=end}
    else:
        dated={(r['sourceRow'],r['contactId']) for r in video['datedActions'] if r['type']=='Send status' and start<=r['date']<=end}
        cohort={key:by_key[key] for key in dated}
    records={row_key(r):r for r in review['records']}
    assert len(records)==len(review['records'])==len(cohort)==review['selfReportedSentRows']
    assert set(records)==set(cohort), 'Cohort record/profile joins do not match current literal source dates'
    asset_keys={key for key,r in cohort.items() if r.get('recordingFieldKind')=='loom_url'}
    no_asset_keys=set(cohort)-asset_keys
    assert len(asset_keys)==review['validVideoAssetRows']
    # Current blank recording cells are not historical non-URL notes.
    assert len(no_asset_keys)==review.get('statusRowsWithoutVideoAsset',review['messageNoteWithoutAssetRows'])
    for key,record in records.items():
        row=by_key[key]
        assert record['recordingFieldKind']==row['recordingFieldKind']
        assert record.get('actualSendInferredFromCrm') is not True
        if 'reportedVideoSentDate' in record:
            assert record['reportedVideoSentDate']==row.get('reportedVideoSentDate')
        if key in asset_keys:
            assert record['crmDealId'] and record['crmNoteIds']
            assert row.get('matchedCrmDealId')==record['crmDealId']
            if 'sourceLoomAssetId' in record:
                assert record['sourceLoomAssetId']==row.get('recordingAssetId')
                assert record['profileMatchVerified'] and record['assetMatchVerified']
        else:
            assert not record.get('assetMatchVerified')
    matches=sum(bool(records[key].get('crmDealId')) for key in asset_keys)
    assert matches==review['videoAssetCohortCrmMatches']
    assert len(asset_keys)-matches==review['expectedVideoCrmMissing']
    identity=review.get('currentIdentityAssetReview')
    if identity:
        eligible=[r for r in rows if r.get('dealId') or r.get('recordingFieldKind')=='loom_url']
        assert identity['rowsReviewed']==len(eligible)
        assert 0<=identity['exactProfileMatches']<=identity['currentCrmRecordsEvidenced']<=len(eligible)
        assert identity['profileMatchedInPersonField']+identity['profileMatchedInDealNote']==identity['exactProfileMatches']
        assert identity['sourceLoomUrls']==sum(r['recordingFieldKind']=='loom_url' for r in eligible)
        assert 0<=identity['sameAssetInCrmNotes']<=identity['sourceLoomUrls']
        eligible_rows={r['sourceRow'] for r in eligible}
        for gap in review.get('specificLinkageGaps',[]):
            source=next(r for r in rows if r['sourceRow']==gap['sourceRow'])
            assert source['company']==gap['company'], 'Gap refers to an old physical row'
            assert gap['sourceRow'] in eligible_rows or (source.get('reportedVideoSentStatus') and not source.get('reportedVideoSentDate')), 'Gap is outside the declared inventory/undated-status scopes'
    if any('reportedVideoSentDate' in r for r in rows):
        assert summary['datedSendStatusRows']==sum(bool(r.get('reportedVideoSentDate')) for r in rows)
        assert summary['reportedVideoSentStatusRows']==sum(r['status']=='Video Sent' for r in rows)
        for row in rows:
            assert row['reportedVideoSentStatus']==(row['status']=='Video Sent')
            assert row['datedSendStatus']==bool(row.get('reportedVideoSentDate'))
        assert summary['reportedFollowUpDateRows']==sum(bool(r.get('reportedFollowUpSentDate')) for r in rows)
        expected={(r['sourceRow'],r['id'],'Send status',r['reportedVideoSentDate']) for r in rows if r.get('reportedVideoSentDate')}
        expected|={(r['sourceRow'],r['id'],'Follow-up status',r['reportedFollowUpSentDate']) for r in rows if r.get('reportedFollowUpSentDate')}
        actual={(r['sourceRow'],r['contactId'],r['type'],r['date']) for r in video['datedActions']}
        assert len(actual)==len(video['datedActions']) and actual==expected, 'Current ledger must use literal current worksheet dates'
        for event in video['datedActions']:
            assert event['datePrecision']=='day' and event['sourceTimezone'] is None
            assert event['sourceField']==('Video Sent Date' if event['type']=='Send status' else 'Follow-up Sent Date')
        current_keys={(r['contactId'],r['type'],r['date']) for r in video['datedActions']}
        history=video.get('retainedHistoricalWorksheetReports',[])
        history_keys={(r['contactId'],r['type'],r['date']) for r in history}
        assert len(history_keys)==len(history) and not current_keys&history_keys
        for event in history:
            assert event['historicalOnly'] is True and event['sourceInventorySnapshotAt']!=video['snapshotAt']
    assert video['sourceVerification']['verifiedVideoDmSends'] is None
    assert video['sourceVerification']['verifiedReplyEvents'] is None


def regression_tests(data):
    video=data['video'];rows=video['rows']
    target=next(r for r in rows if r.get('hasRecordingFieldContent'))
    key=row_key(target)
    incorrect=copy.deepcopy(data)
    original_ids={row_key(r):r.get('dealId') for r in rows}
    changed=next(r for r in incorrect['video']['rows'] if row_key(r)==key)
    changed.update(hasRecordingLink=not target['hasRecordingLink'],recordingFieldKind='incorrect')
    fixed=curate_snapshot(incorrect)
    restored=next(r for r in fixed['video']['rows'] if row_key(r)==key)
    assert restored['hasRecordingLink']==target['hasRecordingLink']
    assert restored['recordingFieldKind']==target['recordingFieldKind']
    assert original_ids=={row_key(r):r.get('dealId') for r in fixed['video']['rows']}
    # A review for an older inventory cannot overwrite a newer source cell.
    newer=copy.deepcopy(video)
    newer['snapshotAt']=(datetime.fromisoformat(video['snapshotAt'].replace('Z','+00:00'))+timedelta(seconds=1)).isoformat()
    changed=next(r for r in newer['rows'] if row_key(r)==key)
    changed.update(hasRecordingLink=False,recordingFieldKind='empty',hasRecordingFieldContent=False,recordingFieldNote=None)
    apply_video_evidence_reviews(newer)
    assert changed['hasRecordingLink'] is False and changed['recordingFieldKind']=='empty'
    for mutate in (
        lambda d:d['video']['crmReconciliation'].update(appliesToSnapshotAt='2000-01-01T00:00:00Z'),
        lambda d:d['video']['crmReconciliation']['records'][0].update(sourceRow=-1),
    ):
        invalid=copy.deepcopy(data);mutate(invalid)
        try:check_video_reconciliation(invalid)
        except AssertionError:pass
        else:raise AssertionError('A stale or mismatched source crosswalk was accepted')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=ROOT/'data/shared-dashboard.json')
    args=parser.parse_args()
    for value in ('LI DM - had already connected on LI','Sent a video DM without loom','javascript:alert(1)','https://[bad'):
        fields=recording_evidence_fields(value)
        assert fields['hasRecordingLink'] is False and fields['recordingFieldKind']=='non_url_note'
    assert recording_evidence_fields(None)['recordingFieldKind']=='empty'
    assert recording_evidence_fields('https://www.loom.com/share/'+'a'*32)['recordingFieldKind']=='loom_url'
    assert recording_evidence_fields('https://loom.com.example.org/share/'+'a'*32)['recordingFieldKind']=='other_url'
    assert apply_video_evidence_reviews({})=={}
    data=json.loads(args.snapshot.read_text());check_video_reconciliation(data);regression_tests(data)
    print('Video reconciliation: scoped recording/identity joins, current literal dates, historical report separation, original IDs and source-time guards passed.')


if __name__=='__main__':main()
