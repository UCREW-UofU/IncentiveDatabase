"""
UCREW -- Commercial & Industrial Energy Efficiency Incentives Database
Scope: set by ENABLED_STATES below. Currently Utah (UT) only; add codes to grow.
Supported states: Utah (UT), Montana (MT), Idaho (ID), Nevada (NV)

Scope: commercial & industrial (C&I) facility incentives only -- residential,
multifamily, and new-home/builder programs are intentionally excluded.

Run manually:  python fetch_incentives.py
Scheduled:     GitHub Actions (.github/workflows/update-incentives.yml) runs daily
               and publishes the site/ folder to GitHub Pages.

Outputs:
  incentives.db    -- SQLite database (all fields including detail content)
  incentives.xlsx  -- Excel workbook (summary columns + Details sheet)
  incentives.html  -- Browser-viewable sortable table with clickable detail modals
  site/            -- Static site published to GitHub Pages (index.html + downloads)
  run_log.txt      -- Timestamped run history
"""

import os
import sqlite3
import importlib
import json
import shutil
import base64
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from collections import Counter

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "incentives.db"
XLSX_PATH = BASE_DIR / "incentives.xlsx"
HTML_PATH = BASE_DIR / "incentives.html"
LOG_PATH = BASE_DIR / "run_log.txt"
# GitHub Pages publishes this folder (Settings -> Pages -> Source: GitHub Actions).
SITE_DIR = BASE_DIR / "site"
# Committed state/reports for the two-tier model (change detection + needs-data list).
DATA_DIR = BASE_DIR / "data"
NEEDS_DATA_PATH = DATA_DIR / "needs_data.md"
SCAN_STATE_PATH = DATA_DIR / "scan_state.json"
# AI-extracted rate overlay + its audit trail. Each entry records the exact PDF
# fingerprint an extraction was made from, so the API is only called when a PDF
# actually changes; committed so promotions/demotions show up as a git diff.
AI_EXTRACTIONS_PATH = DATA_DIR / "ai_extractions.json"
# UCREW brand logo (vendored in-repo so CI builds have no external dependency).
LOGO_PATH = BASE_DIR / "assets" / "ucrew-logo.svg"

# UCREW brand palette (derived from the logo red #be0000). Used to theme the site.
BRAND = "#be0000"        # UCREW red -- primary
BRAND_DARK = "#8a0000"   # hover / gradient bottom
BRAND_DARKER = "#6b0000" # deepest shade


def _logo_data_uri():
    """Return the UCREW logo as a base64 data URI so the HTML stays self-contained
    (works when double-clicked and when served from GitHub Pages, no asset copy)."""
    try:
        raw = LOGO_PATH.read_bytes()
    except OSError:
        return ""
    b64 = base64.b64encode(raw).decode("ascii")
    return "data:image/svg+xml;base64," + b64


STATE_COLORS = {
    "UT": "FF4E79A7",
    "MT": "FF59A14F",
    "ID": "FFF28E2B",
    "NV": "FFE15759",
}

# Canonical ordering + display names for every state the scanner *can* cover.
ALL_STATES = ["UT", "MT", "ID", "NV"]
STATE_NAMES = {"UT": "Utah", "MT": "Montana", "ID": "Idaho", "NV": "Nevada"}

# States the scanner is *currently* scoped to. Start narrow (Utah only) and grow
# by adding codes here as each state is perfected -- e.g. ["UT", "ID"]. This one
# constant drives the scrapers that run, the rows kept, and all site/Excel labels.
ENABLED_STATES = ["UT"]

# Summary columns shown in the Excel main sheets (the full set).
COLUMNS = [
    "State", "Program Name", "Administrator", "Sector", "Incentive Type",
    "Technology", "Incentive Value", "Max Benefit", "Eligible Recipients",
    "Expiration Date", "Application URL", "Last Scraped", "Status", "Notes",
]

# Columns shown in the on-page HTML table -- a trimmed subset. Sector (always
# C&I), Application URL, Last Scraped (shown in the header badge), Notes, and the
# headline dollar figures (Incentive Value, Max Benefit) are intentionally omitted
# here to keep the table scannable; all of them still appear in each program's
# detail modal, so nothing is lost. "State" and "Program Name" must stay first (the
# renderer treats column 0 as the state badge and column 1 as the name button).
HTML_COLUMNS = [c for c in COLUMNS if c not in (
    "Sector", "Application URL", "Last Scraped", "Notes",
    "Incentive Value", "Max Benefit",
)]

# Detail columns stored in SQLite and shown in modal / Excel Details sheet.
# The _ -prefixed structured fields hold the actual numbers used in calculations.
DETAIL_COLUMNS = [
    "_incentive_rate", "_rebate_tiers", "_unit_cap", "_baseline", "_min_project",
    "_implementation", "_methodology", "_example",
    # Two-tier model metadata (see scrapers/base.record).
    "_key", "_detail_level", "_verified_date", "_source_doc", "_changed", "_verified_by",
]

ALL_COLUMNS = COLUMNS + DETAIL_COLUMNS


# ---------------------------------------------------------------------------
# Equipment classification (UCREW audit categories).
#
# ONE keyword vocabulary drives two things:
#   1. build-time: every program is auto-tagged with the equipment categories
#      its text mentions (name + technology + methodology + example + notes).
#   2. run-time: the "AR Finder" box in the site maps a typed assessment
#      recommendation (e.g. "Install VFD on compressors") to the same
#      categories, then surfaces the programs tagged with them.
#
# Matching is case-insensitive and word-boundary aware: a keyword matches only
# at the start of a word, but trailing letters are allowed so the lowercase root
# "compressor" also matches "compressors". This prevents false hits like "led"
# inside "controlled". Recall is favored over precision -- a discovery aid, not a
# billing engine.
# ---------------------------------------------------------------------------
EQUIPMENT_KEYWORDS = {
    "Lighting": [
        "lighting", "light fixture", "led", "lamp", "luminaire", "high bay",
        "high-bay", "troffer", "t8", "t5", "fluorescent", "daylighting",
        "occupancy sensor", "exit sign", "delamping",
    ],
    "Compressed Air": [
        "compressed air", "compressor", "air compressor", "vsd compressor",
        "air dryer", "air leak", "compressed-air",
    ],
    "HVAC": [
        "hvac", "air conditioning", "air conditioner", "rooftop unit", "rtu",
        "chiller", "cooling", "furnace", "heat pump", "thermostat", "economizer",
        "ventilation", "make-up air", "makeup air", "space heating", "packaged unit",
        "mini split", "mini-split", "vrf",
    ],
    "Boilers & Steam": [
        "boiler", "steam", "condensate", "steam trap", "burner", "hot water heating",
        "linkageless", "combustion",
    ],
    "Motors & Drives": [
        "vfd", "variable frequency drive", "variable-frequency", "vsd",
        "variable speed", "adjustable speed", "premium efficiency motor",
        "efficient motor", "motor", "drive", "ecm",
    ],
    "Pumps": [
        "pump", "pumping",
    ],
    "Fans": [
        "fan", "exhaust fan", "ec motor", "ceiling fan",
    ],
    "Refrigeration": [
        "refrigeration", "refrigerated", "walk-in cooler", "walk-in freezer",
        "walk in cooler", "cooler", "freezer", "evaporator", "night cover",
        "anti-sweat", "strip curtain", "case lighting",
    ],
    "Process Heating": [
        "process heat", "oven", "kiln", "industrial dryer", "heat recovery",
        "waste heat", "process load",
    ],
    "Building Envelope": [
        "insulation", "weatherization", "envelope", "window", "roof", "air sealing",
        "pipe insulation", "cool roof", "door seal",
    ],
    "Water Heating": [
        "water heater", "water heating", "domestic hot water", "dhw",
        "heat pump water heater", "hpwh", "tankless",
    ],
    "Controls / EMS": [
        "controls", "control system", "ems", "bms", "building automation",
        "energy management system", "setback", "network lighting control",
        "sensor", "retrocommissioning", "retro-commissioning", "commissioning",
    ],
    "Irrigation": [
        "irrigation", "sprinkler", "center pivot", "agricultural pump",
        "wire-to-water", "scientific irrigation scheduling",
    ],
    "Energy Storage": [
        "battery", "batteries", "energy storage", "storage system",
        "bess", "solar-plus-storage", "solar plus storage",
    ],
    "Solar / PV": [
        "solar", "photovoltaic", "pv system", "solar panel", "solar array",
    ],
    "Custom / Whole Facility": [
        "custom", "multiple technolog", "whole building", "whole-building",
        "whole facility", "comprehensive", "strategic energy management",
        "energy audit", "new construction", "any measure", "all measures",
    ],
}

# Programs tagged with any of these categories are treated as broad measures
# that plausibly cover almost any recommendation, so the AR Finder always
# surfaces them (flagged separately as "custom / whole-facility").
CUSTOM_CATEGORIES = {"Custom / Whole Facility"}


def _kw_hit(keyword, text):
    """True if ``keyword`` appears at a word boundary in ``text`` (trailing
    letters allowed, so "compressor" also matches "compressors")."""
    return re.search(r"\b" + re.escape(keyword), text) is not None


def classify_equipment(text):
    """Return the sorted list of equipment categories whose keywords appear in
    ``text`` (case-insensitive, word-boundary aware)."""
    t = (text or "").lower()
    hits = [cat for cat, kws in EQUIPMENT_KEYWORDS.items()
            if any(_kw_hit(kw, t) for kw in kws)]
    return sorted(hits)



