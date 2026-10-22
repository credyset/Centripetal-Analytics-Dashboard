"""Prepare a bounded CRM browser supplement without replacing the full export.

Only retained accessibility text is parsed. Open-stage inventory, visible cards,
and update labels are observations, never business-event or qualification counts.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/private/refresh_2026_10_21'
BASELINE = ROOT / 'data/private/crm_refresh_2026-10-16/pipedrive_deals.json'

STAGES = {
    2: [('Profiled Lead or Contact (From Sheet or Otherwise)', 8),
        ('Doing Cold Outreach', 14), ('Video DM Outreach', 43),
        ('Intro Call Scheduled - Lead Pipeline', 21), ('Call Complete', 22),
        ('Hightouch Manual', 24), ('Nurture (AutoEmails 1 - 4)', 23),
        ('Nurture (AutoEmails 5 - 8)', 25), ('Graveyard', 11), ('Newsletter', 37)],
    1: [('Parking Lot (Long Term)', 20), ('Parking Lot (Short Term)', 41),
        ('New Lead', 44), ('Intro Meeting', 3), ('Follow-up / Need Analysis', 4),
        ('Negotiating Contract', 5), ('Closed Won', 7), ('Closed Lost', 19)],
    4: [('Centripetal Amigos', 42), ('Centripetal Circle', 26), ('Inner Circle', 39),
        ('Ask Sent', 27), ('Follow-Up Active', 28), ('Intro Promised', 29),
        ('Intro Made', 30), ('Intro Scheduled', 31), ('Intro Complete', 32),
        ('Opportunity ( Referred )', 33), ('Opportunity (Referred)', 33),
        ('Proposal Sent', 34), ('High Touch Manual', 35), ('Hightouch Manual', 35),
        ('Nurture (Automation)', 36), ('Office Hours', 38), ('Graveyard (Newsletter)', 40), ('Graveyard ( Newsletter )', 40)]
}
FILES = [('crm_leads_pipeline_ax.txt', 2, 'Leads Pipeline'),
         ('crm_sales_pipeline_ax.txt', 1, 'Sales Pipeline'),
         ('crm_referrals_pipeline_ax.txt', 4, 'Referral Pipeline')]


def instant(path):
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace('+00:00', 'Z')


def read_pipeline(path, pipeline_id, name, baseline):
    text = path.read_text()
    assert f'/pipeline/{pipeline_id}/user/everyone?quickFilter=none' in text
    assert 'button Show closed deals' in text, 'Open-view scope must be visible'
    total = re.search(r'^\s*\d+ text ([\d,]+) deals?\s*$', text, re.M)
    assert total
    matches = []
    for label, stage_id in STAGES[pipeline_id]:
        for match in re.finditer(r'^\s*\d+ text '+re.escape(label)+r'\s*$', text, re.M):
            matches.append((match.start(), match.end(), label, stage_id))
    matches.sort()
    assert len({x[3] for x in matches}) == len(matches)
    stages, records = [], []
    for i, (start, end, label, stage_id) in enumerate(matches):
        section = text[end:matches[i+1][0] if i+1 < len(matches) else len(text)]
        first_card = re.search(r'^\s*\d+ draggable ', section, re.M)
        header = section[:first_card.start()] if first_card else section
        count = re.search(r'text (\$[\d,.]+) · ([\d,]+) deals?', header)
        value = count.group(1) if count else None
        count_value = int(count.group(2).replace(',', '')) if count else None
        stage = {'stageId': stage_id, 'stage': label,
                 'sourceDisplayedOpenViewCount': count_value,
                 'stageSummaryValueText': value,
                 'stageSummaryValueBasis': 'Verbatim stage header; weighting/amount basis not verified. Do not equate to card values, accepted pipeline or revenue.'}
        cards = list(re.finditer(r'^\s*\d+ draggable (.+)$', section, re.M))
        stage['visibleCardCount'] = len(cards)
        stages.append(stage)
        for j, card in enumerate(cards):
            block = section[card.end():cards[j+1].start() if j+1 < len(cards) else len(section)]
            link = re.search(r'link Description: (?!\$)(.+?), Value: centripetaladvisors\.pipedrive\.com/deal/(\d+)', block)
            deal_id = int(link.group(2)) if link else None
            description = link.group(1) if link else card.group(1)
            updated = re.search(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}, \d{4}, \d{1,2}:\d{2} [AP]M)', description)
            label_text = description[:updated.start()].rstrip() if updated else description
            label_text = re.sub(r' \$[\d,.]+(?: Reply\?| View email conversation)?$', '', label_text)
            known = baseline.get(deal_id, {})
            company = known.get('title')
            person = None
            duplicate = re.match(r'^(.*?) \1(?:,\s*(.*))?$', label_text)
            if duplicate:
                company = duplicate.group(1)
                person = duplicate.group(2)
            if person and '@' in person:
                person = None  # Raw email labels are not necessary for this supplement.
            card_value = re.search(r' (\$[\d,.]+)(?: |$)', card.group(1))
            records.append({'dealId': deal_id, 'company': company,
                            'person': person, 'displayLabel': company or label_text,
                            'pipelineId': pipeline_id, 'pipeline': name,
                            'stageId': stage_id, 'stage': label,
                            'latestUpdateText': updated.group(1) if updated else None,
                            'latestUpdateTimezone': None,
                            'latestUpdateDateBasis': 'Verbatim browser label; timezone unspecified. Not a call/send/progression timestamp.',
                            'sourceEnteredCardValueText': card_value.group(1) if card_value else None,
                            'valueBasis': 'Source-entered card amount, not a verified accepted opportunity, contract, revenue or qualified pipeline.',
                            'url': f'https://centripetaladvisors.pipedrive.com/deal/{deal_id}' if deal_id else None,
                            'sourceStatusScope': 'Open-view card; actual status field not independently refreshed',
                            'absentFromRetainedFullSnapshot': deal_id not in baseline if deal_id else None,
                            'baselineStageId': known.get('stage_id'),
                            'observedStageDiffersFromBaseline': known.get('stage_id') != stage_id if known else None,
                            'collectedAt': instant(path)})
    assert sum(s['sourceDisplayedOpenViewCount'] or 0 for s in stages) == int(total.group(1).replace(',', '')), 'Stage counts must reconcile with observed pipeline total'
    return {'pipelineId': pipeline_id, 'pipeline': name,
            'observedOpenViewDealCount': int(total.group(1).replace(',', '')),
            'ownerScope': 'Everyone, as displayed in source URL',
            'statusScope': 'Open-view inventory; Show closed deals action is visible',
            'countIncludesTestsOrDuplicates': 'Source total is unfiltered for tests and duplicate companies',
            'collectedAt': instant(path), 'stages': stages,
            'visibleCardCount': len(records),
            'visibleCardsWithRetainedId': sum(r['dealId'] is not None for r in records),
            'visibleCardsWithTruncatedUrl': sum(r['dealId'] is None for r in records),
            'isFullDealOrActivityExport': False,
            'sourceSha256': hashlib.sha256(path.read_bytes()).hexdigest()}, records


def build():
    baseline_rows = json.loads(BASELINE.read_text())
    baseline = {r['id']: r for r in baseline_rows}
    pipelines, records = [], []
    for filename, pid, name in FILES:
        source = PRIVATE / filename
        if not source.exists():
            continue
        pipeline, visible = read_pipeline(source, pid, name, baseline)
        pipelines.append(pipeline)
        records.extend(visible)
    assert len(pipelines) >= 2
    all_collected = sorted(p['collectedAt'] for p in pipelines)
    collection = all_collected[-1]
    checked = datetime.fromisoformat(collection.replace('Z', '+00:00')).astimezone(ZoneInfo('America/Denver')).date().isoformat()
    known_records = [r for r in records if r['dealId'] is not None]
    assert len(known_records) == len({r['dealId'] for r in known_records})
    new_ids = sorted(r['dealId'] for r in known_records if r['absentFromRetainedFullSnapshot'])
    result = {'checkedAt': checked, 'collectedAt': collection,
              'collectionStartedAt': all_collected[0],
              'baselineSnapshotAt': '2026-10-17T00:52:01Z',
              'coverage': 'Current open-stage browser observations; not a full deal/activity export',
              'captureTimeBasis': 'Retained source accessibility-file write times; preparation does not refresh collection time',
              'pipelines': pipelines, 'visibleRecords': records,
              'comparison': {'visibleRecordIdsAbsentFromRetainedFullSnapshot': new_ids,
                             'newlyObservedIdentityCount': len(new_ids),
                             'isCreatedOpportunityOrSendCount': False,
                             'basis': 'Identity presence in two differently scoped snapshots; no creation, acceptance, send or progression event is inferred.'},
              'warnings': [
                  'Retain the complete October 16 deal/activity snapshot as the dated baseline. This supplement does not replace its all-status records, source fields or activity history.',
                  'Pipeline stage totals are open-view source inventories across everyone; they include any tests or duplicate companies. Do not sum them into a cleaned account-wide business total.',
                  'Visible cards are a bounded, virtualized browser subset. Truncated URLs stay unresolved; no hidden record IDs were reconstructed.',
                  'A latest-update label is not a call, Video DM send, accepted opportunity or stage-transition event. Source label timezone was not exposed.',
                  'Closed Won and Closed Lost are stage labels. Actual status, won/lost timestamps and first-client evidence must establish business outcomes.',
                  'Stage header monetary labels differ from visible card values in Sales. Weighting/amount basis is unverified; neither is revenue or verified qualified pipeline.',
                  'NuVee deal788 remains qualified/warm by explicit owner confirmation despite its current Parking Lot (Short Term) position. No acceptance date or active commercial next step has been confirmed.',
                  'Venus appears under two deal IDs (791 in Leads and805 in Sales). The owner-confirmed unqualified lead disposition is not automatically reversed by the other record stage. Reconcile company identity and owner disposition.',
                  'The source export could not be completed through the available Chrome download interaction. A refreshed all-status deal export, activity export and event/stage history remain needed.'
              ]}
    (PRIVATE/'crm_browser_patch.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'checkedAt': checked,
                      'pipelines': [{k:p[k] for k in ['pipeline','observedOpenViewDealCount','visibleCardCount','visibleCardsWithRetainedId']} for p in pipelines],
                      'newlyObservedIds': new_ids}))


if __name__ == '__main__':
    build()
