"""Normalize an owner-supplied daily invitation CSV without refreshing other feeds.

The CLI writes a private, reviewable patch and source copy only. Importers can
call apply_invitation_patch() on the Waalaxy section after reviewing the patch.
It does not change the tracked dashboard or infer message events/cohort rates.
"""
from pathlib import Path
from datetime import datetime, date, timedelta, timezone
import argparse
import copy
import csv
import hashlib
import io
import json
import re

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('invitationsSent','invitationsAccepted')
MONTHS={name:i+1 for i,name in enumerate(('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'))}
DAY_NAMES=('Mon','Tue','Wed','Thu','Fri','Sat','Sun')


def parse_source(raw):
    """Reject ambiguous/duplicate/non-contiguous source dates and invalid counts."""
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),strict=True)
    if reader.fieldnames!=['Date','Accepted','Sent']:
        raise ValueError('Expected exactly Date,Accepted,Sent columns.')
    rows=[]
    for source_line,item in enumerate(reader,start=2):
        label=(item.get('Date') or '').strip()
        match=re.fullmatch(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([A-Z][a-z]{2}) (\d{2}) (\d{4})',label)
        if not match or match[2] not in MONTHS:
            raise ValueError(f'Invalid date at CSV line {source_line}.')
        day=date(int(match[4]),MONTHS[match[2]],int(match[3]))
        if DAY_NAMES[day.weekday()]!=match[1]:
            raise ValueError(f'Weekday/date mismatch at CSV line {source_line}.')
        counts={}
        for source_key,target in (('Sent','invitationsSent'),('Accepted','invitationsAccepted')):
            value=(item.get(source_key) or '').strip()
            if not re.fullmatch(r'\d+',value):
                raise ValueError(f'Invalid {source_key} count at CSV line {source_line}.')
            counts[target]=int(value)
        rows.append({'date':day.isoformat(),**counts})
    if not rows or len(rows)!=len({r['date'] for r in rows}):
        raise ValueError('Empty CSV or duplicate source dates.')
    rows.sort(key=lambda row:row['date'])
    expected=(date.fromisoformat(rows[-1]['date'])-date.fromisoformat(rows[0]['date'])).days+1
    if expected!=len(rows):
        raise ValueError('CSV has missing source dates; do not invent zero rows.')
    return rows


def totals(rows):
    return {'sent':sum(row['invitationsSent'] for row in rows),
            'accepted':sum(row['invitationsAccepted'] for row in rows)}


def normalize(source_path,waalaxy,collected_at,reviewed_day='2026-10-22'):
    path=Path(source_path);raw=path.read_bytes();incoming=parse_source(raw)
    first,last=incoming[0]['date'],incoming[-1]['date']
    if last>reviewed_day:
        raise ValueError('Source extends beyond the reviewed reporting day.')
    old_rows=[{key:row[key] for key in ('date',*FIELDS)} for row in waalaxy.get('daily',[])
              if all(key in row for key in FIELDS)]
    old_rows.sort(key=lambda row:row['date'])
    if len(old_rows)!=len({row['date'] for row in old_rows}):
        raise ValueError('Existing invitation series contains duplicate dates.')
    old_by_date={row['date']:row for row in old_rows}
    conflicts=[]
    for row in incoming:
        old=old_by_date.get(row['date'])
        if old and any(old[key]!=row[key] for key in FIELDS):
            conflicts.append({'date':row['date'],
                'prior':{key:old[key] for key in FIELDS},
                'latest':{key:row[key] for key in FIELDS}})
    # Only the overlapping source dates are replaced. Other measures on these
    # days are preserved by apply_invitation_patch(), not copied into this patch.
    merged={row['date']:copy.deepcopy(row) for row in old_rows}
    merged.update({row['date']:copy.deepcopy(row) for row in incoming})
    merged=[merged[key] for key in sorted(merged)]
    start,end=merged[0]['date'],merged[-1]['date']
    complete=((date.fromisoformat(end)-date.fromisoformat(start)).days+1)==len(merged)
    earlier=[row for row in old_rows if row['date']<first]
    later=[row for row in old_rows if row['date']>last]
    previous=waalaxy.get('invitationCoverage') or {}
    segments=[]
    for segment in (earlier,later):
        if segment:
            segments.append({'start':segment[0]['date'],'end':segment[-1]['date'],
                'sourceDays':len(segment),'sourceFilename':previous.get('sourceFilename'),
                'sourceSha256':previous.get('sourceSha256'),
                'collectedAt':waalaxy.get('invitationCollectedAt'),
                'retainedFromPriorSource':True,**totals(segment)})
    current_partial=last==reviewed_day
    latest={'start':first,'end':last,'sourceDays':len(incoming),
        'sourceFilename':path.name,'sourceSha256':hashlib.sha256(raw).hexdigest(),
        'collectedAt':collected_at,'retainedFromPriorSource':False,
        'finalDayPartial':current_partial,**totals(incoming)}
    segments.append(copy.deepcopy(latest));segments.sort(key=lambda row:row['start'])
    coverage={'start':start,'end':end,'complete':complete,'sourceDays':len(merged),
        'zeroActivityDatesConfirmed':True,'currentDayPartial':current_partial,
        'completeDaysThrough':((date.fromisoformat(last)-timedelta(days=1)).isoformat() if current_partial else last),
        'sourceTimezone':None,'sourceDateBasis':'CSV source-day buckets; timezone and acceptance attribution semantics are not supplied. No timestamp or Mountain rebucketing inferred.',
        'accountEvidence':'Owner supplied this file for the Charles-only Waalaxy dashboard. The CSV itself contains no account identifier; identity is attributed by owner context, not embedded verification.',
        'sourceFilename':path.name,'sourceSha256':latest['sourceSha256'],
        'collectedAt':collected_at,'compositeSource':bool(earlier or later),
        'segments':segments}
    summary={**totals(merged),'cohortAcceptanceRate':None,
        'basis':'Sum of retained invitation source-day buckets over composite coverage, not a matched invitation cohort. The latest export replaces overlapping buckets; historical earlier days remain separate source segments.'}
    home=waalaxy.get('accountAnalytics') or {};window=home.get('sourceWindow') or {}
    home_comparison=None
    if window.get('displayedStartDate') and window.get('displayedEndDate'):
        comparable=[row for row in incoming if window['displayedStartDate']<=row['date']<=window['displayedEndDate']]
        all_days=(date.fromisoformat(window['displayedEndDate'])-date.fromisoformat(window['displayedStartDate'])).days+1
        comparable_complete=len(comparable)==all_days
        metric=home.get('metrics') or {}
        home_comparison={'start':window['displayedStartDate'],'end':window['displayedEndDate'],
            'allSourceDaysPresent':comparable_complete,'csv':totals(comparable),
            'home':{'sent':metric.get('invitationActionsSent'),'accepted':metric.get('invitationAcceptancesReported')},
            'sameNumericTotals':comparable_complete and totals(comparable)=={'sent':metric.get('invitationActionsSent'),'accepted':metric.get('invitationAcceptancesReported')},
            'identityIndependentlyVerifiedByCsv':False,'sameExactExtractionTimeEstablished':False,
            'combineWithHomeTotals':False,
            'note':'Same-window numeric agreement is a reconciliation check, not a second activity stream, cohort conversion rate or proof of exact extraction-time equality.'}
    review={'snapshotAt':collected_at,'sourceType':'owner_supplied_daily_invitation_csv',
        'latestExportSummary':latest,'mergedSeriesSummary':{'start':start,'end':end,'sourceDays':len(merged),**totals(merged)},
        'overlapDays':sum(row['date'] in old_by_date for row in incoming),
        'newSourceDays':sum(row['date'] not in old_by_date for row in incoming),
        'revisedDateBuckets':conflicts,'retainedOlderSegments':[row for row in segments if row.get('retainedFromPriorSource')],
        'explicitZeroDates':[row['date'] for row in incoming if not row['invitationsSent'] and not row['invitationsAccepted']],
        'homeReconciliation':home_comparison,
        'limits':['CSV Date buckets have no timezone or timestamps; preserve their source-day labels.',
                  'Accepted buckets changed retrospectively on overlapping dates. Do not assert that a revised acceptance occurred on that bucket date or count the difference as newly occurred activity.',
                  'CSV has invitations only, not message sends, replies, positive responses, or business outcomes.',
                  'Acceptances and sent invitations are not linked by invitation/prospect IDs, so no matched-cohort acceptance rate is established.']}
    reconciliation_note=('Same-window totals reconcile with the retained Charles Home aggregate and are not added to it.'
        if home_comparison and home_comparison['sameNumericTotals'] else
        'Keep this export separate from Home aggregates; same-window numeric agreement is not established.')
    partial_note='The final source day is partial' if current_partial else 'The final source day precedes the review day'
    return {'invitationRows':merged,'invitationCoverage':coverage,'invitationSummary':summary,
        'invitationCollectedAt':collected_at,'invitationImportReview':review,
        'sourceCard':{'id':'waalaxy_invitations','name':'Waalaxy · daily invitation source buckets',
            'asOf':collected_at,'checkedAt':reviewed_day,
            'status':'Current owner-supplied invitation CSV; historical earlier source segment retained',
            'coverage':copy.deepcopy(coverage),
            'method':'Owner-supplied Date/Accepted/Sent CSV; date-key replacement with retained earlier provenance',
            'note':f"Latest CSV has {len(incoming)} daily buckets from {first} through {last}, totaling {latest['sent']} Sent and {latest['accepted']} Accepted. Overlapping buckets replace the prior import; earlier September days remain a separate segment. {reconciliation_note} {partial_note}; timezone, exact extraction time and acceptance attribution semantics are unspecified. This CSV contains no message or reply actions."}}


def apply_invitation_patch(waalaxy,patch):
    current=waalaxy.get('invitationCollectedAt') or ''
    if current>patch['invitationCollectedAt']:
        raise ValueError('A newer invitation import is already present.')
    result=copy.deepcopy(waalaxy)
    by_day={row['date']:copy.deepcopy(row) for row in result.get('daily',[])}
    if len(by_day)!=len(result.get('daily',[])):
        raise ValueError('Existing daily records contain duplicate dates.')
    for row in patch['invitationRows']:
        by_day.setdefault(row['date'],{'date':row['date']}).update(copy.deepcopy(row))
    result['daily']=[by_day[key] for key in sorted(by_day)]
    for key in ('invitationCoverage','invitationSummary','invitationCollectedAt','invitationImportReview'):
        result[key]=copy.deepcopy(patch[key])
    result['notes']=[note for note in result.get('notes',[]) if not note.startswith('Invitation import contains') and not note.startswith('Latest owner-supplied invitation CSV:')]
    result['notes']=[('Other earlier Downloads exports could not be verified as Charles’s account and were excluded; the later owner-supplied invitation CSV is handled separately. Jess remains excluded.' if note.startswith('Recent Downloads exports could not be verified') else note) for note in result['notes']]
    latest=patch['invitationImportReview']['latestExportSummary']
    partial_note='the final source day is partial' if latest['finalDayPartial'] else 'the final source day precedes the review day'
    result['notes'].append(f"Latest owner-supplied invitation CSV: {latest['sourceDays']} source days from {latest['start']} through {latest['end']}; {latest['sent']} Sent and {latest['accepted']} Accepted. Earlier source days are retained separately, overlapping buckets are replaced, and {partial_note}. Account identity is owner-attributed; timezone and acceptance attribution semantics are unspecified. Message/reply events and cohort conversion remain unavailable.")
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv',type=Path)
    parser.add_argument('--snapshot',type=Path,default=ROOT/'data/shared-dashboard.json')
    parser.add_argument('--output',type=Path,default=ROOT/'data/private/waalaxy_actions_refresh_2026_10_22')
    args=parser.parse_args()
    waalaxy=json.loads(args.snapshot.read_text())['waalaxy']
    collected_at=datetime.now(timezone.utc).isoformat()
    patch=normalize(args.csv,waalaxy,collected_at)
    # Idempotent application must not alter other source families or count twice.
    applied=apply_invitation_patch(waalaxy,patch)
    assert apply_invitation_patch(applied,patch)==applied
    for key in ('snapshotAt','metrics','sheetSubset','accountAnalytics','selectedExportSnapshot'):
        assert applied.get(key)==waalaxy.get(key),key
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'source_invitations_5.csv').write_bytes(args.csv.read_bytes())
    (args.output/'invitation_patch.json').write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'patch':str(args.output/'invitation_patch.json'),
        'latestExportSummary':patch['invitationImportReview']['latestExportSummary'],
        'mergedSummary':patch['invitationSummary'],
        'revisedDateBuckets':patch['invitationImportReview']['revisedDateBuckets']}))


if __name__=='__main__':main()
