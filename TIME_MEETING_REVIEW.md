# Christian-only October meeting evidence

Subject: Christian Wutz (`christian@redyset.io`). Scope: Centripetal work indexed from October 1, 2026, midnight Mountain through October 15, 2026, 6:22:30 a.m. Mountain. The current day is partial. All collection was read-only.

## Result

**184.96 minutes, approximately 3 hours 5 minutes, of deduplicated Christian-associated recording duration.** This is a recording-based meeting-time proxy. Individual attendance, billable time and non-meeting work duration are not established by these sources.

| Indexed date, Mountain | Prepared work label | Audio minutes | Counted proxy minutes |
|---|---|---:|---:|
| October 1 | Centripetal GTM | 36.00 | 36.00 |
| October 9 | Centripetal GTM, longer recording | 80.96 | 80.96 |
| October 9 | Centripetal GTM, overlapping recording segment | 33.00 | 0.00 |
| October 13 | Centripetal workflow / GitHub huddle | 68.00 | 68.00 |
| **Total** | **Four source records; three counted recordings** | **217.96** | **184.96** |

All four source records contain Christian's exact email in the participant metadata. Each recording also has the exact Christian Wutz speaker label. The included records have a Centripetal organizer and Centripetal work scope. Their full audio durations do not establish how long Christian personally attended.

## Duplicate resolved with private evidence

The shorter October 9 recording is a segment of the longer recording. This was verified using a limited in-memory comparison; transcript bodies and summaries were not retained in the prepared dataset or private evidence files.

- 87.30% of the shorter recording's distinct normalized five-word sequences occur in the longer recording.
- Ninety-eight exact long-sentence matches cover nearly the shorter recording's full span. Speaker labels agree on every matched sentence.
- Their relative timestamps align at a median 1,794.09-second offset. The 10th–90th percentile offset range is 1,793.73–1,794.35 seconds, supporting the same recorded segment rather than merely similar subject matter.
- The full shorter audio duration, 33 minutes, is excluded. The source record remains in the prepared dataset with `countedMinutes: 0` and an explicit duplicate link.

The private comparison proof stores the matching statistics and SHA256 fingerprints of normalized transcript text, without storing that text. Its own SHA256 is included in `data/time_meetings.json`.

## Calendly scope and zero-match interpretation

Fresh authentication verified Charles Solomon's Calendly account. An October 1–collection-cutoff event-start query returned one event, with no remaining pagination. Its invitee metadata contains no exact Christian email match; event guest metadata also contains no match.

**Calendar-only scheduled minutes in that account scope: zero.** This is not a claim that Christian had no other calendar meetings. Christian's own calendar is not available through this connector. Future events, canceled/rescheduled sources and unrelated meetings are excluded. No Calendly minutes were added to the Fireflies recording proxy.

## Coverage and units

Two descending Fireflies metadata pages, 100 source records, were read until the list crossed the October 1 Mountain boundary into September. Fifty-two indexed source records fall within the requested period; four associate Christian with Centripetal work. The connector's available metadata and exact matching records were reviewed, rather than assigning Charles's or the team's recordings to Christian.

Fireflies defines `duration` as audio minutes. Its `date` field is a transcript creation timestamp in UTC milliseconds; it is not an individual join/leave record. The dashboard preserves this distinction: displayed record dates and derived end timestamps are metadata proxies, not verified meeting start/end times. [Fireflies Transcript Schema](https://docs.fireflies.ai/schema/transcript)

The source coverage is complete for the accessible, indexed metadata list through the cutoff. Recordings absent from this Fireflies account, missing Christian participant metadata, unrecorded meetings, Christian's private calendar and non-meeting work are not covered. No collection failures occurred.

## Prepared data and dashboard use

`tools/prepare_time_meetings.py` produces `data/time_meetings.json` with scope, source freshness, source coverage, four minimal event records, counted audio durations, duplicate proof, references and limitations. The private source metadata is retained under `data/private/time/`.

The prepared records omit transcript bodies, summaries, other participant names/emails, meeting links and recording access links. They retain only Christian's approved subject identity, minimal work labels, source IDs, timing metadata and evidence definitions.

For the October time-and-effort category, show **recorded meeting proxy: about 3h 5m** separately from any independently developed non-meeting estimate range. Do not label this proxy as exact attendance or billable hours, and do not infer non-meeting work from the gaps between these records.