def main(dry_run_ai=False):
    print("\n" + "=" * 60)
    print("  Energy Efficiency Incentives DB -- " + str(date.today()))
    print("=" * 60 + "\n")

    all_rows = _fetch_all_sources()
    all_rows = _deduplicate(all_rows)
    all_rows = _auto_expire(all_rows)
    all_rows = _apply_change_detection(all_rows)
    all_rows = _apply_ai_extraction(all_rows, persist=not dry_run_ai)

    if dry_run_ai:
        # Preview mode: show what AI extraction did without writing outputs or the
        # committed caches, so a run can be reviewed before it goes live.
        _print_ai_dry_run(all_rows)
        return

    print("\nTotal programs collected: " + str(len(all_rows)))
    _print_summary(all_rows)

    _write_sqlite(all_rows)
    _write_excel(all_rows)
    _write_html(all_rows)
    _stage_site()
    _write_needs_data(all_rows)
    _write_log(len(all_rows))

    print("\nDone. Files written:")
    print("  " + str(XLSX_PATH))
    print("  " + str(HTML_PATH))
    print("  " + str(DB_PATH))
    print("  " + str(SITE_DIR) + " (published to GitHub Pages)")


def _stage_site():
    """Assemble the folder GitHub Pages serves: index.html + downloadable data files."""
    SITE_DIR.mkdir(exist_ok=True)
    shutil.copy2(HTML_PATH, SITE_DIR / "index.html")
    if XLSX_PATH.exists():
        shutil.copy2(XLSX_PATH, SITE_DIR / "incentives.xlsx")
    if DB_PATH.exists():
        shutil.copy2(DB_PATH, SITE_DIR / "incentives.db")
    print("Site staged -> " + str(SITE_DIR / "index.html"))


def _fetch_all_sources():
    rows = []
    print("Fetching data sources (states: " + ", ".join(ENABLED_STATES) + ")...\n")

    # (label, module, func, state). state=None means the source is multi-state
    # and is scoped by passing ENABLED_STATES; single-state sources are skipped
    # entirely when their state is not enabled.
    sources = [
        ("Rocky Mountain Power (UT)", "scrapers.rocky_mountain", "fetch_all", "UT"),
        ("Dominion Energy Utah (UT)", "scrapers.dominion_ut", "fetch_all", "UT"),
        ("NV Energy (NV)", "scrapers.nv_energy", "fetch_all", "NV"),
        ("NorthWestern Energy (MT)", "scrapers.northwestern", "fetch_all", "MT"),
        ("Idaho Power (ID)", "scrapers.idaho_power", "fetch_all", "ID"),
        ("Avista (ID)", "scrapers.avista", "fetch_all", "ID"),
        ("Federal (IRS/USDA)", "scrapers.federal", "fetch_all", None),
        ("Discovery (index scan)", "scrapers.discovery", "fetch_all", None),
        ("DSIRE", "scrapers.dsire", "fetch_all", None),
    ]

    for label, module_path, func_name, state in sources:
        if state is not None and state not in ENABLED_STATES:
            continue
        try:
            mod = importlib.import_module(module_path)
            func = getattr(mod, func_name)
            # Multi-state sources accept the enabled-state list; single-state don't.
            result = func(ENABLED_STATES) if state is None else func()
            rows.extend(result)
        except Exception as exc:
            print("  [WARN] " + label + " failed: " + str(exc))

    # Safety net: keep only enabled states (covers multi-state sources and any
    # stray records), so ENABLED_STATES is the single source of truth for scope.
    rows = [r for r in rows if r.get("State") in ENABLED_STATES]
    return rows


def _deduplicate(rows):
    seen = {}
    for row in rows:
        key = (row.get("State", ""), _normalize(row.get("Program Name", "")))
        existing = seen.get(key)
        if existing is None:
            seen[key] = row
        else:
            # Prefer the record with more detail content
            new_detail = len(row.get("_implementation", "")) + len(row.get("_example", ""))
            old_detail = len(existing.get("_implementation", "")) + len(existing.get("_example", ""))
            if new_detail > old_detail:
                seen[key] = row
    return list(seen.values())


def _normalize(s):
    return " ".join(s.lower().split())


# Statuses that should never be auto-expired (manually set by scraper logic)
_SKIP_EXPIRE = {"Temporarily Paused", "Pending"}


def _auto_expire(rows):
    """
    Automatically set Status='Expired' for any row whose Expiration Date is a
    parseable ISO date that has already passed today.  Rows marked Temporarily
    Paused or Pending are left alone -- the scraper controls those.
    Also appends a note so users know the program lapsed and may have renewed.
    """
    today = date.today()
    changed = 0
    for row in rows:
        if row.get("Status") in _SKIP_EXPIRE:
            continue
        exp = str(row.get("Expiration Date") or "")
        try:
            exp_date = date.fromisoformat(exp)
        except ValueError:
            continue  # "Ongoing", "Pending launch", blank -- skip
        if exp_date < today and row.get("Status") != "Expired":
            row["Status"] = "Expired"
            existing_note = row.get("Notes", "")
            lapse_note = "EXPIRED " + exp + " -- program may have renewed; verify at administrator website before advising clients."
            row["Notes"] = (lapse_note + "  " + existing_note).strip() if existing_note else lapse_note
            changed += 1
    if changed:
        print("  Auto-expired " + str(changed) + " programs whose expiration date has passed.")
    return rows


def _print_summary(rows):
    counts = Counter(r["State"] for r in rows)
    for state in ENABLED_STATES:
        print("  " + state + ": " + str(counts.get(state, 0)) + " programs")
    statuses = Counter(r.get("Status", "Active") for r in rows)
    for status, n in statuses.items():
        print("  Status=" + status + ": " + str(n))


# -- SQLite ------------------------------------------------------------------

def _write_sqlite(rows):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    col_defs = ", ".join('"' + c + '" TEXT' for c in ALL_COLUMNS)
    cur.execute(
        "CREATE TABLE IF NOT EXISTS incentives "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, " + col_defs + ")"
    )
    # Migrate: add any columns introduced since the DB was first created
    existing_cols = {r[1] for r in cur.execute("PRAGMA table_info(incentives)")}
    for c in ALL_COLUMNS:
        if c not in existing_cols:
            cur.execute('ALTER TABLE incentives ADD COLUMN "' + c + '" TEXT')
    cur.execute(
        'DELETE FROM incentives WHERE "Last Scraped" = ?',
        (date.today().isoformat(),)
    )
    col_names = ", ".join('"' + c + '"' for c in ALL_COLUMNS)
    placeholders = ", ".join(["?"] * len(ALL_COLUMNS))
    insert_sql = "INSERT INTO incentives (" + col_names + ") VALUES (" + placeholders + ")"
    for row in rows:
        values = [row.get(c, "") for c in ALL_COLUMNS]
        cur.execute(insert_sql, values)
    conn.commit()
    conn.close()
    print("\nSQLite: " + str(len(rows)) + " rows written -> " + DB_PATH.name)


# -- Excel -------------------------------------------------------------------

def _write_excel(rows):
    df_all = pd.DataFrame(rows, columns=ALL_COLUMNS)
    df_all = df_all.sort_values(["State", "Incentive Type", "Program Name"])

    # Summary df (no detail columns)
    df_summary = df_all[COLUMNS]

    with pd.ExcelWriter(XLSX_PATH, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="All States", index=False)
        for state in ENABLED_STATES:
            df_state = df_summary[df_summary["State"] == state]
            if not df_state.empty:
                df_state.to_excel(writer, sheet_name=state, index=False)
        # Details sheet: Program Name + structured calc values + long-form detail columns
        df_details = df_all[[
            "State", "Program Name",
            "_incentive_rate", "_rebate_tiers", "_unit_cap", "_baseline", "_min_project",
            "_implementation", "_methodology", "_example",
        ]].copy()
        df_details.columns = [
            "State", "Program Name",
            "Incentive Rate", "Rebate Tiers", "Per-Unit Cap", "Baseline Assumption", "Min Project Size",
            "Implementation Steps", "Savings Methodology", "Worked Example",
        ]
        df_details.to_excel(writer, sheet_name="Details", index=False)

    _style_excel(df_summary, df_all)
    print("Excel: " + str(len(rows)) + " rows written -> " + XLSX_PATH.name)


