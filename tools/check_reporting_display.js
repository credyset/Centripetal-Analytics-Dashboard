/* Selected-period display and heterogeneous source-coverage regression checks. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const app=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null}});
vm.runInContext(app,ctx);
const run=s=>vm.runInContext(s,ctx);
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
assert.match(html,/<option value="14">Last 14 complete days<\/option>/);
ctx.dateInputs={'#date-start':{},'#date-end':{}};
ctx.document.querySelector=selector=>ctx.dateInputs[selector]||null;
ctx.fortnightFixture={meta:{reportingAsOfDate:'2026-11-13',defaultReportingThrough:'2026-11-13',defaultCompleteReportingThrough:'2026-11-12',defaultDatePreset:'7',currentDayPartial:true},meetings:{fireflies:{records:[],currentWeekPurposeReview:{start:'2026-11-06',end:'2026-11-12',recordingsReviewed:29,selectedPeriodKind:'last_7_complete_days'},fourteenDayPurposeReview:{start:'2026-10-30',end:'2026-11-12',recordingsReviewed:60}}}};
run('S.data=fortnightFixture;preset(S.data.meta.defaultDatePreset);');
assert.equal(ctx.dateInputs['#date-start'].value,'2026-11-06');
assert.equal(ctx.dateInputs['#date-end'].value,'2026-11-12');
assert.match(run('recordingEvidenceReview()'),/Seven-day recording review.*29 available indexed recordings reviewed/);
assert.doesNotMatch(run('recordingEvidenceReview()'),/14-day recording review/);
run("preset('14');");
assert.equal(ctx.dateInputs['#date-start'].value,'2026-10-30');
assert.equal(ctx.dateInputs['#date-end'].value,'2026-11-12');
assert.match(run('recordingEvidenceReview()'),/14-day recording review.*60 available indexed recordings reviewed/);
assert.doesNotMatch(run('recordingEvidenceReview()'),/Seven-day recording review/);

// The complete-month preset stops before the partial reporting day. November
// audio follows selected dates and excludes duplicate artifacts; October's
// owner estimate must not become November effort.
assert.match(html,/<option value="mtd-complete">Month through last complete day<\/option>/);
ctx.novemberEffortFixture={meta:{reportingAsOfDate:'2026-11-19',defaultCompleteReportingThrough:'2026-11-18'},time:{period:{start:'2026-10-01',end:'2026-10-28'},novemberRecordingReview:{coverage:{start:'2026-11-01',end:'2026-11-18'},events:[{indexedAt:'2026-11-10T16:30:00Z',associatedAudioMinutes:21.79},{indexedAt:'2026-11-13T15:30:00Z',associatedAudioMinutes:49.54},{indexedAt:'2026-11-13T15:30:00Z',associatedAudioMinutes:16,excludedDuplicate:true},{indexedAt:'2026-11-17T15:30:00Z',associatedAudioMinutes:46}]}}};
run("S.data=novemberEffortFixture;preset('mtd-complete');");
assert.equal(ctx.dateInputs['#date-start'].value,'2026-11-01');
assert.equal(ctx.dateInputs['#date-end'].value,'2026-11-18');
assert.equal(run('timeVector().activity[0].value'),'1h 57m');
assert.equal(run('timeVector().responses[0].value'),null);
run("preset('7');");
assert.equal(ctx.dateInputs['#date-start'].value,'2026-11-12');
assert.equal(run('timeVector().activity[0].value'),'1h 36m');
run("preset('mtd');");
assert.equal(ctx.dateInputs['#date-end'].value,'2026-11-19');
assert.equal(run('timeVector().activity[0].value'),'1h 57m');
assert.equal(run('timeVector().responses[0].value'),null);
assert.equal(run('timeVector().coverage.end'),'2026-11-18');

// Crossing a month boundary must select the dated audio from both reviews,
// rather than substitute the whole October proxy. Source IDs deduplicate a
// recording retained in both reviews, and explicit duplicate artifacts stay out.
ctx.crossMonthEffortFixture=JSON.parse(JSON.stringify(ctx.novemberEffortFixture));
Object.assign(ctx.crossMonthEffortFixture.time,{snapshotAt:'2026-11-13T13:38:58Z',period:{start:'2026-10-01',end:'2026-10-31'},summary:{ownerEstimateRange:{periodStart:'2026-10-01',coversThrough:'2026-10-28',low:21.75,high:23}},meetings:{events:[{id:'fireflies:oct-first',startAt:'2026-10-01T14:10:00Z',countedMinutes:36},{id:'fireflies:oct-last',startAt:'2026-10-29T14:30:00Z',countedMinutes:37},{id:'fireflies:oct-duplicate',startAt:'2026-10-29T14:30:00Z',countedMinutes:37,duplicateOfId:'fireflies:oct-last'},{id:'fireflies:nov-middle',startAt:'2026-11-13T15:30:00Z',countedMinutes:49.54}]}});
Object.assign(ctx.crossMonthEffortFixture.time.novemberRecordingReview,{snapshotAt:'2026-11-20T05:20:21Z'});
ctx.crossMonthEffortFixture.time.novemberRecordingReview.events[1].recordingId='nov-middle';
run("S.data=crossMonthEffortFixture;S.start='2026-10-31';S.end='2026-11-18';");
assert.equal(run('timeVector().activity[0].value'),'1h 57m');
assert.match(run('timeVector().activity[0].note'),/3 distinct known recordings.*Index dates are proxies.*attendance duration is unmeasured/);
assert.equal(run('timeVector().responses[0].value'),null);
assert.equal(run('timeVector().responses.length'),1); // No October estimate overlaps October 31 onward.
run("preset('30');");
assert.equal(run('timeVector().activity[0].value'),'2h 34m'); // October 29 + November, once each.
assert.equal(run('timeVector().cardOutcome.value'),null); // The November hours are still unknown.
assert.equal(run('timeVector().responses[1].value'),'21.75–23 h');
assert.match(run('timeVector().responses[1].note'),/fixed historical reference.*Oct 1, 2026 – Oct 28, 2026.*no allocation/);
run("preset('90');");
assert.equal(run('timeVector().activity[0].value'),'3h 10m');
run("S.start='2026-10-29';S.end='2026-10-29';");
assert.equal(run('timeVector().activity[0].value'),'0h 37m');
assert.equal(run('timeVector().asOf'),'2026-11-13T13:38:58Z'); // November collection cannot re-date October evidence.
run("S.start='2026-11-19';S.end='2026-11-19';");
assert.equal(run('timeVector().activity[0].value'),null);
assert.match(run('timeVector().activity[0].note'),/No dated associated recording.*total audio remains unknown/);
assert.equal(run('timeVector().responses[0].value'),null);

// An observed partial calendar day is not a complete-day zero. Preserve its
// separately retrieved scheduled-start scope without certifying later bookings.
ctx.partialCalendarFixture={meta:{},meetings:{snapshotAt:'2026-11-20T05:19:15Z',coverage:{start:'2026-07-16',end:'2026-12-04',complete:true,completeDaysThrough:'2026-11-18',observedThrough:'2026-11-19',currentDayPartial:'2026-11-19'},events:[{bookingChainId:'known-chain',bookingCreatedAt:'2026-11-17T17:00:00Z',startAt:'2026-11-18T17:00:00Z',isCurrentBooking:true,status:'active'}]}};
run("S.data=partialCalendarFixture;S.start='2026-11-19';S.end='2026-11-19';");
assert.equal(run('calendarCreationAvailable(S.data.meetings)'),false);
assert.match(run('calendarReview()'),/Period booking counts are unavailable/);
assert.match(run('calendarReview()'),/metric-value[^>]*>—<\/div><div class="metric-label">Booking chains created/);
run("S.start='2026-11-18';S.end='2026-11-18';");
assert.equal(run('calendarCreationAvailable(S.data.meetings)'),true);
run("delete S.data.meetings.coverage.completeDaysThrough;S.start='2026-11-19';S.end='2026-11-19';");
assert.equal(run('calendarCreationAvailable(S.data.meetings)'),false); // The explicit partial-day fallback also stops before it.
run('S.data=novemberEffortFixture;');
run("preset('7');S.data.video={messageDateReview:{platformObservedEvents:[{observationId:'known-followup',date:'2026-11-13',direction:'outbound',messageKind:'video_follow_up'}]}};");
assert.equal(run("vectorData().find(r=>r.id==='video').cardActivity.label"),'Observed video follow-ups');
assert.equal(run("vectorData().find(r=>r.id==='video').cardActivity.value"),'≥1');
assert.equal(run("vectorData().find(r=>r.id==='video').activity[0].value"),null);


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
assert.match(profileHtml,/preset totals are independent of the dashboard date filter/);
assert.doesNotMatch(profileHtml,/35%|163|Aug 1/);
run("S.start='2026-08-01';S.end='2026-08-02';");
assert.equal(run('creatorProfileEvidence(profileFixture)'),profileHtml);
run('profileFixture.profileAnalytics.account.identityVerified=false;');
assert.doesNotMatch(run('creatorProfileEvidence(profileFixture)'),/1,313/);
assert.match(run('creatorProfileEvidence(profileFixture)'),/Account identity is unverified/);
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

ctx.messageFixture={messageDateReview:{reviewedAt:'2026-10-22T14:30:00Z',scope:{},summary:{},records:[{profileId:'kept-proof',reportedSendDate:null,historicalReportedSendDate:'2026-10-21',currentWorksheetReportedSendDates:[],platformSendDate:'2026-10-21'}],nativePlatformCoverage:{cohort:'Earlier reviewed asset cohort.',cohortProfilesChecked:1,cohortExactOutboundVideoMatches:1,profileChecks:[{status:'matched',observedAt:'2026-10-22T14:04:51Z'}]},platformObservedEvents:[{observationId:'kept-native-proof',profileId:'kept-proof',date:'2026-10-21',direction:'outbound',videoIncluded:true,observedAt:'2026-10-22T14:04:51Z',sourceRow:1045,currentSourceRows:[51],historicalSourceSnapshotAt:'2026-10-22T01:02:14Z',evidenceBasis:'Matching asset observed'}]}};
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
// Current source reviews name their response count separately from older
// retained reviews. Render the explicit source count without inferring meetings.
run("S.data.meetings.fireflies.currentWeekPurposeReview={start:'2026-10-19',end:'2026-10-23',sourceBodiesReviewed:26,indexedRecordings:26};");
assert.match(run('recordingEvidenceReview()'),/26 available indexed recordings reviewed for Oct 19, 2026 – Oct 23, 2026/);
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
// A verified unchanged-state check may bridge inventory coverage while its
// original census clock remains intact. Incomplete or unrelated checks cannot.
ctx.stateBridgeFixture={snapshotAt:'2026-10-24T03:11:09.030Z',coverage:{reportingThrough:'2026-10-22',observedThrough:'2026-10-23'},activities:[{id:1},{id:2}],incrementalReview:{counts:{deals_delta:0,deleted_deals_delta:0,activities_delta:0,recents_delta:0,archived_deals:0},effectiveCoverage:{baselineSnapshotAt:'2026-10-24T03:11:09.030Z',baselineCollectionStartedAtUTC:'2026-10-24T03:11:07.475Z',overlapSinceTimestampUTC:'2026-10-24T03:11:07Z',checkCompletedAtUTC:'2026-10-24T06:32:30.142Z',reportingThrough:'2026-10-23',observedThrough:'2026-10-24',currentDayPartial:true,statePreserved:true,comparisonComplete:true,sameAccessibleAccountScope:true,activityStateRecordsCompared:2,newActivityIds:0,removedActivityIds:0,changedActivityRecords:0}}};
const originalStateFixture=JSON.stringify(ctx.stateBridgeFixture);
assert.equal(run('crmStateCoverage(stateBridgeFixture).reportingThrough'),'2026-10-23');
assert.equal(run('crmStateCoverage(stateBridgeFixture).observedThrough'),'2026-10-24');
assert.equal(ctx.stateBridgeFixture.snapshotAt,'2026-10-24T03:11:09.030Z');
assert.equal(JSON.stringify(ctx.stateBridgeFixture),originalStateFixture);
for(const change of [{baselineSnapshotAt:'2026-10-24T03:11:08Z'},{overlapSinceTimestampUTC:'2026-10-24T03:11:09Z'},{comparisonComplete:false},{sameAccessibleAccountScope:false},{activityStateRecordsCompared:3},{removedActivityIds:1},{changedActivityRecords:1},{observedThrough:'2026-10-25'}]){
 ctx.invalidBridge=JSON.parse(originalStateFixture);Object.assign(ctx.invalidBridge.incrementalReview.effectiveCoverage,change);
 assert.equal(run('crmStateCoverage(invalidBridge).reportingThrough'),'2026-10-22');
}
ctx.invalidBridge=JSON.parse(originalStateFixture);ctx.invalidBridge.incrementalReview.counts.deleted_deals_delta=1;
assert.equal(run('crmStateCoverage(invalidBridge).reportingThrough'),'2026-10-22');

// Deal ownership and activity ownership are separate source fields. A task
// belongs to its linked deal's pipeline even when another person owns the deal.
ctx.crossOwnerCRMFixture={crm:{deals:[{id:1,pipelineId:2,owner:'Charles Solomon'},{id:2,pipelineId:2,owner:'Christian W'},{id:3,pipelineId:4,owner:'Charles Solomon'},{id:4,pipelineId:4,owner:'Christian W'},{id:5,pipelineId:2,owner:'Charles Solomon',isTest:true},{id:6,pipelineId:1,owner:'Alex'}],activities:[{id:10,dealId:1,owner:'Christian W'},{id:11,dealId:2,owner:'Charles Solomon'},{id:12,dealId:1,owner:'Charles Solomon'},{id:13,dealId:null,owner:'Christian W'},{id:14,dealId:3,owner:'Charles Solomon'},{id:15,dealId:3,owner:'Christian W'},{id:16,dealId:5,owner:'Charles Solomon'},{id:17,dealId:2,owner:'Charles Solomon',isTest:true},{id:18,dealId:6,owner:'Alex'},{id:19,dealId:6,owner:'Christian W'}]}};
const filteredIds=kind=>JSON.parse(run(`JSON.stringify(crmFiltered().${kind}.map(row=>row.id).sort((a,b)=>a-b))`));
run("S.data=crossOwnerCRMFixture;S.pipeline='2';S.owner='Charles Solomon';");
assert.deepEqual(filteredIds('deals'),[1]);
assert.deepEqual(filteredIds('activities'),[11,12]); // Includes a task on Christian's deal.
run("S.owner='Christian W';");
assert.deepEqual(filteredIds('deals'),[2]);
assert.deepEqual(filteredIds('activities'),[10]); // Includes a task on Charles's deal.
run("S.pipeline='1';");
assert.deepEqual(filteredIds('deals'),[]);
assert.deepEqual(filteredIds('activities'),[19]); // An owner needs no owned deal to own its task.
run("S.pipeline='4';");
assert.deepEqual(filteredIds('deals'),[4]);
assert.deepEqual(filteredIds('activities'),[15]);
run("S.pipeline='2';S.owner='all';");
assert.deepEqual(filteredIds('deals'),[1,2]);
assert.deepEqual(filteredIds('activities'),[10,11,12]); // Test activities and test-deal pipeline membership excluded.
run("S.pipeline='all';S.owner='Christian W';");
assert.deepEqual(filteredIds('deals'),[2,4]);
assert.deepEqual(filteredIds('activities'),[10,13,15,19]); // Unlinked tasks remain in the all-pipeline owner view.
run("S.owner='all';");
assert.deepEqual(filteredIds('deals'),[1,2,3,4,6]);
assert.deepEqual(filteredIds('activities'),[10,11,12,13,14,15,16,18,19]); // Preserve the complete non-test activity inventory.
console.log('Reporting display: selected-date impressions, missing/zero handling, fixed reach and source-specific coverage passed.');

// Import-source context follows selected record IDs, without assigning an
// unverified organic origin to every other new row.
ctx.importContext={assessment:{dealCreationMeasurementReview:{sourceLabelSniperListDealIds:[2,3]}}};
assert.match(run('crmCreatedRecordNote(importContext,[{id:1},{id:2}])'),/^1 carry reviewed Sniper List source labels/);
assert.doesNotMatch(run('crmCreatedRecordNote(importContext,[{id:1}])'),/Sniper List/);
