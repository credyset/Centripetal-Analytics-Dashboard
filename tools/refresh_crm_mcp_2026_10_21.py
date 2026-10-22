"""Build local CRM/referral patches from retained read-only MCP responses.

No source collection, shared-file edits or publication occurs here. Run with the
bundled Python runtime (zoneinfo required). Raw responses stay ignored/private.
"""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_21'
MCP = PRIVATE / 'mcp'
SOURCE = MCP / 'normalized_source'


def load_response(name):
    outer = json.loads((MCP / name).read_text())
    assert not outer.get('isError'), name
    text = [c['text'] for c in outer['content'] if c['type'] == 'text']
    assert len(text) == 1, name
    inner = json.loads(text[0])
    assert inner.get('success') is True, name
    return inner


def stamp(name):
    return datetime.fromtimestamp((MCP / name).stat().st_mtime, timezone.utc).isoformat().replace('+00:00', 'Z')


def pages(names):
    result, pagination = [], []
    next_start = 0
    for name in names:
        value = load_response(name)
        pg = value['additional_data']['pagination']
        assert pg['start'] == next_start, (name, next_start, pg)
        result.extend(value.get('data') or [])
        pagination.append(pg)
        next_start = pg.get('next_start')
    assert pagination[-1]['more_items_in_collection'] is False
    assert len(result) == len({v['id'] for v in result}), names
    return result, pagination


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def build():
    SOURCE.mkdir(exist_ok=True)
    baseline_dir = SOURCE / 'baseline'
    baseline_dir.mkdir(exist_ok=True)
    baseline = baseline_dir / 'crm.json'
    if not baseline.exists():
        baseline.write_bytes((ROOT / 'data/crm_refresh.json').read_bytes())
    baseline_hash = hashlib.sha256(baseline.read_bytes()).hexdigest()
    baseline_crm = json.loads(baseline.read_text())

    deal_names = ['deals_000.json', 'deals_500.json']
    done_names = ['activities_done_000.json', 'activities_done_500.json']
    undone_names = ['activities_undone_000.json']
    deals, dpg = pages(deal_names)
    done, donepg = pages(done_names)
    undone, undonepg = pages(undone_names)
    activities = done + undone
    assert all(a['done'] for a in done) and all(not a['done'] for a in undone)
    assert len(activities) == len({a['id'] for a in activities})
    assert {a['user_id'] for a in activities} == {21932394, 21932405, 22680658}
    assert all(d['status'] != 'deleted' and not d.get('deleted') for d in deals)

    simple = {
        'pipedrive_pipelines.json': 'pipelines.json',
        'pipedrive_stages.json': 'stages.json',
        'pipedrive_activity_types.json': 'activity_types.json',
        'pipedrive_users.json': 'users.json',
        'pipedrive_deal_fields.json': 'deal_fields_000.json',
    }
    source_files = deal_names + done_names + undone_names + list(simple.values())
    snapshot_at = max(stamp(n) for n in source_files)
    for canonical, raw in simple.items():
        inner = load_response(raw)
        pg = (inner.get('additional_data') or {}).get('pagination')
        if pg:
            assert not pg['more_items_in_collection'], raw
        write(SOURCE / canonical, inner.get('data') or [])
    write(SOURCE / 'pipedrive_deals.json', deals)
    write(SOURCE / 'pipedrive_activities.json', activities)
    # Keep the older reviewed history explicitly dated; current selected histories
    # are a separate evidence layer, rather than falsely refreshing all 44 deals.
    write(SOURCE / 'pipedrive_stage_history.json', baseline_crm['assessment']['history'])
    inbox_names = ['leads_inbox_active_000.json', 'leads_inbox_archived_000.json']
    inbox = []
    for name in inbox_names:
        records, _ = pages([name])
        inbox.extend(records)
    assert len(inbox) == len({r['id'] for r in inbox})
    write(SOURCE / 'pipedrive_leads_inbox.json', inbox)
    manifest = {
        'snapshotAt': snapshot_at, 'dealsComplete': True, 'activitiesComplete': True,
        'leadsInboxComplete': True,
        'collectionStartedAt': None,
        'collectionFirstResponseAt': min(stamp(n) for n in source_files),
        'collectionCompletedAt': snapshot_at,
        'collectionTimeBasis': 'Filesystem timestamps when each retained MCP response was saved; exact request-start time was not captured.',
        'filters': {'deals': {'status': 'all_not_deleted', 'limit': 500, 'sort': 'id ASC'},
                    'activities': {'user_id': 0, 'doneStatesExplicitlyRequested': [0, 1], 'limit': 500}},
        'pagination': {'deals': dpg, 'done': donepg, 'undone': undonepg},
        'baselineSnapshotPath': str(baseline_dir.relative_to(ROOT)),
        'sourceFiles': {n: {'collectedAt': stamp(n), 'sha256': hashlib.sha256((MCP / n).read_bytes()).hexdigest()} for n in source_files + inbox_names},
    }
    write(SOURCE / 'pipedrive_manifest.json', manifest)
    normalizer = module('prepare_crm_current_mcp', ROOT / 'tools/prepare_crm.py')
    normalizer.PRIVATE = SOURCE
    normalizer.OUTPUT = PRIVATE / 'crm_mcp_patch.json'
    with contextlib.redirect_stdout(io.StringIO()):
        normalizer.build()
    crm = json.loads(normalizer.OUTPUT.read_text())
    crm['coverage'].update({
        'observedThrough': '2026-10-21', 'reportingThrough': '2026-10-20',
        'currentDayPartial': True, 'currentDayPartialDate': '2026-10-21',
        'method': 'Configured read-only Pipedrive MCP; completed all_not_deleted deal pagination and explicit user_id 0 done/undone activity pagination.',
        'collectionFirstResponseAt': manifest['collectionFirstResponseAt'],
        'collectionTimeBasis': manifest['collectionTimeBasis'],
        'sourceFiles': manifest['sourceFiles'],
        'baselineSnapshotSha256': baseline_hash,
        'archiveCoverage': {
            'archivedRecordsReturned': sum(bool(d.get('is_archived')) for d in deals),
            'nonArchivedRecordsReturned': sum(d.get('is_archived') is False for d in deals),
            'archiveInclusiveCompletenessVerified': False,
            'note': 'All 769 returned records expose is_archived=false. The list-tool schema has no archive filter; completeness is verified for the returned all_not_deleted endpoint scope, not an independently verified archive-inclusive census.',
        },
    })
    raw_by_id = {d['id']: d for d in deals}
    for d in crm['deals']:
        raw = raw_by_id[d['id']]
        d.update({'ownerId': normalizer.ident(raw.get('user_id')), 'creatorId': normalizer.ident(raw.get('creator_user_id')),
                  'isArchived': raw.get('is_archived'), 'archivedAt': normalizer.iso(raw.get('archive_time'))})
    crm['quality']['organizationTestLabelReviewIds'] = [d['id'] for d in crm['deals'] if not d['isTest'] and re.search(r'\btest\b', d.get('company') or '', re.I)]
    crm['quality']['organizationTestLabelPolicy'] = 'Flag only; a test-labelled organization does not auto-exclude a real-name deal without owner confirmation. In particular, 203 remains included and flagged.'
    crm['quality']['caveats'].append(crm['coverage']['archiveCoverage']['note'])

    # Fresh selected changelogs carry raw event timestamps/IDs, not inferred moves.
    fresh_history = {'complete': False, 'scopeComplete': True, 'fromDate': '2026-09-01',
                     'scope': 'Selected deal histories only; all returned flow pages completed. Not account-wide history or proof of held meetings/commercial acceptance.',
                     'dealIdsReviewed': [], 'perDealCoverage': [], 'events': []}
    raw_flow_names = sorted(MCP.glob('flow_*_*.json'))
    stage_map = {s['id']: s for s in crm['stages']}
    for file in raw_flow_names:
        ident = int(file.name.split('_')[1])
        flow = load_response(file.name)
        pg = flow['additional_data']['pagination']
        assert pg['start'] == 0 and not pg['more_items_in_collection'], file.name
        fresh_history['dealIdsReviewed'].append(ident)
        fresh_history['perDealCoverage'].append({'dealId': ident, 'sourceFile': file.name, 'collectedAt': stamp(file.name), 'pagination': pg, 'complete': True})
        for item in flow.get('data') or []:
            data = item.get('data') or {}
            if item.get('object') != 'dealChange' or data.get('field_key') not in ['stage_id', 'pipeline_id', 'status', 'value']:
                continue
            at = normalizer.iso(item.get('timestamp') or data.get('log_time'))
            if not at or at < '2026-09-01':
                continue
            event = {'id': data['id'], 'dealId': ident, 'field': data['field_key'], 'timestamp': at,
                     'oldValue': data.get('old_value'), 'newValue': data.get('new_value'), 'actorId': data.get('user_id'),
                     'changeSource': data.get('change_source'), 'sourceSnapshotAt': stamp(file.name), 'commercialProgression': None}
            if event['field'] == 'stage_id':
                for prefix in ['old', 'new']:
                    val = event[prefix + 'Value']
                    stage = stage_map.get(int(val)) if val is not None and str(val).isdigit() else None
                    event[prefix + 'StageName'] = stage.get('name') if stage else None
                    event[prefix + 'PipelineId'] = stage.get('pipelineId') if stage else None
            fresh_history['events'].append(event)
    fresh_history['collectedAt'] = max(stamp(p.name) for p in raw_flow_names)
    fresh_history['events'].sort(key=lambda e: (e['timestamp'], e['id']))
    crm['assessment']['freshSelectedDealHistory'] = fresh_history
    crm['coverage']['freshSelectedHistorySnapshotAt'] = fresh_history['collectedAt']
    crm['coverage']['freshSelectedHistoryDealCount'] = len(fresh_history['dealIdsReviewed'])

    # Latest record timestamps support distinct-record metrics, never edit-event totals.
    def dated_summary(start, end):
        business = [d for d in crm['deals'] if not d['isTest']]
        def inside(v):
            return start <= (normalizer.localdate(v) or '') <= end
        created = [d for d in business if inside(d['createdAt'])]
        updated = [d for d in business if inside(d['updatedAt'])]
        won = [d for d in business if d['status'] == 'won' and inside(d['wonAt'])]
        return {'start': start, 'end': end, 'currentDayPartial': end == '2026-10-21',
                'newDeals': len(created), 'latestUpdatedDeals': len(updated), 'wonDeals': len(won),
                'newDealIds': [d['id'] for d in created], 'latestUpdatedDealIds': [d['id'] for d in updated],
                'wonDealIds': [d['id'] for d in won],
                'alternativeLatestUpdatedExcludingOrganizationTestFlag': len([d for d in updated if d['id'] not in crm['quality']['organizationTestLabelReviewIds']]),
                'headlineAcceptedOpportunities': None, 'headlineFirstClientWins': None}
    crm['summary']['currentWeekToDate'] = dated_summary('2026-10-19', '2026-10-21')
    crm['summary']['monthToDate'] = dated_summary('2026-10-01', '2026-10-21')
    # Construct exact MTD activity diagnostics, preserving creation/completion/due semantics.
    bacts = [a for a in crm['activities'] if not a['isTest']]
    def between(value):
        return '2026-10-01' <= (normalizer.localdate(value) or '') <= '2026-10-21'
    created_acts = [a for a in bacts if between(a['createdAt'])]
    completed_acts = [a for a in bacts if a['done'] and between(a['completedAt'])]
    due_acts = [a for a in bacts if '2026-10-01' <= (a['dueDate'] or '') <= '2026-10-21']
    crm['assessment']['periods']['monthToDate'] = {
        'start': '2026-10-01', 'end': '2026-10-21', 'activitiesCreated': len(created_acts),
        'activitiesMarkedDone': len(completed_acts), 'activitiesDue': len(due_acts),
        'callsCreated': sum(a['type'] == 'call' for a in created_acts),
        'callsMarkedDone': sum(a['type'] == 'call' for a in completed_acts),
        'callsDue': sum(a['type'] == 'call' for a in due_acts),
        'createdActivityIds': [a['id'] for a in created_acts], 'completedActivityIds': [a['id'] for a in completed_acts],
        'heldCalls': None, 'note': 'CRM timestamps and due dates; a marked-done flag or call type is not independent held-call evidence.'}
    missing = load_response('deal_322.json')['data']
    assert missing['id'] == 322 and missing['status'] == 'deleted' and missing['deleted'] is True
    crm['assessment']['snapshotChanges']['verifiedNoLongerObservedRecords'] = [{
        'id': 322, 'title': missing['title'], 'status': missing['status'], 'deleted': missing['deleted'],
        'sourceUpdatedAt': normalizer.iso(missing['update_time']), 'verifiedAt': stamp('deal_322.json'),
        'note': 'get_deal independently confirms deletion. New Chromie Health record836 has the same title; replacement/merge intent is not independently verified.'}]
    crm = normalizer.redact_contact_addresses(crm)
    write(normalizer.OUTPUT, crm)

    # Derive referrals from this exact same full source, then reuse the partitioner.
    template = copy.deepcopy(json.loads((ROOT / 'data/referral_refresh.json').read_text()))
    current = [d for d in crm['deals'] if d['pipelineId'] == 4]
    template.pop('browserReview', None)
    template['snapshotAt'] = crm['snapshotAt']
    template['stages'] = [dict(s) for s in crm['stages'] if s['pipelineId'] == 4]
    template['records'] = [{
        'dealId': d['id'], 'id': d['id'], 'title': d['title'], 'personName': d['person'], 'organization': d['company'],
        'personId': d['personId'], 'organizationId': d['organizationId'], 'pipelineId': 4, 'stageId': d['stageId'],
        'status': d['status'], 'owner': d['owner'], 'addedAt': d['createdAt'], 'createdAt': d['createdAt'],
        'updatedAt': d['updatedAt'], 'stageChangedAt': d['stageChangedAt'], 'nextActivityDate': d['nextActivityDate'],
        'lastActivityDate': d['lastActivityDate'], 'value': d['value'], 'currency': d['currency']} for d in current]
    template['excludedRecords'] = []
    template['coverage'] = {
        'source': 'Referral Pipeline4 derived from the same fully paginated all_not_deleted CRM MCP read',
        'collectedAt': crm['snapshotAt'], 'scope': 'All accessible returned Pipeline4 records; current positions, not period events.',
        'complete': True, 'independentSnapshot': False, 'parentCRMSnapshotAt': crm['snapshotAt'],
        'parentCRMSource': 'crm_mcp_patch.json', 'requestedFilter': manifest['filters']['deals'],
        'connectorPipelineFilterHonored': None, 'observedSourcePipelineIds': sorted(set(d['pipelineId'] for d in crm['deals'])),
        'accountRowsCollected': len(crm['deals']), 'pagination': dpg, 'appliedLocalFilter': 'pipeline_id == 4',
        'observedThrough': '2026-10-21', 'reportingThrough': '2026-10-20', 'currentDayPartial': True,
        'archiveInclusiveCompletenessVerified': False}
    template['mainCRMComparison'] = {'mainCRMSnapshotAt': crm['snapshotAt'], 'mainCRMSource': 'crm_mcp_patch.json',
        'mainCRMReferralRecords': len(current), 'freshReferralIdsNotInMainCRM': [],
        'independentFreshScope': 'Referrals and refreshed main CRM derive from the same source snapshot; overlapping populations must not be added.'}
    ref_path = PRIVATE / 'referrals_mcp_patch.json'
    write(ref_path, template)
    reconciler = module('referrals_current_mcp', ROOT / 'tools/reconcile_referrals.py')
    reconciler.DATA = ref_path
    reconciler.markdown = lambda _: None
    with contextlib.redirect_stdout(io.StringIO()):
        reconciler.main()
    refs = json.loads(ref_path.read_text())
    refs['quality']['warnings'] = [w for w in refs['quality']['warnings'] if not w.startswith('The requested connector pipeline filter') and not w.startswith('Fresh Referral Pipeline coverage is independent')]
    refs['quality']['warnings'].insert(0, 'Same-source full CRM/referral refresh. Pipeline4 was applied locally to the completed all_not_deleted response; returned records are non-archived, and archive-inclusive completeness is not independently verified.')
    refs['note'] = f"Current same-source Referral Pipeline snapshot: {len(current)} records = " + ' + '.join(f"{v['count']} {k}" for k, v in refs['partitions'].items()) + '. Current positions are not period events.'
    write(ref_path, refs)

    assert len(crm['deals']) == 769 and len(crm['activities']) == 924
    assert crm['summary']['dealCount'] == 765 and crm['summary']['activityCount'] == 919
    assert crm['summary']['currentWeekToDate']['newDeals'] == 15
    assert crm['summary']['currentWeekToDate']['latestUpdatedDeals'] == 28
    assert {d['id'] for d in current} == {r['dealId'] for r in refs['records'] + refs['excludedRecords']}
    assert sum(v['count'] for v in refs['partitions'].values()) == 348
    assert crm['snapshotAt'] == refs['snapshotAt']
    assert not re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', json.dumps(crm) + json.dumps(refs))
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == baseline_hash
    result = {'snapshotAt': snapshot_at, 'deals': len(deals), 'businessDeals': crm['summary']['dealCount'],
              'activities': len(activities), 'businessActivities': crm['summary']['activityCount'],
              'currentWeek': crm['summary']['currentWeekToDate'], 'monthToDate': crm['summary']['monthToDate'],
              'activityInventory': crm['assessment']['inventory'],
              'referralPartitions': {k: v['count'] for k, v in refs['partitions'].items()},
              'freshSelectedHistoryDeals': len(fresh_history['dealIdsReviewed']), 'freshSelectedHistoryEvents': len(fresh_history['events']),
              'outputs': ['crm_mcp_patch.json', 'referrals_mcp_patch.json'], 'publication': 'LOCAL ONLY'}
    write(PRIVATE / 'crm_mcp_review_summary.json', result)
    print(json.dumps({k: result[k] for k in ['snapshotAt', 'deals', 'businessDeals', 'activities', 'businessActivities', 'referralPartitions', 'freshSelectedHistoryDeals', 'freshSelectedHistoryEvents', 'outputs']}, indent=2))


if __name__ == '__main__':
    build()
