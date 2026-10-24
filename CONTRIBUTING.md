# Contributing to Centripetal Analytics Dashboard

Canonical shared project: https://github.com/credyset/Centripetal-Analytics-Dashboard

GitHub holds the dashboard application, the approved curated reporting snapshot and measurement documentation. Live hosting is a publication destination; access to ChatGPT Sites is not needed to contribute to GitHub. Repository access must be granted separately by its owner where required.

Before adding data, read [CONTRIBUTOR_DATA_PRIORITIES.md](CONTRIBUTOR_DATA_PRIORITIES.md) for prioritized fields, source-specific traps, metric definitions and acceptance criteria beyond the README summary.

The latest focused findings are documented in [GAP_RESOLUTION_2026-10-24.md](GAP_RESOLUTION_2026-10-24.md); full source collection and other bounds remain in [REFRESH_REVIEW_2026-10-23.md](REFRESH_REVIEW_2026-10-23.md) and [the input checklist](MANUAL_DATA_REQUEST_2026-10-23.md). `tools/apply_refresh_2026_10_23.py --manifest <private-manifest.json>` and `tools/apply_gap_resolution_2026_10_24.py --manifest <private-manifest.json>` default to private previews; `--write-shared` is the explicit canonical-write step. Keep each source family's clock, guard row-scoped reviews against the exact inventory, and retain historical native observations and email context separately. Independent child reviews survive parent replacement. A newer collection does not authorize changing commercial decisions or Christian's owner-reported hours.

The October 24 review includes three historical September videos and one declined September video-linked reply; October's observed-video minimum remains 18. Source-profile first appearances are a bounded revision comparison, not exact row-add dates or new people. Show their minimum only when the entire comparison interval falls within the selected period. CRM's separately dated unchanged-state verification preserves the original census timestamp and does not establish complete deleted-event history. Charles's personal profile remains the headline content scope.

`tools/apply_mailbox_review_2026_10_24.py` prepares a private preview of independently dated, targeted Sales Inbox context. Keep mailbox ownership separate from the authenticated browser user and verified senders. Curated thread summaries and booking evidence do not change activity counts, commercial decisions or owner hours. Raw messages, addresses, meeting-access links and unrelated financial details remain private. Retain prior review batches with their original clocks when a later selection covers different threads.

CI checks partial-refresh replay, source-age and publication-hold preservation, and source-specific publication minimization. Rules in `PUBLICATION_REDACTIONS.json` are applied during final curation and validated before publication; a later source import must not restore excluded personal identity or context. Raw source content remains private. Earlier October 16 corrections remain documented in [ANALYTICS_REVISION_2026-10-16.md](ANALYTICS_REVISION_2026-10-16.md).

## Run a populated dashboard from a fresh clone

Use Python 3.10 or newer:

```sh
git clone https://github.com/credyset/Centripetal-Analytics-Dashboard.git
cd Centripetal-Analytics-Dashboard
python3 serve.py
```

Open http://127.0.0.1:8765. The app reads tracked `data/shared-dashboard.json` first. No connector credentials, private files or Sites account are needed to view the retained snapshot locally. Local rendering does not refresh source systems.

## Shared files

| File | Contribution scope |
| --- | --- |
| `app.js`, `styles.css`, `index.html`, `assets/` | Interface, category views and interactions |
| `data/shared-dashboard.json` | Approved curated reporting snapshot, including six business categories and Christian's separate October effort evidence |
| `tools/prepare_dashboard.py` | Assemble authorized normalized inputs and refresh local plus shared outputs |
| `tools/prepare_shared_snapshot.py` | Shared curation rules; remove local paths and source provenance, preserve approved reporting details |
| `tools/prepare_time*.py` | Time evidence and explicit estimate assumptions |
| `DATA_GAPS.md`, `SOURCE_REVIEW.md`, source review documents | Coverage, definitions, collection limits and supporting findings |
| `DEPLOYMENT.md` | Existing public hosting identity and publication procedure |

## Contribution workflow

1. Pull current `main`, create a topic branch and make a focused change.
2. Preserve the existing snapshot when changing only interface code. Do not substitute synthetic records or replace real values with zero.
3. For a source update, change only the authorized source's subtree in the shared snapshot. Retain existing fields, record the actual collection/coverage dates in its source entry, and document what changed and what remains unknown. Keep unrelated sources' freshness unchanged. Preserve owner-confirmed lead dispositions unless the owner supplies a correction.
4. If you have the ignored normalized inputs, run `python3 tools/prepare_dashboard.py`; it also writes the curated shared snapshot. If you only have a complete local prepared dashboard, run `python3 tools/prepare_shared_snapshot.py`. These commands overwrite the shared snapshot, so review the diff for unintended changes before committing.
5. Preview the affected views; verify dates, totals, missing-data behavior and any interactive controls. Run `node --check app.js` when Node is available, `python3 tools/check_shared_snapshot.py` and `git diff --check`.
6. Commit the relevant application, curated data and documentation changes, then push a branch and open a pull request. Keep independent changes in separate commits where practical.

Do not commit credentials, `.env` files, raw exports, transcripts, recording/join access links or private evidence. Prospect identities and the curated details already approved for the public dashboard may remain in the shared snapshot. Unknown figures stay null/unavailable. A snapshot total is not period activity; a booking is not attendance; recording duration is not measured Christian labor. Do not infer commercial attribution or actual worked hours from matching names, file dates or agent runtime.

## Publishing

Primary live dashboard: https://credyset.github.io/Centripetal-Analytics-Dashboard/#glance

`.github/workflows/pages.yml` validates the shared snapshot, checks JavaScript and builds the approved static output for pull requests. Pushes to `main` and manually dispatched runs then publish that artifact to GitHub Pages. Agents can update the dashboard by contributing through this repository; ChatGPT Sites access is not required. Check the Actions run and live result after merge. Deployment publishes retained data; it does not collect or refresh source systems.

`python3 tools/build_static_site.py` builds the allowlisted `_site/` artifact locally using tracked files only. Do not publish the repository root or private/raw inputs. Relative assets support the repository URL path. The generated index embeds the shared reporting JSON and application script, preserving all categories without connector access at runtime.

The existing Sites mirror has a separate update procedure in DEPLOYMENT.md. It is not automatically changed by the GitHub Pages workflow.