def _style_excel(df_summary, df_all):
    wb = load_workbook(XLSX_PATH)
    today = date.today()
    warn_date = today + timedelta(days=30)

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        is_details = sheet_name == "Details"

        if is_details:
            # Column widths for details sheet (State, Program, 5 structured, 3 long-form)
            col_widths = [8, 38, 26, 30, 16, 30, 20, 55, 55, 55]
            for i, w in enumerate(col_widths, start=1):
                ws.column_dimensions[get_column_letter(i)].width = w
            hdr_fill = PatternFill("solid", fgColor="FF1F3864")
            for cell in ws[1]:
                cell.fill = hdr_fill
                cell.font = Font(bold=True, color="FFFFFFFF", size=10)
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.row_dimensions[1].height = 30
            ws.freeze_panes = "A2"
            for row_idx in range(2, ws.max_row + 1):
                bg = "FFFFFFFF" if row_idx % 2 == 0 else "FFF5F5F5"
                for col_idx in range(1, ws.max_column + 1):
                    cell = ws.cell(row_idx, col_idx)
                    cell.fill = PatternFill("solid", fgColor=bg)
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
                    cell.font = Font(size=9)
                ws.row_dimensions[row_idx].height = 80
            continue

        df = df_summary if sheet_name == "All States" else df_summary[df_summary["State"] == sheet_name]

        for col_idx, col_name in enumerate(COLUMNS, start=1):
            col_letter = get_column_letter(col_idx)
            vals = [len(str(df.iloc[i][col_name])) for i in range(min(len(df), 100))]
            max_len = max([len(str(col_name))] + vals) if vals else len(str(col_name))
            ws.column_dimensions[col_letter].width = min(max_len + 4, 55)

        hdr_fill = PatternFill("solid", fgColor="FF1F3864")
        hdr_font = Font(bold=True, color="FFFFFFFF", size=10)
        for cell in ws[1]:
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        ws.row_dimensions[1].height = 30
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions

        state_col = COLUMNS.index("State") + 1
        status_col = COLUMNS.index("Status") + 1
        exp_col = COLUMNS.index("Expiration Date") + 1

        for row_idx in range(2, ws.max_row + 1):
            state_val = str(ws.cell(row_idx, state_col).value or "")
            status_val = str(ws.cell(row_idx, status_col).value or "Active")
            exp_val = str(ws.cell(row_idx, exp_col).value or "")

            if status_val == "Expired":
                bg, txt_color = "FFD3D3D3", "FF808080"
            elif status_val in ("Temporarily Paused", "Pending"):
                bg, txt_color = "FFFFF2CC", "FF000000"
            else:
                try:
                    bg = "FFFFF2CC" if date.fromisoformat(exp_val) <= warn_date else (
                        "FFFFFFFF" if row_idx % 2 == 0 else "FFF5F5F5"
                    )
                except ValueError:
                    bg = "FFFFFFFF" if row_idx % 2 == 0 else "FFF5F5F5"
                txt_color = "FF000000"

            row_fill = PatternFill("solid", fgColor=bg)
            for col_idx in range(1, ws.max_column + 1):
                cell = ws.cell(row_idx, col_idx)
                cell.fill = row_fill
                cell.alignment = Alignment(vertical="top", wrap_text=True)
                cell.font = Font(size=9, color=txt_color)

            color = STATE_COLORS.get(state_val, "FFCCCCCC")
            ws.cell(row_idx, state_col).fill = PatternFill("solid", fgColor=color)
            ws.cell(row_idx, state_col).font = Font(bold=True, color="FFFFFFFF", size=9)

    wb.save(XLSX_PATH)


# -- HTML --------------------------------------------------------------------

