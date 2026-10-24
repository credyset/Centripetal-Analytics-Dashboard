"""Pure, public-fixture regressions for focused source reviews and block anchoring."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import copy
import json

from prepare_shared_snapshot import preserve_newer_shared_sources
from apply_gap_resolution_2026_10_24 import apply_patches
from normalize_native_gaps_2026_10_24 import parse_blocks, choose_block
from apply_refresh_2026_10_23 import event_key

ROOT=Path(__file__).resolve().parents[1]
BASE=json.loads((ROOT/'data/shared-dashboard.json').read_text())
FAMILIES=[('crm','incrementalReview','crm_incremental'),
    ('video','gapResolutionReview','video_gap_resolution'),
    ('video','sourceFreshnessReview','video_source_freshness')]


def fixture():
    old=copy.deepcopy(BASE)
    base_time=datetime.fromisoformat(old['meta']['generatedAt'].replace('Z','+00:00'))
    stamp=(base_time+timedelta(days=1)).isoformat()
    later=(base_time+timedelta(days=2)).isoformat()
    for parent,child,card in FAMILIES:
        old[parent][child]={'snapshotAt':stamp,'reviewedAt':stamp,'proof':'retained_'+child}
        old['sources']=[c for c in old['sources'] if c['id']!=card]+[{'id':card,'asOf':stamp,'name':child,'note':'Original independently dated evidence'}]
    return old,stamp,later


def check_child_families_survive_newer_parent():
    old,stamp,later=fixture()
    incoming=copy.deepcopy(old)
    for parent,child,card in FAMILIES:
        incoming[parent].pop(child,None)
        incoming[parent]['snapshotAt']=later
        incoming['sources']=[c for c in incoming['sources'] if c['id']!=card]
    result=preserve_newer_shared_sources(incoming,old)
    for parent,child,card in FAMILIES:
        assert result[parent][child]==old[parent][child]
        assert next(c for c in result['sources'] if c['id']==card)['asOf']==stamp


def check_older_child_rejected_newer_child_retained():
    old,stamp,later=fixture()
    incoming=copy.deepcopy(old)
    for parent,child,card in FAMILIES:
        incoming[parent][child]['snapshotAt']='2020-01-01T00:00:00Z'
        incoming[parent][child]['proof']='wrong'
    result=preserve_newer_shared_sources(incoming,old)
    for parent,child,_ in FAMILIES:
        assert result[parent][child]==old[parent][child]
    for parent,child,card in FAMILIES:
        incoming[parent][child].update(snapshotAt=later,reviewedAt=later,proof='newer')
    result=preserve_newer_shared_sources(incoming,old)
    for parent,child,_ in FAMILIES:
        assert result[parent][child]['proof']=='newer'


def check_newer_child_survives_older_parent_selection():
    old,stamp,later=fixture()
    incoming=copy.deepcopy(old)
    for parent,child,card in FAMILIES:
        incoming[parent]['snapshotAt']='2020-01-01T00:00:00Z'
        incoming[parent][child].update(snapshotAt=later,reviewedAt=later,proof='newer_independent_child')
        incoming['sources']=[c for c in incoming['sources'] if c['id']!=card]+[{'id':card,'asOf':later,'name':child}]
    incoming['video']['gapResolutionReview']['sourceAppearanceReview']={'snapshotAt':later,'proof':'newer_revision_review'}
    result=preserve_newer_shared_sources(incoming,old)
    for parent,child,card in FAMILIES:
        assert result[parent]['snapshotAt']==old[parent]['snapshotAt']
        assert result[parent][child]['proof']=='newer_independent_child'
        assert next(c for c in result['sources'] if c['id']==card)['asOf']==later
    assert result['video']['gapResolutionReview']['sourceAppearanceReview']['proof']=='newer_revision_review'


def check_nested_revision_review_survives_newer_gap_review():
    old,stamp,later=fixture()
    old['video']['gapResolutionReview']['sourceAppearanceReview']={'snapshotAt':stamp,'proof':'historical_bounds'}
    old['video']['gapResolutionReview']['identityDateReview']={'snapshotAt':stamp,'proof':'historical_identity_diagnostics'}
    incoming=copy.deepcopy(old)
    incoming['video']['gapResolutionReview']={'snapshotAt':later,'reviewedAt':later,'proof':'new_gap_review'}
    result=preserve_newer_shared_sources(incoming,old)
    assert result['video']['gapResolutionReview']['snapshotAt']==later
    assert result['video']['gapResolutionReview']['sourceAppearanceReview']==old['video']['gapResolutionReview']['sourceAppearanceReview']
    assert result['video']['gapResolutionReview']['identityDateReview']==old['video']['gapResolutionReview']['identityDateReview']


def raw_fixture():
    return '''1 button Open the options list in your conversation with Charles Solomon and Nadav Cornberg
2 content list
3 text OCT 16, 2025 Charles Solomon sent the following messages at 1:07 PM
4 link View Charles’ profile Charles Solomon, #HIRING, Value: ...
5 text • 1:07 PM
6 text Earlier unrelated introduction
7 text SEP 25
8 link View Charles’ profile Charles Solomon, #HIRING, Value: ...
9 text • 2:41 PM
10 text Made this video for you
11 link https://www.loom.com/share/028cf476dec54073922b204e5359ef61, Value: ...
12 text OCT 13
13 link View Charles’ profile Charles Solomon, #HIRING, Value: ...
14 text • 3:07 PM
15 text Follow-up
16 text entry area (settable) Write a message..., Value:
'''


def check_exact_asset_anchors_own_message_block():
    blocks=parse_blocks(raw_fixture(),'Nadav Cornberg')
    block=choose_block(blocks,'SEP 25','2:41 PM','outbound','Nadav Cornberg','028cf476dec54073922b204e5359ef61')
    assert block['displayedDateLabel']=='SEP 25' and block['sender']=='Charles Solomon'
    try:
        choose_block(blocks,'OCT 16, 2025','1:07 PM','outbound','Nadav Cornberg','028cf476dec54073922b204e5359ef61')
    except AssertionError:
        pass
    else:
        raise AssertionError('Asset incorrectly attached to an older message header')


def check_shortlink_preview_destination_stays_in_own_block():
    raw=raw_fixture().replace('11 link https://www.loom.com/share/028cf476dec54073922b204e5359ef61, Value: ...',
        '11 link Company video preview, Value: loom.com/share/028cf476dec54073922b204e5359ef61')
    blocks=parse_blocks(raw,'Nadav Cornberg')
    block=choose_block(blocks,'SEP 25','2:41 PM','outbound','Nadav Cornberg','028cf476dec54073922b204e5359ef61')
    assert block['displayedTime']=='2:41 PM'


def check_distinct_same_day_text_identities():
    rows=[]
    for shown,fingerprint in [('9:27 AM','a'*64),('9:35 AM','b'*64)]:
        rows.append({'profileId':'same-profile','direction':'outbound','date':'2026-10-21','assetId':None,
            'dedupKey':'same-profile|outbound|2026-10-21|'+shown+':'+fingerprint})
    assert event_key(rows[0])!=event_key(rows[1])


def check_focused_apply_scope_and_inventory_protection():
    baseline=copy.deepcopy(BASE)
    stamp=(datetime.fromisoformat(baseline['meta']['generatedAt'].replace('Z','+00:00'))+timedelta(days=2)).isoformat()
    patch={'snapshotAt':stamp,'reviewedAt':stamp,'appliesToSnapshotAt':baseline['video']['snapshotAt'],
        'scope':'synthetic scoped reread','inventoryChanged':False}
    reporting=max('2026-10-24',baseline['meta']['reportingAsOfDate'])
    result=apply_patches(baseline,{'sheetFreshnessReview':patch},reporting,stamp)
    assert result['video']['snapshotAt']==baseline['video']['snapshotAt']
    assert result['video']['rows']==baseline['video']['rows']
    assert result['crm']==baseline['crm'] and result['time']==baseline['time'] and result['outcomes']==baseline['outcomes']
    bad=copy.deepcopy(patch);bad['appliesToSnapshotAt']='2020-01-01T00:00:00Z'
    try:
        apply_patches(baseline,{'sheetFreshnessReview':bad},reporting,stamp)
    except AssertionError:
        pass
    else:
        raise AssertionError('Stale inventory-scoped review accepted')


def check_raw_content_rejected():
    baseline=copy.deepcopy(BASE)
    stamp=(datetime.fromisoformat(baseline['meta']['generatedAt'].replace('Z','+00:00'))+timedelta(days=2)).isoformat()
    patch={'snapshotAt':stamp,'reviewedAt':stamp,'appliesToVideoInventorySnapshotAt':baseline['video']['snapshotAt'],
        'records':[],'notes':['private@example.com']}
    try:
        apply_patches(baseline,{'gapResolutionReview':patch},max('2026-10-24',baseline['meta']['reportingAsOfDate']),stamp)
    except AssertionError as exc:
        assert 'Raw email identity rejected' in str(exc)
    else:
        raise AssertionError('Raw personal email leaked into public review')


def main():
    tests=[check_child_families_survive_newer_parent,check_older_child_rejected_newer_child_retained,
        check_newer_child_survives_older_parent_selection,check_nested_revision_review_survives_newer_gap_review,
        check_exact_asset_anchors_own_message_block,check_shortlink_preview_destination_stays_in_own_block,check_distinct_same_day_text_identities,
        check_focused_apply_scope_and_inventory_protection,check_raw_content_rejected]
    for test in tests:test()
    print(f'October24 gap review: {len(tests)} public-fixture preservation, exact-block/date, event identity, scope and privacy regressions passed.')


if __name__=='__main__':main()
