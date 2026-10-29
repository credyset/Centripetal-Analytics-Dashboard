/* Observed dates are bounded evidence; report/date families never become extra sends. */
'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const app=fs.readFileSync(path.join(__dirname,'../app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const ctx=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null}});
vm.runInContext(app,ctx);const run=s=>vm.runInContext(s,ctx);
ctx.input={meta:{},video:{summary:{readyRows:20,explicitSendStatusRows:13,sheetCompletedRows:55},messageDateReview:{records:[
  {profileId:'profile-a',company:'Company A',contact:'Contact A',linkedin:'https://www.linkedin.com/in/profile-a/',reportedSendDate:'2026-10-21',platformSendDate:'2026-10-21',platformCheckStatus:'matched'},
  {profileId:'profile-b',company:'Company B',contact:'Contact B',linkedin:'https://www.linkedin.com/in/profile-b/',latestLinkedInReplyDate:'2026-10-20',platformReplyDate:'2026-10-19'}],
  platformObservedEvents:[
  {dedupKey:'a|outbound|2026-10-21|asset',date:'2026-10-21',direction:'outbound',sender:'Charles Solomon',videoIncluded:true},
  {dedupKey:'b|inbound|2026-10-19|general',date:'2026-10-19',direction:'inbound',sender:'Contact B',videoIncluded:false},
  {dedupKey:'b|outbound|2026-10-20|general',date:'2026-10-20',direction:'outbound',sender:'Charles Solomon',videoIncluded:false}],
  separateEmailContext:[{sentAt:'2026-10-21',channel:'email'}]}}};
run("S.data=input;S.start='2026-10-19';S.end='2026-10-22';");
const observed=()=>JSON.parse(run('JSON.stringify(selectedVideoObservations(S.data.video))'));
const vector=()=>JSON.parse(run("JSON.stringify(vectorData().find(r=>r.id==='video'))"));
assert.equal(observed().videoSends,1);assert.equal(observed().generalReplies,1);
assert.equal(vector().cardActivity.value,'≥1');assert.equal(vector().cardActivity.basis,'partial');
assert.equal(vector().responses[0].value,null); // General reply is not a video reply.
assert.equal(vector().outcomes[0].value,null);
const html=run('videoMessageDateEvidence(S.data.video)');
assert.match(html,/Video sent · observed/);assert.match(html,/Sent · worksheet evidence/);
assert.match(html,/Latest LinkedIn reply · retained history/);assert.match(html,/Reply · observed/);
assert.match(html,/not a complete send\/reply census/);
assert.match(run("videoPlatformCheckLabel('matched_native_direct')"),/Video matched · direct conversation/);
assert.match(run("videoPlatformCheckLabel('general_text_observed')"),/Text observed · video unconfirmed/);
assert.match(run("videoPlatformCheckLabel('video_reference_asset_unconfirmed')"),/exact asset unconfirmed/);
assert.equal(run('videoPlatformCheckLabel(null)'),'Not checked');
run("S.start='2026-10-20';S.end='2026-10-20';");
assert.equal(observed().videoSends,0);assert.equal(observed().generalReplies,0);
assert.equal(vector().cardActivity.value,null); // Missing sample evidence never becomes verified zero.
run("S.start='2026-10-21';S.end='2026-10-21';");
assert.equal(observed().videoSends,1);assert.equal(observed().generalReplies,0);
run("S.start='2026-10-23';S.end='2026-10-23';");
assert.equal(vector().cardActivity.value,null);
// Exact worksheet response labels must be visible and searchable without
// becoming dated/native reply events or changing the observed-message ledger.
ctx.capturedTables=[];
run("const originalVideoTable=table;table=(...args)=>{capturedTables.push(args);return originalVideoTable(...args);};");
ctx.responseFixture=[{id:'profile-a',company:'Response A',responseStatus:'Interested',hasResponseStatus:true},{id:'profile-b',company:'Response B',status:'Video Sent',hasResponseStatus:false}];
run("S.data={meta:{},video:{rows:responseFixture,summary:{}}};video();");
const register=ctx.capturedTables.find(t=>t[0]==='video-prospects'),responseCol=register[3].find(c=>c.key==='responseStatus');
assert.ok(responseCol,'The response column must use the actual searchable source field');
assert.match(responseCol.render('Interested',ctx.responseFixture[0]),/^Interested<div/);
assert.match(responseCol.render('Interested',ctx.responseFixture[0]),/Undated worksheet status/);
assert.doesNotMatch(responseCol.render('<script>private body</script>',{}),/<script>/);
assert.equal(vector().responses[0].value,null);
const listeners={},body={innerHTML:''},count={textContent:''},controls={input:{addEventListener:(event,callback)=>{listeners[event]=callback;}},prev:{},next:{}};
ctx.document.getElementById=()=>({querySelector:selector=>selector==='tbody'?body:selector==='.table-count'?count:selector==='input'?controls.input:selector==='[data-page="prev"]'?controls.prev:controls.next,querySelectorAll:()=>[]});
ctx.searchRows=register[2];ctx.searchCols=register[3];run("bindTable('response-search',searchRows,searchCols);");
listeners.input({target:{value:'Interested'}});
assert.match(body.innerHTML,/Response A/);assert.doesNotMatch(body.innerHTML,/Response B/);
assert.equal(count.textContent,'1–1 of 1 records');