def _esc(s):
    """HTML-escape a string for safe embedding."""
    return (str(s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def _write_html(rows):
    df = pd.DataFrame(rows, columns=ALL_COLUMNS)
    df = df.sort_values(["State", "Status", "Program Name"])

    today = date.today()
    warn_date = today + timedelta(days=30)
    logo_uri = _logo_data_uri()

    html_colors = {
        "UT": "#4E79A7", "MT": "#59A14F",
        "ID": "#F28E2B", "NV": "#E15759",
    }

    # Scope labels derived from ENABLED_STATES (drives title, subtitle, legend).
    enabled = [s for s in ALL_STATES if s in ENABLED_STATES]
    enabled_codes = ", ".join(enabled)
    enabled_names = " &middot; ".join(STATE_NAMES.get(s, s) for s in enabled)
    # State filter + state legend chips only make sense with more than one state.
    multi_state = len(enabled) > 1
    legend_states_html = "".join(
        '<span style="background:' + html_colors.get(s, "#888") + '"></span>' + s
        for s in enabled
    ) if multi_state else ""
    if multi_state:
        _state_opts = '<option value="">All</option>' + "".join(
            "<option>" + _esc(s) + "</option>" for s in enabled)
        state_filter_html = '<select id="f-state" onchange="applyFilters()">' + _state_opts + "</select>"
    else:
        state_filter_html = ""

    # Build per-row detail JSON (indexed by row id)
    detail_data = {}
    rows_html = []

    for row_idx, (_, row) in enumerate(df.iterrows()):
        status = str(row.get("Status") or "Active")
        exp = str(row.get("Expiration Date") or "")
        state = str(row.get("State") or "")
        color = html_colors.get(state, "#888")

        row_class = ""
        if status == "Expired":
            row_class = "expired"
        elif status in ("Temporarily Paused", "Pending"):
            row_class = "paused"
        else:
            try:
                if date.fromisoformat(exp) <= warn_date:
                    row_class = "expiring"
            except ValueError:
                pass

        url = str(row.get("Application URL") or "")
        name = str(row.get("Program Name") or "")

        # Auto-classify this program into UCREW equipment categories. Equipment
        # tags come from the full text (so a compressor mentioned in an example
        # still counts). "Custom / whole-facility" is decided from the NAME +
        # technology + type only -- prescriptive measures often mention "custom"
        # in prose as a fallback, and that shouldn't demote them to the custom
        # bucket in the AR Finder. Powers the AR Finder search and modal chips.
        full_text = " ".join(str(row.get(c) or "") for c in (
            "Program Name", "Technology", "Sector", "Incentive Type",
            "_methodology", "_implementation", "_example", "Notes",
        ))
        narrow_text = " ".join(str(row.get(c) or "") for c in (
            "Program Name", "Technology", "Incentive Type",
        ))
        is_custom = any(c in CUSTOM_CATEGORIES for c in classify_equipment(narrow_text))
        equipment = [c for c in classify_equipment(full_text) if c not in CUSTOM_CATEGORIES]
        if is_custom:
            equipment.append("Custom / Whole Facility")
        equipment = sorted(equipment)

        # Store detail data in JS object
        detail_data[row_idx] = {
            "name": name,
            "state": state,
            "admin": str(row.get("Administrator") or ""),
            "sector": str(row.get("Sector") or ""),
            "type": str(row.get("Incentive Type") or ""),
            "tech": str(row.get("Technology") or ""),
            "value": str(row.get("Incentive Value") or ""),
            "max": str(row.get("Max Benefit") or ""),
            "recipients": str(row.get("Eligible Recipients") or ""),
            "expiration": exp,
            "url": url,
            "status": status,
            "notes": str(row.get("Notes") or ""),
            "implementation": str(row.get("_implementation") or ""),
            "methodology": str(row.get("_methodology") or ""),
            "example": str(row.get("_example") or ""),
            "lastScraped": str(row.get("Last Scraped") or ""),
            # Structured calculation values
            "rate": str(row.get("_incentive_rate") or ""),
            "tiers": str(row.get("_rebate_tiers") or ""),
            "cap": str(row.get("_unit_cap") or ""),
            "baseline": str(row.get("_baseline") or ""),
            "minProject": str(row.get("_min_project") or ""),
            "equipment": equipment,
            "custom": is_custom,
            # Two-tier data-completeness metadata.
            "detailLevel": str(row.get("_detail_level") or "general"),
            "verified": str(row.get("_verified_date") or ""),
            "changed": bool(str(row.get("_changed") or "")),
            "sourceDoc": str(row.get("_source_doc") or ""),
            "verifiedBy": str(row.get("_verified_by") or ""),
        }

        # Data-completeness (tier) badge shown next to the program name.
        detail_level = str(row.get("_detail_level") or "general")
        verified = str(row.get("_verified_date") or "")
        verified_by = str(row.get("_verified_by") or "")
        changed = bool(str(row.get("_changed") or ""))
        if changed:
            tier_badge = '<span class="tier tier-changed">&#9888; source changed &middot; re-verify</span>'
        elif detail_level == "detailed" and verified_by == "ai":
            # AI-extracted + confidence-gated: verified, but flagged as machine-read
            # so students know it wasn't hand-checked.
            tier_badge = ('<span class="tier tier-ai">&#10003; AI-verified'
                          + ((' ' + _esc(verified)) if verified else '') + '</span>')
        elif detail_level == "detailed":
            tier_badge = ('<span class="tier tier-verified">&#10003; verified'
                          + ((' ' + _esc(verified)) if verified else '') + '</span>')
        else:
            tier_badge = '<span class="tier tier-general">amount varies &middot; see program</span>'

        cells = [
            '<td><span class="badge" style="background:' + color + '">' + _esc(state) + "</span></td>",
            '<td class="name-cell"><button class="detail-btn" onclick="openDetail(' + str(row_idx) + ')">'
            + _esc(name) + "</button> " + tier_badge + "</td>",
        ]
        for col in HTML_COLUMNS[2:]:
            val = str(row.get(col) or "")
            if col == "Application URL" and val:
                cells.append('<td><a href="' + _esc(val) + '" target="_blank">Open</a></td>')
            elif col in ("Incentive Value", "Max Benefit"):
                # Headline dollar figures -- emphasized so they are scannable in the table
                cells.append('<td class="money">' + _esc(val) + "</td>")
            else:
                cells.append("<td>" + _esc(val) + "</td>")

        rows_html.append(
            '<tr class="' + row_class + '" '
            'data-state="' + _esc(state) + '" '
            'data-type="' + _esc(str(row.get("Incentive Type") or "")) + '" '
            'data-sector="' + _esc(str(row.get("Sector") or "")) + '" '
            'data-tech="' + _esc(str(row.get("Technology") or "")) + '" '
            'data-equipment="' + _esc(";".join(equipment)) + '" '
            'data-custom="' + ("1" if is_custom else "0") + '" '
            'data-detail="' + _esc(detail_level) + '" '
            'data-idx="' + str(row_idx) + '">'
            + "".join(cells) + "</tr>"
        )

    th_cells = "".join(
        '<th onclick="sortTable(' + str(i) + ')">' + col + "</th>"
        for i, col in enumerate(HTML_COLUMNS)
    )

    detail_json = json.dumps(detail_data, ensure_ascii=True)

    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UCREW -- Commercial &amp; Industrial Energy Incentives (""" + enabled_codes + """)</title>
<link rel="icon" type="image/svg+xml" href=\"""" + logo_uri + """\">
<style>
:root {
  --brand: """ + BRAND + """;
  --brand-dark: """ + BRAND_DARK + """;
  --brand-darker: """ + BRAND_DARKER + """;
  --brand-tint: #fbeaea;          /* light red row/hover wash */
  --brand-tint-border: #f0cccc;
  --money: #1f6e1f;               /* green -- dollar figures / savings */
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 13px; background: #f4f6f9; color: #222; }
header { background: linear-gradient(135deg, var(--brand) 0%, var(--brand-dark) 100%); color: #fff; padding: 18px 24px; }
.header-inner { display: flex; align-items: center; gap: 18px; }
.brand-logo { height: 46px; width: auto; flex-shrink: 0; filter: brightness(0) invert(1); }
.header-text { flex: 1; min-width: 0; }
header h1 { font-size: 20px; }
header p { font-size: 12px; opacity: .8; margin-top: 4px; }
.controls { padding: 12px 24px; background: #fff; border-bottom: 1px solid #ddd; display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.controls select { padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; }
.legend { margin-left: auto; display: flex; gap: 8px; align-items: center; font-size: 11px; flex-wrap: wrap; }
.legend span { display: inline-block; width: 12px; height: 12px; border-radius: 2px; }
#count { font-size: 12px; color: #555; }
.table-wrap { overflow-x: auto; padding: 16px 24px; }
table { width: 100%; border-collapse: collapse; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.08); border-radius: 6px; overflow: hidden; }
th { background: var(--brand); color: #fff; padding: 8px 10px; text-align: left; cursor: pointer; white-space: nowrap; font-size: 12px; user-select: none; }
th:hover { background: var(--brand-dark); }
th.asc::after { content: " \25b2"; font-size: 10px; }
th.desc::after { content: " \25bc"; font-size: 10px; }
td { padding: 6px 10px; border-bottom: 1px solid #eee; vertical-align: top; font-size: 12px; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: var(--brand-tint) !important; }
tr.expired td { color: #aaa; background: #fafafa; }
tr.paused td { background: #fffde7; }
tr.expiring td { background: #fff8e1; }
tr.hidden { display: none; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; color: #fff; font-weight: 700; font-size: 11px; }
a { color: var(--brand); text-decoration: none; }
a:hover { text-decoration: underline; }
.detail-btn { background: none; border: none; color: var(--brand); cursor: pointer; text-align: left; font-size: 12px; padding: 0; font-family: inherit; text-decoration: underline; text-decoration-style: dotted; }
.detail-btn:hover { color: var(--brand-dark); }
td:nth-child(2) { min-width: 180px; max-width: 280px; }
td.money { font-weight: 700; color: var(--money); white-space: nowrap; }
tr.expired td.money { color: #9bb69b; }
.header-badges { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.hbadge { display: inline-block; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.25); color: #fff; font-size: 12px; padding: 3px 10px; border-radius: 12px; }
.hbadge.scanned { background: #2d8c2d; border-color: #2d8c2d; font-weight: 600; }

/* AR Finder */
.ar-bar { background: linear-gradient(135deg, #fff 0%, var(--brand-tint) 100%); border-bottom: 1px solid var(--brand-tint-border); padding: 16px 24px; }
.ar-inner { max-width: 960px; }
.ar-label { display: block; font-size: 13px; font-weight: 700; color: var(--brand); margin-bottom: 8px; letter-spacing: .2px; }
.ar-row { display: flex; gap: 8px; }
.ar-input { flex: 1; padding: 11px 14px; border: 2px solid var(--brand-tint-border); border-radius: 6px; font-size: 14px; font-family: inherit; background: #fff; }
.ar-input:focus { outline: none; border-color: var(--brand); box-shadow: 0 0 0 3px rgba(190,0,0,.12); }
.ar-clear { border: 1px solid #ccc; background: #fff; color: #555; border-radius: 6px; padding: 0 14px; font-size: 12px; font-weight: 600; cursor: pointer; }
.ar-clear:hover { background: #f4f4f4; }
.ar-result { font-size: 12.5px; color: #333; margin-top: 10px; line-height: 1.6; }
.ar-result:empty { display: none; }
.ar-result .eq-chip { display: inline-block; background: var(--brand); color: #fff; border-radius: 11px; padding: 2px 9px; font-size: 11px; font-weight: 700; margin: 0 3px 3px 0; }
.ar-result .miss { color: #999; }
.ar-result b { color: var(--brand); }
tr.ar-custom td { background: #fffdf5; }
tr.ar-custom td:first-child { box-shadow: inset 3px 0 0 #e6b800; }
td .eq-tag { display: inline-block; background: #f0e6e6; color: #7a3a3a; border-radius: 9px; padding: 1px 7px; font-size: 10px; font-weight: 700; margin: 1px 2px 1px 0; }
.match-tag { display: inline-block; background: var(--brand); color: #fff; border-radius: 9px; padding: 1px 7px; font-size: 10px; font-weight: 700; margin-left: 6px; vertical-align: middle; }
.custom-tag { display: inline-block; background: #e6b800; color: #4a3b00; border-radius: 9px; padding: 1px 7px; font-size: 10px; font-weight: 700; margin-left: 6px; vertical-align: middle; }
.equip-chip { display: inline-block; background: var(--brand-tint); color: var(--brand); border: 1px solid var(--brand-tint-border); border-radius: 12px; padding: 4px 11px; font-size: 12px; font-weight: 700; margin: 0 5px 5px 0; }
/* Data-completeness (tier) badges */
.tier { display: inline-block; border-radius: 9px; padding: 1px 7px; font-size: 10px; font-weight: 700; white-space: nowrap; vertical-align: middle; }
.tier-verified { background: #e5f4e5; color: #1f6e1f; border: 1px solid #bfe3bf; }
.tier-ai { background: #eaf0fb; color: #2952a3; border: 1px solid #c3d4f0; }
.tier-general { background: #fff4e0; color: #9a6a00; border: 1px solid #f0d9a8; }
.tier-changed { background: #fdecec; color: #b42318; border: 1px solid #f3c4c0; }
.calc-status { font-size: 12px; line-height: 1.5; padding: 9px 12px; border-radius: 6px; margin-bottom: 10px; }
.calc-status.verified { background: #f0f7f0; color: #1f6e1f; border: 1px solid #cfe6cf; }
.calc-status.ai { background: #eef3fc; color: #274b8f; border: 1px solid #cddbf3; }
.calc-status.general { background: #fff8ec; color: #7a5200; border: 1px solid #f0d9a8; }
.calc-status.changed { background: #fdecec; color: #b42318; border: 1px solid #f3c4c0; }
.calc-status a { color: inherit; text-decoration: underline; }

/* Modal */
.overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.55); z-index: 100; overflow-y: auto; padding: 40px 20px; }
.overlay.open { display: flex; align-items: flex-start; justify-content: center; }
.modal { background: #fff; border-radius: 10px; max-width: 800px; width: 100%; box-shadow: 0 8px 40px rgba(0,0,0,.25); }
.modal-header { background: var(--brand); color: #fff; padding: 16px 22px; border-radius: 10px 10px 0 0; display: flex; flex-direction: column; gap: 9px; }
.mh-row { display: flex; align-items: center; gap: 8px; }
.modal-header h2 { font-size: 17px; line-height: 1.35; font-weight: 700; }
.modal-header .state-badge { font-size: 12px; font-weight: 700; padding: 2px 9px; border-radius: 11px; white-space: nowrap; background: rgba(255,255,255,.18); }
.status-pill { font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 11px; background: rgba(255,255,255,.18); color: #fff; text-transform: uppercase; letter-spacing: .3px; }
.close-btn { margin-left: auto; background: none; border: none; color: rgba(255,255,255,.85); font-size: 20px; cursor: pointer; padding: 0 2px; line-height: 1; }
.close-btn:hover { color: #fff; }
.modal-body { padding: 0; }
/* Hero -- what the program pays, up top */
.hero { display: flex; gap: 16px; align-items: flex-start; padding: 18px 24px; border-bottom: 1px solid #eee; }
.hero-main { flex: 1; min-width: 0; }
.hero-side { text-align: right; flex-shrink: 0; }
.hero-label { font-size: 10px; text-transform: uppercase; letter-spacing: .5px; color: #8a8f98; margin-bottom: 4px; }
.hero-value { font-size: 20px; font-weight: 800; color: #1f6e1f; line-height: 1.25; }
.hero-max { font-size: 14px; font-weight: 600; color: #333; }
@media (max-width: 520px) { .hero { flex-direction: column; gap: 10px; } .hero-side { text-align: left; } }
.section { padding: 18px 24px; border-bottom: 1px solid #eee; }
.section:last-child { border-bottom: none; }
.section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: #6b7280; margin-bottom: 10px; }
.section-body { font-size: 13px; line-height: 1.7; color: #333; white-space: pre-line; }
.notes-box { background: #fff8e1; border-left: 3px solid #e6b800; border-radius: 0 6px 6px 0; padding: 12px 16px; font-size: 12px; color: #555; line-height: 1.6; }
/* Calculation values -- neutral card, green reserved for the numbers themselves */
.calc-panel { background: #fafafa; border: 1px solid #e6e6e6; border-radius: 8px; padding: 2px 0; }
.calc-row { display: grid; grid-template-columns: 175px 1fr; gap: 10px; padding: 9px 16px; border-bottom: 1px solid #eee; }
.calc-row:last-child { border-bottom: none; }
.calc-label { font-size: 11px; text-transform: uppercase; letter-spacing: .4px; color: #888; font-weight: 700; align-self: center; }
.calc-val { font-size: 14px; font-weight: 700; color: #1f6e1f; }
.num { background: #e7f3e7; color: #145214; border-radius: 3px; padding: 0 3px; font-weight: 700; }
@media (max-width: 520px) { .calc-row { grid-template-columns: 1fr; gap: 2px; } }
/* Compact key-facts grid */
.facts { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: #eee; border-bottom: 1px solid #eee; }
.fact { background: #fff; padding: 11px 24px; display: flex; flex-direction: column; gap: 2px; }
.fact-wide { grid-column: 1 / -1; }
.fact-label { font-size: 10px; text-transform: uppercase; letter-spacing: .5px; color: #8a8f98; }
.fact-val { font-size: 13px; font-weight: 600; color: #222; }
@media (max-width: 520px) { .facts { grid-template-columns: 1fr; } .fact-wide { grid-column: auto; } }
/* Applies-to equipment, one compact line */
.equip-line { padding: 13px 24px; border-bottom: 1px solid #eee; font-size: 12px; }
.equip-line-label { font-size: 10px; text-transform: uppercase; letter-spacing: .5px; color: #8a8f98; margin-right: 6px; }
/* Collapsible reference sections -- open compact, expand on demand */
.disc { border-bottom: 1px solid #eee; }
.disc > summary { list-style: none; cursor: pointer; padding: 14px 24px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: #6b7280; display: flex; align-items: center; gap: 8px; }
.disc > summary::-webkit-details-marker { display: none; }
.disc > summary::before { content: '\\25b8'; font-size: 10px; color: #b0b4bb; transition: transform .15s; }
.disc[open] > summary::before { transform: rotate(90deg); }
.disc > summary:hover { color: var(--brand); }
.disc .section-body { padding: 0 24px 18px; }
.example-box { background: #f6f8f6; border-left: 3px solid #9ccc9c; border-radius: 0 6px 6px 0; margin: 0 24px 18px; padding: 14px 16px; font-size: 13px; line-height: 1.7; white-space: pre-line; }
.modal-footer { padding: 16px 24px; background: #f8f9fa; border-radius: 0 0 10px 10px; display: flex; justify-content: space-between; align-items: center; }
.apply-btn { display: inline-block; background: var(--brand); color: #fff; padding: 9px 20px; border-radius: 5px; text-decoration: none; font-size: 13px; font-weight: 600; }
.apply-btn:hover { background: var(--brand-dark); color: #fff; text-decoration: none; }
.last-scraped { font-size: 11px; color: #999; }
</style>
</head>
<body>
<header>
  <div class="header-inner">
    <img class="brand-logo" src=\"""" + logo_uri + """\" alt="UCREW">
    <div class="header-text">
      <h1>Commercial &amp; Industrial Energy Incentives</h1>
      <p>""" + enabled_names + """ &nbsp;|&nbsp; Click any program name for the full calculation breakdown</p>
      <div class="header-badges">
        <span class="hbadge scanned">Last scanned: """ + str(today) + """ &middot; refreshes daily</span>
        <span class="hbadge">""" + str(len(rows)) + """ programs</span>
        <span class="hbadge">Commercial &amp; Industrial facilities only</span>
      </div>
    </div>
  </div>
</header>
<div class="ar-bar">
  <div class="ar-inner">
    <label class="ar-label" for="ar-input">&#128269; Find incentives for a recommendation (AR)</label>
    <div class="ar-row">
      <input type="text" id="ar-input" class="ar-input" autocomplete="off"
             placeholder="Describe the measure, e.g. &quot;Install VFD on compressors&quot; or &quot;Install lighting controls&quot;"
             oninput="applyFilters()">
      <button type="button" class="ar-clear" id="ar-clear" onclick="clearAr()">Clear</button>
    </div>
    <div class="ar-result" id="ar-result"></div>
  </div>
</div>
<div class="controls">
  """ + state_filter_html + """
  <span id="count"></span>
  <div class="legend">
    """ + legend_states_html + """
    <span style="background:#fffde7;border:1px solid #ccc"></span>Paused/Pending
    <span style="background:#fff8e1;border:1px solid #ccc"></span>Expiring Soon
  </div>
</div>
<div class="table-wrap">
<table id="tbl">
<thead><tr>""" + th_cells + """</tr></thead>
<tbody>
""" + "\n".join(rows_html) + """
</tbody>
</table>
</div>

<!-- Detail Modal -->
<div class="overlay" id="overlay" onclick="closeOnOverlay(event)">
<div class="modal" id="modal">
  <div class="modal-header">
    <div class="mh-row">
      <span class="state-badge" id="m-state-badge"></span>
      <span class="status-pill" id="m-status"></span>
      <button class="close-btn" onclick="closeDetail()">&#10005;</button>
    </div>
    <h2 id="m-name"></h2>
  </div>
  <div class="modal-body">
    <!-- Hero: what it pays -->
    <div class="hero">
      <div class="hero-main">
        <div class="hero-label">Incentive</div>
        <div class="hero-value" id="m-value"></div>
      </div>
      <div class="hero-side">
        <div class="hero-label">Max benefit</div>
        <div class="hero-max" id="m-max"></div>
      </div>
    </div>
    <!-- The numbers you work with -->
    <div id="m-calc-section" class="section">
      <div class="section-title">Calculation values</div>
      <div id="m-calc-status"></div>
      <div class="calc-panel" id="m-calc-panel"></div>
    </div>
    <!-- Key facts, compact -->
    <div class="facts">
      <div class="fact"><span class="fact-label">Administrator</span><span class="fact-val" id="m-admin"></span></div>
      <div class="fact"><span class="fact-label">Type</span><span class="fact-val" id="m-type"></span></div>
      <div class="fact"><span class="fact-label">Technology</span><span class="fact-val" id="m-tech"></span></div>
      <div class="fact"><span class="fact-label">Expiration</span><span class="fact-val" id="m-exp"></span></div>
      <div class="fact fact-wide"><span class="fact-label">Eligible recipients</span><span class="fact-val" id="m-recip"></span></div>
    </div>
    <div id="m-equip-section" class="equip-line">
      <span class="equip-line-label">Applies to</span> <span id="m-equip"></span>
    </div>
    <div id="m-notes-section" class="section">
      <div class="notes-box" id="m-notes"></div>
    </div>
    <!-- Reference detail, collapsed by default -->
    <details class="disc" id="d-impl">
      <summary>How to apply</summary>
      <div class="section-body" id="m-implementation"></div>
    </details>
    <details class="disc" id="d-meth">
      <summary>Savings methodology</summary>
      <div class="section-body" id="m-methodology"></div>
    </details>
    <details class="disc" id="d-example">
      <summary>Worked example</summary>
      <div class="example-box" id="m-example"></div>
    </details>
  </div>
  <div class="modal-footer">
    <a class="apply-btn" id="m-apply-link" href="#" target="_blank">Apply / More Info &rarr;</a>
    <span class="last-scraped" id="m-last-scraped"></span>
  </div>
</div>
</div>

<script>
var DETAILS = """ + detail_json + """;
var HTML_COLORS = {"UT":"#4E79A7","MT":"#59A14F","ID":"#F28E2B","NV":"#E15759"};
// Equipment vocabulary -- same map the build step used to tag each program, so a
// typed recommendation resolves to the exact categories the programs carry.
var EQUIP_KEYWORDS = """ + json.dumps(EQUIPMENT_KEYWORDS, ensure_ascii=True) + """;
var CUSTOM_CATEGORIES = """ + json.dumps(sorted(CUSTOM_CATEGORIES), ensure_ascii=True) + """;
var sortCol = -1, sortDir = 1;

// Word-boundary keyword test mirroring the Python classifier: the keyword must
// start at a word boundary, but trailing letters are allowed ("compressor"
// matches "compressors"). Avoids false hits like "led" inside "controlled".
function kwHit(hay, needle) {
  var idx = hay.indexOf(needle);
  while (idx >= 0) {
    var before = idx === 0 ? ' ' : hay.charAt(idx - 1);
    if (!/[a-z0-9]/.test(before)) return true;
    idx = hay.indexOf(needle, idx + 1);
  }
  return false;
}

// Map a free-text assessment recommendation to equipment categories by scanning
// for the same keywords used to tag programs. Custom/whole-facility buckets are
// excluded here -- those surface automatically for every AR, not by keyword.
function arCategories(text) {
  var t = String(text).toLowerCase();
  var cats = [];
  for (var cat in EQUIP_KEYWORDS) {
    if (CUSTOM_CATEGORIES.indexOf(cat) >= 0) continue;
    var kws = EQUIP_KEYWORDS[cat];
    for (var i = 0; i < kws.length; i++) {
      if (kwHit(t, kws[i])) { cats.push(cat); break; }
    }
  }
  return cats;
}

function clearAr() {
  document.getElementById('ar-input').value = '';
  applyFilters();
}

// Escape HTML, then wrap money / % / kWh / therm figures in a highlight span so the
// actual numbers used in calculations stand out inside the prose sections.
function hlNums(text) {
  var esc = String(text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return esc.replace(
    /(\\$[\\d,]+(?:\\.\\d+)?(?:\\/[A-Za-z²]+)?|\\b\\d[\\d,]*(?:\\.\\d+)?\\s?(?:%|kWh|kW|MWh|therms?|sq ?ft|SEER2?|HSPF2?|EER|AFUE|COP|UEF|HDD|CDD)\\b)/g,
    '<span class="num">$1</span>'
  );
}

function openDetail(idx) {
  var d = DETAILS[idx];
  if (!d) return;
  document.getElementById('m-name').textContent = d.name;
  var badge = document.getElementById('m-state-badge');
  badge.textContent = d.state;
  badge.style.background = HTML_COLORS[d.state] || '#888';
  document.getElementById('m-value').textContent = d.value || 'See program';
  document.getElementById('m-max').textContent = d.max || 'See program';
  var statusEl = document.getElementById('m-status');
  statusEl.textContent = d.status;
  statusEl.className = 'status-pill status-' + d.status.toLowerCase().replace(/\\s+/g, '-').replace('temporarily-', '');
  document.getElementById('m-type').textContent = d.type;
  document.getElementById('m-tech').textContent = d.tech;
  document.getElementById('m-admin').textContent = d.admin;
  document.getElementById('m-recip').textContent = d.recipients;
  document.getElementById('m-exp').textContent = d.expiration || 'Ongoing';
  var notesSection = document.getElementById('m-notes-section');
  var notesEl = document.getElementById('m-notes');
  if (d.notes) {
    notesEl.textContent = d.notes;
    notesSection.style.display = '';
  } else {
    notesSection.style.display = 'none';
  }
  // Equipment categories this program applies to (auto-classified)
  var equipSection = document.getElementById('m-equip-section');
  var equip = d.equipment || [];
  if (equip.length) {
    document.getElementById('m-equip').innerHTML = equip.map(function(c) {
      return '<span class="equip-chip">' + escHtml(c) + '</span>';
    }).join(' ');
    equipSection.style.display = '';
  } else {
    equipSection.style.display = 'none';
  }
  // Calculation Values panel -- only rows with a value are shown; hide panel if all blank
  var calcFields = [
    ['Incentive rate', d.rate],
    ['Rebate tiers', d.tiers],
    ['Per-unit / project cap', d.cap],
    ['Baseline assumption', d.baseline],
    ['Minimum project size', d.minProject],
  ];
  var calcPanel = document.getElementById('m-calc-panel');
  var calcHtml = '';
  for (var i = 0; i < calcFields.length; i++) {
    var label = calcFields[i][0], val = calcFields[i][1];
    if (val) {
      calcHtml += '<div class="calc-row"><div class="calc-label">' + label +
        '</div><div class="calc-val">' + hlNums(val) + '</div></div>';
    }
  }
  // Data-completeness status + tier handling. "changed" hides possibly-stale
  // numbers; "general" shows what we have but flags it as unverified; "detailed"
  // confirms the values were verified from the source.
  var statusEl2 = document.getElementById('m-calc-status');
  var srcLink = d.sourceDoc ? ' <a href="' + escHtml(d.sourceDoc) + '" target="_blank">see source &rarr;</a>' : '';
  var showPanel = !!calcHtml;
  if (d.changed) {
    statusEl2.className = 'calc-status changed';
    statusEl2.innerHTML = '&#9888; The source document changed since this was verified' +
      (d.verified ? ' (' + escHtml(d.verified) + ')' : '') +
      '. Exact values are pending re-verification — confirm with the program administrator.' + srcLink;
    calcPanel.innerHTML = '';
    showPanel = true;   // show the section for the status note even with no rows
  } else if (d.detailLevel === 'detailed' && d.verifiedBy === 'ai') {
    statusEl2.className = 'calc-status ai';
    statusEl2.innerHTML = '&#10003; Values auto-extracted from the rate PDF by AI' +
      (d.verified ? ' (' + escHtml(d.verified) + ')' : '') +
      ' and cross-checked across multiple reads. Machine-read &mdash; confirm against the source before advising clients.' + srcLink;
    calcPanel.innerHTML = calcHtml;
  } else if (d.detailLevel === 'detailed') {
    statusEl2.className = 'calc-status verified';
    statusEl2.innerHTML = '&#10003; Exact values verified' + (d.verified ? ' ' + escHtml(d.verified) : '') +
      ' from the program source.' + srcLink;
    calcPanel.innerHTML = calcHtml;
  } else {
    statusEl2.className = 'calc-status general';
    statusEl2.innerHTML = "This program's incentive isn't a single published rate &mdash; the " +
      'amount is determined case by case (custom, modeled, competitive, or otherwise ' +
      'application-specific). Contact the program administrator or open the program page ' +
      'below for the figure that applies to your project.' + srcLink;
    calcPanel.innerHTML = calcHtml;
    showPanel = true;   // always show so the note is visible
  }
  document.getElementById('m-calc-section').style.display = showPanel ? '' : 'none';

  // Reference sections: fill each collapsible and hide the whole <details> when
  // there's nothing to show, so sparse programs don't sprout empty expanders.
  function fillDisc(discId, bodyId, content, asHtml) {
    var disc = document.getElementById(discId);
    var body = document.getElementById(bodyId);
    if (content) {
      if (asHtml) { body.innerHTML = hlNums(content); } else { body.textContent = content; }
      disc.style.display = '';
    } else {
      disc.style.display = 'none';
      disc.open = false;
    }
  }
  fillDisc('d-impl', 'm-implementation', d.implementation, false);
  fillDisc('d-meth', 'm-methodology', d.methodology, true);
  fillDisc('d-example', 'm-example', d.example, true);
  var applyLink = document.getElementById('m-apply-link');
  applyLink.href = d.url || '#';
  applyLink.style.display = d.url ? '' : 'none';
  document.getElementById('m-last-scraped').textContent = 'Data last verified: ' + d.lastScraped;
  document.getElementById('overlay').classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeDetail() {
  document.getElementById('overlay').classList.remove('open');
  document.body.style.overflow = '';
}

function closeOnOverlay(e) {
  if (e.target === document.getElementById('overlay')) closeDetail();
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeDetail();
});

function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Remove any AR match tag / styling from a row (called every pass so tags never stack).
function annotateRow(row, arActive, overlap, isCustom) {
  var cell = row.cells[1];
  var old = cell.querySelector('.match-tag, .custom-tag');
  if (old) old.remove();
  row.classList.remove('ar-custom');
  if (!arActive) return;
  // Custom / whole-facility programs are labelled as such even when they also
  // overlap, so specific prescriptive measures (red "match" tag) stand apart.
  if (isCustom) {
    var c = document.createElement('span');
    c.className = 'custom-tag';
    c.textContent = 'custom / whole-facility';
    cell.appendChild(c);
    row.classList.add('ar-custom');
  } else if (overlap.length > 0) {
    var s = document.createElement('span');
    s.className = 'match-tag';
    s.textContent = 'match: ' + overlap.join(', ');
    cell.appendChild(s);
  }
}

// When an AR is active, float the best matches to the top: specific equipment
// matches first (most overlap first), then custom/whole-facility, expired last.
function reorderForAr() {
  var tbody = document.querySelector('#tbl tbody');
  var rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort(function(a, b) {
    // 0 = specific prescriptive match, 1 = custom/whole-facility, 2 = other.
    // Custom outranks-to-bucket-1 even if it overlaps, so exact measures lead.
    function grp(r) { return (r._arSpecific && !r._arCustom) ? 0 : (r._arCustom ? 1 : 2); }
    var ga = grp(a), gb = grp(b);
    if (ga !== gb) return ga - gb;
    if (a._expired !== b._expired) return a._expired ? 1 : -1;
    if (b._arScore !== a._arScore) return b._arScore - a._arScore;
    if (b._arTextScore !== a._arTextScore) return b._arTextScore - a._arTextScore;
    return a.cells[1].textContent.localeCompare(b.cells[1].textContent);
  });
  rows.forEach(function(r) { tbody.appendChild(r); });
  document.querySelectorAll('th').forEach(function(th) { th.className = ''; });
  sortCol = -1;
}

function renderArBanner(arActive, arText, arCats, specificCount, customCount) {
  var el = document.getElementById('ar-result');
  if (!arActive) { el.innerHTML = ''; return; }
  if (arCats.length === 0) {
    el.innerHTML = 'No specific equipment recognized in <b>&ldquo;' + escHtml(arText) +
      '&rdquo;</b>. Showing custom / whole-facility programs that can cover most measures, plus any text matches. ' +
      'Try naming the equipment &mdash; compressor, lighting, boiler, motor/VFD, fan, pump, refrigeration&hellip;';
    return;
  }
  var chips = arCats.map(function(c) { return '<span class="eq-chip">' + c + '</span>'; }).join(' ');
  var msg = 'Matched equipment: ' + chips + ' &mdash; <b>' + specificCount + '</b> targeted incentive' +
    (specificCount === 1 ? '' : 's');
  if (customCount > 0) {
    msg += ', plus <b>' + customCount + '</b> custom / whole-facility program' +
      (customCount === 1 ? '' : 's') + ' that typically also apply';
  }
  el.innerHTML = msg + '. Best matches are listed first.';
}

function applyFilters() {
  var searchEl = document.getElementById('search');
  var q = searchEl ? searchEl.value.toLowerCase() : '';
  var stateEl = document.getElementById('f-state');
  var state = stateEl ? stateEl.value : '';
  var arText = document.getElementById('ar-input').value.trim();
  var arActive = arText.length > 0;
  var arCats = arActive ? arCategories(arText) : [];
  document.getElementById('ar-clear').style.visibility = arActive ? 'visible' : 'hidden';

  var visible = 0, specificCount = 0, customCount = 0;
  document.querySelectorAll('#tbl tbody tr').forEach(function(row) {
    var text = row.textContent.toLowerCase();
    var idx = row.dataset.idx;
    var d = DETAILS[idx] || {};
    var fullText = text + ' ' + (d.implementation || '').toLowerCase() + ' ' + (d.example || '').toLowerCase();
    var base =
      (!q || fullText.indexOf(q) >= 0) &&
      (!state || row.dataset.state === state);

    var overlap = [];
    var isCustom = row.dataset.custom === '1';
    if (arActive) {
      var eq = (row.dataset.equipment || '').split(';').filter(Boolean);
      overlap = eq.filter(function(c) { return arCats.indexOf(c) >= 0; });
    }
    row._arScore = overlap.length;
    row._arSpecific = overlap.length > 0;
    row._arCustom = isCustom;
    row._expired = row.classList.contains('expired');
    // Secondary relevance: how many AR words actually appear in this program's
    // text. Breaks ties so e.g. the "Wastewater / Aeration" measure leads for an
    // aeration query even though many programs share the Motors & Drives tag.
    if (arActive) {
      var words = arText.toLowerCase().split(/[^a-z0-9]+/).filter(function(w) { return w.length > 2; });
      row._arTextScore = words.reduce(function(n, w) { return n + (fullText.indexOf(w) >= 0 ? 1 : 0); }, 0);
    } else {
      row._arTextScore = 0;
    }

    var arOk = !arActive || overlap.length > 0 || isCustom;
    var match = base && arOk;
    annotateRow(row, arActive, overlap, isCustom);
    row.classList.toggle('hidden', !match);
    if (match) {
      visible++;
      // Count consistently with the ranking buckets: custom is custom even when
      // it overlaps; only non-custom overlaps count as targeted matches.
      if (arActive && isCustom) customCount++;
      else if (arActive && overlap.length > 0) specificCount++;
    }
  });

  if (arActive) reorderForAr();
  document.getElementById('count').textContent = visible + ' programs shown';
  renderArBanner(arActive, arText, arCats, specificCount, customCount);
}

function sortTable(col) {
  var tbody = document.querySelector('#tbl tbody');
  var rows = Array.from(tbody.querySelectorAll('tr'));
  if (sortCol === col) { sortDir *= -1; } else { sortCol = col; sortDir = 1; }
  rows.sort(function(a, b) {
    var av = a.cells[col] ? a.cells[col].textContent.trim() : '';
    var bv = b.cells[col] ? b.cells[col].textContent.trim() : '';
    return av.localeCompare(bv, undefined, {numeric: true}) * sortDir;
  });
  rows.forEach(function(r) { tbody.appendChild(r); });
  document.querySelectorAll('th').forEach(function(th, i) {
    th.className = i === col ? (sortDir === 1 ? 'asc' : 'desc') : '';
  });
}

applyFilters();
</script>
</body>
</html>"""

    HTML_PATH.write_text(html, encoding="utf-8")
    print("HTML: " + str(len(rows)) + " rows written -> " + HTML_PATH.name)


# -- Log ---------------------------------------------------------------------

def _write_log(count):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(datetime.now().isoformat() + " -- " + str(count) + " programs fetched\n")


def _load_scan_state():
    try:
        return json.loads(SCAN_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"programs": {}}


def _save_scan_state(state):
    DATA_DIR.mkdir(exist_ok=True)
    SCAN_STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _apply_change_detection(rows):
    """Compare each detailed program's source-document fingerprint against the
    fingerprint captured when its values were last verified. If they differ, the
    entry is flagged _changed=True and STAYS flagged every run (its exact numbers
    are withheld pending re-verification) until a human re-verifies -- signalled by
    bumping the measure's verified_date in the scraper, which re-baselines here.
    New programs are counted; vanished ones are aged out. Persisted to
    data/scan_state.json so the committing workflow gives a git-diff audit trail."""
    from scrapers.base import fingerprint  # local import: base has only light deps

    state = _load_scan_state()
    progs = state.setdefault("programs", {})
    today = date.today().isoformat()

    # Fingerprint each unique *detailed* source doc once (only detailed entries can
    # meaningfully "change" -- general ones are already pending).
    detailed_urls = {str(r.get("_source_doc") or "") for r in rows
                     if str(r.get("_detail_level")) == "detailed" and r.get("_source_doc")}
    fps = {u: fingerprint(u) for u in detailed_urls if u}

    changed, new = 0, 0
    current_keys = set()
    for r in rows:
        key = str(r.get("_key") or "")
        if not key:
            continue
        current_keys.add(key)
        level = str(r.get("_detail_level") or "general")
        src = str(r.get("_source_doc") or "")
        vdate = str(r.get("_verified_date") or "")
        fp = fps.get(src, "")
        prev = progs.get(key)
        if prev is None:
            new += 1

        entry = dict(prev) if prev else {}
        entry.update({
            "source_doc": src,
            "detail_level": level,
            "last_fingerprint": fp or entry.get("last_fingerprint", ""),
            "first_seen": entry.get("first_seen", today),
            "last_seen": today,
            "missing_runs": 0,
        })

        if level == "detailed":
            # Re-baseline the verified fingerprint on first sight or when a human
            # re-verified (verified_date changed). Otherwise compare against it --
            # a mismatch is a sticky "source changed" until the next re-verify.
            if prev is None or entry.get("verified_date") != vdate:
                entry["verified_date"] = vdate
                entry["verified_fingerprint"] = fp
            else:
                vfp = entry.get("verified_fingerprint", "")
                if vfp and fp and fp != vfp:
                    r["_changed"] = "1"
                    changed += 1
        else:
            entry["verified_date"] = vdate
            entry.pop("verified_fingerprint", None)

        progs[key] = entry

    # Age out programs that vanished from this scan (log only -- no row to display).
    gone = [k for k in progs if k not in current_keys]
    for k in gone:
        progs[k]["missing_runs"] = int(progs[k].get("missing_runs", 0)) + 1

    _save_scan_state(state)
    print("Change detection: " + str(new) + " new, " + str(changed)
          + " source(s) changed since last verified"
          + ((", " + str(len(gone)) + " not seen this run") if gone else "")
          + " -> " + SCAN_STATE_PATH.name)
    return rows


def _load_ai_extractions():
    try:
        return json.loads(AI_EXTRACTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"extractions": {}}


def _save_ai_extractions(cache):
    DATA_DIR.mkdir(exist_ok=True)
    AI_EXTRACTIONS_PATH.write_text(
        json.dumps(cache, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _overlay_ai_fields(row, entry):
    """Apply a cached passing AI extraction onto a row: fill the calc values,
    promote it to a verified 'detailed'/AI row, and clear any 'changed' flag.
    The stored extraction date (not today's) is used so the verified date is
    stable across runs."""
    f = entry["fields"]
    if f.get("value"):
        row["Incentive Value"] = f["value"]
    if f.get("max"):
        row["Max Benefit"] = f["max"]
    row["_incentive_rate"] = f.get("rate", "")
    row["_rebate_tiers"] = f.get("tiers", "")
    row["_unit_cap"] = f.get("cap", "")
    row["_baseline"] = f.get("baseline", "")
    row["_min_project"] = f.get("minp", "")
    if f.get("methodology"):
        row["_methodology"] = f["methodology"]
    ai_note = ("Rate values auto-extracted from the program's rate PDF by Claude ("
               + entry.get("model", "") + ") and confidence-checked (agreed across "
               + str(entry.get("samples", 0)) + " independent reads; sheet effective "
               + (f.get("effective_date") or "n/a") + "). Verify against the source PDF "
               "before advising clients.")
    existing = row.get("Notes", "")
    if f.get("notes"):
        existing = (f["notes"] + "  " + existing).strip()
    row["Notes"] = (ai_note + "  " + existing).strip() if existing else ai_note
    row["_detail_level"] = "detailed"
    row["_verified_by"] = "ai"
    row["_verified_date"] = entry.get("date", "")
    row["_changed"] = ""


def _apply_ai_extraction(rows, persist=True):
    """Passive AI promotion: hand rate PDFs to Claude and overlay the confidence-
    gated result, so new categories and revised sheets get exact numbers without a
    human. Candidacy (only rows whose source_doc is a PDF):
      * 'general' stubs -- AI owns these outright;
      * a human 'detailed' row flagged '_changed' -- its sheet moved, so re-verify;
      * a row the AI already owns (passing cache entry) -- keep it, and re-extract
        only when the PDF's fingerprint moves.
    A human 'detailed' row whose PDF has NOT moved is never touched. Extractions are
    cached by (key, PDF fingerprint) so the API is called only when a PDF actually
    changes; a failed read is cached too, so an unchanged 'not confident' PDF isn't
    retried daily. The whole step is skipped unless INCENTIVES_AI_EXTRACT is on and
    credentials resolve -- so the build is unchanged when AI extraction is disabled."""
    from scrapers import extractor
    from scrapers.base import fingerprint

    cache = _load_ai_extractions()
    entries = cache.setdefault("extractions", {})

    # Candidates: rows backed by a PDF rate sheet.
    def is_pdf(u):
        return bool(u) and u.lower().endswith(".pdf")

    candidates = [r for r in rows if is_pdf(str(r.get("_source_doc") or ""))
                  and str(r.get("_key") or "")]
    if not candidates:
        return rows

    on = extractor.available()
    if not on:
        # Extraction disabled: still overlay any previously-cached passing results
        # whose PDF hasn't changed, so the committed AI data keeps rendering.
        applied = 0
        for r in candidates:
            key = str(r["_key"])
            e = entries.get(key)
            if not e or e.get("confidence") != "pass":
                continue
            fp = fingerprint(str(r["_source_doc"]))
            if fp and fp == e.get("fingerprint") and str(r.get("_verified_by")) != "human":
                _overlay_ai_fields(r, e)
                applied += 1
        if applied:
            print("AI extraction: disabled; re-applied " + str(applied)
                  + " cached result(s) from " + AI_EXTRACTIONS_PATH.name)
        return rows

    print("\nAI extraction: enabled (model " + extractor.MODEL + ", "
          + str(extractor.SAMPLES) + " reads/PDF) -- checking "
          + str(len(candidates)) + " PDF-backed program(s)...")
    promoted = reused = failed = calls = 0
    today = date.today().isoformat()

    for r in candidates:
        key = str(r["_key"])
        src = str(r["_source_doc"])
        level = str(r.get("_detail_level") or "general")
        is_human = str(r.get("_verified_by")) == "human"
        is_changed = bool(str(r.get("_changed") or ""))
        e = entries.get(key)
        fp = fingerprint(src)

        # 1. AI already owns this exact PDF -> overlay from cache, no API call.
        if e and e.get("confidence") == "pass" and fp and fp == e.get("fingerprint"):
            _overlay_ai_fields(r, e)
            reused += 1
            continue
        # 2. This exact PDF was already read and failed the gate -> don't retry.
        if e and e.get("confidence") == "fail" and fp and fp == e.get("fingerprint"):
            r["_ai_note"] = "ai: low confidence -- " + str(e.get("reason", ""))
            failed += 1
            continue
        # 3. Decide whether to (re)extract.
        ai_owned_stale = bool(e and e.get("confidence") == "pass")  # passed before, fp moved
        want = (level != "detailed") or is_changed or ai_owned_stale
        if is_human and not is_changed and not ai_owned_stale:
            continue  # untouched human sheet, unchanged -> leave human values
        if not want:
            continue

        print("  [ai] extracting: " + r.get("Program Name", key))
        calls += 1
        result = extractor.extract_measure(src, r.get("Program Name", ""), r.get("Administrator", ""))
        entry = {
            "confidence": result["confidence"],
            "fingerprint": fp,
            "source_doc": src,
            "date": today,
            "model": extractor.MODEL,
            "samples": result.get("samples", 0),
            "reason": result.get("reason", ""),
        }
        if result["confidence"] == "pass":
            # Preserve the original first-verified date if we already had one.
            if e and e.get("confidence") == "pass" and e.get("date"):
                entry["date"] = today  # a changed PDF is a fresh verification
            entry["fields"] = result["fields"]
            entries[key] = entry
            _overlay_ai_fields(r, entry)
            promoted += 1
            print("    [ai] PASS -- " + result["reason"])
        else:
            entries[key] = entry  # cache the failure (keyed to this fingerprint)
            r["_ai_note"] = "ai: low confidence -- " + result.get("reason", "")
            failed += 1
            print("    [ai] FAIL -- " + result["reason"])

    if persist:
        _save_ai_extractions(cache)
    print("AI extraction: " + str(promoted) + " promoted, " + str(reused)
          + " re-applied from cache, " + str(failed) + " left pending ("
          + str(calls) + " API extraction(s) this run) -> " + AI_EXTRACTIONS_PATH.name)
    return rows


def _ai_smoke_test():
    """One-shot smoke test: run the extractor against a single real rate PDF and
    print the result. Proves the API authenticates and the confidence gate produces
    sane figures, without touching any output file, cache, or the live site. Used by
    `python fetch_incentives.py --ai-smoke`."""
    from scrapers import extractor, rocky_mountain
    print("\n" + "=" * 60)
    print("  AI SMOKE TEST -- one PDF, nothing written")
    print("=" * 60)
    if not extractor.available():
        print("\nExtractor unavailable. Need INCENTIVES_AI_EXTRACT=1, the anthropic")
        print("package, and resolvable ANTHROPIC_API_KEY. Aborting (no API call made).")
        return
    # A known, stable RMP rate sheet with clear prescriptive $/unit figures.
    pdf = rocky_mountain.PDF["compressed_air"]
    name = "wattsmart Business -- Compressed Air System Optimization (calculated)"
    print("\nModel:  " + extractor.MODEL + " (" + str(extractor.SAMPLES) + " reads)")
    print("PDF:    " + pdf + "\n")
    result = extractor.extract_measure(pdf, name, "Rocky Mountain Power", debug=True)

    # Always show what each read produced -- pass or fail -- so the run is never
    # opaque. This is what tells a real rate discrepancy from comparison noise.
    runs = result.get("runs") or []
    for i, run in enumerate(runs, start=1):
        figs = run.get("figures_found") or []
        print("Read " + str(i) + ": confident=" + str(run.get("confident"))
              + " | effective=" + str(run.get("effective_date") or "-")
              + " | $ signature=" + str(list(extractor._sig(figs))))
        print("        figures_found: " + (", ".join(figs) if figs else "(none)"))
    print("")

    print("Verdict: " + result["confidence"].upper() + " -- " + result.get("reason", ""))
    f = result.get("fields")
    if f:
        print("\nExtracted values:")
        print("  value:          " + f.get("value", ""))
        print("  max_benefit:    " + f.get("max", ""))
        print("  incentive_rate: " + f.get("rate", ""))
        print("  tiers:          " + f.get("tiers", ""))
        print("  unit_cap:       " + f.get("cap", ""))
        print("  baseline:       " + f.get("baseline", ""))
        print("  effective_date: " + f.get("effective_date", ""))
        print("  figures_found:  " + ", ".join(f.get("figures", [])))
        print("\nEyeball these against the PDF above. If they match, the pipeline works.")
    else:
        print("\nNo values returned (gate not passed). This is the SAFE failure mode --")
        print("in a real run the row would stay a 'general' stub, not publish a guess.")
        print("(The per-read figures above show why.)")


def _print_ai_dry_run(rows):
    """Preview report for `--ai-dry-run`: list every AI-verified row and its
    extracted figures, without writing outputs or the committed cache."""
    ai_rows = [r for r in rows if str(r.get("_verified_by")) == "ai"]
    print("\n" + "=" * 60)
    print("  AI EXTRACTION DRY RUN -- nothing written")
    print("=" * 60)
    if not ai_rows:
        print("\nNo rows were AI-verified this run. Check that INCENTIVES_AI_EXTRACT=1,")
        print("ANTHROPIC_API_KEY is set, and candidate PDFs exist. See the log above")
        print("for any per-PDF FAIL reasons.")
        return
    print("\n" + str(len(ai_rows)) + " row(s) would be promoted to AI-verified:\n")
    for r in ai_rows:
        print("- " + str(r.get("Program Name", "")))
        print("    key:   " + str(r.get("_key", "")))
        print("    value: " + str(r.get("Incentive Value", "")))
        print("    rate:  " + str(r.get("_incentive_rate", "")))
        if r.get("_rebate_tiers"):
            print("    tiers: " + str(r.get("_rebate_tiers")))
        print("    src:   " + str(r.get("_source_doc", "")))
        print("")
    print("Review these against the source PDFs. To go live, run without --ai-dry-run.")


def _write_needs_data(rows):
    """Write the maintainer worklist: programs that are 'general' (exact values
    pending) or 'changed' (source updated, needs re-verification). This is the
    'ask for a PDF/data' surface -- committed as data/needs_data.md so it shows
    up in git and can be worked through, promoting entries to 'detailed'."""
    pending = []
    for r in rows:
        level = str(r.get("_detail_level") or "general")
        changed = bool(str(r.get("_changed") or ""))
        if level == "detailed" and not changed:
            continue
        ai_note = str(r.get("_ai_note") or "")
        if ai_note:
            reason = ai_note
        elif changed:
            reason = "changed -- re-verify"
        else:
            reason = "general -- values pending"
        pending.append({
            "name": str(r.get("Program Name") or ""),
            "key": str(r.get("_key") or ""),
            "admin": str(r.get("Administrator") or ""),
            "reason": reason,
            "source": str(r.get("_source_doc") or r.get("Application URL") or ""),
        })

    detailed = len(rows) - len(pending)
    print("\nData completeness: " + str(detailed) + " detailed (verified), "
          + str(len(pending)) + " need data (general/changed).")

    DATA_DIR.mkdir(exist_ok=True)
    lines = [
        "# Incentives needing exact data",
        "",
        "Auto-generated each run. These programs are listed with a **general** description "
        "because their exact per-unit values are pending, or their source **changed** and needs "
        "re-verification. Promote one by pasting its source PDF/values to Claude, reviewing the "
        "drafted rate, and committing it as a `detailed` measure (see README).",
        "",
        "_" + str(date.today()) + " -- " + str(detailed) + " detailed, "
        + str(len(pending)) + " pending._",
        "",
    ]
    for p in sorted(pending, key=lambda x: (x["admin"], x["name"])):
        src = (" — [source](" + p["source"] + ")") if p["source"] else ""
        lines.append("- **" + p["name"] + "**  \n  `" + p["key"] + "` · "
                     + p["admin"] + " · _" + p["reason"] + "_" + src)
    NEEDS_DATA_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Needs-data list -> " + str(NEEDS_DATA_PATH))


if __name__ == "__main__":
    import sys
    # --ai-dry-run forces AI extraction on and previews the result without writing
    # any output files or the committed AI cache (for reviewing before it goes live).
    if "--ai-smoke" in sys.argv:
        os.environ["INCENTIVES_AI_EXTRACT"] = "1"
        _ai_smoke_test()
        sys.exit(0)
    dry = "--ai-dry-run" in sys.argv
    if dry:
        os.environ["INCENTIVES_AI_EXTRACT"] = "1"
    main(dry_run_ai=dry)
