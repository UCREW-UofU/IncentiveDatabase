"""
Rocky Mountain Power (PacifiCorp) -- Utah wattsmart(R) Business incentives.
Commercial & Industrial energy efficiency only (UCREW scope).

Accuracy note: rather than one broad "custom" bucket, measures are broken out to
the granularity RMP actually publishes, with the exact rate for each. RMP posts
its Utah incentive amounts in per-category pages/PDFs (linked per measure below);
the daily scanner keeps the pages live-checked and auto-expires stale ones. When
RMP revises a rate, update the matching entry here.

Sources:
  Incentive lists (all categories): .../ut-incentive-lists.html
  Compressed air:                   .../ut-incentive-lists/ut-compressed-air.html
  Motors & drives:                  .../ut-incentive-lists/ut-motors-drives.html
  HVAC:                             .../ut-incentive-lists/ut-hvac.html
"""
from .base import record, make_key

UTIL = "rmp"
# Measures with an exact, human-verified rate (everything else is "general" --
# a real category, but the exact per-unit amount is still pending a PDF/data pull).
VERIFIED_DATE = "2026-07-31"  # default verified date; a measure may override with its own "verified"
DETAILED_KEYS = {
    "rmp:vfd-air-compressor-75-hp",
    "rmp:compressed-air-system-optimization-calculated",
    "rmp:express-lighting-retrofit-prescriptive-per-watt-installed",
    "rmp:calculated-lighting-system-retrofit-non-prescriptive-per-watt-reduced",
    "rmp:hvac-heat-pump",
    "rmp:motors-vfds-pumps-fans",
    "rmp:appliances-office-equipment",
    "rmp:commercial-food-service-equipment",
    "rmp:building-envelope-insulation-cool-roof",
    "rmp:wastewater-other-refrigeration",
    "rmp:oil-gas-field-efficiency",
    "rmp:irrigation-sprinklers-nozzles-pump-vfd",
    "rmp:farm-dairy-equipment",
}

BASE = "https://www.rockymountainpower.net"
BIZ = BASE + "/savings-energy-choices/business/wattsmart-efficiency-incentives-utah"
LISTS = BIZ + "/ut-incentive-lists"
ADMIN = "Rocky Mountain Power"
STATE = "UT"
SECTOR = "Commercial & Industrial"
RECIP = "Commercial & industrial Rocky Mountain Power customers in Utah"

# Authoritative per-category incentive pages (published rates live in their PDFs).
# Each measure points its source at one of these; scrapers/discovery.py treats a
# category as "covered" when some measure's source URL matches it.
URL = {
    "lighting": LISTS + "/ut-lighting.html",
    "hvac": LISTS + "/ut-hvac.html",
    "motors": LISTS + "/ut-motors-drives.html",
    "foodservice": LISTS + "/ut-foodservice.html",
    "compressed_air": LISTS + "/ut-compressed-air.html",
    "envelope": LISTS + "/ut-building-envelope.html",
    "appliances": LISTS + "/ut-appliances-office.html",
    "agriculture": BIZ + "/ut-agriculture.html",
    "wbnc": LISTS + "/wbnc.html",
    "wastewater": LISTS + "/ut-wastewater-other-refrigeration.html",
    "oil_gas": LISTS + "/ut-oil-gas.html",
    "lists": LISTS + ".html",
    "business": BIZ + ".html",
    "battery": BASE + "/savings-energy-choices/wattsmart-battery-program.html",
}

# Authoritative rate PDFs (the numbers live here, not in the HTML page above).
# Used as source_doc for change detection -- a rate revision changes the PDF's bytes.
PDF = {
    "lighting_express": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                               "wattsmart-business/utah/UT_Wattsmart_Business_Express_Lighting_Retrofits_Incentives.pdf",
    "lighting_calc": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                            "wattsmart-business/utah/UT_Wattsmart_Business_Lighting_System_Retrofits_Incentives.pdf",
    "compressed_air": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                             "wattsmart-business/utah/UT_Wattsmart_Business_Compressed_Air_Incentives.pdf",
    "hvac": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                   "wattsmart-business/utah/UT_wattsmart_Business_HVAC_Equipment_Incentives.pdf",
    "motors": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                     "wattsmart-business/utah/UT_Wattsmart_Business_Motors_Incentives.pdf",
    "appliances": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                         "wattsmart-business/utah/UT_Wattsmart_Business_Appliances_OtherEquip_Incentives.pdf",
    "foodservice": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                          "wattsmart-business/utah/UT_Wattsmart_Business_Food_Services_Equipment_Incentives.pdf",
    "envelope": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                       "wattsmart-business/utah/UT_Wattsmart_Business_Building_Envelope_Retrofits_Incentives.pdf",
    "wastewater": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                         "wattsmart-business/utah/UT_Wattsmart_Business_WasteWaterRefrigeration_Incentives.pdf",
    "oil_gas": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                      "wattsmart-business/utah/UT_Wattsmart_Business_Oil_Gas_Incentives.pdf",
    "irrigation": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                         "wattsmart-business/utah/UT_Wattsmart_Business_Water_Distribution_Irrigation_Incentives.pdf",
    "farm_dairy": BASE + "/content/dam/pcorp/documents/en/rockymountainpower/savings-energy-choices/"
                         "wattsmart-business/utah/UT_Wattsmart_Business_Farm_Dairy_Equipment_Incentives.pdf",
}

# RMP's lighting calculator tool -- qualified make/model numbers are entered here to
# compute the watts the incentive is paid on. The tool reports Actual and Stipulated
# savings; the INCENTIVE is paid on the STIPULATED wattage (industry-standard practice),
# not the actual measured wattage. Accessed via the wattsmart Business trade-ally portal.
LIGHTING_CALCULATOR = "https://wattsmartbusiness.com/trade-ally-resources/"
LIGHTING_CALCULATOR_NOTE = (
    "Where to calculate: RMP's wattsmart Business Lighting Calculator Tool (via the "
    "trade-ally portal at wattsmartbusiness.com/trade-ally-resources, or ask RMP at "
    "WattsmartBusiness@RockyMountainPower.net / 385-300-0150). Enter each qualified "
    "make/model; the tool returns the Stipulated wattage the incentive is paid on "
    "(incentives pay on Stipulated, not Actual, savings)."
)

def fetch_all():
    rows = _measures()
    print("  Rocky Mountain Power [UT]: " + str(len(rows)) + " programs")
    return rows
    # Coverage gaps are now surfaced by scrapers/discovery.py, which adds any
    # uncovered category as a 'general' entry (not just a warning).


