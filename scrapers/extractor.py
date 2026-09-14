"""
Confidence-gated AI extraction of exact incentive rates from utility rate PDFs.

This is what makes the site *passively* self-updating: when the daily scanner sees
a new category with a rate PDF, or a previously verified PDF whose bytes changed,
it hands the PDF to Claude, which extracts the structured calculation values
(incentive rate, tiers, per-unit cap, baseline, minimum project size). The result
is only promoted to a "detailed"/verified row when it clears a confidence gate --
otherwise the row stays a "general" stub, exactly as the manual pipeline left it.

Why a gate (and not raw extraction): the entire value of this site is *exact*
published rates that feed real energy-assessment savings math. A single
transposed digit, a missed tier, or a stale effective date, published unattended,
would be worse than an honest "values pending". So the happy path is passive, but
never blindly trusting:

  * Self-consistency -- the same PDF is extracted N times (default 2). The runs
    must agree on the exact set of dollar/numeric figures found.
  * Required fields -- a headline value AND a per-unit rate must be present.
  * Effective date -- the PDF must yield an effective/revision date, so we never
    promote a sheet we couldn't even locate a date on.
  * Money sanity -- at least one real "$" figure must appear.

Anything that fails the gate is left for a human (it shows up in needs_data.md as
"ai: low confidence"), so the failure mode is "not promoted", never "wrong number
published".

Design notes:
  * Model is Claude (Anthropic SDK, structured outputs). Default claude-opus-5 --
    accuracy-critical, and it runs only when a PDF actually changes (rarely), so
    cost is negligible. Override with INCENTIVES_AI_MODEL.
  * PDFs are sent as native `document` blocks (no OCR needed).
  * This module is import-safe without the `anthropic` package installed or an API
    key set: callers check `available()` first, and every failure degrades to a
    "fail" result rather than raising, so a bad run never breaks the build.
"""
import os
import re
import json
import base64

try:  # anthropic is only needed when extraction is enabled; keep import optional
    import anthropic
except ImportError:  # pragma: no cover - env without the SDK
    anthropic = None

from .base import get

# Default to the most capable model: these are dollar figures a human would
# otherwise verify by hand. Override for cost (e.g. "claude-sonnet-5") via env.
# NB: an unset GitHub Actions *variable* arrives as an empty string, not unset, so
# `or`/isdigit guards are required -- os.environ.get's default only covers absence.
MODEL = os.environ.get("INCENTIVES_AI_MODEL", "").strip() or "claude-opus-5"
# How many independent extractions must agree before a rate is auto-promoted.
_samples = os.environ.get("INCENTIVES_AI_SAMPLES", "").strip()
SAMPLES = int(_samples) if _samples.isdigit() and int(_samples) > 0 else 2

SYSTEM = (
    "You extract exact commercial & industrial energy-efficiency incentive rates "
    "from a utility's official rate PDF, for a database that feeds real energy-audit "
    "savings calculations. Accuracy is paramount.\n"
    "Rules:\n"
    "- Report ONLY figures explicitly printed in this PDF. Never infer, average, or "
    "guess a number that is not on the page.\n"
    "- If a field is not stated in the PDF, return an empty string for it. An honest "
    "blank is always better than an invented value.\n"
    "- Preserve units exactly as printed ($/kWh, $/ton, $/hp, $/sq ft, % of cost, etc.).\n"
    "- 'figures_found' must list every distinct per-unit dollar/percentage amount the "
    "incentive pays, each as printed (e.g. '$0.15/kWh', '$200/hp', '70% of cost'). This "
    "list is used to cross-check the extraction, so be exhaustive and exact.\n"
    "- 'effective_date' is the effective/revised/version date printed on the sheet "
    "(ISO YYYY-MM-DD if possible). Empty string if the PDF shows no date.\n"
    "- Set 'confident' false if the PDF is unclear, scanned/garbled, not actually a "
    "rate sheet, or you had to strain to read the numbers."
)

