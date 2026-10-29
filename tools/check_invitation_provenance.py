"""Regress clipped composite invitation lineage without private source files."""
from import_waalaxy_actions_2026_10_22 import retained_source_segments


def main():
    rows=[{'date':f'2026-09-{day:02d}','invitationsSent':day,'invitationsAccepted':1} for day in range(15,31)]
    previous={'compositeSource':True,'sourceFilename':'latest-prior.csv','sourceSha256':'latest',
        'segments':[{'start':'2026-09-15','end':'2026-09-21','sourceFilename':'original.csv',
            'sourceSha256':'original','collectedAt':None},
            {'start':'2026-09-22','end':'2026-10-22','sourceFilename':'latest-prior.csv',
                'sourceSha256':'latest','collectedAt':'2026-10-22T12:00:00Z','finalDayPartial':True}]}
    actual=retained_source_segments(rows,previous,'2026-10-01','2026-10-29','2026-10-22T12:00:00Z')
    assert len(actual)==2
    assert actual[0]['start']=='2026-09-15' and actual[0]['end']=='2026-09-21'
    assert actual[0]['sourceFilename']=='original.csv' and actual[0]['sourceSha256']=='original'
    assert actual[0]['collectedAt'] is None
    assert actual[1]['start']=='2026-09-22' and actual[1]['end']=='2026-09-30'
    assert actual[1]['sourceFilename']=='latest-prior.csv' and actual[1]['collectedAt']=='2026-10-22T12:00:00Z'
    assert not actual[1].get('finalDayPartial'), 'Clipped September end inherited October22 partial-day flag'
    assert sum(row['sent'] for row in actual)==sum(row['invitationsSent'] for row in rows)
    assert sum(row['accepted'] for row in actual)==16
    # A newer middle-window import can retain both sides with the same source
    # identity, but the gap is never falsely joined as contiguous coverage.
    middle=retained_source_segments(rows,previous,'2026-09-19','2026-09-25','new')
    assert [(r['start'],r['end']) for r in middle]==[('2026-09-15','2026-09-18'),('2026-09-26','2026-09-30')]
    assert middle[0]['sourceFilename']=='original.csv' and middle[1]['sourceFilename']=='latest-prior.csv'
    unknown=retained_source_segments(rows,{'compositeSource':True,'sourceFilename':'do-not-attribute.csv'},'2026-10-01','2026-10-29','new')
    assert all(r['sourceFilename'] is None and r['collectedAt'] is None for r in unknown)
    overlap={'segments':[previous['segments'][0],dict(previous['segments'][0])]}
    try:retained_source_segments(rows,overlap,'2026-10-01','2026-10-29','new')
    except ValueError:pass
    else:raise AssertionError('Overlapping historical provenance was accepted')
    print('Invitation provenance: original segmented clocks/hashes, clipped counts, disjoint ranges, unknown lineage and overlap rejection passed.')


if __name__=='__main__':main()
