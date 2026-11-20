/* Revision-pair and identity guards: repeated proofs must not inflate floors. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'..'),app=fs.readFileSync(path.join(root,'app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null}});
vm.runInContext(app,ctx);
const run=code=>vm.runInContext(code,ctx),copy=value=>JSON.parse(JSON.stringify(value));
let checks=0;
function select(video,start='2026-11-12',end='2026-11-18'){
  ctx.videoInput=video;ctx.periodStart=start;ctx.periodEnd=end;
  run('S.data={video:videoInput};S.start=periodStart;S.end=periodEnd;');
  return JSON.parse(run('JSON.stringify(selectedVideoSourceAppearanceRefresh(videoInput))'));
}
function measured(video,expected,start,end){
  const original=JSON.stringify(video),selected=select(video,start,end);
  assert.deepEqual({valid:selected.valid,profiles:selected.profiles,occurrences:selected.occurrences},{valid:true,...expected});
  const rendered=run('videoSourceAppearanceEvidence(videoInput)');
  if(expected.profiles){assert.match(rendered,new RegExp(`<strong>≥${expected.profiles}<\\/strong>`));assert.ok(rendered.includes(`${expected.occurrences} row occurrences were added`));}
  else{assert.match(rendered,/<strong>Not measured<\/strong>/);assert.doesNotMatch(rendered,/≥0|0 row occurrences were added/);}
  assert.equal(JSON.stringify(video),original,'selection/render mutated retained evidence');checks++;
}
function unavailable(video){
  const selected=select(video);assert.equal(selected.valid,false);assert.equal(selected.profiles,null);assert.equal(selected.occurrences,null);
  const rendered=run('videoSourceAppearanceEvidence(videoInput)');assert.match(rendered,/<strong>Not measured<\/strong>/);assert.match(rendered,/minimum is unavailable/);assert.doesNotMatch(rendered,/≥0|0 row occurrences were added/);checks++;
}
function fixture(){
  const after='2026-11-12T18:00:00Z',by='2026-11-13T01:00:00Z',snapshotAt='2026-11-14T12:00:00Z';
  const row={sourceRow:2,id:'new-profile',company:'Company',contact:'Person'};
  return {snapshotAt,rows:[{sourceRow:1,id:'existing',company:'Existing',contact:'Person'},row],sourceAppearanceRefresh:{appliesToSnapshotAt:snapshotAt,currentHeadMatchesLiveRows:true,stableIdentityComparisonVerified:true,revisionComparisonComplete:true,baselineRevisionId:'before',laterRevisionId:'after',currentRevisionId:'after',firstAppearedAfter:after,firstAppearedBy:by,currentRevisionAt:by,baselineValidSourceRows:1,laterValidSourceRows:2,currentValidSourceRows:2,retainedPriorRowOccurrences:1,newStableSourceRecordsMinimum:1,newUniqueProfilesMinimum:1,rowOccurrencesAdded:1,extraOccurrencesBeyondDistinctNewIdentities:0,sourceRecordsRemoved:0,records:[{profileId:row.id,company:row.company,contact:row.contact,currentSourceRow:2,firstAppearedAfter:after,firstAppearedBy:by,recordOccurrencesAdded:1}],intervals:[{baselineRevisionId:'before',laterRevisionId:'after',firstAppearedAfter:after,firstAppearedBy:by,newStableIdentities:1,addedRowOccurrences:1,removedRowOccurrences:0}]}};
}
const fixtureVideo=fixture();measured(fixtureVideo,{profiles:1,occurrences:1});
let changed=copy(fixtureVideo);changed.sourceAppearanceRefresh.intervals.push(copy(changed.sourceAppearanceRefresh.intervals[0]));measured(changed,{profiles:1,occurrences:1});
changed=copy(fixtureVideo);changed.sourceAppearanceRefresh.records.push(copy(changed.sourceAppearanceRefresh.records[0]));measured(changed,{profiles:1,occurrences:1});
changed=copy(fixtureVideo);changed.sourceAppearanceRefresh.intervals.push({...changed.sourceAppearanceRefresh.intervals[0],addedRowOccurrences:2});unavailable(changed);
changed=copy(fixtureVideo);changed.sourceAppearanceRefresh.intervals.push({...changed.sourceAppearanceRefresh.intervals[0],baselineRevisionId:'other-before',laterRevisionId:'other-after'});unavailable(changed);
changed=copy(fixtureVideo);changed.sourceAppearanceRefresh.records[0].company='Different source identity';unavailable(changed);
changed=copy(fixtureVideo);changed.sourceAppearanceRefresh.records.push({...changed.sourceAppearanceRefresh.records[0],recordOccurrencesAdded:2});unavailable(changed);
changed=copy(fixtureVideo);changed.sourceAppearanceRefresh.appliesToSnapshotAt='2026-11-13T12:00:00Z';unavailable(changed);
changed=copy(fixtureVideo);changed.sourceAppearanceRefresh.intervals[0].firstAppearedBy='2026-11-13T01:00:00';unavailable(changed);
changed=copy(fixtureVideo);changed.sourceAppearanceRefresh.intervals.push(null);unavailable(changed);

const supplied=process.argv[2],defaultSnapshot=path.join(root,'data/shared-dashboard.json');
const snapshotPath=supplied?path.resolve(supplied):fs.existsSync(defaultSnapshot)?defaultSnapshot:null;
if(snapshotPath){
  const video=JSON.parse(fs.readFileSync(snapshotPath,'utf8')).video;
  // Independently recomputed from all 15 retained, hash-matched source CSV
  // revisions (1427 through 1734). The five extra occurrences are older identities.
  measured(video,{profiles:52,occurrences:52},'2026-11-12','2026-11-18');
  measured(video,{profiles:147,occurrences:152},'2026-11-01','2026-11-18');
  measured(video,{profiles:194,occurrences:199},'2026-11-01','2026-11-19');
  const pair=video.sourceAppearanceRefresh.intervals.find(row=>row.newStableIdentities===43);assert.ok(pair,'retained 43-identity revision proof missing');
  changed=copy(video);changed.sourceAppearanceRefresh.intervals.push(copy(pair));measured(changed,{profiles:52,occurrences:52});
  changed=copy(video);changed.sourceAppearanceRefresh.intervals.push({...pair,newStableIdentities:44,addedRowOccurrences:44});unavailable(changed);
  changed=copy(video);changed.sourceAppearanceRefresh.intervals.push({...pair,baselineRevisionId:'overlap-before',laterRevisionId:'overlap-after',firstAppearedAfter:'2026-11-12T22:12:13.992Z'});unavailable(changed);
  changed=copy(video);changed.sourceAppearanceRefresh.records.push(...copy(changed.sourceAppearanceRefresh.records));measured(changed,{profiles:52,occurrences:52});
  changed=copy(video);changed.sourceAppearanceRefresh.intervals[5].baselineRevisionId='disconnected';unavailable(changed);
  changed=copy(video);changed.sourceAppearanceRefresh.intervals[4].addedRowOccurrences=44;unavailable(changed);
  changed=copy(video);changed.sourceAppearanceRefresh.records[0].currentSourceRow=-1;unavailable(changed);
  // The 47-profile interval spans November 18/19 Mountain. It belongs to
  // neither single day, and a misleading convenience bucket cannot assign it.
  measured(video,{profiles:0,occurrences:0},'2026-11-18','2026-11-18');
  measured(video,{profiles:0,occurrences:0},'2026-11-19','2026-11-19');
  measured(video,{profiles:47,occurrences:47},'2026-11-18','2026-11-19');
  changed=copy(video);changed.sourceAppearanceRefresh.intervals.find(row=>row.newStableIdentities===47).bucket='completed_window';
  measured(changed,{profiles:0,occurrences:0},'2026-11-18','2026-11-18');
  assert.equal(video.sourceAppearanceRefresh.unassignedBoundaryRows,47);
}
console.log(`Video source appearances: ${checks} revision, identity and Mountain-boundary checks passed.`);
