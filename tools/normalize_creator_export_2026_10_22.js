/* Normalize the downloaded creator XLSX and independently retained Charles UI.
 * No network access, source mutations, shared-snapshot writes or publication. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const XLSX=require('/Users/christianwutz/mcp-servers/centripetal/node_modules/xlsx');
const ROOT=path.resolve(__dirname,'..'),DIR=path.join(ROOT,'data/private/completion_audit_2026_10_22/creator');
const file=path.join(DIR,'AggregateAnalytics_Charles Solomon_2026-07-25_2026-10-22.xlsx');
const uiFile=path.join(DIR,'creator_export_source_ax.txt'),ui=fs.readFileSync(uiFile,'utf8');
const workbook=XLSX.readFile(file),sheet=name=>XLSX.utils.sheet_to_json(workbook.Sheets[name],{header:1,defval:null});
const date=value=>{const m=String(value).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);assert(m,`Invalid source date ${value}`);return `${m[3]}-${m[1].padStart(2,'0')}-${m[2].padStart(2,'0')}`;};
const integer=value=>{assert(value!==null&&value!==undefined&&value!=='','Missing numeric source field');const n=Number(String(value).replaceAll(',',''));assert(Number.isInteger(n)&&n>=0,`Invalid source count ${value}`);return n;};
const sum=(rows,key)=>rows.reduce((n,r)=>n+r[key],0);
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
assert(ui.includes('button Charles Solomon Me')&&ui.includes('linkedin.com/in/solomoncharles/')&&ui.includes('button 90 days')&&ui.includes('Daily data is recorded in UTC'));
const observedAt=fs.statSync(uiFile).mtime.toISOString(),downloadCompletedAt=fs.statSync(file).mtime.toISOString();
const discovery=sheet('DISCOVERY');assert.equal(discovery[0][1],'7/25/2026 - 10/22/2026');
const impressions=integer(discovery.find(r=>r[0]==='Impressions')[1]),reach=integer(discovery.find(r=>r[0]==='Members reached')[1]);
const rows=sheet('ENGAGEMENT');assert.deepEqual(rows[0],['Date','Impressions','Engagements']);
const daily=rows.slice(1).map(r=>({date:date(r[0]),impressions:integer(r[1]),engagements:integer(r[2])}));
assert.equal(daily.length,90);assert.equal(daily[0].date,'2026-07-25');assert.equal(daily.at(-1).date,'2026-10-22');
assert.equal(new Set(daily.map(r=>r.date)).size,daily.length);
daily.forEach((r,i)=>{if(i)assert.equal((Date.parse(r.date)-Date.parse(daily[i-1].date))/86400000,1);});
assert.equal(sum(daily,'impressions'),impressions);
const points=[...ui.matchAll(/image (?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), ([A-Z][a-z]{2} \d{1,2}, 2026), ([\d,]+)\. Impressions\./g)].map(m=>({date:new Date(`${m[1]} 12:00:00 UTC`).toISOString().slice(0,10),cumulativeImpressions:integer(m[2])}));
assert.equal(points.length,90);let running=0;daily.forEach((r,i)=>{running+=r.impressions;assert.equal(points[i].date,r.date);assert.equal(points[i].cumulativeImpressions,running);});
function following(label){const m=ui.match(new RegExp(`text ${label}\\n\\s*\\d+ text ([\\d,]+)`));assert(m,`Missing UI ${label}`);return integer(m[1]);}
function preceding(label){const m=ui.match(new RegExp(`text ([\\d,]+)\\n\\s*\\d+ text ${label}`));assert(m,`Missing UI ${label}`);return integer(m[1]);}
const summary={impressions,membersReached:reach,socialEngagements:preceding('Social engagements'),
  reactions:following('Reactions'),comments:following('Comments'),reposts:following('Reposts'),saves:following('Saves'),sendsOnLinkedIn:following('Sends on LinkedIn'),
  linkEngagements:preceding('Link engagements'),premiumCustomButtonEngagements:following('Premium custom button engagements'),visitsToLinksInAllPosts:following('Visits to links in all posts'),
  inNetworkPercent:30,outOfNetworkPercent:70,exportEngagements:sum(daily,'engagements')};
assert.equal(summary.reactions+summary.comments+summary.reposts+summary.saves+summary.sendsOnLinkedIn,summary.socialEngagements);
assert.equal(summary.exportEngagements,555);assert.equal(summary.socialEngagements,545);assert.equal(summary.linkEngagements,10);
assert(ui.includes(`${reach.toLocaleString('en-US')} Members reached`));
assert(ui.includes('In-network (followers and connections) 30% Out-of-network 70%'));
const comparisonMatch=ui.match(/text (\d+)%\n\s*\d+ text vs\. prior 90 days/);assert(comparisonMatch);
const old=JSON.parse(fs.readFileSync(path.join(ROOT,'data/shared-dashboard.json'),'utf8')).content.creatorAnalytics;
const coverage={...old.coverage,start:'2026-07-25',end:'2026-10-22',finalDayPartial:true,completeDaysThrough:'2026-10-21',observedMountainDate:'2026-10-22',sourceMayRestate:true};
const postRows=sheet('TOP POSTS');assert(postRows[0][0].includes('Maximum of 50 posts'));assert.equal(postRows[2][0],'Post URL');
const posts=new Map();let engagementRows=0,impressionRows=0;
for(const [offset,metric] of [[0,'engagements'],[4,'impressions']])for(const r of postRows.slice(3)){
  if(!r[offset])continue;
  const url=new URL(r[offset]);assert.equal(url.hostname,'www.linkedin.com');
  const m=url.pathname.match(/(ugcPost|share)-(\d+)/);assert(m,'No stable post object identity');
  const id=`${m[1]}:${m[2]}`,publishedAt=date(r[offset+1]),prior=posts.get(id);
  if(prior)assert.equal(prior.publishedAt,publishedAt);
  const p=prior||{postId:id,url:String(r[offset]),publishedAt,account:'Charles Solomon',impressions:null,engagements:null,impressionRank:null,engagementRank:null};
  const rank=metric==='impressions'?++impressionRows:++engagementRows;p[metric]=integer(r[offset+2]);p[metric==='impressions'?'impressionRank':'engagementRank']=rank;
  posts.set(id,p);
}
assert(impressionRows<=50&&engagementRows<=50);
const followerRows=sheet('FOLLOWERS'),followers=integer(followerRows[0][1]);assert.equal(followerRows[0][0],'Total followers on 10/22/2026');
assert.deepEqual(followerRows[2],['Date','New followers']);
const followerDaily=followerRows.slice(3).map(r=>({date:date(r[0]),newFollowers:integer(r[1])}));
assert.equal(followerDaily.length,90);assert.deepEqual(followerDaily.map(r=>r.date),daily.map(r=>r.date));
const exportAnalytics={snapshotAt:downloadCompletedAt,collectedAt:downloadCompletedAt,coverage,
  source:'Authenticated Charles creator workbook',
  engagementDefinition:'Original worksheet field Engagements; broader source measure kept separate from the signed-in UI Social engagements. Daily social-only components are not supplied.',
  daily,summary:{impressions,membersReached:reach,engagements:sum(daily,'engagements')},
  postCoverage:{completePublishingHistory:false,rankingCapPerMetric:50,engagementRankedRows:engagementRows,impressionRankedRows:impressionRows,uniqueRankedPosts:posts.size,measurementWindow:{start:coverage.start,end:coverage.end,sourceTimezone:'UTC'},note:'Union of separately capped engagement and impression rankings, deduplicated by the source post object ID. Publication dates select posts; performance belongs to the full export window. Missing ranking metrics remain null; no zero or publishing census is inferred.'},
  rankedPosts:[...posts.values()].sort((a,b)=>(a.impressionRank??1000)-(b.impressionRank??1000)),
  followers:{snapshotOn:'2026-10-22',total:followers,daily:followerDaily,newFollowersInWindow:sum(followerDaily,'newFollowers'),definition:'Source new followers field, not net follower change; unfollows and opening follower inventory are unavailable.'},
  demographics:{audience:sheet('AUDIENCE DEMOGRAPHICS').slice(1).map(r=>({category:r[0],value:r[1],percentageLabel:r[2]})),content:sheet('CONTENT DEMOGRAPHICS').slice(1).map(r=>({category:r[0],value:r[1],percentageLabel:r[2]})),note:'Rounded or suppressed percentage labels retained as text. Audience and content populations differ; no numeric conversion or unduplicated audience total is inferred.'},
  notes:['Impressions and all 90 daily rows reconcile to the independently retained cumulative UI chart.','Export Engagements total 555; separate UI social total 545 and link total 10 are retained with distinct definitions. The numeric difference is not used to allocate daily social or link events.','Ranked posts include publication dates outside the source measurement window. No lifetime performance or complete publishing history is implied.','New followers are source additions, not net audience growth; daily unique reach remains unavailable.','October 22 UTC is partial. The dashboard reporting cutoff remains October 21; this fixed source extends beyond that cutoff.']};
const creator={...old,snapshotAt:observedAt,collectedAt:observedAt,checkedAt:'2026-10-22',coverage,summary,
  method:'Authenticated Charles Chrome creator workbook download, independently reconciled to retained creator UI',
  comparison:{...old.comparison,percentChange:integer(comparisonMatch[1]),label:`${comparisonMatch[1]}% higher versus prior 90 days`},
  chart:{...old.chart,points},
  daily:daily.map(r=>({...r,engagements:null,exportEngagements:r.engagements,account:'Charles Solomon',sourceId:'charles_creator_export',sourceTimezone:'UTC',currentDayPartial:r.date===coverage.end,derivation:'Direct XLSX worksheet row, impression values independently reconciled to cumulative UI'})),
  exportAnalytics,
  topPosts:old.topPosts.map(p=>{const m=p.url.match(/urn:li:(ugcPost|share):(\d+)/),record=m?posts.get(`${m[1]}:${m[2]}`):null;return record?{...p,impressions:record.impressions,engagements:record.engagements,publishedAt:record.publishedAt}:p;}),
  notes:exportAnalytics.notes,
  evidence:{sourceFileSha256:sha(file),uiFileSha256:sha(uiFile),observationTimeBasis:'UI capture write time; workbook download completion retained separately'}};
const patch={creatorAnalytics:creator,validation:{identityVerified:true,dailyRows:daily.length,impressionsReconciledToEveryUiPoint:true,exportEngagements:summary.exportEngagements,socialEngagements:summary.socialEngagements,rankedPosts:posts.size,followers}};
fs.writeFileSync(path.join(DIR,'creator_export_patch.json'),JSON.stringify(patch,null,2)+'\n');
console.log(JSON.stringify(patch.validation));