// Broader current identity/asset coverage is a separate denominator from the
// dated source cohort. Original and matched IDs stay separate in the gap table.
ctx.actualVideo=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/shared-dashboard.json'),'utf8')).video;
const identityHtml=run('videoIdentityAssetEvidence(actualVideo)'),identity=ctx.actualVideo.crmReconciliation.currentIdentityAssetReview;
assert.match(identityHtml,/broader ID\/asset scope is separate from the dated report cohort/);
assert.ok(identityHtml.includes(`${identity.sameAssetInCrmNotes} of ${identity.sourceLoomUrls}`));
assert.match(identityHtml,/not sent messages/);
const gaps=ctx.capturedTables.find(t=>t[0]==='video-crm-linkage-gaps');
assert.equal(gaps[2].length,ctx.actualVideo.crmReconciliation.specificLinkageGaps.length);
const mapped=gaps[2].find(r=>r.sourceSheetDealId&&r.matchedCrmDealId&&r.sourceSheetDealId!==r.matchedCrmDealId);
assert.ok(mapped);assert.notEqual(mapped.sourceSheetDealId,mapped.matchedCrmDealId);
ctx.staleVideo=JSON.parse(JSON.stringify(ctx.actualVideo));ctx.staleVideo.snapshotAt='2099-01-01T00:00:00Z';
const staleHtml=run('videoIdentityAssetEvidence(staleVideo)');
assert.match(staleHtml,/different worksheet snapshot/);assert.doesNotMatch(staleHtml,/Exact profile matches/);

