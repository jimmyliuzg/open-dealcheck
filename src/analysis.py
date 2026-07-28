"""
OpenDealCheck — Financial Analysis Engine
Layer 3: Pure calculations, no I/O. All the investment metrics.

Metrics computed:
- Cash flow (monthly & annual)
- Cap rate, Cash-on-Cash return, ROI
- Gross Rent Multiplier (GRM)
- Debt Coverage Ratio (DCR)
- Break-Even Ratio (BER)
- Rent-to-Value ratio
- 10-year projections (value, loan balance, equity, cumulative cash flow)
"""
import numpy as np
import numpy_financial as npf
from dataclasses import dataclass, field
from typing import Optional

from src.config import FINANCIAL


@dataclass
class AnalysisResult:
    """Complete financial analysis for a single property."""
    # ── Identity ──────────────────────────────────────────────
    address: str = ""
    listing_id: str = ""

    # ── Purchase ──────────────────────────────────────────────
    list_price: float = 0
    down_payment: float = 0
    loan_amount: float = 0
    closing_costs: float = 0
    rehab_budget: float = 0
    total_cash_needed: float = 0

    # ── Property ──────────────────────────────────────────────
    beds: int = 0
    baths: int = 0
    sqft: float = 0
    lot_sqft: float = 0
    year_built: int = 0
    price_per_sqft: float = 0

    # ── Monthly costs ─────────────────────────────────────────
    monthly_pi: float = 0
    monthly_tax: float = 0
    monthly_insurance: float = 0
    monthly_piti: float = 0

    # ── Rental income ─────────────────────────────────────────
    estimated_monthly_rent: float = 0
    vacancy_loss: float = 0
    mgmt_fee: float = 0
    maintenance: float = 0
    monthly_cash_flow: float = 0

    # ── Annual ────────────────────────────────────────────────
    annual_gross_rent: float = 0
    annual_expenses: float = 0
    annual_noi: float = 0
    annual_cash_flow: float = 0

    # ── Return metrics ────────────────────────────────────────
    cap_rate: float = 0
    coc_return: float = 0
    grm: float = 0
    dcr: float = 0
    break_even_ratio: float = 0
    rent_to_value: float = 0

    # ── IRR ───────────────────────────────────────────────────
    irr: Optional[float] = None

    # ── Market comps ──────────────────────────────────────────
    rent_source: str = ""           # "comps" or "estimate"
    rent_comp_count: int = 0
    median_rent: float = 0
    median_rent_per_sqft: float = 0
    sale_comp_count: int = 0
    median_sale_price: float = 0
    median_sale_price_per_sqft: float = 0
    arv: float = 0                  # After Repair Value
    arv_source: str = ""            # "comps" or "listing_price"

    # ── Projections ───────────────────────────────────────────
    projections: list = field(default_factory=list)


def analyze(enriched: dict) -> AnalysisResult:
    """
    Run full financial analysis on an enriched listing dict.
    
    Returns an AnalysisResult with all metrics computed.
    """
    f = FINANCIAL
    result = AnalysisResult()

    # ── Copy identity fields ──────────────────────────────────
    result.address = enriched.get("formatted_address", "")
    result.listing_id = enriched.get("listing_id", "")
    result.beds = enriched.get("beds", 0)
    result.baths = enriched.get("full_baths", 0)
    result.sqft = enriched.get("sqft", 0)
    result.lot_sqft = enriched.get("lot_sqft", 0)
    result.year_built = enriched.get("year_built", 0)

    # ── Purchase metrics (from enrichment) ────────────────────
    result.list_price = enriched.get("list_price", 0)
    result.down_payment = enriched.get("down_payment", 0)
    result.loan_amount = enriched.get("loan_amount", 0)
    result.closing_costs = enriched.get("closing_costs", 0)
    result.rehab_budget = f["rehab_budget"]
    result.total_cash_needed = enriched.get("total_cash_needed", 0)
    result.price_per_sqft = enriched.get("price_per_sqft", 0)

    # ── Market comps (from enrichment) ────────────────────────
    result.rent_source = enriched.get("rent_source", "estimate")
    result.rent_comp_count = enriched.get("rent_comp_count", 0)
    result.median_rent = enriched.get("median_rent", 0)
    result.median_rent_per_sqft = enriched.get("median_rent_per_sqft", 0)
    result.sale_comp_count = enriched.get("sale_comp_count", 0)
    result.median_sale_price = enriched.get("median_sale_price", 0)
    result.median_sale_price_per_sqft = enriched.get("median_sale_price_per_sqft", 0)
    result.arv = enriched.get("arv", 0)
    result.arv_source = enriched.get("arv_source", "listing_price")

    # ── Monthly PITI (from enrichment) ────────────────────────
    result.monthly_pi = enriched.get("monthly_pi", 0)
    result.monthly_tax = enriched.get("monthly_tax", 0)
    result.monthly_insurance = enriched.get("monthly_insurance", 0)
    result.monthly_piti = enriched.get("monthly_piti", 0)

    # ── Rental income ─────────────────────────────────────────
    result.estimated_monthly_rent = enriched.get("estimated_monthly_rent", 0)
    gross_monthly_rent = result.estimated_monthly_rent

    # Vacancy loss
    result.vacancy_loss = gross_monthly_rent * f["vacancy_rate"]

    # Effective gross income
    effective_gross_income = gross_monthly_rent - result.vacancy_loss

    # Property management fee (% of effective gross)
    result.mgmt_fee = effective_gross_income * f["property_mgmt_pct"]

    # Maintenance (1% of property value / 12)
    result.maintenance = (result.list_price * f["maintenance_pct"]) / 12

    # Operating expenses (excluding mortgage)
    monthly_opex = (
        result.monthly_tax
        + result.monthly_insurance
        + result.mgmt_fee
        + result.maintenance
    )

    # Net operating income (monthly, before mortgage)
    monthly_noi = effective_gross_income - monthly_opex

    # Cash flow (after mortgage)
    result.monthly_cash_flow = monthly_noi - result.monthly_pi

    # ── Annual figures ────────────────────────────────────────
    result.annual_gross_rent = gross_monthly_rent * 12
    result.annual_expenses = monthly_opex * 12
    result.annual_noi = monthly_noi * 12
    result.annual_cash_flow = result.monthly_cash_flow * 12

    # ── Return metrics ────────────────────────────────────────
    price = result.list_price

    # Cap rate = NOI / purchase price
    result.cap_rate = (result.annual_noi / price * 100) if price > 0 else 0

    # Cash-on-Cash = annual cash flow / total cash invested
    result.coc_return = (
        (result.annual_cash_flow / result.total_cash_needed * 100)
        if result.total_cash_needed > 0
        else 0
    )

    # GRM = price / annual gross rent
    result.grm = (
        price / result.annual_gross_rent
        if result.annual_gross_rent > 0
        else 0
    )

    # DCR = NOI / annual debt service
    annual_debt_service = result.monthly_pi * 12
    result.dcr = (
        result.annual_noi / annual_debt_service
        if annual_debt_service > 0
        else 0
    )

    # Break-even ratio = (PITI + opex) / gross rent
    annual_piti_plus_opex = (result.monthly_piti + monthly_opex) * 12
    result.break_even_ratio = (
        annual_piti_plus_opex / result.annual_gross_rent * 100
        if result.annual_gross_rent > 0
        else 0
    )

    # Rent-to-value = monthly rent / price
    result.rent_to_value = (
        gross_monthly_rent / price * 100 if price > 0 else 0
    )

    # ── 10-Year Projections ───────────────────────────────────
    result.projections = _calc_projections(result, f)

    # ── IRR ───────────────────────────────────────────────────
    result.irr = _calc_irr(result, f)

    return result


