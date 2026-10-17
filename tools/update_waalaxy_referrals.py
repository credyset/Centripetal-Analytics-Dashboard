"""Compatibility entrypoint for scoped, validated analytics imports.

The former hardcoded snapshot overwrote verified referral data and omitted zero
invitation days. Use explicit source inputs; see apply_analytics_revisions.py.
"""
from apply_analytics_revisions import main

if __name__ == '__main__':
    main()
