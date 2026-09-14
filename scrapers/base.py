"""Shared utilities for all scrapers."""
import re
import requests
from datetime import date

TODAY = date.today().isoformat()


def slugify(text):
    """Lowercase kebab-case slug, e.g. 'VFD Air Compressor (<=75 hp)' -> 'vfd-air-compressor-75-hp'."""
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def make_key(util, name):
    """Stable program key like 'rmp:vfd-air-compressor-75-hp'. Uses the part of the
    name after the last '--' so the utility prefix in the name doesn't bloat the key."""
    tail = str(name).split("--")[-1]
    return util + ":" + slugify(tail)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}

def get(url, timeout=15, **kwargs):
    resp = requests.get(url, headers=HEADERS, timeout=timeout, **kwargs)
    resp.raise_for_status()
    return resp


def fingerprint(url, timeout=10):
    """Cheap change signal for a source document: an HTTP validator, without
    downloading (let alone parsing) the file. Prefers Content-Length -- on the
    utilities' CDNs Last-Modified/ETag vary per edge node (false positives) while
    Content-Length is stable and only shifts when the file's bytes actually change.
    Falls back to Last-Modified then ETag. Returns "" if unavailable, so the caller
    keeps the last known state rather than flagging a false change. ToS-safe: HEAD
    only, never parses the document."""
    try:
        resp = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code >= 400:
            return ""
        h = resp.headers
        if h.get("Content-Length"):
            return "cl:" + h["Content-Length"]
        if h.get("Last-Modified"):
            return "lm:" + h["Last-Modified"]
        if h.get("ETag"):
            return "etag:" + h["ETag"]
        return ""
    except Exception:
        return ""

def record(
    state, name, administrator, sector, incentive_type,
    technology, value, max_benefit, eligible_recipients,
    expiration, url, status="Active", notes="",
    implementation="", methodology="", example="",
    incentive_rate="", rebate_tiers="", unit_cap="", baseline="", min_project="",
    key="", detail_level="detailed", verified_date="", source_doc="", changed=False,
    verified_by="", description="",
):
    return {
        "State": state,
        "Program Name": name,
        # Short plain-language blurb: what this incentive is for. Shown first in
        # the detail modal so the reader gets the gist before the numbers.
        "_description": description,
        "Administrator": administrator,
        "Sector": sector,
        "Incentive Type": incentive_type,
        "Technology": technology,
        "Incentive Value": value,
        "Max Benefit": max_benefit,
        "Eligible Recipients": eligible_recipients,
        "Expiration Date": expiration,
        "Application URL": url,
        "Last Scraped": TODAY,
        "Status": status,
        "Notes": notes,
        # Detail page fields (not shown in Excel summary columns)
        "_implementation": implementation,
        "_methodology": methodology,
        "_example": example,
        # Structured calculation values (surfaced in the "Calculation Values" panel).
        # All optional -- blank values are hidden gracefully in the UI.
        "_incentive_rate": incentive_rate,   # e.g. "$0.10/kWh first-year savings"
        "_rebate_tiers": rebate_tiers,       # e.g. "$300 (tier 1); $600 (tier 2)"
        "_unit_cap": unit_cap,               # e.g. "$900/unit" or "$14,000/household"
        "_baseline": baseline,               # e.g. "ASHRAE 90.1 standard-efficiency HVAC"
        "_min_project": min_project,         # e.g. "50,000 kWh/yr savings"
        # Two-tier data model. "detailed" = exact values a human verified from a
        # source doc; "general" = auto-discovered breadth stub, exact values pending.
        "_key": key,                         # stable id, e.g. "rmp:compressed-air-vfd"
        "_detail_level": detail_level,       # "detailed" | "general"
        "_verified_date": verified_date,     # ISO date the exact values were confirmed
        "_source_doc": source_doc,           # authoritative PDF/page the values came from
        "_changed": "1" if changed else "",  # set when source_doc changed since verified
        # Who verified the exact values: "human" (hand-curated from a PDF),
        # "ai" (auto-extracted + confidence-gated by scrapers/extractor.py), or
        # "" (general stub, unverified). Drives the tier badge in the UI.
        "_verified_by": verified_by,
    }
