"""
Federal C&I incentives that apply in every state (so they show up for Utah too).

These are the high-value, relatively stable federal programs a commercial or
industrial facility can stack on top of utility rebates -- most importantly the
Investment Tax Credit, which for a battery purchase is usually the largest single
incentive (30% of installed cost). DSIRE would normally be the automated source
for these, but its API now returns 403 and its pages render program data via
client-side JS, so it cannot be scraped reliably. These are curated from the
authoritative federal sources linked per program; the daily scanner still runs
and auto-expires anything past its date. Tax law changes -- verify current terms.
"""
from .base import record, make_key

UTIL = "federal"
VERIFIED_DATE = "2026-07-31"
# ITC rates (30%) are verified from primary sources; the others (MACRS mechanism,
# 179D inflation-indexed amount, REAP grant share) vary or are indexed -> general.
DETAILED_KEYS = {
    "federal:battery-storage-section-48e",
    "federal:solar-pv-section-48e",
}

ADMIN_IRS = "U.S. Federal (IRS)"
ADMIN_USDA = "U.S. Federal (USDA Rural Development)"
SECTOR = "Commercial & Industrial"
RECIP = "U.S. commercial, industrial, and agricultural taxpayers/businesses"

# Each dict is one federal program. Applied to every enabled state.
PROGRAMS = [
    {
        "name": "Federal Investment Tax Credit -- Battery Storage (Section 48E)",
        "desc": "A 30% federal tax credit on the installed cost of commercial battery storage "
                "-- usually the largest single incentive when buying a battery.",
        "type": "Tax Credit",
        "tech": "Energy Storage / Battery",
        "value": "30% of installed cost",
        "max": "No cap (credit = 30%+ of cost)",
        "rate": "30% base Investment Tax Credit on total installed cost (equipment, labor, permitting)",
        "baseline": "Standalone or paired battery energy storage >=3 kWh (commercial/business-owned)",
        "minp": "Battery capacity >=3 kWh; business/commercial owner",
        "url": "https://www.irs.gov/credits-deductions/clean-electricity-investment-credit",
        "notes": "Section 48E Clean Electricity Investment Credit. Standalone or solar-paired storage >=3 kWh "
                 "qualifies at a 30% base rate, through 2032 before phase-down (26% in 2033, 22% in 2034). "
                 "Domestic-content, energy-community, and low-income adders can raise it above 30%. Stacks on "
                 "top of utility programs. Confirm current eligibility with a tax advisor.",
        "impl": "1. Confirm the battery is business-owned and >=3 kWh. 2. Install the qualifying system. "
                "3. Document installed cost (equipment, labor, permitting) and any bonus-credit qualifications. "
                "4. Claim the credit on the business's federal return (Form 3468). 5. Consider stacking with "
                "MACRS depreciation and any utility battery incentive.",
        "meth": "Credit = 30% x total installed cost (base rate). Adders: +10% domestic content, +10% energy "
                "community, plus low-income bonuses on smaller systems. Battery must be >=3 kWh.",
        "example": "Example: A Utah manufacturer installs a $400,000, 250 kWh commercial battery. Base ITC: "
                   "0.30 x $400,000 = $120,000 federal tax credit. Stacking MACRS depreciation and the Rocky "
                   "Mountain Power wattsmart Battery incentive further reduces net cost.",
    },
    {
        "name": "Federal Investment Tax Credit -- Solar PV (Section 48E)",
        "desc": "A 30% federal tax credit on the installed cost of a commercial solar PV system.",
        "type": "Tax Credit",
        "tech": "Solar PV",
        "value": "30% of installed cost",
        "max": "No cap (credit = 30%+ of cost)",
        "rate": "30% base Investment Tax Credit on total installed solar cost",
        "baseline": "Commercial/business-owned solar photovoltaic system",
        "minp": "Business/commercial owner; begin-construction timing rules apply",
        "url": "https://www.irs.gov/credits-deductions/clean-electricity-investment-credit",
        "notes": "Section 48E Clean Electricity Investment Credit, 30% base, with domestic-content / "
                 "energy-community / low-income adders. Begin-construction timing rules apply after the 2025 "
                 "federal changes -- confirm deadlines with a tax advisor. Pairs with battery storage (also "
                 "30%) and MACRS depreciation.",
        "impl": "1. Size the PV system and confirm commercial ownership. 2. Track begin-construction date and "
                "domestic-content/energy-community status. 3. Install. 4. Claim on Form 3468. 5. Stack with "
                "MACRS depreciation.",
        "meth": "Credit = 30% x installed cost (base), plus adders. Applies to equipment, labor, and interconnection.",
        "example": "Example: A 200 kW rooftop PV system at $1.60/W costs ~$320,000. Base ITC: 0.30 x $320,000 = "
                   "$96,000, before any domestic-content or energy-community adders.",
    },
    {
        "name": "MACRS + Bonus Depreciation (Energy Property)",
        "desc": "Lets a business write off solar, storage, and other energy equipment over just "
                "five years, cutting its tax bill on top of the ITC.",
        "type": "Tax Deduction (Depreciation)",
        "tech": "Multiple Technologies",
        "value": "Accelerated 5-year depreciation of energy property",
        "max": "Depends on system cost and tax rate",
        "rate": "5-year MACRS accelerated depreciation on eligible energy property basis",
        "baseline": "Depreciable basis = installed cost less one-half of any ITC claimed",
        "minp": "Business-owned depreciable energy property (solar, storage, efficient equipment)",
        "url": "https://www.irs.gov/forms-pubs/about-publication-946",
        "notes": "Depreciate qualifying energy property over 5 years (plus any bonus depreciation per current "
                 "law). The depreciable basis is reduced by half the ITC claimed. Frequently stacked with the "
                 "ITC to cut a battery or solar project's net cost by another ~20-25%. Confirm the current "
                 "bonus percentage with a tax advisor.",
        "impl": "1. Determine depreciable basis (installed cost minus half the ITC). 2. Apply 5-year MACRS "
                "(plus any bonus depreciation) on the business return. 3. Coordinate with a tax advisor to "
                "stack with the ITC.",
        "meth": "Depreciable basis = cost - 0.5 x ITC. Deduct over the 5-year MACRS schedule (plus bonus). Tax "
                "benefit = basis x depreciation schedule x tax rate.",
        "example": "Example: On a $400,000 battery with a $120,000 ITC, depreciable basis = $400,000 - $60,000 = "
                   "$340,000. At a 21% federal rate, MACRS deductions are worth ~$71,000 over time -- on top of "
                   "the ITC.",
    },
    {
        "name": "179D Energy Efficient Commercial Buildings Deduction",
        "desc": "A per-square-foot federal tax deduction for energy-efficient lighting, HVAC, "
                "and envelope upgrades in commercial buildings.",
        "type": "Tax Deduction",
        "tech": "HVAC / Lighting / Envelope",
        "value": "Up to ~$5.81/sq ft (2025, inflation-indexed)",
        "max": "Per-sq-ft deduction scaled by efficiency and prevailing-wage compliance",
        "rate": "Sliding per-sq-ft deduction for efficient lighting, HVAC, and envelope in commercial buildings",
        "baseline": "ASHRAE 90.1 reference building; % energy-cost reduction determines the rate",
        "minp": "Commercial building (or tax-exempt building via allocation to the designer)",
        "url": "https://www.energy.gov/eere/buildings/179d-commercial-buildings-energy-efficiency-tax-deduction",
        "notes": "The per-square-foot deduction scales with modeled energy savings and whether prevailing-wage "
                 "/ apprenticeship requirements are met (higher tier). Amounts are inflation-indexed annually -- "
                 "confirm the current-year figure. Applies to new construction and major retrofits.",
        "impl": "1. Model the building's energy-cost savings vs. ASHRAE 90.1. 2. Obtain the required third-party "
                "certification. 3. Claim the per-sq-ft deduction on the business return (designers of tax-exempt "
                "buildings may receive an allocation).",
        "meth": "Deduction ($/sq ft) increases with modeled energy-cost reduction and prevailing-wage compliance, "
                "applied to conditioned floor area.",
        "example": "Example: A 100,000 sq ft office achieves a qualifying efficiency improvement and meets "
                   "prevailing-wage rules; at a representative $3.00/sq ft the deduction is ~$300,000 -- confirm "
                   "the current-year rate and tier.",
    },
    {
        "name": "USDA REAP -- Rural Energy for America Program",
        "desc": "USDA grants and loan guarantees that help rural businesses and farms pay for "
                "renewable energy and efficiency projects.",
        "type": "Grant + Loan Guarantee",
        "tech": "Multiple Technologies",
        "value": "Grants up to 50% of cost (historically 25%); loan guarantees",
        "max": "Renewable energy grant up to $1,000,000; efficiency grant up to $500,000",
        "rate": "Grant covering a share of project cost (renewable systems and efficiency improvements) + loan guarantees",
        "baseline": "Eligible rural small business or agricultural producer",
        "minp": "Rural small business or ag producer; project in an eligible rural area",
        "url": "https://www.rd.usda.gov/programs-services/energy-programs/rural-energy-america-program-renewable-energy-systems-energy-efficiency-improvement-guaranteed-loans",
        "notes": "Covers renewable energy (solar, wind, storage, biogas) and efficiency (VFDs, lighting, HVAC, "
                 "grain dryers, irrigation, refrigeration). Much of Utah qualifies as rural. Grant share and "
                 "caps are set by current funding rounds -- confirm the percentage and application window. "
                 "Stacks with the federal ITC and utility rebates.",
        "impl": "1. Confirm rural eligibility (address check on USDA's map) and business/ag-producer status. "
                "2. Obtain an energy assessment/audit for efficiency projects. 3. Apply through USDA Rural "
                "Development during an open window. 4. If awarded, install and submit for reimbursement. "
                "5. Stack with the ITC and any utility incentive.",
        "meth": "Grant = eligible share of total project cost (up to the program cap); loan guarantees available "
                "for larger projects. Combine with ITC (30%) and utility rebates for very low net cost.",
        "example": "Example: A rural Utah dairy installs $200,000 of VFDs, efficient refrigeration, and solar. "
                   "A REAP grant covers a portion of the cost; the solar/storage portion also earns the 30% ITC, "
                   "and Rocky Mountain Power rebates apply to the efficiency measures.",
    },
]


def fetch_all(states=None):
    """Return curated federal C&I incentives for each requested state (federal
    programs apply everywhere, so they are emitted per enabled state)."""
    states = states or ["UT"]
    rows = []
    for state in states:
        for p in PROGRAMS:
            key = make_key(UTIL, p["name"])
            detailed = key in DETAILED_KEYS
            rows.append(record(
                state, p["name"], _admin(p), SECTOR, p["type"], p["tech"],
                p["value"], p["max"], RECIP, "Ongoing", p["url"],
                notes=p["notes"], implementation=p["impl"], methodology=p["meth"],
                example=p["example"], incentive_rate=p["rate"],
                baseline=p["baseline"], min_project=p["minp"],
                description=p.get("desc", ""),
                key=key,
                detail_level=("detailed" if detailed else "general"),
                verified_date=(VERIFIED_DATE if detailed else ""),
                verified_by=("human" if detailed else ""),
                source_doc=p["url"],
            ))
    print("  Federal (IRS/USDA): " + str(len(PROGRAMS)) + " programs x " + str(len(states)) + " state(s)")
    return rows


def _admin(p):
    return ADMIN_USDA if "USDA" in p["name"] else ADMIN_IRS
