# Live dashboard

Public URL: https://centripetal-analytics-dashboard.christian399556.chatgpt.site

Published October 14, 2026 (Mountain time), using the Sites plugin. The owner explicitly selected access for anyone on the internet. GitHub remains the private application project; Sites hosts the public website.

## Published scope

Six sections: LinkedIn Ads, Waalaxy, LinkedIn content, Pipedrive, Video DMs and a Referrals placeholder. Source dates are retained; publication is not a data refresh. No unattended collection has been installed.

The public build omits prospect names, contact links, individual record tables, raw exports and local file paths. Anonymous calculation rows preserve date, stage and owner-group filtering. The internal source snapshot stays local and outside GitHub. New public versions require rebuilding this sanitized package; never deploy the internal checkout or its original dashboard JSON directly.

## Source and hosting identity

- Private project: https://github.com/credyset/Centripetal-Analytics-Dashboard
- Sites project ID: `appgprj_6ad03dfa7c78819193bc9778aa17c805`
- Source checkout: `public_site/` (ignored by the parent Git repository)
- Authoritative Sites manifest: `public_site/.openai/hosting.json`
- Static output: `public_site/dist`
- Initial saved version: `appgprj_6ad03dfa7c78819193bc9778aa17c805~appgver_e07486d33d308191ab4995f313cc6649`
- Initial deployed source commit: `2bb0dd2396bb218e8e480f6b919e3055b6bc9ca3`

## Updating

1. Refresh authorized local snapshots and run `tools/prepare_dashboard.py` only when new data is available.
2. Run `tools/prepare_public_site.py` from this project to rebuild the public allowlisted output. It checks for private links and local paths and strips identities.
3. Follow the Sites skill: reuse the project ID, get a short-lived source credential, open/synchronize the Sites checkout, run needed checks, package the exact pushed source and save/deploy that version. Pass credentials only through hidden stdin; never store them.
4. Preserve the public audience unless the owner changes the access request. Check the deployment result and source freshness before sharing.

The project ID and live URL above are non-secret. Credentials and recipient-level source files must never be committed.
