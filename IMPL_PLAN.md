# OpenDealCheck — Deal-Finding Pipeline Implementation Plan

> Automated listing monitor + financial analysis + report generation.
> Personal use, runs as a cron job.

## Architecture

```
Layer 1: LISTING MONITOR      → HomeHarvest (Realtor.com scraper)
Layer 2: PROPERTY ENRICHMENT   → Listing data + tax estimation
Layer 3: ANALYSIS ENGINE       → Pure Python financial calculations
Layer 4: REPORT GENERATION     → Jinja2 HTML → WeasyPrint PDF
Layer 5: DELIVERY              → Cron job → file output (+ optional Telegram)
```

## Data Flow

```
Cron (every 8h)
  │
  ├─ 1. search_listings()          → DataFrame of matching listings
  ├─ 2. diff_new(listings, db)     → only NEW listings not seen before
  ├─ 3. for each new listing:
  │     ├─ enrich(listing)         → add tax estimate, monthly payment
  │     ├─ analyze(enriched)       → full financial model
  │     └─ generate_report(data)   → PDF saved to reports/
  └─ 4. notify(new_reports)        → summary to Telegram or file
```

## File Structure

```
open-dealcheck/
├── .venv/                          # Python virtualenv
├── data/
│   ├── listings.db                 # SQLite: seen listings, dedup
│   └── reports/                    # Generated PDF reports
├── src/
│   ├── __init__.py
│   ├── config.py                   # Search criteria, financial assumptions
│   ├── search.py                   # Layer 1: HomeHarvest wrapper
│   ├── enrich.py                   # Layer 2: tax estimation, data cleanup
│   ├── analysis.py                 # Layer 3: financial calculations
│   ├── report.py                   # Layer 4: PDF report generation
│   ├── db.py                       # SQLite: listing tracking, dedup
│   └── notify.py                   # Layer 5: notification delivery
├── templates/
│   └── report.html                 # Jinja2 PDF template
├── run.py                          # Main entry point (called by cron)
├── requirements.txt
└── PLAN.md
```

## Implementation Tasks

### Task 1: config.py — Search Criteria & Financial Assumptions

Single source of truth for all configurable parameters.

```python
# Search criteria (your exact requirements)
SEARCH = {
    "location": "94087",
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

# Financial assumptions for analysis
FINANCIAL = {
    "down_payment_pct": 0.20,          # 20% down
    "interest_rate": 0.065,            # 6.5% (adjust to current)
    "loan_term_years": 30,
    "property_tax_rate": 0.0115,       # 1.15% (CA Prop 13 base)
    "insurance_annual": 3_600,         # $300/mo estimate
    "maintenance_pct": 0.01,           # 1% of value/year
    "vacancy_rate": 0.05,              # 5%
    "property_mgmt_pct": 0.08,         # 8% of gross rent
    "closing_cost_pct": 0.02,          # 2% of purchase price
    "rehab_budget": 0,                 # $0 (move-in ready assumption)
    "appreciation_rate": 0.03,         # 3%/yr
    "rent_growth_rate": 0.02,          # 2%/yr
    "expense_growth_rate": 0.02,       # 2%/yr
    "hold_years": 10,                  # projection horizon
    "rent_estimate_sqft": 3.50,        # $/sqft/mo (manual override)
}

# Reporting
REPORTS_DIR = "data/reports"
DB_PATH = "data/listings.db"
```

### Task 2: db.py — Listing Tracking & Dedup

SQLite database to track seen listings and avoid re-processing.

```sql
CREATE TABLE listings (
    listing_id TEXT PRIMARY KEY,        -- Realtor.com listing ID
    property_url TEXT,
    formatted_address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    beds INTEGER,
    full_baths INTEGER,
    half_baths INTEGER,
    sqft REAL,
    lot_sqft REAL,
    list_price REAL,
    year_built INTEGER,
    days_on_mls INTEGER,
    estimated_value REAL,
    assessed_value REAL,
    tax REAL,
    latitude REAL,
    longitude REAL,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzed INTEGER DEFAULT 0,
    report_path TEXT
);
```

Functions:
- `init_db()` — create tables if not exist
- `is_new_listing(listing_id)` — check if already seen
- `save_listing(row)` — insert new listing
- `mark_analyzed(listing_id, report_path)` — mark as processed
- `get_listings_for_zip(zip_code, days=30)` — recent listings

### Task 3: search.py — Layer 1: Listing Monitor

Wraps HomeHarvest with our config.

```python
def search_listings() -> pd.DataFrame:
    """Search Realtor.com for matching listings."""
    from homeharvest import scrape_property
    from config import SEARCH

    results = scrape_property(
        location=SEARCH["location"],
        listing_type=SEARCH["listing_type"],
        beds_min=SEARCH["beds_min"],
        beds_max=SEARCH["beds_max"],
        baths_min=SEARCH["baths_min"],
        baths_max=SEARCH["baths_max"],
        sqft_min=SEARCH["sqft_min"],
        sqft_max=SEARCH["sqft_max"],
        lot_sqft_min=SEARCH.get("lot_sqft_min"),
        price_min=SEARCH["price_min"],
        price_max=SEARCH["price_max"],
    )
    return results
```

### Task 4: enrich.py — Layer 2: Property Enrichment

Takes raw listing data and adds calculated fields.

