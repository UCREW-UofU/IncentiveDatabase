"""
Dominion Energy / Enbridge Gas Utah -- ThermWise Business natural gas efficiency.
Commercial & Industrial programs only (UCREW scope).
Source: dominionenergy.com/utah/save-energy/thermwise
"""
from .base import record, make_key

UTIL = "dominion"
# ThermWise amounts are published as ranges ($0.50-1.00/therm) not exact verified
# rates, so both are "general" until a specific rate schedule/PDF is pulled in.
DETAILED_KEYS = set()

ADMIN = "Dominion Energy / Enbridge Gas Utah"
STATE = "UT"
SECTOR = "Commercial & Industrial"
DOMSAVINGS = "https://www.domsavings.com/"


def fetch_all():
    rows = _business()
    print("  Dominion Energy Utah [UT]: " + str(len(rows)) + " programs")
    return rows


def _business():
    programs = [
        (
            "Pays commercial gas customers per therm saved for custom natural-gas "
            "efficiency projects verified by measurement.",
            "ThermWise Business -- Custom Rebates", "Multiple Technologies",
            "Custom calculation per therm saved", "Custom",
            "$0.50-1.00/therm verified savings",
            "", "", "Existing equipment / billing-data baseline (ASHRAE M&V)", "500 therms/yr savings",
            "Commercial customers on Dominion/Enbridge GS rate schedule in Utah", "Ongoing",
            "Submit project proposal; must demonstrate quantifiable natural gas reduction",
            "1. Contact Dominion Energy commercial team at domsavings.com. 2. Submit project proposal with engineering analysis showing projected therm savings. 3. Await pre-approval (3-5 weeks). 4. Implement approved project. 5. Submit post-installation documentation. 6. Receive rebate based on verified therm savings.",
            "Rebate = verified therm savings/yr x incentive rate (typically $0.50-1.00/therm). Therm savings verified via billing data comparison or ASHRAE Measurement & Verification. Minimum project: 500 therms/yr savings.",
            "Example: A commercial laundry in Draper, UT replaces natural gas boilers with condensing units (96% efficiency vs. 80%). Annual therm savings: 2,400 therms. Rebate: 2,400 x $0.75 = $1,800. New boilers: $18,000 installed. Annual gas savings: 2,400 x $0.85/therm = $2,040. Payback after rebate: ~7.9 years.",
        ),
        (
            "A rebate for replacing an older commercial gas boiler with a "
            "high-efficiency condensing unit (90%+ efficiency).",
            "ThermWise Business -- Gas Boiler Replacement", "HVAC / Boiler",
            "Varies by efficiency gain", "Varies",
            "Prescriptive per therm saved",
            "Condensing boilers >= 90% thermal efficiency qualify", "",
            "Existing boiler thermal efficiency (~80%)", "Pre-approval required",
            "Commercial Dominion Energy / Enbridge customers in Utah", "Ongoing",
            "Pre-approval required; condensing boilers (>= 90% thermal efficiency) qualify",
            "1. Get quotes from licensed commercial HVAC contractors. 2. Submit pre-approval application showing existing and new boiler specs. 3. Install qualifying condensing boiler. 4. Submit final documentation with invoices and thermal efficiency test results.",
            "Savings = (new efficiency - old efficiency) / old efficiency x annual therm consumption x gas rate. Commercial gas rate in Utah: ~$0.80-0.95/therm. Typical upgrade from 80% to 92% thermal efficiency saves ~13% on gas boiler consumption.",
            "Example: A hotel in Salt Lake City replaces two 80% efficiency boilers with 92% condensing units. Annual gas consumption (boilers): 18,000 therms. New consumption: ~15,600 therms. Annual savings: 2,400 therms x $0.88 = $2,112. Estimated rebate: ~$2,400. Boiler cost: $28,000. Payback after rebate: ~12 years.",
        ),
    ]
    rows = []
    for (desc, name, tech, value, max_b, rate, tiers, cap, baseline, minp,
         recip, exp, notes, impl, meth, ex) in programs:
        key = make_key(UTIL, name)
        detailed = key in DETAILED_KEYS
        rows.append(record(
            STATE, name, ADMIN, SECTOR, "Rebate", tech, value, max_b, recip, exp, DOMSAVINGS,
            notes=notes, implementation=impl, methodology=meth, example=ex,
            incentive_rate=rate, rebate_tiers=tiers, unit_cap=cap,
            baseline=baseline, min_project=minp,
            description=desc,
            key=key,
            detail_level=("detailed" if detailed else "general"),
            verified_date="", source_doc=DOMSAVINGS,
        ))
    return rows
