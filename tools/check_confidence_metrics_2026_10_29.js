/* Long-history charts must retain recent weeks and respect partial-day limits. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const app=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>({})}});
vm.runInContext(app,ctx);
const run=source=>vm.runInContext(source,ctx);
const asJSON=source=>JSON.parse(run(`JSON.stringify(${source})`));
const dayMs=86400000;
function monday(date){const day=new Date(date+'T12:00:00Z');day.setUTCDate(day.getUTCDate()-(day.getUTCDay()+6)%7);return day.toISOString().slice(0,10);}
function weekCount(start,end){return Math.round((Date.parse(monday(end))-Date.parse(monday(start)))/(7*dayMs))+1;}

// 115 complete source weeks, followed by an explicitly partial observed day.
// An arbitrary cap at100 dropped recent weeks even when the source was complete.
ctx.longFixture={meta:{generatedAt:'2002-03-18T18:00:00Z'},crm:{snapshotAt:'2002-03-18T18:00:00Z',
  coverage:{earliestDealCreatedDate:'2000-01-03',reportingThrough:'2002-03-17',observedThrough:'2002-03-18',currentDayPartial:true},
  deals:[],activities:[]}};
ctx.longRows=[{createdAt:'2000-01-03',amount:2},{createdAt:'2002-03-17',amount:3},{createdAt:'2002-03-18',amount:5}];
run("S.data=longFixture;S.start='2000-01-03';S.end='2002-03-18';");
let series=asJSON("weekly(longRows,'createdAt','amount')");
assert.equal(series.length,115,'All complete weeks must remain represented, including the recent ones.');
assert.equal(series.at(-1).date,'2002-03-11');
assert.equal(series.reduce((n,row)=>n+row.value,0),5,'The partial observed day must stay excluded by default.');
assert.equal(run('S.end'),'2002-03-18','Chart coverage must not rewrite the selected reporting end.');
series=asJSON("weekly(longRows,'createdAt','amount',null,true)");
assert.equal(series.length,116);
assert.equal(series.at(-1).date,'2002-03-18');
assert.equal(series.reduce((n,row)=>n+row.value,0),10,'An explicitly requested observed-day chart may include the partial day.');
assert.equal(run('S.end'),'2002-03-18');

// Also exercise the actual published All available history selection. The
// assertion derives its bound and values from current data, rather than fixing
// today's776records or112weeks into the implementation contract.
ctx.published=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/shared-dashboard.json'),'utf8'));
run("S.data=published;preset('all');");
const selection=asJSON('({start:S.start,end:S.end,coverage:normalizeCRM().coverage})');
const coveredThrough=selection.coverage.reportingThrough<selection.end?selection.coverage.reportingThrough:selection.end;
const expectedRows=asJSON('normalizeCRM().deals').filter(row=>{
  ctx.row=row;
  const date=run('localDate(row.createdAt)');
  return date>=selection.start&&date<=coveredThrough;
});
series=asJSON("weekly(normalizeCRM().deals,'createdAt')");
assert.equal(series.length,weekCount(selection.start,coveredThrough));
assert.equal(series.at(-1).date,monday(coveredThrough));
assert.equal(series.reduce((n,row)=>n+row.value,0),expectedRows.length,'Recent CRM records must not disappear from the all-history chart.');

// A separately verified UI aggregate may establish four explicit zeros inside
// its exact scope/window. It must never invent daily/individual campaign rows,
// owner-qualified leads, bookings, video metrics or zero commercial outcomes.
const clone=value=>JSON.parse(JSON.stringify(value));
const retainedIds=[...new Set([...(ctx.published.ads.review.sourceScope.exportedAdSetIds||[]),
  ...(ctx.published.ads.review.sourceScope.uiOnlyZeroDeliveryAdSetIds||[])])].sort();
const zeroReview={snapshotAt:'2026-10-29T06:35:02.571Z',reviewedAt:'2026-10-29T06:40:00Z',
  accountId:ctx.published.ads.lifecycleReview.accountId,identityVerified:true,
  reviewKind:'authenticated_ui_aggregate_zero',
  coverage:{start:'2026-10-22',end:'2026-10-29',sourceTimezone:'UTC',finalDayPartial:true,completeDaysThrough:'2026-10-28'},
  metrics:{spend:0,impressions:0,clicks:0,rawLeads:0},
  scope:{adSetIds:retainedIds,matchesRetainedAdSetScope:true,adSetsReviewed:retainedIds.length},
  sourceDailyRowsAdded:0};
ctx.zeroData=clone(ctx.published);ctx.zeroData.ads.zeroDeliveryReview=clone(zeroReview);
const sourceBytes=JSON.stringify({daily:ctx.zeroData.ads.daily,campaigns:ctx.zeroData.ads.campaigns,
  outcomes:ctx.zeroData.outcomes,time:ctx.zeroData.time});
run("S.data=zeroData;S.start='2026-10-22';S.end='2026-10-29';");
let selected=asJSON('selectedAds()');
assert.equal(selected.daily.length,0);
assert.ok(selected.selectedUiZeroEvidence);
for(const key of ['spend','impressions','clicks','rawLeads'])assert.equal(selected.selectedTotals[key],0);
for(const key of ['qualifiedLeads','formOpens','videoViews','videoCompletions'])assert.equal(selected.selectedTotals[key],null);
let paid=asJSON("vectorData().find(v=>v.id==='ads')");
assert.ok(paid.outcomes.every(metric=>metric.value===null),'Zero platform delivery cannot establish qualified leads or matched bookings.');
assert.equal(paid.activity[0].basis,'partial','The observed October29 source day remains partial.');
assert.equal(paid.asOf,zeroReview.snapshotAt,'The later validation clock cannot re-date source collection.');
run("S.end='2026-10-28';");
assert.equal(run("vectorData().find(v=>v.id==='ads').activity[0].basis"),'period');
run("S.start='2026-10-29';S.end='2026-10-29';");
assert.equal(run('selectedAds().selectedTotals.spend'),0);
assert.equal(run("vectorData().find(v=>v.id==='ads').activity[0].basis"),'partial');
run('ads();');
assert.equal(JSON.stringify({daily:ctx.zeroData.ads.daily,campaigns:ctx.zeroData.ads.campaigns,
  outcomes:ctx.zeroData.outcomes,time:ctx.zeroData.time}),sourceBytes,
  'Rendering bounded zeros must not edit CSV rows, campaign rows, owner outcomes or effort.');
assert.ok(ctx.zeroData.ads.daily.every(row=>row.date<'2026-10-22'));

for(const [start,end]of [['2026-10-21','2026-10-29'],['2026-10-22','2026-10-30'],['2026-10-30','2026-10-30'],['2026-10-29','2026-10-22']]){
  ctx.window={start,end};run('S.start=window.start;S.end=window.end;');
  assert.equal(run('selectedAdsUiZeroEvidence(S.data.ads)'),null,'A wider/outside/invalid period cannot inherit bounded zeros.');
}
run("S.start='2026-10-21';S.end='2026-10-29';");
selected=asJSON('selectedAds()');
assert.equal(selected.selectedUiZeroEvidence,null);
assert.equal(selected.selectedTotals.spend,ctx.zeroData.ads.daily.filter(r=>r.date==='2026-10-21').reduce((total,row)=>total+row.spend,0));
run("S.start='2026-10-22';S.end='2026-10-29';");
const invalidChanges=[
  review=>review.identityVerified=false,
  review=>review.accountId='another-account',
  review=>review.reviewKind='missing_rows_assumed_zero',
  review=>review.scope.matchesRetainedAdSetScope=false,
  review=>review.scope.adSetIds[0]='wrong-scope-even-though-the-old-flag-is-true',
  review=>review.scope.adSetIds[0]=review.scope.adSetIds[1],
  review=>review.scope.adSetsReviewed=1,
  review=>review.sourceDailyRowsAdded=1,
  review=>review.coverage.sourceTimezone='America/Denver',
  review=>review.metrics.spend=0.01,
  review=>review.metrics.clicks=null,
  review=>delete review.reviewedAt
];
for(const mutate of invalidChanges){
  ctx.zeroData.ads.zeroDeliveryReview=clone(zeroReview);mutate(ctx.zeroData.ads.zeroDeliveryReview);
  assert.equal(run('selectedAdsUiZeroEvidence(S.data.ads)'),null,'An unverified, nonzero or incompatible aggregate cannot supply zero metrics.');
  const unavailable=asJSON('selectedAds().selectedTotals');
  for(const key of ['spend','impressions','clicks','rawLeads'])assert.equal(unavailable[key],null);
}
ctx.zeroData.ads.zeroDeliveryReview=clone(zeroReview);
console.log('Confidence metrics: full history, complete/partial days, scoped UI zeros, preserved CSV rows and unknown commercial outcomes passed.');

// Snapshot comparisons must not silently retain a previous worksheet cohort.
ctx.comparison={sheetSubsetCollectedAt:'2026-10-29T05:51:57Z',sheetSubset:{metrics:{connectedProspects:173}},selectedExportSnapshot:{reviewedAt:'2026-10-22T01:02:14Z',sourceObservationThrough:'2026-10-20',metrics:{connectedProspects:206},overlapWithSheet:{sameProfiles:167,onlyInExports:39,onlyInSheet:6,reviewedAt:'2026-10-29T06:36:06Z',appliesToSheetSnapshotAt:'2026-10-29T05:51:57Z',exportParentReviewedAt:'2026-10-22T01:02:14Z',exportUniqueProfiles:206,sheetUniqueProfiles:173}}};
let comparisonHtml=run('waalaxySelectedExportReview(comparison)');
assert.match(comparisonHtml,/39 in CSV only; 6 in worksheet only/);
assert.match(comparisonHtml,/comparison reviewed/);
ctx.comparison.sheetSubsetCollectedAt='2026-10-30T05:51:57Z';
comparisonHtml=run('waalaxySelectedExportReview(comparison)');
assert.match(comparisonHtml,/Current exact overlap is unavailable/);
assert.doesNotMatch(comparisonHtml,/39 in CSV only/);
ctx.comparison.sheetSubsetCollectedAt='2026-10-29T05:51:57Z';
ctx.comparison.selectedExportSnapshot.reviewedAt='2026-10-30T01:02:14Z';
assert.match(run('waalaxySelectedExportReview(comparison)'),/Current exact overlap is unavailable/);
// The operating-card estimate must disclose its earlier owner coverage cutoff.
ctx.timeFixture={time:{period:{start:'2026-10-01',end:'2026-10-29'},summary:{ownerEstimateRange:{low:21.75,high:23,coversThrough:'2026-10-28'}}}};
run('S.data=timeFixture;');
assert.match(run('timeVector().cardOutcome.note'),/Estimate through Oct 28, 2026/);
console.log('Confidence display: current-source overlap guards and explicit owner-estimate cutoff passed.');