# Structured-output schema: mirrors the measure fields the site renders in its
# "Calculation Values" panel, plus the cross-check metadata the gate needs.
SCHEMA = {
    "type": "object",
    "properties": {
        "value": {"type": "string", "description": "Headline incentive value, concise (e.g. '$0.15/kWh of annual savings')"},
        "max_benefit": {"type": "string", "description": "Max benefit / project cap (e.g. '70% of project cost')"},
        "incentive_rate": {"type": "string", "description": "Full per-unit rate description, all tiers/measures in prose"},
        "rebate_tiers": {"type": "string", "description": "Tiered amounts if any, else empty"},
        "unit_cap": {"type": "string", "description": "Per-unit or per-project cap"},
        "baseline": {"type": "string", "description": "Baseline / eligibility assumption the rate is measured against"},
        "min_project": {"type": "string", "description": "Minimum project size / qualifying threshold"},
        "methodology": {"type": "string", "description": "One or two sentences: how the incentive is calculated"},
        "notes": {"type": "string", "description": "Key eligibility caveats printed on the sheet"},
        "effective_date": {"type": "string", "description": "Effective/revision date on the sheet, ISO if possible, else ''"},
        "figures_found": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Every distinct per-unit dollar/percent amount the incentive pays, each exactly as printed",
        },
        "confident": {"type": "boolean", "description": "False if the PDF was unclear or not a usable rate sheet"},
        "confidence_note": {"type": "string", "description": "Brief reason for the confidence judgement"},
    },
    "required": [
        "value", "max_benefit", "incentive_rate", "rebate_tiers", "unit_cap",
        "baseline", "min_project", "methodology", "notes", "effective_date",
        "figures_found", "confident", "confidence_note",
    ],
    "additionalProperties": False,
}


def available():
    """True when AI extraction can actually run (opt-in flag + SDK + credentials).
    Callers gate on this so the build works unchanged when extraction is off."""
    if os.environ.get("INCENTIVES_AI_EXTRACT", "").lower() not in ("1", "true", "yes", "on"):
        return False
    if anthropic is None:
        return False
    # SDK resolves ANTHROPIC_API_KEY (or an `ant auth login` profile); a bare
    # client construction is cheap and confirms creds are resolvable.
    try:
        anthropic.Anthropic()
    except Exception:
        return False
    return True


# Match a dollar amount specifically ($0.15, $2, $1,500, $ 200) -- the per-unit
# *rate* the incentive pays. We deliberately do NOT match bare numbers: rate sheets
# are full of eligibility thresholds (25-75 hp, <=500 scfm, 2 gal/scfm) and percent
# caps (70% of cost) that two reads categorize inconsistently and that are not the
# rate. Comparing only the paid dollar amounts is the thing that must be exact.
_MONEY = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")


def _sig(figures):
    """Normalized dollar-amount signature of a 'figures_found' list: the sorted
    multiset of $ amounts it mentions, order-independent. Two extractions with the
    same signature agree on every per-unit rate paid (thresholds/caps/formatting
    aside). A real transposition ($6/hp vs $8/hp) still changes the signature."""
    amounts = []
    for f in figures or []:
        for m in _MONEY.findall(str(f)):
            amounts.append(m.replace(",", ""))
    return tuple(sorted(amounts, key=lambda x: (float(x), x)))


def _download_pdf_b64(url):
    """Fetch a PDF and return base64 (no newlines), or None on any failure."""
    try:
        resp = get(url, timeout=30)
    except Exception as exc:
        print("    [ai] PDF download failed: " + str(exc))
        return None
    ctype = resp.headers.get("Content-Type", "").lower()
    if "pdf" not in ctype and not url.lower().endswith(".pdf"):
        print("    [ai] source is not a PDF (" + ctype + "); skipping")
        return None
    return base64.standard_b64encode(resp.content).decode("ascii")


def _extract_once(client, pdf_b64, program_name, admin):
    """One structured extraction pass. Returns the parsed dict, or None on error."""
    prompt = (
        "Program: " + program_name + "\nAdministrator: " + admin + "\n\n"
        "Extract this incentive's exact calculation values from the attached rate PDF, "
        "following the schema. Report only what is printed."
    )
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "document", "source": {
                        "type": "base64", "media_type": "application/pdf", "data": pdf_b64,
                    }},
                    {"type": "text", "text": prompt},
                ],
            }],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
    except Exception as exc:
        print("    [ai] API call failed: " + str(exc))
        return None
    try:
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)
    except (StopIteration, ValueError) as exc:
        print("    [ai] could not parse response: " + str(exc))
        return None


