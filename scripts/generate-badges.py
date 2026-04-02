#!/usr/bin/env python3
"""Generate shields.io badge JSON files from GoatCounter analytics.

Reads hit counts per path from the GoatCounter API and writes one
shields.io-compatible endpoint JSON per tracked action to public/badges/.
GitHub Pages serves those files so shields.io can render live badges.

Required environment variables:
    GOATCOUNTER_CODE        Site code chosen during registration
                            (e.g. "ios-agent-skills")
    GOATCOUNTER_API_TOKEN   API token from GoatCounter Settings → API

Optional:
    BADGE_OUTPUT_DIR        Output directory (default: public/badges)
"""

import json
import os
import sys
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GOATCOUNTER_CODE = os.environ.get("GOATCOUNTER_CODE", "")
GOATCOUNTER_TOKEN = os.environ.get("GOATCOUNTER_API_TOKEN", "")
OUTPUT_DIR = os.environ.get("BADGE_OUTPUT_DIR", "public/badges")

# GoatCounter path → (output filename stem, badge label, shields.io color)
TRACKED_PATHS = {
    "/visit":                            ("visitors",                     "visitors",          "blue"),
    "/install/all":                      ("installs-all",                 "installs",          "brightgreen"),
    "/install/swift-concurrency":        ("installs-swift-concurrency",   "installs",          "brightgreen"),
    "/install/swiftui-mvvm-architecture":("installs-swiftui-mvvm",        "installs",          "brightgreen"),
    "/install/mvvm-uikit-architecture":  ("installs-mvvm-uikit",         "installs",          "brightgreen"),
    "/install/ios-testing":             ("installs-ios-testing",         "installs",          "brightgreen"),
    "/install/gcd-operationqueue":      ("installs-gcd-operationqueue",  "installs",          "brightgreen"),
    "/install/ios-security-audit":      ("installs-ios-security-audit",  "installs",          "brightgreen"),
    "/update":                          ("updates",                      "updates",           "orange"),
}


def fetch_hits() -> dict | None:
    start = "2025-01-01"
    end = date.today().isoformat()
    url = (
        f"https://{GOATCOUNTER_CODE}.goatcounter.com/api/v0/stats/hits"
        f"?limit=100&start={start}&end={end}"
    )
    req = Request(url, headers={"Authorization": f"Bearer {GOATCOUNTER_TOKEN}"})
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"⚠️  GoatCounter API returned HTTP {e.code}: {e.reason} — writing placeholder badges.", file=sys.stderr)
        return None
    except URLError as e:
        print(f"⚠️  Cannot reach GoatCounter: {e.reason} — writing placeholder badges.", file=sys.stderr)
        return None


def write_badge(filename: str, label: str, message: str, color: str) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    badge = {
        "schemaVersion": 1,
        "label": label,
        "message": message,
        "color": color,
    }
    path = os.path.join(OUTPUT_DIR, f"{filename}.json")
    with open(path, "w") as f:
        json.dump(badge, f)
    print(f"  ✅ {path}  →  {label}: {message}")


def format_count(total: int, unique: int) -> str:
    if total == 0:
        return "0"
    if 0 < unique < total:
        return f"{total} ({unique} unique)"
    return str(total)


def main() -> None:
    if not GOATCOUNTER_CODE or not GOATCOUNTER_TOKEN:
        print(
            "⚠️  GOATCOUNTER_CODE or GOATCOUNTER_API_TOKEN not set — "
            "writing placeholder badges.",
            file=sys.stderr,
        )
        for filename, label, color in TRACKED_PATHS.values():
            write_badge(filename, label, "N/A", "lightgrey")
        return

    print(f"Fetching GoatCounter stats for '{GOATCOUNTER_CODE}'...")
    data = fetch_hits()

    if data is None:
        for filename, label, color in TRACKED_PATHS.values():
            write_badge(filename, label, "N/A", "lightgrey")
        return

    hits = data.get("hits", [])
    counts = {h["path"]: h.get("count", 0) for h in hits}
    counts_unique = {h["path"]: h.get("count_unique", 0) for h in hits}

    for path, (filename, label, color) in TRACKED_PATHS.items():
        total = counts.get(path, 0)
        unique = counts_unique.get(path, 0)
        write_badge(filename, label, format_count(total, unique), color)

    print("Done.")


if __name__ == "__main__":
    main()
