/* Selected-period display and heterogeneous source-coverage regression checks. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const app=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null}});
vm.runInContext(app,ctx);
const run=s=>vm.runInContext(s,ctx);
ctx.input={meta:{},content:{creatorAnalytics:{coverage:{start:'2026-07-25',end:'2026-10-22',finalDayPartial:true},summary:{impressions:9999,membersReached:777,socialEngagements:50},exportAnalytics:{coverage:{start:'2026-10-18',end:'2026-10-22',finalDayPartial:true},daily:[{date:'2026-10-18',impressions:800},{date:'2026-10-19',impressions:0},{date:'2026-10-20',impressions:27},{date:'2026-10-21',impressions:5},{date:'2026-10-22',impressions:null}],followers:{daily:[]}}}}};
run("S.data=input;S.start='2026-10-19';S.end='2026-10-21';");
const primary=()=>JSON.parse(run("JSON.stringify(vectorData().find(r=>r.id==='content').activity[0])"));
assert.equal(primary().value,'32'); // Excludes October 18 and the fixed 90-day total.
assert.equal(primary().basis,'period');
run("S.start='2026-10-19';S.end='2026-10-19';");
assert.equal(primary().value,'0'); // An explicit source zero remains measured.
run("S.start='2026-10-19';S.end='2026-10-22';");
assert.equal(primary().value,null); // One unavailable source value is not coerced to zero.
assert.equal(primary().basis,'partial');
run("S.start='2026-10-23';S.end='2026-10-23';");
assert.equal(primary().value,null); // No covered days must not fall back to a 90-day total.
assert.match(primary().note,/0 retained UTC source days.*incomplete/);
assert.equal(run("vectorData().find(r=>r.id==='content').activity[1].value"),'777');
assert.equal(run("vectorData().find(r=>r.id==='content').activity[1].basis"),'snapshot');

const coverage=value=>{ctx.coverage=value;return run('sourceCoverageLabel(coverage)');};
assert.match(coverage({earliestDealCreatedDate:'2024-09-11',reportingThrough:'2026-10-21',observedThrough:'2026-10-22',currentDayPartial:true}),/earliest retained deal created Sep 11, 2024.*Complete reporting days through Oct 21, 2026.*Observed through Oct 22, 2026.*partial/);
assert.match(coverage({scope:'Current referral positions, not period events',reportingThrough:'2026-10-21'}),/Current referral positions, not period events.*Oct 21, 2026/);
assert.match(coverage({oldestIndexedAt:'2026-09-18T19:00:00Z',newestIndexedAt:'2026-10-21T14:30:00Z',completeForActualHeldMeetings:false}),/Indexed recordings reviewed.*Actual held-meeting coverage is incomplete/);
assert.match(coverage({start:'2026-07-16',end:'2026-11-13',endExclusive:true,eventStartMinInclusive:'2026-07-16T06:00:00Z'}),/end exclusive.*Scheduled-start scope.*attendance are not established/);
assert.equal(coverage('Fixed source window'),'Fixed source window');
assert.equal(coverage(null),'Coverage not supplied');
assert.equal(coverage({}),'Coverage not supplied');

// A newer company export can contain an explicit source day beyond Ads coverage.
ctx.companyFixture={companyAnalytics:{snapshotAt:'2026-10-24T03:14:12Z',coverage:{start:'2026-09-04',end:'2026-10-22',sourceDelayUpToDays:2},summary:{},daily:[],notes:[],reconciliation:{ads:{coverage:{start:'2026-09-04',end:'2026-10-21'},dailyMetricsAgree:true,comparedDateCount:48,companyDatesWithoutPaidRows:['2026-10-22']}}},companyAvailabilityReview:{reviewedAt:'2026-10-24T03:13:21Z',latestAvailableDate:'2026-10-22',unavailableDates:['2026-10-23','2026-10-24'],newDailyRowsImported:2}};
run("S.start='2026-10-19';S.end='2026-10-23';");
const companyHtml=run('companyContentEvidence(companyFixture)');
assert.match(companyHtml,/disables these UTC source dates: Oct 23, 2026, Oct 24, 2026/);
assert.match(companyHtml,/2 additional source-day rows/);
assert.match(companyHtml,/compared dates: Sep 4, 2026 – Oct 21, 2026 UTC \(48 source days\)/);
assert.match(companyHtml,/Company source dates without a retained Ads row: Oct 22, 2026/);
assert.match(companyHtml,/do not establish paid-source activity or create an Ads zero row/);
assert.doesNotMatch(companyHtml,/disables October 21–22/);

// Profile-view aggregates keep their own clock/preset and never inherit the
// creator workbook's exact dates, daily series or unlike trend comparison.
ctx.profileFixture={profileAnalytics:{snapshotAt:'2026-10-24T03:40:47Z',profileViewers:1313,sourcePreset:'Past 90 days',sourceTimezone:null,account:{identityVerified:true},coverage:{start:null,end:null,exactDateBoundariesEstablished:false},chartMetadata:{displayedBucketCount:13,lastDisplayedBucket:'2026-10-24',lastDisplayedBucketViewers:163},comparison:{percentChange:-35}}};
const profileHtml=run('creatorProfileEvidence(profileFixture)');
assert.match(profileHtml,/1,313/);
assert.match(profileHtml,/LinkedIn preset: Past 90 days/);
assert.match(profileHtml,/Exact start and end dates are not exposed/);
assert.match(profileHtml,/Source timezone is not supplied/);
assert.match(profileHtml,/does not follow the dashboard date filter/);
assert.match(profileHtml,/no daily or selected-period profile-view count/);
assert.doesNotMatch(profileHtml,/35%|163|Aug 1/);
run("S.start='2026-08-01';S.end='2026-08-02';");
assert.equal(run('creatorProfileEvidence(profileFixture)'),profileHtml);
run('profileFixture.profileAnalytics.account.identityVerified=false;');
assert.doesNotMatch(run('creatorProfileEvidence(profileFixture)'),/1,313/);
assert.match(run('creatorProfileEvidence(profileFixture)'),/aggregate is withheld/);
run("S.start='2026-10-19';S.end='2026-10-23';");

ctx.reconciliationFixture={crmReconciliation:{cohortStartDate:'2026-10-21',cohortEndDate:'2026-10-22',cohortDate:'2026-10-22',reviewedAt:'2026-10-24T03:18:50Z',selfReportedSentRows:21,validVideoAssetRows:19,videoAssetCohortCrmMatches:19,expectedVideoCrmMissing:0,statusRowsWithoutVideoAsset:2,messageNoteWithoutAssetRows:2,records:[{recordingFieldKind:'empty'},{recordingFieldKind:'empty'}]}};
const reconciliationHtml=run('videoCrmReconciliation(reconciliationFixture)');
assert.match(reconciliationHtml,/Source report cohort: Oct 21, 2026 – Oct 22, 2026/);
assert.match(reconciliationHtml,/2 other status rows have no video asset URL \(2 empty fields\)/);
assert.doesNotMatch(reconciliationHtml,/other status rows contain message notes/);

// Capture register inputs: historical worksheet reports must never enter current counts.
run('globalThis.capturedTables=[];globalThis.retainedTable=table;table=(...args)=>{capturedTables.push(args);return retainedTable(...args);};');
ctx.videoFixture={snapshotAt:'2026-10-24T03:10:06Z',summary:{reportedVideoSentStatusRows:24},rows:[{id:'nace',sourceRow:30,company:'Nace',contact:'Historical contact'}],datedActions:[{contactId:'current-send',sourceRow:51,date:'2026-10-21',type:'Send status',sourceField:'Video Sent Date'},{contactId:'current-followup',sourceRow:52,date:'2026-10-22',type:'Follow-up status',sourceField:'Follow-up Sent Date'}],retainedHistoricalWorksheetReports:[{contactId:'nace',sourceRow:1040,historicalSourceRow:1040,date:'2026-10-16',type:'Email send status',channel:'email',sourceInventorySnapshotAt:'2026-10-22T01:02:14Z'}],metadataFreshnessCheck:{snapshotAt:'2026-10-22T12:11:21Z',valuesFreshnessLabel:'Earlier revision rechecked'}};
run("S.start='2026-10-01';S.end='2026-10-23';");
const datedHtml=run('videoDatedEvidence(videoFixture)');
assert.match(datedHtml,/current literal worksheet date fields/);
assert.match(datedHtml,/Earlier worksheet reports · retained separately/);
assert.match(datedHtml,/Earlier worksheet freshness check/);
assert.match(datedHtml,/current inventory was collected separately/);
assert.doesNotMatch(datedHtml,/Dates parsed from worksheet status text/);
assert.equal(run("capturedTables.find(t=>t[0]==='video-dated-status')[2].length"),2);
assert.equal(run("capturedTables.find(t=>t[0]==='video-dated-status')[2].some(r=>r.type==='Email send status')"),false);
assert.equal(run("capturedTables.find(t=>t[0]==='video-historical-worksheet-reports')[2][0].sourceRow"),1040);
assert.equal(run("capturedTables.find(t=>t[0]==='video-historical-worksheet-reports')[2][0].currentSourceRow"),30);

ctx.messageFixture={messageDateReview:{reviewedAt:'2026-10-22T14:30:00Z',scope:{},summary:{},records:[{profileId:'kept-proof',reportedSendDate:null,historicalReportedSendDate:'2026-10-21',currentWorksheetReportedSendDates:[],platformSendDate:'2026-10-21'}],nativePlatformCoverage:{cohort:'Earlier reviewed asset cohort.',cohortProfilesChecked:1,cohortExactOutboundVideoMatches:1,profileChecks:[{status:'matched',observedAt:'2026-10-22T14:04:51Z'}]},platformObservedEvents:[{profileId:'kept-proof',date:'2026-10-21',direction:'outbound',videoIncluded:true,observedAt:'2026-10-22T14:04:51Z',sourceRow:1045,currentSourceRows:[51],historicalSourceSnapshotAt:'2026-10-22T01:02:14Z',evidenceBasis:'Matching asset observed'}]}};
run('capturedTables=[];');
const messageHtml=run('videoMessageDateEvidence(messageFixture)');
assert.match(messageHtml,/Conversation checks collected through Oct 22, 2026/);
assert.match(messageHtml,/Refreshing the worksheet does not re-date this proof/);
assert.match(run("capturedTables.find(t=>t[0]==='video-message-dates')[3].find(c=>c.key==='reportedSendDate').render(null,messageFixture.messageDateReview.records[0])"),/Earlier worksheet report · absent from current date fields/);
const observationContext=run("capturedTables.find(t=>t[0]==='video-platform-observations')[3].find(c=>c.key==='evidenceBasis').render('Matching asset observed',messageFixture.messageDateReview.platformObservedEvents[0])");
assert.match(observationContext,/Original evidence row 1045/);
assert.match(observationContext,/Current inventory row 51/);

// Review counts/ranges remain data-driven when the inventory grows again.
ctx.recordingFixture={snapshotAt:'2026-10-24T03:10:37Z',coverage:{octoberIndexedRecords:91},records:[{id:'older',indexedAt:'2026-10-02T16:00:00Z',heldStatus:'source_corroborated'}],currentWeekPurposeReview:{start:'2026-10-19',end:'2026-10-23',recordingsReviewed:23,note:'Bounded review'},octoberPurposeReview:{reviewedAt:'2026-10-22T07:30:31Z',retainedOctoberIndexedRecords:76,reviewStatusCounts:{dialogue_reviewed_purpose_classified:65,dialogue_reviewed_insufficient_for_business_purpose:5,response_success_no_dialogue:6}},incrementalPurposeReview:{reviewedAt:'2026-10-24T03:14:39Z',newRecordingsReviewed:15,priorInsufficientRecordsRetried:11,notes:[],records:[{id:'newer',indexedAt:'2026-10-23T19:00:00Z',classification:'founder_introduction_owner_review'}]}};
run('S.data={meetings:{fireflies:recordingFixture}};capturedTables=[];');
const recordingHtml=run('recordingEvidenceReview()');
assert.match(recordingHtml,/23 available indexed recordings reviewed for Oct 19, 2026 – Oct 23, 2026/);
assert.match(recordingHtml,/Earlier October inventory review/);
assert.match(recordingHtml,/15 new recording dialogues and 11 earlier insufficient responses/);
assert.match(recordingHtml,/91/);
assert.equal(run("capturedTables.find(t=>t[0]==='crm-recording-evidence')[2].length"),2);
// Company distribution must never become Charles's headline content activity,
// including when personal creator evidence is absent or a historical date is selected.
ctx.personalFocusData=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/shared-dashboard.json'),'utf8'));
run("S.data=personalFocusData;S.start=personalFocusData.content.creatorAnalytics.exportAnalytics.coverage.start;S.end=personalFocusData.content.creatorAnalytics.exportAnalytics.coverage.completeDaysThrough;");
const focusedVector=JSON.parse(run("JSON.stringify(vectorData().find(v=>v.id==='content'))"));
assert.equal(focusedVector.name,'Charles’s LinkedIn content');
assert.equal(focusedVector.scope,'Charles Solomon · personal profile');
const focusCoverage=ctx.personalFocusData.content.creatorAnalytics.exportAnalytics.coverage;
const expectedPersonalImpressions=ctx.personalFocusData.content.creatorAnalytics.exportAnalytics.daily.filter(r=>r.date>=focusCoverage.start&&r.date<=focusCoverage.completeDaysThrough).reduce((total,r)=>total+r.impressions,0);
assert.equal(focusedVector.activity[0].value,expectedPersonalImpressions.toLocaleString('en-US'));
assert.ok(focusedVector.activity.every(m=>!/company/i.test(m.label)));
const focusedHtml=run('content()'),supplementAt=focusedHtml.indexOf('<details class="activity-review-details">');
assert.ok(supplementAt>0);
assert.match(focusedHtml.slice(supplementAt),/Supplementary company-page/);
assert.doesNotMatch(focusedHtml.slice(0,supplementAt),/Centripetal company-page analytics|Company sponsored impressions/);
ctx.onlyCompany={meta:{},content:{daily:[{date:'2026-10-20',account:'Centripetal Advisors',impressions:999999,engagements:888888}],accounts:[{name:'Centripetal Advisors',impressions:999999}],publicObservations:{profiles:[{name:'Centripetal Advisors',followers:777777},{name:'Charles Solomon',followers:666666}]}}};
run("S.data=onlyCompany;S.start='2026-10-19';S.end='2026-10-23';");
assert.equal(run("vectorData().find(v=>v.id==='content').activity[0].value"),null);
assert.equal(run("vectorData().find(v=>v.id==='content').responses[0].value"),null);
ctx.onlyCompany.content.daily.push({date:'2026-10-20',account:'Charles Solomon',impressions:17,engagements:3});
assert.equal(run("vectorData().find(v=>v.id==='content').activity[0].value"),'17');
assert.equal(run("vectorData().find(v=>v.id==='content').responses[0].value"),'3');
console.log('Reporting display: selected-date impressions, missing/zero handling, fixed reach and source-specific coverage passed.');
