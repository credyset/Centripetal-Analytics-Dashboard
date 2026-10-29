"""Validate a bounded authenticated Ads zero aggregate; write private patches.

The explicit table aggregate supplies four source metrics only. Individual-row
dashes and absent CSV days remain unavailable. This performs no source or
canonical dashboard write.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/confidence_audit_2026_10_29'


def table_columns(block):
    lines = block.splitlines()
    starts = [i for i, line in enumerate(lines) if re.match(r'^\t+\d+ column header(?: row selection)?$', line)]
    result = []
    for n, start in enumerate(starts):
        if lines[start].endswith('row selection'):
            continue
        end = starts[n+1] if n+1 < len(starts) else len(lines)
        values = [match.group(1) for line in lines[start+1:end]
            if (match := re.match(r'^\t+\d+ (?:text|button) (.+)$', line))]
        assert values, 'A column has no explicit header/value text'
        result.append(values[0])
    return result


def verify_zero_review(ax, controls, meta, ads):
    account = str(ads['lifecycleReview']['accountId'])
    assert str(meta['accountId']) == account == '515259390'
    assert meta.get('account', 'Charles Solomon') == 'Charles Solomon' and 'Hi Charles' in ax
    assert f'/accounts/{account}/campaigns?' in ax
    assert 'tab (selected) Ad sets 7 total' in ax and 'Columns: Performance' in ax
    starts = [i for i, line in enumerate(ax.splitlines()) if re.match(r'^\t+\d+ row$', line)]
    assert len(starts) >= 3
    lines = ax.splitlines()
    headers = table_columns('\n'.join(lines[starts[0]:starts[1]]))
    totals = table_columns('\n'.join(lines[starts[1]:starts[2]]))
    assert len(headers) == len(totals) == 20 and totals[0] == '7 ad sets'
    mapping = dict(zip(headers, totals))
    expected = {'Spent': '$0.00', 'Impressions': '0', 'Clicks': '0', 'Leads': '0'}
    assert {name: mapping.get(name) for name in expected} == expected, 'Explicit aggregate zero columns do not match'
    visible_ids = re.findall(r'\btext ID: (\d+) · Sponsored Content', ax)
    retained = set(ads['review']['sourceScope']['exportedAdSetIds']) | set(ads['review']['sourceScope']['uiOnlyZeroDeliveryAdSetIds'])
    assert len(visible_ids) == len(set(visible_ids)) == 7
    assert set(visible_ids) == set(meta['adSetIds']) == retained, 'The observed filter differs from retained Ads scope'
    unfiltered = meta.get('viewFilterCleared') is True
    if unfiltered:
        assert meta['unfilteredAdSetCount'] == 7 and meta['parentCampaignCount'] == 18
        assert 'checkbox Status Completed, Value: 0' in ax
        assert 'pop up button Filters (' not in ax
        assert 'There are 7 results shown in the table. There are 7 results total.' in ax
        assert len(re.findall(r'\bbutton Completed$', ax, re.M)) == 7
        assert 'button Page 1' in ax and 'button Page 2' not in ax
        assert 'Show 15 per page' in ax
        assert 'Campaigns 18 total' in ax
    chart = re.search(r'Value: (linkedin\.com/campaignmanager/accounts/\d+/performance-chart\?[^\n]+)', ax)
    assert chart, 'Filtered chart URL is unavailable'
    query = parse_qs(urlparse('https://' + chart.group(1)).query)
    assert set(map(str, json.loads(query['campaignIds'][0]))) == retained
    date_range = json.loads(query['dateRange'][0])
    source_start = datetime.strptime(date_range['startDate'], '%m/%d/%Y').date().isoformat()
    source_end = datetime.strptime(date_range['endDate'], '%m/%d/%Y').date().isoformat()
    assert (source_start, source_end) == (meta['start'], meta['end']) == ('2026-10-22', '2026-10-29')
    assert f"Start date, Value: {date_range['startDate']}" in controls
    assert f"End date, Value: {date_range['endDate']}" in controls
    assert 'text Time in UTC' in controls and meta['sourceTimezone'] == 'UTC'
    observed = datetime.fromisoformat(meta['observedAt'].replace('Z', '+00:00'))
    assert observed.tzinfo is not None and observed.astimezone(timezone.utc).date().isoformat() == source_end
    assert meta['finalDayPartial'] is True and meta.get('sourceDailyRowsAdded', 0) == 0
    assert meta.get('sourceSystemWrites', 0) == 0
    assert meta.get('individualAdSetDashesAreNotConvertedToZeros', True) is True
    metrics = {key: 0 for key in ('spend', 'impressions', 'clicks', 'rawLeads')}
    assert meta['aggregateMetricsObserved'] == metrics
    return {'snapshotAt': meta['observedAt'],
        'reviewedAt': datetime.now(timezone.utc).isoformat(),
        'accountId': account, 'identityVerified': True,
        'reviewKind': 'authenticated_ui_aggregate_zero',
        'coverage': {'start': source_start, 'end': source_end, 'sourceTimezone': 'UTC',
            'finalDayPartial': True,
            'completeDaysThrough': (datetime.fromisoformat(source_end).date()-timedelta(days=1)).isoformat(),
            'sourceMayRestate': True},
        'metrics': metrics,
        'scope': {'adSetIds': sorted(retained), 'matchesRetainedAdSetScope': True,
            'adSetsReviewed': len(retained), 'accountWideCompleteCampaignCoverage': False,
            'viewFilterCleared': unfiltered, 'allVisibleCurrentAdSetsVerified': unfiltered,
            'unfilteredAdSetCount': len(retained) if unfiltered else None,
            'parentCampaignCount': meta.get('parentCampaignCount'),
            'parentCampaignCountIsSeparateGrain': True},
        'sourceDailyRowsAdded': 0,
        'notes': [
            'Authenticated Performance table aggregate explicitly reports $0.00 Spent, 0 Impressions, 0 Clicks and 0 platform Leads for October22–29UTC in the same seven retained ad sets. October29 is partial at the observation clock.',
            'These four nonnegative aggregate metrics support zero for a selected source-date subwindow wholly inside this observed all-zero interval. They do not create daily or campaign rows; the actual CSV dates still end October21UTC.',
            ('The view filter is cleared; all seven displayed ad sets are Completed and the source reports seven shown/seven total on one page. The Campaigns tab reports eighteen parent entities, a different grain; that is not evidence of eleven omitted ad sets.' if unfiltered else 'This evidence is limited to the seven reviewed ad sets.'),
            'Individual ad-set cells display dashes and remain unavailable. The verified metric scope remains the seven exact retained ad sets; no individual campaign or daily zero rows are inferred.',
            'Qualified leads, matched bookings, form opens, video views/completions and actual commercial outcomes remain independently unavailable for this interval. Platform Leads is not owner qualification.',
            'The aggregate retains its own observation clock and may be restated. It must not refresh an older CSV, an individual lead record, or a native message observation.'
        ]}


def main():
    ax_path = PRIVATE / 'ads_zero_period_unfiltered_ax.txt'
    controls_path = PRIVATE / 'ads_zero_period_date_controls_ax.txt'
    meta_path = PRIVATE / 'ads_zero_period_unfiltered_meta.json'
    ads = json.loads((ROOT / 'data/shared-dashboard.json').read_text())['ads']
    review = verify_zero_review(ax_path.read_text(), controls_path.read_text(), json.loads(meta_path.read_text()), ads)
    old_path = PRIVATE / 'ads_zero_delivery_review_patch.json'
    if old_path.exists():
        previous = json.loads(old_path.read_text())
        if previous['snapshotAt'] != review['snapshotAt']:
            review['retainedPriorReviews'] = [previous]
        elif previous.get('retainedPriorReviews'):
            review['retainedPriorReviews'] = previous['retainedPriorReviews']
    card = {'id': 'ads_zero_delivery', 'name': 'LinkedIn Ads · bounded zero-delivery aggregate',
        'asOf': review['snapshotAt'], 'checkedAt': '2026-10-29',
        'status': 'Verified aggregate zero for four metrics; October29 partial',
        'coverage': review['coverage'],
        'method': 'Unfiltered authenticated Performance headers/aggregate; seven shown/seven total ad sets, exact retained IDs and UTC controls verified',
        'note': 'Spent, impressions, clicks and platform Leads are explicitly zero in this bounded interval. No individual-row dash or missing CSV day is converted to zero. Qualified leads, bookings, video and form opens retain separate unknown coverage.'}
    for name, value in [('ads_zero_delivery_review_patch.json', review), ('ads_zero_delivery_source_card.json', card)]:
        (PRIVATE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    audit = {'sourceHashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ax_path, controls_path, meta_path)},
        'independentValidation': {'headersAndAggregateColumnsMatched': True, 'allSevenRetainedAdSetIdsMatched': True,
            'exactAppliedRangeAndUTCControlsMatched': True, 'individualDashesNotZeroed': True,
            'canonicalOrSourceWrites': 0, 'dailyRowsAdded': 0}, 'review': review}
    (PRIVATE / 'ads_zero_delivery_validation.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'privateChild': 'data/private/confidence_audit_2026_10_29/ads_zero_delivery_review_patch.json',
        'snapshotAt': review['snapshotAt'], 'adSets': review['scope']['adSetsReviewed'],
        'metrics': review['metrics'], 'canonicalWrites': 0, 'dailyRowsAdded': 0}))


if __name__ == '__main__':
    main()
