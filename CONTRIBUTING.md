# Contributing to Centripetal Analytics Dashboard

Canonical shared project: https://github.com/credyset/Centripetal-Analytics-Dashboard

GitHub holds the dashboard application, the approved curated reporting snapshot and measurement documentation. Live hosting is a publication destination; access to ChatGPT Sites is not needed to contribute to GitHub. Repository access must be granted separately by its owner where required.

Before adding data, read [CONTRIBUTOR_DATA_PRIORITIES.md](CONTRIBUTOR_DATA_PRIORITIES.md) for prioritized fields, source-specific traps, metric definitions and acceptance criteria beyond the README summary.

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

GitHub updates and live publication are separate steps; automatic deployment is not installed. Agents without Sites access should submit the completed GitHub change and identify the commit to publish. A publisher with Sites access follows `DEPLOYMENT.md`, builds the tracked shared snapshot into the existing Site, and records the deployed source/version. Never create a replacement Site merely to publish a contribution.
