/* Read the retained LinkedIn company-page XLS export without changing it.
 * Output is an isolated companyAnalytics patch. Sponsored metrics overlap Ads;
 * this script never merges them into personal content or paid delivery totals. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const XLSX=require('/Users/christianwutz/mcp-servers/centripetal/node_modules/xlsx');
const ROOT=path.resolve(__dirname,'..'),DIR=path.join(ROOT,'data/private/refresh_2026_10_22/company');
const input=process.argv[2]||path.join(DIR,'company_content.xls'),output=process.argv[3]||path.join(DIR,'company_patch.json');
const raw=fs.readFileSync(input),book=XLSX.read(raw,{type:'buffer',cellDates:false,cellNF:true,cellText:true});
assert.deepEqual(book.SheetNames,['Metrics'],'Review new workbook sheets before changing the parser');
const rows=XLSX.utils.sheet_to_json(book.Sheets.Metrics,{header:1,raw:true,defval:null});
assert.match(rows[0][0],/Data is delayed by up to 2 days/);
assert.match(rows[0][0],/All dates and times are in UTC/);
const headers=rows[1];
const pairs=['Impressions','Clicks','Reactions','Comments','Reposts'];
function date(value){const m=/^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);assert(m,'Unexpected source date');return `${m[3]}-${m[1]}-${m[2]}`;}
function number(value){if(value===null||value===undefined||value===''||value==='-'||value==='—')return null;assert.equal(typeof value,'number');assert(Number.isFinite(value));return value;}
const daily=rows.slice(2).filter(r=>r[0]).map((r,i)=>{
  const cells=Object.fromEntries(headers.map((h,j)=>[h,r[j]])),out={date:date(r[0]),sourceRow:i+3,sourceTimezone:'UTC'};
  for(const metric of pairs){const key=metric[0].toLowerCase()+metric.slice(1);for(const kind of ['organic','sponsored','total'])out[key+kind[0].toUpperCase()+kind.slice(1)]=number(cells[`${metric} (${kind})`]);
    const [o,s,t]=['Organic','Sponsored','Total'].map(s=>out[key+s]);
    if([o,s,t].every(n=>n!==null))assert.equal(o+s,t,`Source partition mismatch ${out.date} ${metric}`);
  }
  out.organicUniqueImpressionsDaily=number(cells['Unique impressions (organic)']);
  for(const kind of ['organic','sponsored','total'])out['sourceEngagementRate'+kind[0].toUpperCase()+kind.slice(1)]=number(cells[`Engagement rate (${kind})`]);
  return out;
});
assert.equal(daily.length,new Set(daily.map(r=>r.date)).size,'Duplicate source-day rows');
assert.equal(daily.length,47);assert.equal(daily[0].date,'2026-09-04');assert.equal(daily.at(-1).date,'2026-10-20');
const sum=(key,selected=daily)=>selected.every(r=>r[key]!==null&&r[key]!==undefined)?selected.reduce((n,r)=>n+r[key],0):null;
const summary={};
for(const kind of ['Organic','Sponsored','Total']){
  const data={};for(const metric of pairs){const key=metric[0].toLowerCase()+metric.slice(1);data[key]=sum(key+kind);}
  data.socialActions=data.reactions===null||data.comments===null||data.reposts===null?null:data.reactions+data.comments+data.reposts;
  data.engagementRate=null;data.uniqueReach=null;summary[kind.toLowerCase()]=data;
}
assert.equal(summary.total.impressions,24698);assert.equal(summary.total.clicks,105);
assert.equal(summary.total.reactions,8);assert.equal(summary.total.comments,0);assert.equal(summary.total.reposts,1);
assert.equal(summary.organic.impressions,9);assert.equal(summary.sponsored.impressions,24689);
const ads=JSON.parse(fs.readFileSync(path.join(ROOT,'data/private/refresh_2026_10_22/ads/ads_patch.json'),'utf8'));
const sourceAds=ads.daily.filter(r=>r.date>=daily[0].date&&r.date<=daily.at(-1).date),adByDate=new Map(sourceAds.map(r=>[r.date,r]));
const comparisons={impressions:'impressions',clicks:'clicks',reactions:'reactions',comments:'comments',reposts:'shares'};
const reconciled={};
for(const [companyKey,adKey] of Object.entries(comparisons)){
  const observed=sourceAds.reduce((n,r)=>n+r[adKey],0);reconciled[companyKey]={companySponsored:summary.sponsored[companyKey],paidSource:observed,equal:summary.sponsored[companyKey]===observed};
  assert(reconciled[companyKey].equal,`Review source difference for ${companyKey}`);
  assert(daily.every(r=>r[companyKey+'Sponsored']===adByDate.get(r.date)?.[adKey]),`Review daily difference for ${companyKey}`);
}
// Freeze collection metadata once; replaying normalization must not make the
// source appear newer or borrow a later original-file modification timestamp.
const original=path.join('/Users/christianwutz/Downloads','centripetal-advisors_content_1792650141480.xls');
const sha=crypto.createHash('sha256').update(raw).digest('hex'),metadataPath=path.join(DIR,'source_metadata.json');
let metadata;
if(fs.existsSync(metadataPath)){metadata=JSON.parse(fs.readFileSync(metadataPath,'utf8'));assert.equal(metadata.sha256,sha,'Retained source changed; review collection metadata');}
else{
  const originalMatches=fs.existsSync(original)&&crypto.createHash('sha256').update(fs.readFileSync(original)).digest('hex')===sha;
  metadata={sha256:sha,collectedAt:new Date(fs.statSync(originalMatches?original:input).mtimeMs).toISOString(),timeBasis:originalMatches?'Original LinkedIn export download completion, independently observed by parent browser review':'Retained local-file inspection metadata; upstream generation timestamp unavailable'};
  fs.mkdirSync(DIR,{recursive:true});fs.writeFileSync(metadataPath,JSON.stringify(metadata,null,2)+'\n');
}
const patch={
  snapshotAt:metadata.collectedAt,collectedAt:metadata.collectedAt,
  collectionTimeBasis:metadata.timeBasis,
  sourceGeneratedAt:null,method:'Read-only XLS export from authenticated company-page admin analytics; parsed with existing local SheetJS library',
  account:{name:'Centripetal Advisors',companyId:'66767979',url:'https://www.linkedin.com/company/centripetal-advisors/',identityVerified:true,identityBasis:'Parent verified Charles Solomon signed-in native Chrome company-admin view and matching company ID; extension independently verified public company ID'},
  coverage:{start:daily[0].date,end:daily.at(-1).date,sourceTimezone:'UTC',finalDayPartial:false,sourceDelayUpToDays:2,sourceMayRestate:true,completeWithinExport:true,requestedEndUnavailable:'2026-10-21',dateBasis:'View/action date for organic and sponsored company posts, not post publication date'},
  sourceHeader:rows[0][0],summary,daily,
  followersSnapshot:{followers:899,checkedAt:'2026-10-22',basis:'Point-in-time company-page follower count, independently visible in public and authenticated admin views; not followers gained during the metric window'},
  posts:[],postCoverage:{status:'not_exported',complete:false,publishedPostCount:null,note:'This workbook contains only Metrics, without post IDs, titles, publication dates or per-post performance. Missing post rows do not establish zero publishing.'},
  reconciliation:{ads:{coverage:{start:daily[0].date,end:daily.at(-1).date,sourceTimezone:'UTC'},metrics:reconciled,dailyMetricsAgree:true,treatment:'Company-sponsored metrics exactly match the same-day paid-source subset here. They overlap Ads and must not be added to paid delivery or reported as incremental reach.'}},
  notes:[
    'Company-page metrics are a separate account scope from Charles personal creator analytics. Their impression and engagement scopes are not an account-wide unique-audience total.',
    'The export contains explicit numeric zeros, which are retained. Missing or dash fields remain null. All 47 UTC view/action-date rows and organic/sponsored/total partitions reconcile.',
    'The source states data may be delayed by up to two days. October21 was unavailable in the admin date picker; October20 was the latest accepted export end. Later dates remain unknown, not zero.',
    'Daily unique organic impressions remain daily values only. They are not summed into period unique reach, and sponsored unique reach is not supplied.',
    'Source daily engagement-rate fields are preserved without averaging. The workbook lacks a complete additive numerator for that broader rate; no aggregate engagement rate or inferred total engagements is manufactured.',
    'Social actions here mean reactions + comments + reposts only, separate from clicks and the platform broader engagement-rate definition.',
    'The Metrics worksheet does not establish the publishing census or individual post results. A post-level export/register remains required.',
    'Sponsored company delivery matches the same-window Ads export. These two measurements are overlapping views of distribution and cannot be summed.',
    'Followers are a point-in-time inventory and do not follow the reporting-period filter. No source-attributed lead, accepted opportunity, client win or revenue is inferred from company content.'
  ],
  review:{worksheets:book.SheetNames,sourceRange:book.Sheets.Metrics['!ref'],dailyRows:daily.length,checks:{sourcePartitionsReconcile:true,dateKeysUnique:true,explicitZerosPreserved:true,adsSponsoredDailyCountersAgree:true,noPostCoverageInvented:true,noPeriodUniqueReachInvented:true,noDailyRateAveraged:true}},
  provenance:{file:path.basename(input),sha256:sha}
};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(patch,null,2)+'\n');
fs.writeFileSync(path.join(DIR,'normalization_review.json'),JSON.stringify({snapshotAt:patch.snapshotAt,coverage:patch.coverage,summary:patch.summary,postCoverage:patch.postCoverage,reconciliation:patch.reconciliation,review:patch.review},null,2)+'\n');
console.log(JSON.stringify({output,coverage:patch.coverage,summary:patch.summary,postCoverage:patch.postCoverage,checks:patch.review.checks}));
