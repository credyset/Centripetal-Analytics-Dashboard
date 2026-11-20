/* Current helper projections must not alter historical inventory or events. */
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.join(__dirname,'..'),app=fs.readFileSync(path.join(root,'app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null}});
vm.runInContext(app,ctx);const run=code=>vm.runInContext(code,ctx),copy=value=>JSON.parse(JSON.stringify(value));
const one={sourceRow:2,id:'one',company:'Company One',contact:'Contact One',connected:false,connectedAt:null,connectionLabel:'Not connected',action:'Awaiting connection',status:'Connection Invite Sent'};
const two={sourceRow:3,id:'two',company:'Company Two',contact:'Contact Two',connected:true,connectedAt:'2026-10-01',connectionLabel:'Connected',action:'Already sent/completed',status:'Video Sent'};
const before={connected:false,connectedAt:null,action:'Awaiting connection',connectionMatchCount:0},after={connected:true,connectedAt:'2026-11-19',action:'Ready for video DM',connectionMatchCount:1};
const baseSummary={readyRows:0,connectedRows:1,reviewRows:0,awaitingConnectionRows:1,verifyConnectionRows:0,notConnectedRows:1,currentLedgerRows:1,ledgerHelperConnectedRows:1,ledgerHelperVerifyRows:0};
const newSummary={...baseSummary,readyRows:1,connectedRows:2,awaitingConnectionRows:0,notConnectedRows:0,currentLedgerRows:2,ledgerHelperConnectedRows:2};
const review={appliesToSnapshotAt:'2026-11-20T05:18:16Z',snapshotAt:'2026-11-20T16:37:37Z',reviewedAt:'2026-11-20T16:37:37Z',rowChangeAllowlist:['connected','connectedAt','action','connectionMatchCount'],baseSummary,newSummary,
 records:[{sourceRow:2,id:'one',company:'Company One',contact:'Contact One',before,after,sourceConnectionLabel:'Connected',ledgerSourceRow:3,ledgerProfileId:'one',ledgerRecordedDate:'2026-11-19',sourceFieldChanges:{'Connected?':{before:'Not connected',after:'Connected'}}}],
 summary:{newConnectionRecords:1,currentLedgerRows:2,inventoryDeltaOnly:true,newConnectionRecordsArePeriodConnections:false,ledgerHelperVerificationCounts:{Connected:2,'Verify connection':0}},
 coverage:{reportingPeriodConnectionsAdded:0,completeConnectionEventStream:false}};
const fixture={snapshotAt:review.appliesToSnapshotAt,rows:[one,two],summary:{sourceRows:2,uniqueProfiles:2,acceptedConnectionRecords:1,readyRows:0,connectedRows:1,reviewRows:0,awaitingConnectionRows:1},datedActions:[{date:'2026-11-17',type:'Follow-up status'}],messageDateReview:{platformObservedEvents:[{observationId:'proof',date:'2026-11-17',direction:'outbound',videoIncluded:true,observedAt:'2026-11-18T12:00:00Z'}]},sourceAppearanceRefresh:{reviewedAt:'2026-11-19T12:00:00Z'},connectionInventoryReview:review};
function overlay(value){ctx.fixture=value;return JSON.parse(run('JSON.stringify(videoCurrentInventory(fixture))'));}
const original=copy(fixture),projected=overlay(fixture);
assert.deepEqual(fixture,original);assert.equal(projected.summary.readyRows,1);assert.equal(projected.summary.connectedRows,2);
assert.equal(projected.snapshotAt,fixture.snapshotAt);assert.equal(projected.summary.acceptedConnectionRecords,1);
for(const key of ['datedActions','messageDateReview','sourceAppearanceRefresh'])assert.deepEqual(projected[key],fixture[key]);
assert.deepEqual(overlay(fixture),projected);assert.equal(projected.rows[0].sourceConnectionLabel,'Connected');
const absent=copy(fixture);delete absent.connectionInventoryReview;assert.deepEqual(overlay(absent).summary,absent.summary);
let rejected=0;
for(const change of [
 r=>r.appliesToSnapshotAt='2026-11-19T00:00:00Z',
 r=>r.records[0].id='wrong-profile',r=>r.records[0].sourceRow=999,
 r=>r.records[0].company='Wrong company',r=>r.records[0].contact='Wrong contact',
 r=>r.records[0].before.connected=true,r=>r.records[0].before.connectedAt='2026-11-01',
 r=>r.records[0].before.action='Review',r=>r.records[0].after.status='Sent',
 r=>r.records[0].after.connectedAt=null,r=>r.records[0].after.action='Sent',
 r=>r.newSummary.readyRows=2,r=>r.summary.ledgerHelperVerificationCounts.Connected=99,
 r=>r.records.push(copy(r.records[0])),r=>r.summary.newConnectionRecordsArePeriodConnections=true,
 r=>r.records[0].sourceFieldChanges['Loom Link']={before:'',after:'private asset'},
 r=>r.records[0].ledgerProfileId='wrong-ledger-profile',r=>r.records[0].ledgerSourceRow=4,
]){
 const bad=copy(fixture);change(bad.connectionInventoryReview);const unchanged=copy(bad);
 assert.throws(()=>overlay(bad),/Invalid current Video DM helper review/);assert.deepEqual(bad,unchanged);rejected++;
}
// Only a missing base match-count attribute may skip a prior-value comparison.
const unknownPrior=copy(fixture);unknownPrior.connectionInventoryReview.records[0].before.connectionMatchCount=7;overlay(unknownPrior);
unknownPrior.rows[0].connectionMatchCount=0;assert.throws(()=>overlay(unknownPrior),/prior connectionMatchCount/);
const undated=copy(fixture),r=undated.connectionInventoryReview;
Object.assign(r.records[0],{sourceConnectionLabel:'Verify connection',ledgerRecordedDate:null});
Object.assign(r.records[0].after,{connected:false,connectedAt:null,action:'Review'});
Object.assign(r.newSummary,{readyRows:0,connectedRows:1,reviewRows:1,verifyConnectionRows:1,ledgerHelperConnectedRows:1,ledgerHelperVerifyRows:1});
r.summary.ledgerHelperVerificationCounts={Connected:1,'Verify connection':1};
const held=overlay(undated);assert.equal(held.rows[0].connected,false);assert.equal(held.rows[0].connectedAt,null);assert.equal(held.rows[0].action,'Review');
// Exercise actual curated data when present without relying on ignored sources.
const source=JSON.parse(fs.readFileSync(process.argv[2]||path.join(root,'data/shared-dashboard.json'),'utf8'));
if(source.video.connectionInventoryReview){
 const immutable=copy(source),current=overlay(source.video),review=source.video.connectionInventoryReview;
 assert.deepEqual(source,immutable);assert.equal(current.summary.readyRows,review.newSummary.readyRows);
 assert.equal(current.summary.connectedRows,review.newSummary.connectedRows);assert.equal(current.snapshotAt,source.video.snapshotAt);
 for(const key of ['datedActions','messageDateReview','sourceAppearanceRefresh','snapshotDelta','crmReconciliation'])assert.deepEqual(current[key],source.video[key]);
 ctx.source=source;run("S.data=source;S.start='2026-11-12';S.end='2026-11-18';");
 const panel=run('video()');assert.match(panel,/Current ledger rows/);assert.match(panel,/not new weekly connections/);
 assert.match(panel,/Original main workbook inventory/);assert.match(panel,/helpers reviewed separately/);
 assert.match(run('overview()'),/Current helpers reviewed/);
 assert.match(run("JSON.stringify(vectorData().find(v=>v.id==='video').activity)"),/Current helpers reviewed/);
 assert.deepEqual(source,immutable);
}
console.log(`Video helper JS overlay: pure current queue, held/mismatch boundaries, ${rejected} corrupt-child rejections and unchanged dated evidence passed.`);