```python
def enrich_listing(row: dict) -> dict:
    """Add financial estimates to a listing."""
    from config import FINANCIAL

    price = row["list_price"]
    f = FINANCIAL

    # Down payment
    down_payment = price * f["down_payment_pct"]

    # Loan amount
    loan_amount = price - down_payment

    # Monthly mortgage (P&I)
    monthly_rate = f["interest_rate"] / 12
    n_payments = f["loan_term_years"] * 12
    if monthly_rate > 0:
        monthly_pi = loan_amount * (monthly_rate * (1 + monthly_rate)**n_payments) / \
                     ((1 + monthly_rate)**n_payments - 1)
    else:
        monthly_pi = loan_amount / n_payments

    # Property tax (use listing data if available, else estimate)
    if row.get("tax") and not pd.isna(row["tax"]):
        monthly_tax = row["tax"] / 12
    else:
        monthly_tax = (price * f["property_tax_rate"]) / 12

    # Insurance
    monthly_insurance = f["insurance_annual"] / 12

    # Total monthly PITI
    monthly_piti = monthly_pi + monthly_tax + monthly_insurance

    # Total cash needed
    closing_costs = price * f["closing_cost_pct"]
    total_cash_needed = down_payment + closing_costs + f["rehab_budget"]

    row.update({
        "down_payment": down_payment,
        "loan_amount": loan_amount,
        "monthly_pi": monthly_pi,
        "monthly_tax": monthly_tax,
        "monthly_insurance": monthly_insurance,
        "monthly_piti": monthly_piti,
        "closing_costs": closing_costs,
        "total_cash_needed": total_cash_needed,
    })
    return row
```

### Task 5: analysis.py — Layer 3: Financial Calculations

Pure functions. No I/O. Comprehensive tests possible.

Core calculations:
1. `calc_cash_flow(monthly_rent, monthly_piti, vacancy_rate, mgmt_pct, maintenance_monthly)`
2. `calc_returns(noi, total_cash_needed, property_value)` → cap_rate, COC, ROI
3. `calc_amortization(loan_amount, rate, term_years)` → yearly schedule
4. `calc_projections(analysis, years)` → year-by-year table
5. `calc_irr(cash_flows)` → internal rate of return (numpy financial or manual)

Output shape per analysis:

```python
@dataclass
class AnalysisResult:
    # Purchase
    list_price: float
    down_payment: float
    loan_amount: float
    closing_costs: float
    rehab_budget: float
    total_cash_needed: float

    # Monthly
    monthly_pi: float
    monthly_tax: float
    monthly_insurance: float
    monthly_piti: float
    estimated_monthly_rent: float
    vacancy_loss: float
    mgmt_fee: float
    maintenance: float
    monthly_cash_flow: float

    # Annual
    annual_noi: float
    annual_cash_flow: float

    # Returns
    cap_rate: float
    coc_return: float
    price_per_sqft: float
    rent_to_value: float
    gross_rent_multiplier: float
    break_even_ratio: float
    debt_coverage_ratio: float

    # Projections
    projections: list  # [{year, property_value, loan_balance, equity, cumulative_cf, total_profit}]
```

### Task 6: report.py — Layer 4: Report Generation

Jinja2 HTML template → WeasyPrint PDF.

Report sections (matching dealcheck.io style):
1. **Header** — address, price, key metrics in a summary bar
2. **Property Overview** — beds, baths, sqft, lot, year built, days on market
3. **Purchase Analysis** — price, down payment, loan, closing costs, total cash
4. **Monthly Cash Flow** — rent, PITI breakdown, vacancy, mgmt, maintenance, net CF
5. **Return Metrics** — cap rate, COC, ROI, GRM, DCR, BER, rent-to-value
6. **10-Year Projections** — year-by-year table (value, loan, equity, CF, profit)
7. **Assumptions** — all financial parameters used

PDF output: `data/reports/{address_slug}_{date}.pdf`

### Task 7: run.py — Main Entry Point

Orchestrates the full pipeline:

```python
def main():
    # 1. Search
    listings = search_listings()

    # 2. Find new
    new_listings = [row for _, row in listings.iterrows()
                    if is_new_listing(row["listing_id"])]

    if not new_listings:
        print("No new listings found.")
        return

    # 3. Process each
    reports = []
    for row in new_listings:
        enriched = enrich_listing(row)
        analysis = analyze(enriched)
        report_path = generate_report(analysis)
        save_listing(row)
        mark_analyzed(row["listing_id"], report_path)
        reports.append((row, report_path))

    # 4. Notify
    send_notification(reports)
```

### Task 8: notify.py — Layer 5: Delivery

For now: print summary + save report paths to a log file.
Later: Telegram notification via Hermes cron.

### Task 9: templates/report.html — PDF Template

Clean, professional HTML/CSS. Sections match dealcheck.io report style:
- Summary bar at top (price, beds/baths, sqft, key metrics)
- Clean tables for cash flow and projections
- Professional typography (system fonts, no external deps)

### Task 10: Cron Integration

Hermes cron job that runs `run.py` every 8 hours.
Output goes to local file. Optional Telegram delivery.

## Execution Order

```
Step 1: config.py + db.py              (foundation)
Step 2: search.py                      (listing monitor)
Step 3: enrich.py + analysis.py        (financial engine)
Step 4: templates/report.html          (PDF template)
Step 5: report.py                      (PDF generation)
Step 6: run.py                         (orchestration)
Step 7: notify.py                      (delivery)
Step 8: Cron job setup                 (scheduling)
```

## Testing Strategy

- Each layer testable independently
- `search.py`: run once, verify DataFrame shape and columns
- `analysis.py`: unit test with known inputs/outputs (use dealcheck.io sample report as ground truth)
- `report.py`: generate one report, visually inspect PDF
- `run.py`: end-to-end dry run

## Out of Scope (for now)

- Multiple zip codes
- Rent estimation from market data (using manual $/sqft estimate)
- Comparable sales analysis
- Owner lookup
- Interactive web UI
