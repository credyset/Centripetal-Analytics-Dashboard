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
run("S.start='2026-10-20';S.end='2026-10-20';");
assert.equal(observed().videoSends,0);assert.equal(observed().generalReplies,0);
assert.equal(vector().cardActivity.value,null); // Missing sample evidence never becomes verified zero.
run("S.start='2026-10-21';S.end='2026-10-21';");
assert.equal(observed().videoSends,1);assert.equal(observed().generalReplies,0);
run("S.start='2026-10-23';S.end='2026-10-23';");
assert.equal(vector().cardActivity.value,null);
console.log('Video date display: observed source-day minimums, reported/history separation, no email duplication, no inferred reply/outcome or zero passed.');
