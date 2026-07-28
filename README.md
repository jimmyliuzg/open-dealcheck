# OpenDealCheck

Automated real estate deal-finding pipeline. Monitors new listings on Realtor.com,
runs financial analysis, and generates PDF reports — like dealcheck.io but
self-hosted and free.

## What it does

1. **Search** — Scans Realtor.com for listings matching your criteria (zip, beds,
   baths, sqft, price range)
2. **Enrich** — Calculates PITI, closing costs, total cash needed
3. **Analyze** — Cap rate, CoC, IRR, DCR, GRM, 10-year projections
4. **Report** — Generates a PDF report per listing (like dealcheck.io's purchase report)
5. **Dedup** — SQLite tracks seen listings so you only see new ones

## Quick start

```bash
cd ~/Desktop/Projects/open-dealcheck
source .venv/bin/activate

# Dry run (no DB writes, no comps — fast)
python run.py --dry-run --no-comps

# Full run (saves to DB, fetches comps)
python run.py

# Single zip override
python run.py --zip 94087

# Re-analyze everything (ignore dedup)
python run.py --force
```

## Configuration

Edit `src/config.py` to change search criteria and financial assumptions:

```python
SEARCH = {
    "location": "94087",           # zip code
    "beds_min": 3, "beds_max": 3,
    "baths_min": 2, "baths_max": 2,
    "sqft_min": 1000, "sqft_max": 2000,
    "lot_sqft_min": 5000,          # post-hoc filter (may be NaN)
    "price_min": 1_600_000,
    "price_max": 1_800_000,
}

FINANCIAL = {
    "down_payment_pct": 0.20,
    "interest_rate": 0.065,
    "rent_estimate_sqft": 3.50,    # $/sqft/mo — tune to local market
    # ... see config.py for all options
}
```

## CLI flags

| Flag | What it does |
|------|-------------|
| `--dry-run` | Search + analyze, don't save to DB |
| `--force` | Re-analyze all listings (skip dedup) |
| `--zip 94087` | Override search zip code |
| `--no-comps` | Skip rent/sale comps (uses $/sqft estimate) |

## Reports

PDF reports are saved to `data/reports/`. Each report includes:
- Summary bar (price, rent, cash flow, cap rate, CoC)
- Purchase analysis (down payment, loan, closing costs, total cash)
- Monthly cash flow breakdown (rent → vacancy → PITI → net)
- Return metrics (cap rate, CoC, IRR, DCR, GRM, rent-to-value)
- 10-year projections (value, loan balance, equity, cumulative cash flow)
- Assumptions footer

## Data sources

- **Listings:** Realtor.com via [HomeHarvest](https://github.com/ZacharyHampton/HomeHarvest) (free, pip install)
- **Comps:** Optional — rent + sale comparables from Realtor.com (adds ~2 API calls per listing)
- **Tax data:** Realtor.com tax field when available, else 1.15% of price estimate

## Tech stack

- Python 3.14, pandas, numpy, numpy-financial
- HomeHarvest (Realtor.com scraper)
- Jinja2 + WeasyPrint (PDF generation)
- SQLite (listing dedup/tracking)

## License

AGPL-3.0