// A newly reviewed historical source fact is visible in its own review, while
// selected October send/reply minimums remain unchanged without event evidence.
ctx.gapFixture={snapshotAt:'2026-10-24T15:00:00Z',summary:{note:'Two source questions were reviewed; coverage stays bounded.'},records:[{profileId:'profile-c',company:'Historical C',contact:'Contact C',status:'Historical asset matched; date bounded',findings:['Original video source day verified; CRM note link remains absent.'],platformSendDate:'2026-09-10',platformReplyDate:'2026-09-16',sendAssetObserved:true,crmDealId:123},{profileId:'profile-d',company:'Bounded D',status:'Still unresolved',findings:['Matching outbound asset was not visible.'],sendAssetObserved:false}],notes:['No commercial decision was changed.']};
run('S.data=input;S.data.video.gapResolutionReview=gapFixture;');
const beforeGap=observed(),gapHtml=run('videoGapResolutionEvidence(S.data.video)');
assert.match(gapHtml,/fixed review is independent of the reporting-period filter/);
assert.match(gapHtml,/adds no send, reply or commercial-outcome count/);
const gapTable=ctx.capturedTables.find(t=>t[0]==='video-gap-resolution');
assert.equal(gapTable[2].length,2);assert.equal(gapTable[2][0].platformSendDate,'2026-09-10');
const assetCol=gapTable[3].find(c=>c.key==='sendAssetObserved');
assert.equal(assetCol.render(false,{}),'Not observed in bounded view');assert.equal(assetCol.render(undefined,{}),'Not established');
assert.deepEqual(observed(),beforeGap);
assert.equal(vector().responses[0].value,null);assert.equal(vector().outcomes[0].value,null);
// A text reply can explicitly refer to a video without containing one itself.
// Its September source day must not increase October replies; a general October
// acknowledgment remains unattributed even if it appears after an outbound.
ctx.actualOutcomes=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/shared-dashboard.json'),'utf8')).outcomes;
run("S.data.outcomes=actualOutcomes;S.start='2026-10-01';S.end='2026-10-24';");
const priorOutcomes=run('JSON.stringify(selectedOutcomeMetrics())'),priorLedger=JSON.stringify(ctx.actualOutcomes);
ctx.historicalReply={dedupKey:'c|inbound|2026-09-16|explicit-video-reply',profileId:'profile-c',date:'2026-09-16',direction:'inbound',videoIncluded:false,replyToVideoAttributionEstablished:true,replyToVideoAssetId:'a'.repeat(32),attributionBasis:'Explicit response to a question about the video.',dateYearConfidence:'moderate',dateBasis:'Current-year label convention; exact source timezone unknown.'};
run('S.data.video.messageDateReview.platformObservedEvents.push(historicalReply);');
run("S.start='2026-10-01';S.end='2026-10-24';");
assert.equal(observed().videoReplies,0);assert.equal(observed().generalReplies,1);
assert.equal(vector().responses[0].value,null);
assert.equal(run('JSON.stringify(selectedOutcomeMetrics())'),priorOutcomes);
run("S.start='2026-09-01';S.end='2026-09-30';");
assert.equal(observed().videoReplies,1);assert.equal(observed().generalReplies,0);
assert.equal(vector().responses[0].value,'≥1');assert.equal(vector().responses[0].basis,'partial');
const attributedHtml=run('videoMessageDateEvidence(S.data.video)');
assert.match(attributedHtml,/Observed replies linked to video/);
assert.match(attributedHtml,/not necessarily positive interest/);
assert.match(attributedHtml,/Account-wide Video DM replies/);
const latestNativeTable=ctx.capturedTables.filter(t=>t[0]==='video-platform-observations').at(-1),nativeEvidenceCol=latestNativeTable[3].find(c=>c.key==='evidenceBasis');
assert.match(nativeEvidenceCol.render('Observed source block',ctx.historicalReply),/moderate confidence/);
assert.match(nativeEvidenceCol.render('Observed source block',ctx.historicalReply),/source timezone unknown/);
assert.equal(run('JSON.stringify(S.data.outcomes)'),priorLedger);
ctx.historicalReply.replyToVideoAttributionEstablished=false;
assert.equal(observed().videoReplies,0);assert.equal(observed().generalReplies,1);
assert.equal(vector().responses[0].value,null); // videoIncluded=false alone is never attribution.
// A revision-bound source minimum is usable only when both offset instants
// fall inside the selected Mountain dates; it is never a video-send count.
ctx.appearanceVideo={snapshotAt:'2026-10-24T03:10:06Z',rows:[{id:'existing',sourceRow:3,company:'Prior company',contact:'Prior contact'},{id:'new-a',sourceRow:431,company:'New Co A',contact:'New Contact A'},{id:'new-b',sourceRow:432,company:'New Co B',contact:'New Contact B'}],gapResolutionReview:{sourceAppearanceReview:{snapshotAt:'2026-10-24T06:35:26Z',reviewedAt:'2026-10-24T06:35:26Z',appliesToSnapshotAt:'2026-10-24T03:10:06Z',revisionComparisonComplete:true,stableIdentityComparisonVerified:true,baselineRevisionId:'1253',laterRevisionId:'1290',firstAppearedAfter:'2026-10-21T20:42:06.138Z',firstAppearedBy:'2026-10-22T21:59:05.316Z',baselineValidSourceRows:1,laterValidSourceRows:3,retainedPriorStableIdentities:1,newStableSourceRecordsMinimum:2,newUniqueProfilesMinimum:2,sourceRecordsRemoved:0,records:[{profileId:'new-a',currentSourceRow:431,company:'New Co A',contact:'New Contact A',firstAppearedAfter:'2026-10-21T20:42:06.138Z',firstAppearedBy:'2026-10-22T21:59:05.316Z'},{profileId:'new-b',currentSourceRow:432,company:'New Co B',contact:'New Contact B',firstAppearedAfter:'2026-10-21T20:42:06.138Z',firstAppearedBy:'2026-10-22T21:59:05.316Z'}]}}};
run("S.start='2026-10-19';S.end='2026-10-25';");
assert.equal(run('selectedVideoSourceAppearances(appearanceVideo).value'),2);
assert.match(run('videoSourceAppearanceEvidence(appearanceVideo)'),/≥2/);
assert.match(run('videoSourceAppearanceEvidence(appearanceVideo)'),/not exact row-added timestamps/);
run("S.start='2026-10-21';S.end='2026-10-21';");
assert.equal(run('selectedVideoSourceAppearances(appearanceVideo).value'),null);
const partialAppearanceHtml=run('videoSourceAppearanceEvidence(appearanceVideo)');
assert.match(partialAppearanceHtml,/Not measured/);assert.match(partialAppearanceHtml,/Oct 22, 2026/);assert.doesNotMatch(partialAppearanceHtml,/≥2/);
for(const mutation of [r=>r.revisionComparisonComplete=false,r=>r.stableIdentityComparisonVerified=false,r=>r.appliesToSnapshotAt='2000-01-01T00:00:00Z',r=>r.newStableSourceRecordsMinimum=0,r=>r.laterValidSourceRows=99,r=>r.sourceRecordsRemoved=1,r=>r.records[0].profileId='wrong-profile',r=>r.records[0].contact='Different person']){
 ctx.invalidAppearance=JSON.parse(JSON.stringify(ctx.appearanceVideo));mutation(ctx.invalidAppearance.gapResolutionReview.sourceAppearanceReview);
 run("S.start='2026-10-19';S.end='2026-10-25';");
 assert.equal(run('selectedVideoSourceAppearances(invalidAppearance).value'),null);
}
// Both bounds share a UTC calendar day but straddle two Mountain days.
ctx.offsetAppearance=JSON.parse(JSON.stringify(ctx.appearanceVideo));
const offsetReview=ctx.offsetAppearance.gapResolutionReview.sourceAppearanceReview;
offsetReview.firstAppearedAfter='2026-10-22T05:30:00Z';offsetReview.firstAppearedBy='2026-10-22T06:30:00Z';
for(const record of offsetReview.records){record.firstAppearedAfter=offsetReview.firstAppearedAfter;record.firstAppearedBy=offsetReview.firstAppearedBy;}
run("S.start='2026-10-22';S.end='2026-10-22';");assert.equal(run('selectedVideoSourceAppearances(offsetAppearance).value'),null);
run("S.start='2026-10-21';S.end='2026-10-22';");assert.equal(run('selectedVideoSourceAppearances(offsetAppearance).value'),2);
const eventCountBeforeAppearance=run('S.data.video.messageDateReview.platformObservedEvents.length');
run('S.data.video.gapResolutionReview.sourceAppearanceReview=appearanceVideo.gapResolutionReview.sourceAppearanceReview;videoSourceAppearanceEvidence(S.data.video);');
assert.equal(run('S.data.video.messageDateReview.platformObservedEvents.length'),eventCountBeforeAppearance);
assert.equal(run('JSON.stringify(S.data.outcomes)'),priorLedger);

