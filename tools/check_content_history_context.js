/* Preserve historical source wording while preventing stale "current" claims. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'..'),source=fs.readFileSync(path.join(root,'app.js'),'utf8').replace(/\ninit\(\);\s*$/,'');
const context=vm.createContext({Intl,Date,URL,setTimeout:()=>{},document:{querySelector:()=>null}});
vm.runInContext(source,context);
const run=code=>vm.runInContext(code,context);
let checks=0;
function verifyContext(content){
  context.contentInput=content;
  const original=JSON.stringify(content),html=run('supplementaryContentEvidence(contentInput)');
  const history=html.slice(html.indexOf('<h2>Historical source context</h2>'));
  assert.ok(history.startsWith('<h2>Historical source context</h2>'),'historical source heading is missing');
  assert.match(history,/EARLIER COLLECTIONS/);
  assert.match(history,/These notes retain the wording and dates of earlier collections\./);
  assert.match(history,/“Current” refers to those earlier collection dates\./);
  assert.match(history,/Use the dated creator and company evidence above for the latest retained source coverage\./);
  const explanation=history.indexOf('“Current” refers to those earlier collection dates.');
  for(const note of content.notes||[]){
    context.noteInput=note;
    const escaped=run('esc(noteInput)');
    assert.ok(history.indexOf(`<li>${escaped}</li>`)>explanation,'source note changed or appeared before its historical explanation');
  }
  assert.equal(JSON.stringify(content),original,'rendering changed retained source data');
  checks++;
}

// This fixture makes the contradiction explicit even when no operational snapshot is available.
verifyContext({notes:['Current creator workbook supplies 90 UTC daily rows through October22 partial, including source-export Engagements. Its 555 Engagements remain distinct from the independently observed 545 social engagements and 10 link engagements.','The current follower worksheet reports 11,557 total followers on October22.']});

// Pass a retained snapshot to check the real historical prose and source rows.
if(process.argv[2]){
  const snapshot=JSON.parse(fs.readFileSync(path.resolve(process.argv[2]),'utf8'));
  verifyContext(snapshot.content);
  context.snapshot=snapshot;
  run('S.data=snapshot;');
  const original=JSON.stringify(snapshot.content);
  const windows=[['2026-11-12','2026-11-18'],['2026-11-16','2026-11-19'],['2026-11-01','2026-11-19'],['2026-11-20','2026-11-20'],['2026-08-21','2026-11-18']];
  for(const [start,end] of windows){
    context.periodStart=start;context.periodEnd=end;
    run('S.start=periodStart;S.end=periodEnd;');
    const selected=run('JSON.stringify(selectedCreatorExport(S.data.content))');
    const current=run('creatorContentEvidence(S.data.content)');
    run('content();');
    assert.equal(run('JSON.stringify(selectedCreatorExport(S.data.content))'),selected,'historical context changed selected metrics');
    assert.equal(run('creatorContentEvidence(S.data.content)'),current,'historical context changed current creator evidence');
    assert.equal(JSON.stringify(snapshot.content),original,'historical rendering changed the canonical content snapshot');
    checks++;
  }
}
console.log(`Content source context: ${checks} historical-wording and retained-range checks passed.`);
