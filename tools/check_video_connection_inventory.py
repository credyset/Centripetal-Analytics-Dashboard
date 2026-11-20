"""Check bounded current-helper reviews without changing historical source proof."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

from video_connection_inventory import validate_video_connection_inventory

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    rows = [dict(sourceRow=2, id='buyer-a', company='Company A', contact='Buyer A', connected=False, connectedAt=None, action='Awaiting connection', connectionLabel='Not connected'),
            dict(sourceRow=3, id='buyer-b', company='Company B', contact='Buyer B', connected=False, connectedAt=None, action='Awaiting connection', connectionLabel='Not connected'),
            dict(sourceRow=4, id='duplicate', company='Company C', contact='Buyer C', connected=False, connectedAt=None, action='Review', connectionLabel='Review duplicate'),
            dict(sourceRow=5, id='duplicate', company='Company C', contact='Buyer C', connected=False, connectedAt=None, action='Review', connectionLabel='Review duplicate')]
    video = dict(snapshotAt='2026-11-20T05:18:16Z', rows=rows,
        companyOnlyTargets=[{'sourceRow': 6, 'company': 'Company-only target'}],
        summary=dict(sourceRows=4, uniqueProfiles=3, readyRows=0, connectedRows=0, reviewRows=2, awaitingConnectionRows=2, acceptedConnectionRecords=2),
        connectionDiagnostics=dict(verifyConnectionRows=0, acceptedProfilesMatchedMain=0, acceptedProfilesWithoutConnectedFlag=0, acceptedProfilesWithoutConnectedFlagMissingDate=0, serialConnectionDatesDecodedAndCorroborated=0),
        datedActions=[dict(date='2026-11-12', type='Follow-up status')],
        messageDateReview={'platformObservedEvents':[{'date':'2026-11-12','direction':'outbound'}]},
        sourceAppearanceRefresh={'rows':[]})
    base = dict(readyRows=0, connectedRows=0, reviewRows=2, awaitingConnectionRows=2, currentLedgerRows=2, ledgerHelperConnectedRows=1, ledgerHelperVerifyRows=1, verifyConnectionRows=0, notConnectedRows=2, acceptedProfilesMatchedMain=0, acceptedProfilesWithoutConnectedFlag=0, acceptedProfilesWithoutConnectedFlagMissingDate=0, serialConnectionDatesDecodedAndCorroborated=0)
    current = dict(readyRows=1, connectedRows=1, reviewRows=3, awaitingConnectionRows=0, currentLedgerRows=5, ledgerHelperConnectedRows=3, ledgerHelperVerifyRows=2, verifyConnectionRows=1, notConnectedRows=0, acceptedProfilesMatchedMain=3, acceptedProfilesWithoutConnectedFlag=2, acceptedProfilesWithoutConnectedFlagMissingDate=1, serialConnectionDatesDecodedAndCorroborated=1)
    records = []
    for row, label, ledger_row, ledger_date in [(rows[0], 'Connected', 4, '2026-11-19'), (rows[1], 'Verify connection', 5, None), (rows[2], 'Review duplicate', 6, '2026-11-19'), (rows[3], 'Review duplicate', 6, '2026-11-19')]:
        before = {key:row[key] for key in ('connected','connectedAt','action')};before['connectionMatchCount']=0
        after = dict(connected=label=='Connected', connectedAt=ledger_date if label=='Connected' else None, action='Ready for video DM' if label=='Connected' else 'Review', connectionMatchCount=1)
        raw = {'Connection Match Count':dict(before='0',after='1')}
        if label!=row['connectionLabel']:raw['Connected?']=dict(before=row['connectionLabel'],after=label)
        if after['connectedAt']:raw['Connected At']=dict(before='',after='46345')
        if after['action']!=before['action']:raw['DM Action']=dict(before=before['action'],after=after['action'])
        records.append(dict(sourceRow=row['sourceRow'], id=row['id'], company=row['company'], contact=row['contact'], before=before, after=after, sourceConnectionLabel=label,
            ledgerSourceRow=ledger_row, ledgerProfileId=row['id'], ledgerRecordedDate=ledger_date, sourceFieldChanges=raw,
            eventTimezone=None, heldCallConfirmed=None, heldStatus='Not established by this helper review',datePrecision='day'if after['connectedAt']else'unknown'))
    def counts(label_counts,actions,ready,connected):
        return dict(contactRows=4,uniqueProfiles=3,companyOnlyTargetRows=1,allTargetRows=5,readyRows=ready,connectedRows=connected,connectionLabels=label_counts,actionCounts=actions)
    captures=[]
    for name,area,size,clock in [('prior-main-1.json','Main!A1:AC750',3,None),('prior-main-2.json','Main!A751:AC5002',2,None),('prior-ledger.json',"'Ledger'!A1:AR1011",3,None),('main.json','Main!A1:AC5002',5,'2026-11-20T16:00:00Z'),('ledger.json',"'Ledger'!A1:AN1000",6,'2026-11-20T16:01:00Z'),('helpers.json',"'Ledger'!AO1:AR1011",6,'2026-11-20T16:02:00Z')]:
        captures.append(dict(file=name,range=area,returnedRowsIncludingHeader=size,capturedAt=clock,sha256='a'*64,captureClockBasis='Explicit capture clock'if clock else'Prior separately verified bounded read'))
    source_counts=Counter(key for record in records for key in record['sourceFieldChanges'])
    review = dict(schemaVersion=1,status='current_bounded_helper_inventory',appliesToSnapshotAt=video['snapshotAt'],parentVideoInventorySnapshotAt=video['snapshotAt'],snapshotAt='2026-11-20T16:02:00Z',reviewedAt='2026-11-20T16:02:00Z',atomicSnapshot=False,
        rowChangeAllowlist=['connected','connectedAt','action','connectionMatchCount'],literalSourceColumnAllowlist=['Connected?','Connected At','DM Action','Connection Match Count'],records=records,baseSummary=base,newSummary=current,sourceCaptures=captures,
        coverage=dict(completeCurrentMainAndLedgerValues=True,completeConnectionEventStream=False,sourceRecordedDatesIndependentlyVerifiedAsAcceptanceEvents=False,reportingPeriodConnectionsAdded=0),
        summary=dict(prior=counts({'Not connected':2,'Review duplicate':2},{'Awaiting connection':2,'Review':2},0,0),current=counts({'Connected':1,'Verify connection':1,'Review duplicate':2},{'Ready for video DM':1,'Review':3},1,1),
            priorLedgerRows=2,currentLedgerRows=5,newConnectionRecords=3,inventoryDeltaOnly=True,newConnectionRecordsArePeriodConnections=False,newLedgerRowsWithRecordedDate=2,newLedgerRowsWithoutRecordedDate=1,
            ledgerRowsWithRecordedDate=3,ledgerRowsWithoutRecordedDate=2,ledgerHelperVerificationCounts={'Connected':3,'Verify connection':2},changedContactRows=4,changedHelperCells=sum(source_counts.values()),changedSourceColumnCounts=dict(source_counts),acceptedProfilesMatchedMain=3,acceptedProfilesWithoutConnectedFlag=2,acceptedProfilesWithoutConnectedFlagMissingDate=1,serialConnectionDatesDecodedAndCorroborated=1))
    video['connectionInventoryReview']=review
    return video


def check_rejections(video):
    def record(value):return value['connectionInventoryReview']['records'][0]
    mutations = [
        lambda v:v['connectionInventoryReview'].update(appliesToSnapshotAt='2000-01-01T00:00:00Z'),
        lambda v:record(v).update(id='another-profile'),
        lambda v:record(v).update(sourceRow=-1),
        lambda v:record(v).update(company='Another company'),
        lambda v:record(v).update(contact='Another contact'),
        lambda v:record(v)['before'].update(connected=True),
        lambda v:record(v)['before'].update(connectedAt='2000-01-01'),
        lambda v:record(v)['before'].update(action='Review'),
        lambda v:v['connectionInventoryReview']['records'].append(deepcopy(record(v))),
        lambda v:record(v)['after'].update(status='Sent'),
        lambda v:v['connectionInventoryReview']['newSummary'].update(readyRows=999),
        lambda v:v['connectionInventoryReview']['baseSummary'].update(connectedRows=999),
        lambda v:record(v).update(ledgerProfileId='another-profile'),
        lambda v:record(v).update(ledgerRecordedDate='2000-01-01'),
        lambda v:v['connectionInventoryReview']['summary'].update(newConnectionRecordsArePeriodConnections=True),
        lambda v:v['connectionInventoryReview']['sourceCaptures'][0].update(sha256='not-a-sha'),
        lambda v:v['connectionInventoryReview'].update(reviewedAt='2026-11-20'),
    ]
    for mutate in mutations:
        invalid=deepcopy(video);mutate(invalid)
        try:validate_video_connection_inventory(invalid)
        except (AssertionError,ValueError):pass
        else:raise AssertionError('A corrupt current helper review was accepted')
    # The only omitted base field exception is match count. If it exists, it
    # must match too; a missing action or connection day is never waived.
    with_count=deepcopy(video)
    first=with_count['connectionInventoryReview']['records'][0]
    next(row for row in with_count['rows']if row['sourceRow']==first['sourceRow'])['connectionMatchCount']=first['before']['connectionMatchCount']+1
    try:validate_video_connection_inventory(with_count)
    except AssertionError:pass
    else:raise AssertionError('Populated prior match count was ignored')
    verify=next((r for r in video['connectionInventoryReview']['records']if r['sourceConnectionLabel']=='Verify connection'),None)
    if verify:
        invalid=deepcopy(video);next(r for r in invalid['connectionInventoryReview']['records']if r['sourceRow']==verify['sourceRow'])['after'].update(connected=True)
        try:validate_video_connection_inventory(invalid)
        except AssertionError:pass
        else:raise AssertionError('Undated Verify connection row became a confirmed connection')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,default=ROOT/'data/shared-dashboard.json')
    args=parser.parse_args()
    synthetic=fixture();original=deepcopy(synthetic)
    validate_video_connection_inventory(synthetic);check_rejections(synthetic)
    assert synthetic==original,'Schema validation mutated the video source'
    assert validate_video_connection_inventory({'rows':[]}) is True
    snapshot=json.loads(args.snapshot.read_text());video=snapshot['video'];before=deepcopy(video)
    validate_video_connection_inventory(video)
    if video.get('connectionInventoryReview'):
        check_rejections(video)
        captures=video['connectionInventoryReview']['sourceCaptures']
        private=ROOT/'data/private/qc_2026_11_20/video'
        if all((private/item['file']).exists()for item in captures):
            for item in captures:
                assert hashlib.sha256((private/item['file']).read_bytes()).hexdigest()==item['sha256'],'Retained source capture changed'
        assert video==before,'Current helper validation mutated historical source data'
        # An omitted child on a same-source import must not erase a later
        # independently dated helper review or borrow the parent source clock.
        from prepare_shared_snapshot import preserve_newer_shared_sources
        incoming=deepcopy(snapshot)
        incoming['video'].pop('connectionInventoryReview')
        incoming['sources']=[card for card in incoming['sources']if card['id']!='video_connection_inventory']
        kept=preserve_newer_shared_sources(incoming,snapshot)
        assert kept['video']['connectionInventoryReview']==video['connectionInventoryReview']
        assert kept['video']['snapshotAt']==video['snapshotAt']
        assert next(card for card in kept['sources']if card['id']=='video_connection_inventory')['asOf']==video['connectionInventoryReview']['snapshotAt']
        conflicting=deepcopy(snapshot)
        conflicting['video']['connectionInventoryReview']['newSummary']['readyRows']+=1
        try:preserve_newer_shared_sources(conflicting,snapshot)
        except AssertionError:pass
        else:raise AssertionError('Conflicting helper reviews shared an independent collection clock')
    subprocess.run(['node',str(ROOT/'tools/check_video_connection_inventory.js'),str(args.snapshot)],check=True,cwd=ROOT)
    print('Video helper inventory: exact schema/identity/counter/source guards, undated holds and immutable historical source checks passed.')


if __name__=='__main__':main()