// A historical unsuccessful check stays historical after a later exact asset
// observation. Neither a different asset nor an earlier observation closes it.
ctx.cohortFixture={summary:{},messageDateReview:{records:[],platformObservedEvents:[{
  dedupKey:'subimage|outbound|2026-10-26|exact-asset',profileId:'alexchantavy',company:'SubImage',
  date:'2026-10-26',direction:'outbound',videoIncluded:true,assetId:'a'.repeat(32),observedAt:'2026-10-29T06:10:00Z'
}],nativePlatformCoverage:{cohort:'Retained October asset cohort.',cohortProfilesChecked:19,
  cohortExactOutboundVideoMatches:18,reviewedAt:'2026-10-24T03:45:00Z',profileChecks:[{
    profileId:'alexchantavy',company:'SubImage',status:'checked_unconfirmed',assetId:'a'.repeat(32),
    observedAt:'2026-10-24T03:45:00Z',basis:'Exact asset was not visible in the earlier bounded review.'
  }]},focusedNativeReviews:{profilesChecked:25,reviewedAt:'2026-10-29T06:10:00Z'}}};
run("S.data={meta:{},video:cohortFixture,outcomes:actualOutcomes};S.start='2026-10-26';S.end='2026-10-29';");
const cohortBefore=JSON.stringify(ctx.cohortFixture),resolvedCohortHtml=run('videoMessageDateEvidence(S.data.video)');
assert.match(resolvedCohortHtml,/Earlier cohort review: 18 of 19/);
assert.match(resolvedCohortHtml,/SubImage was subsequently verified on source day Oct 26, 2026/);
assert.doesNotMatch(resolvedCohortHtml,/SubImage remains unconfirmed/);
assert.match(resolvedCohortHtml,/Latest focused review: 25 profiles checked/);
assert.equal(JSON.stringify(ctx.cohortFixture),cohortBefore,'Rendering must preserve earlier checks and later proof');
assert.equal(observed().videoSends,1);
ctx.cohortFixture.messageDateReview.platformObservedEvents[0].assetId='b'.repeat(32);
assert.match(run('videoMessageDateEvidence(S.data.video)'),/SubImage remains unconfirmed/);
ctx.cohortFixture.messageDateReview.platformObservedEvents[0].assetId='a'.repeat(32);
ctx.cohortFixture.messageDateReview.platformObservedEvents[0].observedAt='2026-10-23T06:10:00Z';
assert.match(run('videoMessageDateEvidence(S.data.video)'),/SubImage remains unconfirmed/);
ctx.cohortFixture.messageDateReview.platformObservedEvents[0].observedAt='2026-10-29T06:10:00Z';

