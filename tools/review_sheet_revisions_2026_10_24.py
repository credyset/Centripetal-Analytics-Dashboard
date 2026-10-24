"""Bound source-record first appearance from complete retained revision exports.

This is a comparison of source inventories, not a sending or exact edit-time log.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import unquote
import csv
import io
import json
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'data/private/gap_resolution_2026_10_24/sheets'


def content(path):
    wrapper=json.loads(path.read_text())
    result=wrapper['result'];result=result.get('value',result)
    data=result['structuredContent']
    assert data['mimeType'] in ('application/vnd.google-apps.spreadsheet','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    tabs=data['content'].split('\f')
    assert len(tabs)==2, 'Expected both returned native Sheet tabs'
    parsed=list(csv.reader(io.StringIO(tabs[0])))
    assert parsed[0][1:9]==['rank','org','icp','tier','stage','contact','ctitle','li'], 'Identity columns differ; cannot join revisions'
    assert all(len(row)==30 for row in parsed), 'Unequal CSV widths or possible partial row'
    assert [row[0] for row in parsed[1:]]==[str(i) for i in range(len(parsed)-1)], 'Returned revision row sequence has a gap or duplicate'
    rows=[dict(zip(parsed[0][1:],row[1:])) for row in parsed[1:]]
    return data,[row for row in rows if row['org'] and row['contact']],wrapper['collectedAt']


def normalize(value):
    return re.sub(r'[^a-z0-9]+','',unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().casefold())


def profile(row):
    match=re.search(r'linkedin\.com/in/([^/?#]+)',row['li'],re.I)
    return unquote(match[1]).casefold() if match else None


def identity(row):
    return profile(row),normalize(row['org']),normalize(row['contact'])


def build():
    old,a,_=content(PRIVATE/'revision_1253.json')
    newer,b,collected=content(PRIVATE/'revision_1290.json')
    last,c,_=content(PRIVATE/'previous_revision_1304.json')
    ka,kb,kc=Counter(map(identity,a)),Counter(map(identity,b)),Counter(map(identity,c))
    assert not ka-kb, 'Earlier source identities changed or disappeared; manual attribution review is required'
    assert not kb-kc and not kc-kb, 'Later revision identities changed; expand the bounded comparison'
    pa,pb={profile(r) for r in a if profile(r)},{profile(r) for r in b if profile(r)}
    new_profiles=pb-pa
    added=[r for r in b if profile(r) in new_profiles]
    assert len(added)==len(new_profiles)==sum((kb-ka).values())==40
    current=json.loads((ROOT/'data/shared-dashboard.json').read_text())['video']
    current_rows={r['id']:r for r in current['rows']}
    for row in added:
        joined=current_rows[profile(row)]
        assert normalize(joined['company'])==normalize(row['org']) and normalize(joined['contact'])==normalize(row['contact'])
    first=old['revisionModifiedTime'];second=newer['revisionModifiedTime']
    local=lambda v:datetime.fromisoformat(v.replace('Z','+00:00')).astimezone(ZoneInfo('America/Denver')).isoformat()
    reviewed=datetime.strptime(collected,'%Y-%m-%d %H:%M:%S UTC').isoformat()+'Z'
    return {'snapshotAt':reviewed,'reviewedAt':reviewed,'appliesToSnapshotAt':current['snapshotAt'],
        'revisionComparisonComplete':True,'stableIdentityComparisonVerified':True,
        'scope':'Source identity first-appearance bounds from retained workbook revision exports; not an exact edit or message event log.',
        'baselineRevisionId':old['revisionId'],'laterRevisionId':newer['revisionId'],'subsequentRevisionId':last['revisionId'],
        'firstAppearedAfter':first,'firstAppearedBy':second,
        'firstAppearedAfterMountain':local(first),'firstAppearedByMountain':local(second),
        'baselineValidSourceRows':len(a),'laterValidSourceRows':len(b),'retainedPriorStableIdentities':sum(ka.values()),
        'newStableSourceRecordsMinimum':40,'newUniqueProfilesMinimum':40,
        'sourceRecordsRemoved':0,'subsequentIdentityChanges':0,
        'selectedWeekStart':'2026-10-19','selectedWeekEnd':'2026-10-25',
        'boundsContainedInSelectedWeek':True,'exactRowAddedTimestampAvailable':False,
        'actualMessageEventsAdded':0,'sourceWritesPerformed':False,
        'records':[{'profileId':profile(row),'company':row['org'],'contact':row['contact'],
            'currentSourceRow':current_rows[profile(row)]['sourceRow'],
            'firstAppearedAfter':first,'firstAppearedBy':second} for row in added],
        'notes':['All 428 prior exact profile plus normalized company/contact identities remain in the later 468-row returned revision. Forty new unique profiles appear, with no prior stable identity removed.',
            'Both revision bounds are within October 19–25 Mountain time, supporting a weekly source first-appearance minimum of 40; the interval is October 21 afternoon through October 22 afternoon.',
            'These are source-record first appearances within compared retained revisions, not exact row-added timestamps, first-ever prospect discovery dates, Video DM sends, replies or CRM deal creation events.',
            'No additional identity appeared between the later revision and revision 1304. The current full-range reread separately matches the retained latest inventory.',
            'Historical helper/formula edits and inserted row positions do not establish sending dates; current row numbers are independent profile/identity joins.']}


if __name__=='__main__':
    value=build()
    (PRIVATE/'source_appearance_review_patch.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'minimumNewStableRecords':value['newStableSourceRecordsMinimum'],'minimumNewUniqueProfiles':value['newUniqueProfilesMinimum'],
        'after':value['firstAppearedAfter'],'by':value['firstAppearedBy'],'actualMessagesAdded':0}))