# Each dict is one measure. Keep names specific ("VFD Air Compressor (<=75 hp)")
# so the AR Finder matches them precisely and shows the right rate. Rates that RMP
# calculates from an engineering estimate are still exact per-kWh figures -- the
# *rate* is fixed, only the annual-kWh input varies.
MEASURES = [
    # ---- Compressed air (rate confirmed from the RMP wattsmart application) ----
    {
        "name": "wattsmart Business -- VFD Air Compressor (<=75 hp)",
        "tech": "Compressed Air / VFD",
        "value": "$0.15/kWh of annual energy savings",
        "max": "By estimated annual savings",
        "rate": "$0.15 per kWh of annual energy savings (savings estimated by Rocky Mountain Power)",
        "tiers": "",
        "cap": "",
        "cap": "70% of energy-efficiency project cost; cannot reduce simple payback below 1 year",
        "baseline": "Total system compressor capacity <=75 hp (all compressors combined, excluding backup)",
        "minp": "VFD must be the primary means of capacity control; savings estimate subject to RMP approval",
        "url": URL["compressed_air"],
        "source_doc": PDF["compressed_air"],
        "verified": "2026-08-31",
        "notes": "Incentive is paid at $0.15 per kWh of annual energy savings. Program staff provide "
                 "the energy savings estimate; subject to Rocky Mountain Power approval. Qualifying unit "
                 "is a variable-frequency-drive oil-injected screw compressor in a system of <=75 hp total "
                 "(all compressors combined, not counting backup capacity) that adjusts speed as the "
                 "primary means of capacity control.",
        "impl": "1. Get an incentive application package from Rocky Mountain Power (1-866-870-3419) or a "
                "wattsmart Business Trade Ally. 2. Confirm the system qualifies (<=75 hp total, VFD primary "
                "capacity control). 3. Purchase and install the qualifying VFD screw compressor. 4. Submit "
                "the application package with IRS Form W-9. 5. Program staff estimate annual kWh savings and "
                "approve. 6. Receive incentive check (typically within 45 days).",
        "meth": "Incentive = estimated annual energy savings (kWh) x $0.15/kWh. Rocky Mountain Power "
                "determines the annual kWh savings estimate for the specific system; the $0.15/kWh rate is "
                "fixed. Applies only when total compressor capacity is <=75 hp and the VFD is the primary "
                "capacity-control method.",
        "example": "Example: A Salt Lake City shop replaces a 50 hp load/no-load screw compressor (its only "
                   "production unit, plus a small backup) with a 50 hp VFD screw compressor. RMP estimates "
                   "38,000 kWh/yr savings from matching output to demand. Incentive: 38,000 x $0.15 = $5,700. "
                   "Incremental cost of the VFD unit: ~$9,000. Payback after incentive: well under 2 years.",
    },
    {
        "name": "wattsmart Business -- Compressed Air System Optimization (calculated)",
        "tech": "Compressed Air",
        "value": "Prescriptive: $2/scfm, $3/gal, $6/hp, $100/drain; end-use reduction $0.15/kWh",
        "max": "70% of project cost",
        "rate": "Prescriptive per-unit amounts (systems <=75 hp unless noted): Low-pressure-drop filter "
                "$2/scfm; receiver capacity addition $3/gallon (above 2 gal/scfm of trim capacity); cycling "
                "refrigerated dryer $2/scfm; zero-loss condensate drain $100 each (any system size); outside-"
                "air intake ductwork $6/hp. Compressed-air end-use reduction: $0.15/kWh annual energy savings "
                "(any system size).",
        "tiers": "Low-pressure-drop filter $2/scfm; receiver addition $3/gal (above 2 gal/scfm trim); cycling "
                 "refrigerated dryer $2/scfm; zero-loss condensate drain $100 each; outside-air intake $6/hp; "
                 "end-use reduction $0.15/kWh",
        "cap": "70% of energy-efficiency project cost; cannot reduce simple payback below 1 year",
        "baseline": "Existing compressed-air equipment being replaced (standard filter, non-cycling dryer, "
                    "timer drain, room-air intake); each measure has specific efficiency limitations in the PDF",
        "minp": "Most measures require total compressor capacity <=75 hp (excl. backup); zero-loss drains and "
                "end-use reduction have no size limit. Filter requires 25-75 hp system + >=2 psi setpoint drop",
        "url": URL["compressed_air"],
        "source_doc": PDF["compressed_air"],
        "verified": "2026-08-31",
        "notes": "Prescriptive compressed-air measures beyond the <=75 hp VFD compressor. Exact per-unit "
                 "amounts: low-pressure-drop filter $2/scfm (system 25-75 hp, discharge pressure cut >=2 psi); "
                 "receiver capacity addition $3/gallon above 2 gal/scfm of trim capacity (trim must be "
                 "load/unload, not VFD/modulating); cycling refrigerated dryer $2/scfm (<=500 scfm); zero-loss "
                 "condensate drain $100 each (any size); outside-air intake ductwork $6/hp. Compressed-air "
                 "end-use reduction (functionally equivalent alternatives / isolation valves) is calculated at "
                 "$0.15/kWh of annual savings, any system size. Max incentive rates are set by the Utah PSC "
                 "Schedule 140 tariff.",
        "impl": "1. Contact Rocky Mountain Power or a Trade Ally for a compressed-air assessment. 2. Identify "
                "qualifying prescriptive measures (filter, receiver, dryer, drains, outside-air intake) and/or "
                "end-use reductions. 3. Confirm each measure's limitations (system hp, trim control type, scfm "
                "caps). 4. Submit the application; install and submit invoices. 5. Receive incentive (capped at "
                "70% of project cost).",
        "meth": "Prescriptive measures pay a fixed per-unit amount (per scfm, per gallon, per hp, or each). "
                "End-use reduction is paid as estimated annual kWh savings x $0.15/kWh, verified/approved by "
                "Rocky Mountain Power.",
        "example": "Example: A shop adds 240 gallons of receiver capacity (120 gal above the 2 gal/scfm "
                   "threshold) and a cycling refrigerated dryer rated 300 scfm. Receiver: 120 x $3 = $360; "
                   "dryer: 300 x $2 = $600. Plus two zero-loss drains at $100 = $200. Total ~$1,160, capped at "
                   "70% of project cost.",
    },
    # ---- HVAC ----
    {
        "name": "wattsmart Business -- HVAC / Heat Pump",
        "tech": "Heat Pump / HVAC",
        "value": "$50-$100/ton (AC); heat pumps $50-$300/ton; VRF $1,000/head or $125/ton",
        "max": "Per ton of cooling capacity (heat pumps: cooling tons only)",
        "rate": "Prescriptive per-ton amounts (retrofit/major renovation). Unitary commercial AC (air-cooled "
                "split): $50/ton at CEE Tier 1, $75/ton at CEE Tier 2, $100/ton at CEE Tier 3 (Tier 3 only for "
                ">=65,000 Btu/hr). Water-cooled / evaporatively-cooled AC: $50/ton (CEE Tier 1). Unitary heat "
                "pumps: water-cooled $50/ton, ground-source $50/ton, groundwater-source $50/ton, air-cooled "
                "upgrade $120/ton, air-cooled conversion (from non-heat-pump) $300/ton. PTAC $25/ton; PTHP "
                "$50/ton. VRF heat pumps: air-cooled $1,000 per indoor unit head, water-cooled $125/ton. "
                "Heat-pump loop (ground/groundwater) $125/ton.",
        "tiers": "AC air-cooled split: $50/ton (CEE T1), $75/ton (CEE T2), $100/ton (CEE T3, >=65k Btu/hr). "
                 "AC water/evap-cooled: $50/ton (T1). Heat pumps: water/ground/groundwater $50/ton; air-cooled "
                 "upgrade $120/ton; air-cooled conversion $300/ton. PTAC $25/ton; PTHP $50/ton. VRF: $1,000/"
                 "indoor head (air-cooled) or $125/ton (water-cooled). Heat-pump loop $125/ton.",
        "cap": "Per ton of net cooling capacity (AHRI-rated); heat pumps paid per cooling ton only, not heating",
        "baseline": "Standard-efficiency equipment; qualifying unit must meet the CEE tier / ENERGY STAR / EER "
                    "+ COP minimums listed for its size class in RMP's HVAC equipment catalog",
        "minp": "Retrofit or major renovation; equipment must meet all listed efficiency requirements. "
                "PTHPs must replace (and remove) electric-resistance heat",
        "url": URL["hvac"],
        "source_doc": PDF["hvac"],
        "verified": "2026-08-31",
        "notes": "Prescriptive per-ton incentives for high-efficiency commercial HVAC and heat pumps "
                 "(retrofit/major renovation). Amounts are fixed per ton of AHRI-rated net cooling capacity "
                 "and depend on the CEE efficiency tier the equipment meets. Heat pumps pay per COOLING ton "
                 "only (must meet both cooling- and heating-mode efficiency). Air-cooled heat-pump CONVERSION "
                 "(replacing non-heat-pump equipment) pays the most at $300/ton. Note: evaporative cooling, "
                 "advanced rooftop-unit controls (ARC), and HVAC tune-ups/check-ups have their own separate "
                 "incentive sheets on the RMP HVAC page. Max rates set by the Utah PSC Schedule 140 tariff.",
        "impl": "1. Contact Rocky Mountain Power (1-866-870-3419) or a Trade Ally. 2. Select equipment meeting "
                "the CEE tier / ENERGY STAR / EER+COP minimum for its size class. 3. Get bids from licensed "
                "HVAC contractors. 4. Install and submit the application with invoices and AHRI equipment "
                "specs (rated cooling tons). 5. Receive the per-ton rebate.",
        "meth": "Incentive = cooling capacity (tons) x the per-ton amount for the equipment type and CEE tier. "
                "1 ton = 12,000 Btu/hr cooling. VRF air-cooled is paid per indoor unit head instead of per ton.",
        "example": "Example: A Salt Lake City office installs a 20-ton air-cooled split AC meeting CEE Tier 2. "
                   "Incentive: 20 tons x $75/ton = $1,500. If it instead met CEE Tier 3 (and is >=65k Btu/hr), "
                   "20 x $100 = $2,000. An air-cooled heat-pump conversion of the same size pays 20 x $300 = "
                   "$6,000.",
    },
    # ---- Lighting: Express (prescriptive, paid per watt INSTALLED) ----
    # Exact rates from RMP's "Incentives for Express Lighting System Retrofits" table
    # (UT wattsmart Business lighting catalog, effective 7/11/2025, v4/8/2026).
    {
        "name": "wattsmart Business -- Express Lighting Retrofit (Prescriptive, per watt installed)",
        "tech": "LED Lighting",
        "value": "$0.75-$1.75/W installed (interior); $1.20/W installed (exterior)",
        "max": "70% of project cost",
        "rate": "Paid per watt INSTALLED. Interior new fixture/retrofit kit: $0.75/W (without controls), "
                "$1.00/W (plug-and-play controls ready), $1.25/W (networked lighting controls), $1.75/W "
                "(luminaire-level controls / LLLC). Exterior new fixture/retrofit kit without controls "
                "(up to 285 W): $1.20/W.",
        "tiers": "Interior w/o controls $0.75/W; plug-and-play ready $1.00/W; networked $1.25/W; "
                 "LLLC $1.75/W; exterior w/o controls (<=285 W) $1.20/W -- all per watt installed",
        "cap": "70% of energy-efficiency project cost; cannot reduce simple payback below 1 year",
        "baseline": "Like-for-like (lumen-for-lumen) retrofit that uses less energy than the existing "
                    "system; must use qualified equipment from RMP's Qualified Lighting Equipment lists",
        "minp": "Projects with EXISTING controls, street lighting, and exterior seasonal lighting are NOT "
                "eligible for Express -- use the Calculated (Non-Prescriptive) lighting offer instead",
        "url": URL["lighting"],
        "source_doc": PDF["lighting_express"],
        "verified": "2026-08-31",
        "notes": "Prescriptive 'Express' path for straightforward LED retrofits: a fixed dollar amount per "
                 "watt INSTALLED, no engineering study. For like-for-like fixture/retrofit-kit swaps only, "
                 "with no existing lighting controls. Parking garages and areas under parking decks count as "
                 "interior (IECC 2021); top decks are exterior. " + LIGHTING_CALCULATOR_NOTE,
        "impl": "1. Confirm the job is a like-for-like retrofit with no existing controls (else use the "
                "Calculated offer). 2. Choose qualified make/model fixtures from RMP's Qualified Lighting "
                "Equipment lists. 3. Enter the make/model into RMP's lighting calculator tool to get the "
                "Stipulated installed wattage. 4. Install. 5. Submit the Express application with the tool "
                "output and invoices. 6. Receive incentive (capped at 70% of project cost).",
        "meth": "Incentive = installed watts (Stipulated, from the lighting calculator tool) x the per-watt "
                "rate for the controls tier. Capped at 70% of project cost and cannot cut payback below 1 yr.",
        "example": "Example: An Ogden warehouse installs new LED high-bays totaling 12,000 W installed "
                   "(no controls). Express incentive: 12,000 W x $0.75/W = $9,000, subject to the 70% "
                   "project-cost cap. Adding networked controls would pay $1.25/W = $15,000 instead.",
    },
    # ---- Lighting: Calculated / Non-Prescriptive (paid per watt REDUCED or CONTROLLED) ----
    # Exact rates from RMP's "Calculated Incentives for Lighting System Retrofits
    # (Non-Prescriptive)" tables, same catalog (effective 7/11/2025, v4/8/2026).
    {
        "name": "wattsmart Business -- Calculated Lighting System Retrofit (Non-Prescriptive, per watt reduced)",
        "tech": "LED Lighting",
        "value": "$0.15-$1.20/W reduced (interior); $0.10-$0.70/W (exterior); CEA $0.03-$0.05/kWh",
        "max": "70% of project cost",
        "rate": "Paid per watt REDUCED (new fixtures) or per watt CONTROLLED (controls-only). "
                "INTERIOR new fixtures/retrofit kits: $0.60/W (no/basic controls), $0.80/W (plug-and-play "
                "ready), $1.00/W (networked area/circuit), $1.20/W (advanced networked/LLLC). Interior "
                "controls-only: $0.45/W (basic), $0.60/W (networked), $0.75/W (advanced/LLLC), $0.15/W "
                "(control re-commissioning). Controlled Environment Agriculture (CEA): $0.05/kWh (fixtures), "
                "$0.03/kWh (replacement lamps). EXTERIOR new fixtures/retrofit kits: $0.35/W (no controls), "
                "$0.50/W (basic dimming), $0.70/W (advanced networked dimming). Exterior controls-only: "
                "$0.35/W (basic dimming), $0.60/W (advanced networked dimming). Street lighting: $0.35/W. "
                "Exterior seasonal (Large/Medium/Small): $0.18-$0.39/W reduced by tier.",
        "tiers": "INTERIOR new fixtures: no/basic $0.60/W, plug-and-play $0.80/W, networked $1.00/W, LLLC "
                 "$1.20/W (per W reduced). Interior controls-only: basic $0.45/W, networked $0.60/W, LLLC "
                 "$0.75/W, re-commissioning $0.15/W (per W controlled). Interior custom: no controls $0.15/W, "
                 "basic $0.30/W, LLLC $0.85/W. CEA: fixtures $0.05/kWh, lamps $0.03/kWh. EXTERIOR new "
                 "fixtures: no controls $0.35/W, basic dimming $0.50/W, advanced networked $0.70/W (per W "
                 "reduced). Exterior controls-only: basic dimming $0.35/W, advanced networked $0.60/W (per W "
                 "controlled). Street lighting: basic or advanced dimming $0.35/W reduced. Exterior custom: "
                 "no controls $0.10/W, dimming controls $0.30/W. Exterior SEASONAL (Large/Med/Small per W): "
                 "no controls $0.18/$0.20/$0.20; basic dimming $0.25/$0.28/$0.28; advanced networked "
                 "$0.35/$0.39/$0.39 reduced; controls-only basic $0.18/$0.20/$0.20, advanced $0.30/$0.33/$0.33.",
        "cap": "70% of energy-efficiency project cost; cannot reduce simple payback below 1 year. "
               "Control re-commissioning-only projects: 100% cost cap, no 1-year payback floor.",
        "baseline": "New system must use less energy than the existing/baseline system as determined by RMP. "
                    "Where controls already exist, the new control strategy must save more than the existing "
                    "one. Qualified equipment per RMP's Qualified Lighting Equipment lists.",
        "minp": "One RMP incentive per measure; cannot combine with the Express or wattsmart Homes offers. "
                "CEA fixtures must be on the DLC horticultural QPL. 3-year waiting period on re-incentivizing "
                "ANLC control re-commissioning.",
        "url": URL["lighting"],
        "source_doc": PDF["lighting_calc"],
        "verified": "2026-08-31",
        "notes": "The engineered/calculated lighting path -- used for anything with controls, street, "
                 "seasonal, CEA (grow lights), or non-like-for-like scopes. New fixtures pay on watts "
                 "REDUCED vs. the existing/baseline system; controls-only measures pay on watts CONTROLLED. "
                 "Higher control tiers (plug-and-play -> networked -> luminaire-level/LLLC) pay progressively "
                 "more. " + LIGHTING_CALCULATOR_NOTE,
        "impl": "1. Assess the space and pick the control strategy (drives which rate tier applies). "
                "2. Enter qualified make/model numbers into RMP's lighting calculator tool to get the "
                "Stipulated watts reduced/controlled. 3. Submit the Non-Prescriptive application with the "
                "tool output (an incentive offer letter may be required). 4. Install. 5. Verify and receive "
                "the incentive (capped at 70% of project cost).",
        "meth": "Incentive = Stipulated watts reduced (new fixtures) or controlled (controls-only), from the "
                "lighting calculator tool, x the per-watt rate for the interior/exterior category and control "
                "tier. CEA is paid per kWh instead. Capped at 70% of project cost.",
        "example": "Example: An office retrofit reduces connected interior load by 8,000 W and adds "
                   "area/circuit networked controls. Calculated incentive: 8,000 W x $1.00/W reduced = "
                   "$8,000, subject to the 70% project-cost cap. Basic-controls-only on the same fixtures "
                   "would instead pay 8,000 W x $0.45/W controlled = $3,600.",
    },
    # ---- Building envelope ----
    {
        "name": "wattsmart Business -- Building Envelope (Insulation / Cool Roof)",
        "tech": "Insulation / Weatherization",
        "value": "Insulation $0.30-$0.40/sq ft; windows $1.00/sq ft; cool roof $0.04/sq ft",
        "max": "Per square foot (window film paid per kWh)",
        "rate": "Roof/attic insulation $0.40/sq ft (minimum R-10 increment of insulation added); wall "
                "insulation $0.30/sq ft (minimum R-10 increment); windows (U-factor <=0.30 and SHGC <=0.33, "
                "site-built or full assembly) $1.00/sq ft of whole window assembly; cool roof (meets Green "
                "Globes SRI) $0.04/sq ft; window film $0.15/kWh annual energy savings.",
        "tiers": "Roof/attic insulation $0.40/sq ft (min R-10 added); wall insulation $0.30/sq ft (min R-10); "
                 "windows (U<=0.30, SHGC<=0.33) $1.00/sq ft assembly; cool roof $0.04/sq ft; window film $0.15/kWh",
        "cap": "Per square foot by measure; window film paid per kWh (subject to RMP approval)",
        "baseline": "Existing envelope; building MUST be mechanically cooled to qualify. Insulation must add at "
                    "least an R-10 increment; window sq ft = whole assembly (not just glass); skylights not eligible",
        "minp": "Windows rated per NFRC; site-built metal frames need a thermal break. Window-film savings "
                "depend on film spec + window orientation",
        "url": URL["envelope"],
        "source_doc": PDF["envelope"],
        "verified": "2026-08-31",
        "notes": "Prescriptive per-square-foot envelope retrofits (building must have mechanical cooling). "
                 "Roof/attic insulation $0.40/sq ft and wall insulation $0.30/sq ft are paid per R-10 increment "
                 "of insulation added. High-performance windows (U-factor <=0.30, SHGC <=0.33) pay $1.00/sq ft "
                 "of the entire window assembly. Cool roofs meeting the Green Globes SRI pay $0.04/sq ft. "
                 "Window film is calculated at $0.15/kWh. This is the retrofit sheet; new construction / major "
                 "renovation has its own envelope incentives. Max rates set by the Utah PSC Schedule 140 tariff.",
        "impl": "1. Obtain contractor bids and NFRC/R-value documentation. 2. Complete installation (add at "
                "least an R-10 increment for insulation measures). 3. Submit the building-envelope application "
                "with invoices, photos, and R-value / window ratings.",
        "meth": "Insulation/windows/cool roof: qualifying sq ft x the per-sq-ft rate (insulation must add at "
                "least an R-10 increment to qualify). Window film: estimated annual kWh savings x $0.15/kWh.",
        "example": "Example: A 20,000 sq ft retail building adds roof insulation (>=R-10 increment): 20,000 x "
                   "$0.40 = $8,000. Replacing 1,500 sq ft of windows with U-0.28/SHGC-0.30 units: 1,500 x "
                   "$1.00 = $1,500. (Confirm with RMP whether larger R-value adds increase the per-sq-ft rate.)",
    },
    # ---- Appliances / plug load ----
    {
        "name": "wattsmart Business -- Appliances & Office Equipment",
        "tech": "Appliances / Plug Load",
        "value": "Smart plug strip $5; engine block heater control $125; commercial clothes washer $100",
        "max": "Per qualifying unit",
        "rate": "Smart plug strip (load/occupancy sensing) $5/qualifying unit; engine block heater controls "
                "$125/unit; high-efficiency commercial clothes washer (ENERGY STAR, must have electric water "
                "heating and/or electric dryer) $100. Heat-pump water heaters and residential appliances used "
                "in a business are handled under the wattsmart Homes program (Schedule 111).",
        "tiers": "Smart plug strip $5/unit; engine block heater controls $125/unit; commercial ENERGY STAR "
                 "clothes washer $100",
        "cap": "Fixed amount per qualifying unit",
        "baseline": "Standard plug strip / uncontrolled block heater / standard commercial clothes washer",
        "minp": "Equipment must be on RMP's Qualified Product List and meet the efficiency standard in effect "
                "on the purchase date",
        "url": URL["appliances"],
        "source_doc": PDF["appliances"],
        "verified": "2026-08-31",
        "notes": "Office and other plug-load equipment: smart plug strips that cut idle/standby power ($5/unit), "
                 "thermostatically-controlled engine block heater controls ($125/unit), and high-efficiency "
                 "commercial clothes washers ($100, ENERGY STAR with electric water heating and/or electric "
                 "dryer). NOTE: commercial refrigeration controls are under the Wastewater & Other Refrigeration "
                 "and Food Service measures, not here. Residential appliances used in a business use wattsmart "
                 "Homes (Schedule 111). Max rates set by the Utah PSC Schedule 140 tariff.",
        "impl": "1. Confirm the unit is on RMP's Qualified Product List. 2. Purchase and install. 3. Submit the "
                "office/appliance application with proof of purchase and model numbers.",
        "meth": "Rebate is a fixed amount per qualifying unit (plug strip, block heater control, or washer).",
        "example": "Example: An office deploys 40 smart plug strips on workstations: 40 x $5 = $200. A fleet "
                   "yard adds engine block heater controls to 10 trucks: 10 x $125 = $1,250.",
    },
    # ---- Motors & VFDs ----
    {
        "name": "wattsmart Business -- Motors & VFDs (Pumps / Fans)",
        "tech": "Motors & Drives / VFD",
        "value": "VFD (HVAC fans/pumps) $200/hp; ECM $200/hp or $3/watt",
        "max": "By motor hp / ECM watts",
        "rate": "Variable-frequency drives on HVAC fans and pumps (<=100 hp): $200/horsepower. Electronically "
                "commutated motors (ECM, retrofit only): <=1 hp refrigeration application $3/watt; <=1 hp HVAC "
                "application $200/hp; >1 hp and <=10 hp HVAC application $200/hp.",
        "tiers": "VFD on HVAC fans/pumps (<=100 hp) $200/hp; ECM <=1 hp refrigeration $3/watt; ECM <=1 hp HVAC "
                 "$200/hp; ECM >1-10 hp HVAC $200/hp",
        "cap": "Per horsepower (VFD, HVAC ECM) or per watt (refrigeration ECM <=1 hp)",
        "baseline": "Fixed-speed operation (VFD); standard motor (ECM retrofit). A variable load must be "
                    "present for VFD savings",
        "minp": "VFD: throttling/bypass devices (inlet vanes, bypass dampers, 3-way/throttling valves) must be "
                "removed or permanently disabled; code-required VFDs are NOT eligible. ECM is retrofit only",
        "url": URL["motors"],
        "source_doc": PDF["motors"],
        "verified": "2026-08-31",
        "notes": "Prescriptive per-hp incentives for variable-frequency drives on HVAC fans and pumps up to "
                 "100 hp ($200/hp) and for electronically commutated motors (ECM retrofits). ECM: $3/watt for "
                 "<=1 hp refrigeration applications, $200/hp for HVAC applications (<=10 hp). To qualify, VFDs "
                 "must serve a genuinely variable load and any throttling/bypass devices must be removed; VFDs "
                 "installed to meet energy code are not eligible. NOTE: compressed-air VFDs are not paid here -- "
                 "they use the compressed-air program at $0.15/kWh. Larger/process motors and non-HVAC VFDs go "
                 "through the Custom/Calculated program. Max rates set by the Utah PSC Schedule 140 tariff.",
        "impl": "1. Identify HVAC fans/pumps with variable load suited to a VFD, or refrigeration/HVAC motors "
                "suited to an ECM retrofit. 2. Confirm eligibility (remove throttling/bypass; not code-required; "
                "ECM is retrofit-only). 3. Install. 4. Submit the application with motor nameplate hp/watts and "
                "invoices. 5. Receive the per-hp (or per-watt) rebate.",
        "meth": "VFD incentive = motor horsepower x $200/hp. ECM incentive = hp x $200 (HVAC) or ECM watts x $3 "
                "(<=1 hp refrigeration). Straight prescriptive amounts -- no kWh calculation required.",
        "example": "Example: A VFD on a 40 hp HVAC supply fan pays 40 x $200 = $8,000, often covering much of "
                   "the drive cost. A 0.5 hp (~370 W) ECM retrofit on a walk-in cooler evaporator fan pays "
                   "370 x $3 = ~$1,110.",
    },
    # ---- Food service ----
    {
        "name": "wattsmart Business -- Commercial Food Service Equipment",
        "tech": "Food Service / Refrigeration",
        "value": "Per-unit ENERGY STAR amounts ($100-$1,000); anti-sweat $16-$20/ft; DCKV $0.15/kWh",
        "max": "Per qualifying appliance / measure",
        "rate": "ENERGY STAR fixed per-unit amounts. Commercial dishwasher (high-temp w/electric booster): "
                "$100 under-counter, $300 single-tank stationary/door, $500 single- or multi-tank conveyor. "
                "Electric insulated holding cabinet: $400 (half, V<13), $600 (full, 13-28), $1,000 (double, "
                ">=28). Electric steam cooker $600; combination oven (3-40 pan) $700; convection oven $350 "
                "full / $200 half; fryer $300; griddle $300. Air-cooled ice machine $125 (<500 lb/day) / $150 "
                "(>=500). Anti-sweat heater controls (retrofit): $20/linear ft low-temp cases, $16/ft mid-temp. "
                "Demand-controlled kitchen ventilation hood (retrofit): $0.15/kWh annual savings.",
        "tiers": "Dishwasher $100/$300/$500 by type; holding cabinet $400/$600/$1,000 by size; steam cooker "
                 "$600; combi oven $700; convection $350/$200; fryer $300; griddle $300; ice machine $125/$150; "
                 "anti-sweat controls $20/ft (low-temp) or $16/ft (mid-temp); DCKV hood $0.15/kWh",
        "cap": "Fixed amount per qualifying appliance; DCKV hood paid on kWh (subject to RMP approval)",
        "baseline": "Standard (non-ENERGY STAR) commercial kitchen equipment; anti-sweat/DCKV are retrofit-only",
        "minp": "Equipment must be ENERGY STAR qualified for its category; residential units used in a business "
                "use wattsmart Homes (Schedule 111)",
        "url": URL["foodservice"],
        "source_doc": PDF["foodservice"],
        "verified": "2026-08-31",
        "notes": "Fixed per-unit incentives for ENERGY STAR commercial kitchen equipment plus two refrigeration/"
                 "ventilation retrofit measures. Commercial high-temperature dishwashers with electric boosters "
                 "$100-$500 by type; electric insulated holding cabinets $400-$1,000 by size; steam cookers "
                 "$600; combination ovens $700; convection ovens $350/$200; fryers/griddles $300; air-cooled "
                 "ice machines $125-$150. Anti-sweat heater controls pay per linear foot of case ($20 low-temp, "
                 "$16 mid-temp); demand-controlled kitchen ventilation hoods pay $0.15/kWh. Max rates set by "
                 "the Utah PSC Schedule 140 tariff.",
        "impl": "1. Select ENERGY STAR-qualified equipment (or the qualifying retrofit control). 2. Purchase "
                "and install. 3. Submit the food-service application with proof of purchase and model numbers "
                "(DCKV hoods require a savings estimate approved by RMP).",
        "meth": "Rebate is the sum of the fixed per-unit amounts for each qualifying appliance; anti-sweat "
                "controls pay per linear foot of case; DCKV hoods pay estimated annual kWh savings x $0.15/kWh.",
        "example": "Example: A restaurant installs a single-tank door-type dishwasher ($300), a full-size "
                   "convection oven ($350), and an air-cooled ice machine rated 400 lb/day ($125). Total "
                   "prescriptive rebate: $775.",
    },
    # ---- Agriculture / irrigation ----
    {
        "name": "wattsmart Business -- Irrigation (Sprinklers, Nozzles, Pump VFD)",
        "tech": "Irrigation / Agricultural",
        "value": "Sprinklers/nozzles $0.50-$2 ea; pivot drops $2-$7; pump VFD $0.15/kWh",
        "max": "Per unit / per drop; pump VFD per kWh",
        "rate": "WHEEL/HAND/PORTABLE lines (retrofit, electric-pump systems, max 2 units/acre): rotating "
                "sprinkler $0.50 ea; new/rebuilt impact sprinkler $0.50 ea; nozzle $1.50 ea; gasket $2 ea; "
                "drain $2 ea; leveler $1 ea; cut/press or weld repair $8/repair. PIVOTS & LINEARS (retrofit, "
                "per drop): high-pressure replacement $7/drop; MESA replacement $4/drop; LESA/LEPA/MDI "
                "replacement $2/drop; upgrade high-pressure->MESA $7/drop; high-pressure->LESA/LEPA/MDI "
                "$7/drop; MESA->LESA/LEPA/MDI $5/drop. ANY SYSTEM (retrofit or new): irrigation pump VFD "
                "$0.15/kWh annual savings.",
        "tiers": "Wheel/hand line (max 2/acre): rotating or impact sprinkler $0.50 ea, nozzle $1.50, gasket $2, "
                 "drain $2, leveler $1, cut/weld repair $8. Pivot/linear per drop: HP replace $7, MESA $4, "
                 "LESA/LEPA/MDI $2; upgrades HP->MESA $7, HP->LESA $7, MESA->LESA $5. Pump VFD $0.15/kWh",
        "cap": "Per-unit measures: 2 units per irrigated acre. Pump VFD: 70% of project cost, no payback < 1 yr",
        "baseline": "Worn/leaking sprinklers, nozzles, gaskets, drains; higher-pressure sprinkler packages; "
                    "fixed-speed irrigation pump. Fixed-in-place (solid-set) systems NOT eligible for hardware",
        "minp": "Electric-pump systems only (not diesel/gravity). Hardware measures are retrofit-only; pump "
                "VFD is retrofit OR new construction. New flow must be same-design-flow or less",
        "url": URL["agriculture"],
        "source_doc": PDF["irrigation"],
        "verified": "2026-08-31",
        "notes": "RMP's Water Distribution & Irrigation sheet. Wheel/hand/portable-line hardware pays small "
                 "per-unit amounts (sprinklers $0.50, nozzles $1.50, gaskets/drains $2, levelers $1, pipe "
                 "repairs $8), capped at 2 units per irrigated acre. Pivot/linear sprinkler swaps pay per drop, "
                 "with the biggest amounts for moving high-pressure to low-pressure MESA/LESA/LEPA/MDI packages "
                 "($5-$7/drop). Adding a VFD to any electric irrigation pump pays $0.15/kWh (retrofit or new). "
                 "Only electric-pump systems qualify; solid-set systems are excluded from hardware measures. "
                 "Max rates set by the Utah PSC Schedule 140 tariff.",
        "impl": "1. Get an irrigation incentive application from RMP or a Trade Ally. 2. Identify qualifying "
                "measures (replace worn hardware like-for-like at same or lower flow; upgrade pivot packages; "
                "add a pump VFD). 3. Install. 4. Submit the application with invoices (rebuild kits itemized). "
                "5. Receive incentive.",
        "meth": "Hardware: quantity x per-unit amount, capped at 2/acre. Pivot/linear: number of drops x the "
                "per-drop amount for the replacement/upgrade type. Pump VFD: annual kWh savings x $0.15/kWh.",
        "example": "Example: A 120-acre pivot upgrades 480 drops from high-pressure impact to LESA: 480 x $7 = "
                   "$3,360. Adding a VFD to the 60 hp pivot pump (est. 40,000 kWh/yr saved): 40,000 x $0.15 = "
                   "$6,000 (capped at 70% of the VFD project cost).",
    },
    {
        "name": "wattsmart Business -- Farm & Dairy Equipment",
        "tech": "Agricultural / Motors",
        "value": "Circulating fans $25-$75; ventilation fans $45-$150; vacuum-pump VFD $165/hp",
        "max": "Per fan / per hp; heat recovery & pre-cooler per kWh",
        "rate": "High-efficiency circulating fan (by diameter, meeting lbf/kW minimum): $25 (12-23\"), $35 "
                "(24-35\"), $50 (36-47\"), $75 (>=48\"). High-efficiency ventilation fan (by diameter, cfm/W "
                "minimum): $45 (12-23\"), $75 (24-35\"), $125 (36-47\"), $150 (>=48\"). Programmable ventilation "
                "controllers $20/fan controlled. VFD on dairy vacuum pump (retrofit only) $165/hp. Heat "
                "recovery (milk-cooling heat to water heating) and milk pre-cooler (retrofit) $0.15/kWh.",
        "tiers": "Circulating fan $25/$35/$50/$75 by diameter; ventilation fan $45/$75/$125/$150 by diameter; "
                 "programmable ventilation controller $20/fan; dairy vacuum-pump VFD $165/hp; heat recovery "
                 "$0.15/kWh; milk pre-cooler $0.15/kWh",
        "cap": "70% of energy-efficiency project cost; cannot reduce simple payback below 1 year",
        "baseline": "Standard fans / uncontrolled ventilation / fixed-speed vacuum pump; heat recovery and "
                    "milk pre-cooler require electric water heating and are retrofit-only",
        "minp": "Fan performance must be rated to ANSI/AMCA standards. Vacuum-pump VFD and milk pre-cooler are "
                "retrofit-only (no new construction / no VFD replacement); most fans qualify for both",
        "url": URL["agriculture"],
        "source_doc": PDF["farm_dairy"],
        "verified": "2026-08-31",
        "notes": "RMP's Farm & Dairy Equipment sheet. High-efficiency circulating and ventilation fans pay a "
                 "fixed amount per fan that scales with diameter (circulating $25-$75; ventilation $45-$150), "
                 "provided the fan meets the lbf/kW or cfm/W efficiency minimum for its size. Programmable "
                 "ventilation controllers pay $20 per fan controlled. A VFD on a dairy vacuum pump pays $165/hp "
                 "(retrofit only). Milk-cooling heat recovery and milk pre-coolers are calculated at $0.15/kWh. "
                 "Max rates set by the Utah PSC Schedule 140 tariff.",
        "impl": "1. Get a farm/dairy incentive application from RMP or a Trade Ally. 2. Select qualifying "
                "equipment (fans meeting the efficiency minimum, controllers, vacuum-pump VFD, heat recovery). "
                "3. Install. 4. Submit the application with invoices and fan efficiency ratings. 5. Receive "
                "incentive (capped at 70% of cost).",
        "meth": "Fans: quantity x the per-fan amount for the diameter class. Controllers: fans controlled x "
                "$20. Vacuum-pump VFD: motor hp x $165. Heat recovery / pre-cooler: annual kWh saved x $0.15.",
        "example": "Example: A dairy installs eight 50\" high-efficiency ventilation fans (8 x $150 = $1,200) "
                   "and a 7.5 hp VFD on its vacuum pump (7.5 x $165 = ~$1,238) for ~$2,438 in incentives, "
                   "capped at 70% of project cost.",
    },
    # ---- Wastewater / process ----
    {
        "name": "wattsmart Business -- Wastewater & Other Refrigeration",
        "tech": "Refrigeration / Process",
        "value": "$0.15/kWh annual energy savings (all measures)",
        "max": "70% of project cost",
        "rate": "Paid at $0.15/kWh of annual energy savings for each measure: adaptive refrigeration control "
                "(replaces conventional defrost timeclock / thermostat / evaporator-fan / TXV controls); fast-"
                "acting door (replaces manual/slow door, strip curtain, or open entryway on a refrigerated/"
                "conditioned space); wastewater low-power mixer (extended-range circulator / low-power mixer "
                "replacing excess aeration capacity).",
        "tiers": "Adaptive refrigeration control $0.15/kWh; fast-acting door $0.15/kWh; wastewater low-power "
                 "mixer $0.15/kWh -- all on annual energy savings",
        "cap": "70% of energy-efficiency project cost; cannot reduce simple payback below 1 year",
        "baseline": "Existing conventional refrigeration controls / slow or missing cold-storage door / "
                    "over-sized aeration; savings estimated and approved by RMP",
        "minp": "Savings estimate subject to RMP approval",
        "url": URL["wastewater"],
        "source_doc": PDF["wastewater"],
        "verified": "2026-08-31",
        "notes": "The RMP 'Wastewater and Other Refrigeration' sheet -- three calculated measures each paid at "
                 "$0.15/kWh of annual savings: adaptive refrigeration controllers (replacing conventional "
                 "defrost/fan/TXV controls, sometimes with an electric expansion valve), fast-acting cold-"
                 "storage doors, and low-power wastewater mixers/circulators that replace excess aeration. "
                 "Larger wastewater aeration/blower and dissolved-oxygen-control projects that aren't one of "
                 "these prescriptive measures go through the Custom/Calculated program instead. Max rates set "
                 "by the Utah PSC Schedule 140 tariff.",
        "impl": "1. Identify the qualifying measure (adaptive refrigeration control, fast-acting door, or "
                "low-power mixer). 2. Submit the application with a savings analysis. 3. RMP reviews/approves "
                "the estimate. 4. Install and submit invoices. 5. Receive incentive (capped at 70% of cost).",
        "meth": "Incentive = estimated annual kWh savings x $0.15/kWh, verified/approved by Rocky Mountain "
                "Power. Applies per qualifying measure.",
        "example": "Example: A cold-storage warehouse adds adaptive refrigeration controllers estimated to save "
                   "60,000 kWh/yr: 60,000 x $0.15 = $9,000, capped at 70% of project cost.",
    },
    # ---- Oil & gas ----
    {
        "name": "wattsmart Business -- Oil & Gas Field Efficiency",
        "tech": "Process / Controls",
        "value": "Pump-off controller $1,500 per controller",
        "max": "70% of project cost",
        "rate": "Oil and gas pump-off controller: $1,500 per controller (added to an existing oil or gas well).",
        "tiers": "Pump-off controller $1,500 each",
        "cap": "70% of energy-efficiency project cost; cannot reduce simple payback below 1 year",
        "baseline": "Existing oil/gas well with no pump-off controller",
        "minp": "Savings/costs subject to RMP approval",
        "url": URL["oil_gas"],
        "source_doc": PDF["oil_gas"],
        "verified": "2026-08-31",
        "notes": "RMP's oil & gas prescriptive sheet lists one measure: a pump-off controller added to an "
                 "existing oil or gas well pays $1,500 per controller. Other field-efficiency measures (VFDs "
                 "and efficient motors on pump jacks, compressors, and pumps) are not on this prescriptive "
                 "sheet -- they go through the Motors/VFD or Custom/Calculated programs. Max rates set by the "
                 "Utah PSC Schedule 140 tariff.",
        "impl": "1. Identify wells suited to a pump-off controller. 2. Install the controller. 3. Submit the "
                "oil & gas application with invoices. 4. Receive $1,500 per controller (capped at 70% of cost).",
        "meth": "Incentive = number of qualifying pump-off controllers x $1,500 each.",
        "example": "Example: An operator adds pump-off controllers to 6 wells: 6 x $1,500 = $9,000, capped at "
                   "70% of project cost.",
    },
    # ---- Whole-building new construction / major renovation ----
    {
        "name": "wattsmart Business -- Whole-Building New Construction / Major Renovation",
        "tech": "Multiple Technologies",
        "value": "Whole-building performance incentive by modeled savings",
        "max": "Varies",
        "rate": "Incentive scaled to modeled whole-building energy savings vs. code (performance path)",
        "tiers": "",
        "cap": "",
        "baseline": "ASHRAE 90.1 / Utah energy code reference building",
        "minp": "New construction or major renovation; energy modeling required",
        "url": URL["wbnc"],
        "notes": "For new construction and major renovations: a whole-building performance-path incentive scaled "
                 "to modeled energy savings beyond code, plus access to prescriptive measures. Also a system-by-"
                 "system path for individual upgrades. Confirm current incentive structure on RMP's WBNC page.",
        "impl": "1. Engage RMP early in design. 2. Model the building vs. ASHRAE 90.1 / Utah code. 3. Choose the "
                "whole-building performance path or system-by-system prescriptive measures. 4. Submit the "
                "application with modeling. 5. Build and verify. 6. Receive incentive.",
        "meth": "Whole-building path: incentive scales with modeled % energy savings vs. the code baseline. "
                "System path: sum of prescriptive measure amounts.",
        "example": "Example: A new 80,000 sq ft office modeled 25% better than code earns a whole-building "
                   "incentive plus prescriptive lighting/HVAC rebates; confirm the current per-savings rate.",
    },
    # ---- Battery storage (separate wattsmart Battery / dispatch program) ----
    {
        "name": "wattsmart Battery -- Commercial Battery Storage (dispatch)",
        "tech": "Energy Storage / Battery",
        "value": "Per kW of battery capacity (upfront + annual bill credit)",
        "max": "Scales with enrolled battery kW",
        "rate": "Incentive per kW of committed battery capacity: an upfront incentive plus an ongoing annual "
                "bill credit (confirm current commercial $/kW with RMP)",
        "tiers": "",
        "cap": "",
        "baseline": "Battery power capacity (kW) enrolled for utility dispatch",
        "minp": "Enroll the battery in RMP's dispatch program; solar or solar+battery may be required",
        "url": URL["battery"],
        "notes": "Rocky Mountain Power's wattsmart Battery program pays an incentive based on battery size (kW) "
                 "in exchange for letting the utility dispatch the battery (a virtual power plant). Published "
                 "residential terms are about $150/kW for each committed year plus a $15/kW annual bill credit; "
                 "commercial terms are set by RMP and were updated in 2026 -- confirm the current commercial "
                 "$/kW, term length, and eligibility (solar/solar+battery requirement). Stacks with the 30% "
                 "federal storage ITC, which is usually the larger incentive when buying a battery.",
        "impl": "1. Contact Rocky Mountain Power (or a participating battery installer) about wattsmart Battery "
                "enrollment. 2. Confirm eligibility and current commercial $/kW and term. 3. Install a qualifying "
                "battery and enroll it for dispatch. 4. Receive the upfront incentive and ongoing annual bill "
                "credit. 5. Separately claim the 30% federal ITC on the battery.",
        "meth": "Incentive = committed battery kW x the program's $/kW upfront rate (per committed year) plus a "
                "$/kW annual bill credit for participating years. Value scales with enrolled power capacity (kW).",
        "example": "Example: A business enrolls a 100 kW battery. Using published residential reference rates "
                   "(~$150/kW/yr committed + $15/kW annual credit) the utility incentive is on the order of "
                   "thousands per year; confirm the current commercial figures. Separately, a $300,000 battery "
                   "earns a 0.30 x $300,000 = $90,000 federal ITC.",
    },
    # ---- Custom catch-all (only for measures with no prescriptive rate) ----
    {
        "name": "wattsmart Business -- Custom / Calculated Projects (Industrial)",
        "tech": "Multiple Technologies",
        "value": "$0.08-0.12/kWh verified first-year savings",
        "max": "Custom",
        "rate": "~$0.08-0.12/kWh of verified first-year savings (measure-specific)",
        "tiers": "",
        "cap": "",
        "baseline": "IPMVP Option A/B/C measured baseline",
        "minp": "Typically ~$5,000 in annual energy savings",
        "url": URL["business"],
        "notes": "For non-prescriptive measures not covered by a published per-unit/per-kWh amount -- ideal "
                 "for industrial process loads and whole-system projects. If a measure has a prescriptive "
                 "rate (e.g. the $0.15/kWh compressed-air program), use that instead for a more accurate value.",
        "impl": "1. Contact the Rocky Mountain Power business team. 2. Submit a pre-approval application with "
                "an energy-savings analysis (modeling or M&V plan). 3. Await approval (2-4 weeks). 4. Implement. "
                "5. Submit post-installation M&V. 6. Receive rebate.",
        "meth": "Custom projects use IPMVP Option A/B/C. Rebate = verified first-year kWh savings x the "
                "measure's custom rate (~$0.08-0.12/kWh). Minimum project size ~ $5,000 in energy savings.",
        "example": "Example: A food plant installs VFDs on 15 pump motors; M&V confirms 350,000 kWh/yr. Rebate "
                   "at $0.10/kWh = $35,000. (A compressed-air VFD instead would use the $0.15/kWh program.)",
    },
]


def _measures():
    rows = []
    for m in MEASURES:
        key = make_key(UTIL, m["name"])
        detailed = key in DETAILED_KEYS
        rows.append(record(
            STATE, m["name"], ADMIN, SECTOR, "Rebate", m["tech"],
            m["value"], m["max"], RECIP, "Ongoing", m["url"],
            notes=m["notes"], implementation=m["impl"], methodology=m["meth"],
            example=m["example"], incentive_rate=m["rate"], rebate_tiers=m["tiers"],
            unit_cap=m["cap"], baseline=m["baseline"], min_project=m["minp"],
            key=key,
            detail_level=("detailed" if detailed else "general"),
            verified_date=(m.get("verified", VERIFIED_DATE) if detailed else ""),
            source_doc=m.get("source_doc", m["url"]),
            verified_by=("human" if detailed else ""),
        ))
    return rows
