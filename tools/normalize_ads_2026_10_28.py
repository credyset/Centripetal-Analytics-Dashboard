"""Reconcile retained October 29 LinkedIn daily exports, without network or publication.

The requested window, actual dated rows, download clocks and lifecycle UI review
are independent. Missing export dates are never manufactured as zero delivery.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/private/refresh_2026_10_28/ads'
spec = importlib.util.spec_from_file_location('prior_ads_normalizer', ROOT / 'tools/normalize_ads_2026_10_22.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def parse(path):
    # Reuse the well-tested encoding/TSV handling without its dated-window guard.
    import csv
    import io
    raw = path.read_bytes()
    text = raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig')
    meta = {}
    for label, key in [('Report Start', 'start'), ('Report End', 'end'), ('Date Generated', 'generated')]:
        match = re.search(rf'"{label}: ([^"]+)"', text)
        assert match, label
        meta[key] = datetime.strptime(match[1], '%B %d, %Y, %I:%M %p').replace(tzinfo=timezone.utc).isoformat()
    rows = list(csv.DictReader(io.StringIO(text[text.index('Start Date (in UTC)\t'):]), delimiter='\t'))
    assert rows and all(r['Currency'] == 'USD' and 'Centripetal' in r['Account Name'] for r in rows)
    assert meta['start'][:10] == '2026-09-04' and meta['end'][:10] == '2026-10-29'
    assert all(meta['start'][:10] <= prior.day(r['Start Date (in UTC)']) <= meta['end'][:10] for r in rows)
    meta['downloadedAt'] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    return rows, meta


def build(adsets, creatives, baseline, output):
    rows, meta = parse(adsets)
    ads, creative_meta = parse(creatives)
    assert meta['start'] == creative_meta['start'] and meta['end'] == creative_meta['end']
    assert len({(r['Ad Set ID'], prior.day(r['Start Date (in UTC)'])) for r in rows}) == len(rows)
    assert len({(r['Ad ID'], prior.day(r['Start Date (in UTC)'])) for r in ads}) == len(ads)
    totals = prior.sums(rows)
    days = prior.daily(rows)
    assert totals == prior.sums(ads), 'Ad-set and creative additive totals differ'
    assert days == prior.daily(ads), 'Ad-set and creative daily totals differ'
    assert all(totals[k] == v for k, v in prior.EXPECTED.items()), 'UI control totals differ'
    incoming = json.loads(baseline.read_text())['ads']
    comparison_path = RAW / 'baseline_ads_before_refresh.json'
    if not comparison_path.exists():
        write(comparison_path, incoming)
    old = json.loads(comparison_path.read_text())
    result = copy.deepcopy(incoming)
    mapping = {r['id']: r for r in result['campaigns']}
    assert set(mapping) == {r['Ad Set ID'] for r in rows} == {r['Ad Set ID'] for r in ads}
    for ident, record in mapping.items():
        group = [r for r in rows if r['Ad Set ID'] == ident]
        latest = max(group, key=lambda r: prior.day(r['Start Date (in UTC)']))
        record.update(**prior.sums(group), daily=prior.daily(group), name=latest['Ad Set Name'],
                      objective=latest['Ad Set Objective'], statusAsOfExport=latest['Ad Set Status'],
                      parentCampaignId=latest['Campaign ID'])
    result['creatives'] = []
    for ident in sorted({r['Ad ID'] for r in ads}):
        group = [r for r in ads if r['Ad ID'] == ident]
        latest = max(group, key=lambda r: prior.day(r['Start Date (in UTC)']))
        result['creatives'].append({'id': ident, 'name': latest['Ad Name'], 'adSetId': latest['Ad Set ID'],
            'campaignCode': mapping[latest['Ad Set ID']]['code'], 'parentCampaignId': latest['Campaign ID'],
            'objective': latest['Ad Set Objective'], 'statusAsOfExport': latest['Ad Status'],
            **prior.sums(group), 'daily': prior.daily(group)})
    generated = max(meta['generated'], creative_meta['generated'])
    downloaded = max(meta['downloadedAt'], creative_meta['downloadedAt'])
    localday = datetime.fromisoformat(downloaded).astimezone(ZoneInfo('America/Denver')).date().isoformat()
    last_complete = (datetime.fromisoformat(generated) - timedelta(days=1)).date().isoformat()
    actual_dates = {r['date'] for r in days}
    start = datetime.fromisoformat(meta['start']).date()
    end = datetime.fromisoformat(meta['end']).date()
    expected_dates = [(start + timedelta(days=n)).isoformat() for n in range((end-start).days+1)]
    missing = [d for d in expected_dates if d not in actual_dates]
    zero_days = [d['date'] for d in days if all(d[k] == 0 for k in prior.FIELDS.values())]
    result.update(status='available', snapshotAt=generated, collectedAt=downloaded, preparedAt=localday,
        reportGeneratedAt=generated, refreshMode='manual_authenticated_export',
        coverage={'start': days[0]['date'], 'end': days[-1]['date'], 'sourceTimezone': 'UTC',
                  'finalDayPartial': days[-1]['date'] > last_complete,
                  'completeDaysThrough': min(days[-1]['date'], last_complete),
                  'reportRequestedStart': start.isoformat(), 'reportRequestedEnd': end.isoformat(),
                  'requestedFinalDayPartial': end.isoformat() > last_complete,
                  'requestedCompleteDaysThrough': last_complete,
                  'sourceMayRestate': True, 'missingRequestedDates': missing,
                  'actualZeroMetricDates': zero_days, 'syntheticDailyRowsAdded': 0},
        dateBasis='Explicit UTC daily export rows; no Mountain rebucketing and no missing dates filled with zero',
        daily=days, reportWindow={'start': meta['start'], 'end': meta['end'], 'sourceTimezone': 'UTC',
            'adSetGeneratedAt': meta['generated'], 'creativeGeneratedAt': creative_meta['generated'],
            'adSetDownloadedAt': meta['downloadedAt'], 'creativeDownloadedAt': creative_meta['downloadedAt']})
    result['totals'] = {'spend': totals['spend'], 'impressions': totals['impressions'], 'clicks': totals['clicks'],
        'formOpens': totals['opens'], 'rawLeads': totals['leads'],
        'qualifiedLeads': incoming['totals']['qualifiedLeads'], 'videoViews': totals['videoViews'],
        'videoCompletions': totals['videoCompletions']}
    result['platformTotals'] = totals
    assert result['leads'] == incoming['leads'] and len(result['leads']) == totals['leads'] == 4
    if result.get('browserReview'):
        result['browserReviewSupersededByExport'] = result.pop('browserReview')
    changes = {k: round(result['totals'][k] - old['totals'][k], 2) for k in
               ['spend', 'impressions', 'clicks', 'formOpens', 'rawLeads', 'videoViews', 'videoCompletions']}
    old_days = {d['date']: d for d in old['daily']}
    restatements = [d['date'] for d in days if d['date'] in old_days and any(
        old_days[d['date']].get(k) != d[k] for k in prior.FIELDS.values())]
    new_dates = sorted(actual_dates - set(old_days))
    assert not any(changes.values()) and not restatements and not new_dates, 'Refresh now differs; revise the unchanged-delivery assessment'
    for folder, records, key in [('calculation_aid_adsets', list(mapping.values()), 'ad_set_id'),
                                  ('calculation_aid_creatives', result['creatives'], 'ad_id')]:
        aid = json.loads((RAW/folder/'linkedin_ads_analysis.json').read_text())
        assert len(aid['rollups']) == len(records)
        indexed = {r['id']: r for r in records}
        for rollup in aid['rollups']:
            record = indexed[rollup['key'][key]]
            assert all(abs(rollup['totals'][src] - record[dest]) < .001 for src, dest in prior.FIELDS.items()), 'Independent calculation aid differs'
    ui_meta = json.loads((RAW/'source_meta.json').read_text())
    ui_text = (RAW/'source_ax.txt').read_text()
    assert ui_meta['accountIdentityVerified'] and ui_meta['accountId'] == '515259390'
    assert ui_meta['start'] == start.isoformat() and ui_meta['end'] == end.isoformat()
    assert len(re.findall(r'button Completed(?:\n|$)', ui_text)) == 7
    for text in ('$3,592.31', '25,055', '106'):
        assert text in ui_text
    previous_lifecycle = copy.deepcopy(incoming.get('lifecycleReview'))
    lifecycle = {'snapshotAt': ui_meta['observedAt'], 'reviewedAt': ui_meta['observedAt'],
        'accountId': '515259390', 'identityVerified': True,
        'ownerReportedConcludedOn': previous_lifecycle.get('ownerReportedConcludedOn') if previous_lifecycle else None,
        'platformStatus': 'Completed', 'adSetsReviewed': 7, 'completedAdSets': 7, 'activeAdSets': 0,
        'reportingWindow': {'start': start.isoformat(), 'end': end.isoformat(), 'sourceTimezone': 'UTC',
                            'finalDayPartial': ui_meta['finalDayPartial']},
        'displayedTotals': {'spend': totals['spend'], 'impressions': totals['impressions'], 'clicks': totals['clicks']},
        'matchesRetainedExportTotals': True, 'retainedDailyThrough': days[-1]['date'],
        'newDailyRowsImported': len(new_dates), 'concludedAt': None,
        'note': 'All seven filtered ad sets are Completed in Charles’s authenticated account. '
                'UI totals agree with the separately generated October29 exports. Actual daily rows stop October21; '
                'October22–29 remain absent export rows. No zero daily values or exact conclusion timestamp are inferred.'}
    result['lifecycleReview'] = lifecycle
    result['notes'] = [
        'Fresh authenticated Ad Set and Ad performance exports for account 515259390, generated October 29 at 06:03 and 06:02 UTC; requested September 4–October 29 UTC.',
        f'Both files contain {len(days)} actual dated buckets covering September 4–October 21 UTC. Missing October 22–29 rows remain unavailable; neither the wider export request nor unchanged aggregate totals creates daily zero rows.',
        'Five delivered A–E ad sets, six ads and three parent campaign IDs reconcile at both grains and every date; campaign and creative totals are never added together.',
        'The separately dated account UI shows all seven filtered ad sets Completed, including two zero-delivery UI-only sets absent from export rows. It does not establish a precise completion timestamp.',
        'All retained control totals and daily additive values are unchanged from the prior export. This refresh adds no measured delivery growth and no new daily row.',
        'A–E are ad-set variants retained for continuity. E has Website visits objective despite its video-views name; compare within objective.',
        'Four aggregate platform lead submissions remain reported. Individual submission exports were not refreshed; identities, qualification and booking/held evidence retain their independent evidence dates.',
        'Owner qualification remains one qualified/warm paid lead, NuVee. Platform Qualified Leads is independently zero and does not override owner decisions. The one platform appointment is not independently confirmed attendance, accepted opportunity or win.',
        'Company-page organic/sponsored distribution overlaps paid delivery and must not be added to Ads totals.'
    ]
    checks = {'adsetCreativeTotalsAgree': True, 'dailyAdsetCreativeTotalsAgree': True, 'dailyKeysUnique': True,
              'browserControlTotalsAgree': True, 'ownerDispositionsPreserved': True,
              'actualRowsOnly': True, 'comparisonUsesSameRequestedStart': True,
              'independentCalculationAidBothGrainsAgree': True}
    result['review'] = {'checkedAt': localday, 'sourceAsOf': generated, 'accountId': '515259390',
        'rawAdSetRows': len(rows), 'rawCreativeRows': len(ads), 'dailyBuckets': len(days),
        'uniqueAdSets': len(mapping), 'uniqueAds': len(result['creatives']),
        'parentCampaignIds': sorted({r['Campaign ID'] for r in rows}),
        'latestCompleteUTCDate': min(days[-1]['date'], last_complete), 'currentMountainDateIncomplete': True,
        'leadDetailAccess': {**copy.deepcopy(old.get('review', {}).get('leadDetailAccess', {})),
                            'notRefreshedInThisCollection': True},
        'priorCoverageEnd': old['coverage']['end'], 'changeSincePriorSnapshot': changes,
        'commonDailyRestatementDates': restatements, 'newDailyDates': new_dates,
        'checks': checks, 'sourceScope': {'exportedAdSetIds': sorted(mapping),
            'uiOnlyZeroDeliveryAdSetIds': ['409641733', '445365453'],
            'uiOnlyZeroDeliveryNames': ['Top of Funnel - Video - Testimonial ( Megadata ) 1campaign- Jul 29, 2025',
                                       "(B TEST) Top-of-funnel - Video - Testimonial ( Megadata ) - Q3 '25"],
            'uiOnlySourceBasis': 'Authenticated filtered account UI; no matching exported delivery rows',
            'accountWideCompleteCampaignCoverage': False,
            'note': 'Seven selected UI ad sets; only five delivered sets represented in retained exports.'}}
    result['sources'] = [dict(prior.provenance(adsets), downloadedAt=meta['downloadedAt'], reportGeneratedAt=meta['generated']),
                         dict(prior.provenance(creatives), downloadedAt=creative_meta['downloadedAt'], reportGeneratedAt=creative_meta['generated'])]
    write(output, result)
    write(RAW/'ads_lifecycle_review_patch.json', lifecycle)
    write(RAW/'normalization_review.json', {'adSetMeta': meta, 'creativeMeta': creative_meta,
        'totals': result['totals'], 'platformTotals': totals, 'actualDailyCoverage': result['coverage'],
        'rawRows': {'adsets': len(rows), 'creatives': len(ads)}, 'checks': checks, 'changes': changes,
        'commonDailyRestatementDates': restatements, 'newDailyDates': new_dates,
        'ownerLeadsPreserved': result['leads'] == incoming['leads'],
        'priorLifecycleReview': previous_lifecycle, 'freshLifecycleReview': lifecycle})
    print(json.dumps({'output': str(output), 'totals': result['totals'], 'coverage': result['coverage'],
                      'changes': changes, 'commonDailyRestatementDates': restatements, 'newDailyDates': new_dates}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adsets', type=Path, default=RAW/'account_515259390_campaign_performance_report (8).csv')
    parser.add_argument('--creatives', type=Path, default=RAW/'account_515259390_creative_performance_report (10).csv')
    parser.add_argument('--baseline', type=Path, default=ROOT/'data/private/refresh_2026_10_28/baseline_shared.json')
    parser.add_argument('--output', type=Path, default=RAW/'ads_inventory_patch.json')
    args = parser.parse_args()
    build(args.adsets, args.creatives, args.baseline, args.output)