def _calc_projections(r: AnalysisResult, f: dict) -> list[dict]:
    """
    Year-by-year projection table.
    
    Each row: year, property_value, loan_balance, equity, 
              annual_cash_flow, cumulative_cash_flow, total_profit
    """
    projections = []
    value = r.list_price
    balance = r.loan_amount
    cum_cf = 0
    annual_rent = r.annual_gross_rent
    annual_pi = r.monthly_pi * 12

    for year in range(1, f["hold_years"] + 1):
        # Property appreciation
        value *= (1 + f["appreciation_rate"])

        # Rent growth → recalculate NOI
        annual_rent *= (1 + f["rent_growth_rate"])

        # Expense growth (tax, insurance, maintenance, mgmt)
        annual_vacancy = annual_rent * f["vacancy_rate"]
        annual_egi = annual_rent - annual_vacancy
        annual_opex = r.annual_expenses * (1 + f["expense_growth_rate"]) ** year
        annual_noi = annual_egi - annual_opex

        # Cash flow = NOI - debt service
        annual_cf = annual_noi - annual_pi
        cum_cf += annual_cf

        # Loan balance (amortization)
        for _ in range(12):
            if balance > 0:
                interest = balance * (f["interest_rate"] / 12)
                principal = annual_pi / 12 - interest
                balance = max(0, balance - principal)

        equity = value - max(0, balance)
        total_profit = equity + cum_cf - r.total_cash_needed

        projections.append({
            "year": year,
            "property_value": round(value, 0),
            "loan_balance": round(max(0, balance), 0),
            "equity": round(equity, 0),
            "annual_rent": round(annual_rent, 0),
            "annual_noi": round(annual_noi, 0),
            "annual_cash_flow": round(annual_cf, 0),
            "cumulative_cash_flow": round(cum_cf, 0),
            "total_profit": round(total_profit, 0),
        })

    return projections


def _calc_irr(r: AnalysisResult, f: dict) -> Optional[float]:
    """
    Internal Rate of Return on the investment.
    
    Cash flows: Year 0 = -total_cash_needed, Years 1-N = annual cash flow + equity gain
    """
    cash_flows = [-r.total_cash_needed]

    # Simulate year-by-year for IRR
    value = r.list_price
    balance = r.loan_amount
    annual_rent = r.annual_gross_rent
    annual_pi = r.monthly_pi * 12

    for year in range(1, f["hold_years"] + 1):
        value *= (1 + f["appreciation_rate"])
        annual_rent *= (1 + f["rent_growth_rate"])
        annual_vacancy = annual_rent * f["vacancy_rate"]
        annual_egi = annual_rent - annual_vacancy
        annual_opex = r.annual_expenses * (1 + f["expense_growth_rate"]) ** year
        annual_noi = annual_egi - annual_opex
        annual_cf = annual_noi - annual_pi

        for _ in range(12):
            if balance > 0:
                interest = balance * (f["interest_rate"] / 12)
                principal = annual_pi / 12 - interest
                balance = max(0, balance - principal)

        if year == f["hold_years"]:
            # Final year: cash flow + sale proceeds (equity)
            sale_proceeds = value - max(0, balance)
            cash_flows.append(annual_cf + sale_proceeds)
        else:
            cash_flows.append(annual_cf)

    try:
        irr = npf.irr(cash_flows)
        return round(irr * 100, 2) if np.isfinite(irr) else None
    except Exception:
        return None