def extract_measure(source_doc, program_name, admin, debug=False):
    """Extract + confidence-gate one incentive's rates from its source PDF.

    Returns a dict:
      {"confidence": "pass"|"fail", "reason": str, "fields": {...}|None, "samples": int}
    'fields' (on pass) carries the measure-shaped values ready to overlay onto a row.
    With debug=True, a "runs" list of the raw per-read extractions is attached to the
    result (used by the smoke test to show exactly what each read produced).
    Never raises -- any failure returns a "fail" result so the build continues.
    """
    _runs_seen = []

    def fail(reason):
        res = {"confidence": "fail", "reason": reason, "fields": None, "samples": len(_runs_seen)}
        if debug:
            res["runs"] = _runs_seen
        return res

    if anthropic is None:
        return fail("anthropic SDK not installed")
    pdf_b64 = _download_pdf_b64(source_doc)
    if not pdf_b64:
        return fail("PDF unavailable or not a PDF")

    try:
        client = anthropic.Anthropic()
    except Exception as exc:
        return fail("no API credentials: " + str(exc))

    runs = _runs_seen
    for i in range(max(1, SAMPLES)):
        r = _extract_once(client, pdf_b64, program_name, admin)
        if r is not None:
            runs.append(r)
    if len(runs) < max(1, SAMPLES):
        return fail("only " + str(len(runs)) + "/" + str(SAMPLES) + " extraction passes succeeded")

    # --- Confidence gate -----------------------------------------------------
    # 1. Every pass must self-report confidence.
    if not all(r.get("confident") for r in runs):
        note = next((r.get("confidence_note", "") for r in runs if not r.get("confident")), "")
        return fail("model not confident: " + note)

    # 2. Self-consistency: all passes must agree on the exact set of figures.
    sigs = {_sig(r.get("figures_found")) for r in runs}
    if len(sigs) != 1:
        res = fail("extractions disagreed on the figures across " + str(len(runs)) + " passes")
        # Attach each run's figures so a caller (e.g. the smoke test) can show what
        # actually differed instead of guessing.
        res["figures_by_run"] = [list(r.get("figures_found") or []) for r in runs]
        return res
    signature = next(iter(sigs))
    if not signature:
        return fail("no numeric figures found in the PDF")

    # Use the first passing run as the canonical values (all agree on figures).
    r = runs[0]

    # 3. Required headline fields present.
    if not (r.get("value") or "").strip() or not (r.get("incentive_rate") or "").strip():
        return fail("missing headline value or rate")

    # 4. An effective date must have been located on the sheet.
    if not (r.get("effective_date") or "").strip():
        return fail("no effective date found on the sheet")

    # 5. Money sanity: at least one printed dollar figure.
    if not any("$" in str(f) for f in r.get("figures_found", [])):
        return fail("no dollar figure among the extracted amounts")

    fields = {
        "value": r["value"].strip(),
        "max": (r.get("max_benefit") or "").strip(),
        "rate": r["incentive_rate"].strip(),
        "tiers": (r.get("rebate_tiers") or "").strip(),
        "cap": (r.get("unit_cap") or "").strip(),
        "baseline": (r.get("baseline") or "").strip(),
        "minp": (r.get("min_project") or "").strip(),
        "methodology": (r.get("methodology") or "").strip(),
        "notes": (r.get("notes") or "").strip(),
        "effective_date": r["effective_date"].strip(),
        "figures": list(r.get("figures_found") or []),
    }
    res = {
        "confidence": "pass",
        "reason": "agreed across " + str(len(runs)) + " passes; " + str(len(signature)) + " $ amounts",
        "fields": fields,
        "samples": len(runs),
    }
    if debug:
        res["runs"] = runs
    return res