// A person whose only dated evidence is a native follow-up belongs in that
// selected week's register, without becoming an additional video send/reply.
ctx.followUpFixture={summary:{},messageDateReview:{records:[
  {profileId:'follow-up-only',company:'Follow-up only company',platformFollowUpDate:'2026-10-26'},
  {profileId:'prior-follow-up',company:'Outside earlier',platformFollowUpDate:'2026-10-25'},
  {profileId:'later-follow-up',company:'Outside later',platformFollowUpDate:'2026-10-30'}
],platformObservedEvents:[{dedupKey:'follow-up-only|outbound|2026-10-26|text',
  profileId:'follow-up-only',date:'2026-10-26',direction:'outbound',videoIncluded:false}]}};
run("S.data={meta:{},video:followUpFixture,outcomes:actualOutcomes};S.start='2026-10-26';S.end='2026-10-29';");
const followUpHtml=run('videoMessageDateEvidence(S.data.video)');
const followUpTable=ctx.capturedTables.filter(t=>t[0]==='video-message-dates').at(-1);
assert.deepEqual(Array.from(followUpTable[2],r=>r.profileId),['follow-up-only']);
const followUpCol=followUpTable[3].find(c=>c.key==='platformFollowUpDate');
assert.ok(followUpCol,'Observed follow-ups need a dedicated date column');
assert.equal(followUpCol.label,'Video follow-up · observed');
assert.equal(followUpCol.render('2026-10-26'),'Oct 26, 2026');
assert.match(followUpHtml,/Video follow-up · observed/);
ctx.followUpRows=followUpTable[2];ctx.followUpCols=followUpTable[3];
run("bindTable('follow-up-fixture',followUpRows,followUpCols);");
assert.match(body.innerHTML,/Follow-up only company/);assert.match(body.innerHTML,/Oct 26, 2026/);
assert.doesNotMatch(body.innerHTML,/Outside earlier|Outside later/);
assert.equal(observed().videoSends,0);assert.equal(observed().videoReplies,0);
assert.equal(run('JSON.stringify(S.data.outcomes)'),priorLedger);

