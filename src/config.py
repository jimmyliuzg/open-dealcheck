"""
OpenDealCheck — Configuration
Single source of truth for search criteria and financial assumptions.
"""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"
DB_PATH = DATA_DIR / "listings.db"

# Ensure dirs exist
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# ── Search Criteria ────────────────────────────────────────────
# Adjust these to your buy box
SEARCH = {
    "location": "94087",  # Sunnyvale, CA
    "listing_type": "for_sale",
    "beds_min": 3,
    "beds_max": 3,
    "baths_min": 2,
    "baths_max": 2,
    "sqft_min": 1000,
    "sqft_max": 2000,
    "lot_sqft_min": 5000,
    "price_min": 1_600_000,
    "price_max": 1_800_000,
}

# ── Financial Assumptions ──────────────────────────────────────
FINANCIAL = {
    # Financing
    "down_payment_pct": 0.20,        # 20% down
    "interest_rate": 0.065,          # 6.5% (adjust to current rates)
    "loan_term_years": 30,

    # Holding costs (monthly)
    "property_tax_rate": 0.0115,     # 1.15% of value/year (CA Prop 13 base)
    "insurance_annual": 3_600,       # $300/mo estimate
    "maintenance_pct": 0.01,         # 1% of value/year

    # Rental assumptions
    "vacancy_rate": 0.05,            # 5%
    "property_mgmt_pct": 0.08,       # 8% of gross rent

    # Transaction costs
    "closing_cost_pct": 0.02,        # 2% of purchase price
    "rehab_budget": 0,               # $0 (move-in ready assumption)

    # Growth projections
    "appreciation_rate": 0.03,       # 3%/yr property value growth
    "rent_growth_rate": 0.02,        # 2%/yr rent growth
    "expense_growth_rate": 0.02,     # 2%/yr expense growth
    "hold_years": 10,                # projection horizon

    # Rent estimation (manual override until market data is added)
    "rent_estimate_sqft": 3.50,      # $/sqft/month
}
