"""
Phase 5 — call Trustee authorized trace (after sender has registered + MEs signed).

Usage (from repo root, PYTHONPATH=.):
  python trace_request.py PA-xxxxxxxx

Uses TRACE_AUTH_TOKEN from config (default dev token unless env overrides).
"""
import sys

import requests

from config import TRACE_AUTH_TOKEN, TRUSTEE_URL


def main():
    if len(sys.argv) < 2:
        print("Usage: python trace_request.py <pseudonym>")
        sys.exit(1)
    pseudonym = sys.argv[1].strip()
    r = requests.post(
        f"{TRUSTEE_URL.rstrip('/')}/trace/reconstruct",
        json={"pseudonym": pseudonym},
        headers={"Authorization": f"Bearer {TRACE_AUTH_TOKEN}"},
        timeout=30,
    )
    print(r.status_code, r.json())


if __name__ == "__main__":
    main()