// Later native proof closes a displayed gap without overwriting the old
// unsuccessful bounded review or silently creating activity-ledger events.
ctx.closedGapFixture={summary:{},messageDateReview:{platformObservedEvents:[]},gapResolutionReview:{
  snapshotAt:'2026-10-29T06:10:00Z',records:[{
    profileId:'alexchantavy',company:'SubImage',status:'Closed: exact native send verified',
    findings:['Earlier unconfirmed observation retained; later exact asset directly observed.'],
    platformSendDate:'2026-10-21',sendAssetObserved:false,
    nativeSendEvidence:{date:'2026-10-26',assetId:'a'.repeat(32),observedAt:'2026-10-29T06:10:00Z'}
  },{profileId:'still-unconfirmed',company:'Still bounded',status:'Unresolved',sendAssetObserved:false}]
}};
run('S.data={meta:{},video:closedGapFixture,outcomes:actualOutcomes};');
const gapBefore=JSON.stringify(ctx.closedGapFixture),gapCountsBefore=observed();
const closedGapHtml=run('videoGapResolutionEvidence(S.data.video)');
const closedGapTable=ctx.capturedTables.filter(t=>t[0]==='video-gap-resolution').at(-1);
const nativeGapRow=closedGapTable[2][0],closedDateCol=closedGapTable[3].find(c=>c.key==='platformSendDate'),
  closedAssetCol=closedGapTable[3].find(c=>c.key==='sendAssetObserved');
assert.match(closedGapHtml,/adds no send, reply or commercial-outcome count/);
ctx.closedGapRows=closedGapTable[2];ctx.closedGapCols=closedGapTable[3];
run("bindTable('closed-gap-fixture',closedGapRows,closedGapCols);");
assert.match(body.innerHTML,/Closed: exact native send verified/);assert.match(body.innerHTML,/Oct 26, 2026/);
assert.match(body.innerHTML,/Asset observed in reviewed message/);
assert.equal(closedDateCol.render(nativeGapRow.platformSendDate,nativeGapRow),'Oct 26, 2026');
assert.equal(closedAssetCol.render(nativeGapRow.sendAssetObserved,nativeGapRow),'Asset observed in reviewed message');
assert.equal(closedAssetCol.render(false,closedGapTable[2][1]),'Not observed in bounded view');
assert.equal(nativeGapRow.sendAssetObserved,false,'Earlier bounded result must retain its historical value');
assert.equal(nativeGapRow.platformSendDate,'2026-10-21','Native date display must not rewrite the source report');
assert.equal(JSON.stringify(ctx.closedGapFixture),gapBefore);
assert.deepEqual(observed(),gapCountsBefore,'Gap display alone must not create observed-message events');
assert.equal(run('JSON.stringify(S.data.outcomes)'),priorLedger);
console.log('Video date display: observed minimums, exact worksheet responses, scoped identity evidence, historical gap resolution and follow-up dates passed.');
