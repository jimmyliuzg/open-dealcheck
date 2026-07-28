"""
OpenDealCheck — Property Enrichment
Layer 2: Adds calculated financial fields to raw listing data.
Integrates comp data when available for better rent estimation.
"""
import numpy as np
from typing import Optional

from src.config import FINANCIAL


def enrich_listing(row: dict, comps=None) -> dict:
    """
    Take a normalized listing dict and add PITI, closing costs, cash needed.
    
    If comps (CompsResult) is provided, uses comp-based rent estimation
    instead of the simple $/sqft fallback.
    
    Modifies the dict in-place and returns it.
    """
    price = row.get("list_price", 0)
    if price <= 0:
        return row

    f = FINANCIAL

    # ── Down payment ──────────────────────────────────────────
    down_payment = price * f["down_payment_pct"]

    # ── Loan amount ───────────────────────────────────────────
    loan_amount = price - down_payment

    # ── Monthly mortgage (P&I) ────────────────────────────────
    monthly_rate = f["interest_rate"] / 12
    n_payments = f["loan_term_years"] * 12
    if monthly_rate > 0:
        monthly_pi = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** n_payments
        ) / ((1 + monthly_rate) ** n_payments - 1)
    else:
        monthly_pi = loan_amount / n_payments

    # ── Property tax ──────────────────────────────────────────
    tax = row.get("tax")
    if tax and tax > 0:
        monthly_tax = float(tax) / 12
    else:
        monthly_tax = (price * f["property_tax_rate"]) / 12

    # ── Insurance ─────────────────────────────────────────────
    monthly_insurance = f["insurance_annual"] / 12

    # ── Total PITI ────────────────────────────────────────────
    monthly_piti = monthly_pi + monthly_tax + monthly_insurance

    # ── Transaction costs ─────────────────────────────────────
    closing_costs = price * f["closing_cost_pct"]
    total_cash_needed = down_payment + closing_costs + f["rehab_budget"]

    # ── Price per sqft ────────────────────────────────────────
    sqft = row.get("sqft", 0)
    price_per_sqft = price / sqft if sqft > 0 else 0

    # ── Estimated rent (comps-aware) ──────────────────────────
    if comps and comps.estimated_rent > 0:
        estimated_monthly_rent = comps.estimated_rent
    else:
        estimated_monthly_rent = sqft * f["rent_estimate_sqft"] if sqft > 0 else 0

    row.update({
        "down_payment": round(down_payment, 2),
        "loan_amount": round(loan_amount, 2),
        "monthly_pi": round(monthly_pi, 2),
        "monthly_tax": round(monthly_tax, 2),
        "monthly_insurance": round(monthly_insurance, 2),
        "monthly_piti": round(monthly_piti, 2),
        "closing_costs": round(closing_costs, 2),
        "total_cash_needed": round(total_cash_needed, 2),
        "price_per_sqft": round(price_per_sqft, 2),
        "estimated_monthly_rent": round(estimated_monthly_rent, 2),
    })

    # ── Attach comp metadata if available ─────────────────────
    if comps:
        row["rent_source"] = comps.rent_source
        row["rent_comp_count"] = comps.rent_comp_count
        row["median_rent"] = comps.median_rent
        row["median_rent_per_sqft"] = comps.median_rent_per_sqft
        row["arv"] = comps.arv
        row["arv_source"] = comps.arv_source
        row["sale_comp_count"] = comps.sale_comp_count
        row["median_sale_price"] = comps.median_sale_price
        row["median_sale_price_per_sqft"] = comps.median_sale_price_per_sqft
        row["rent_comps"] = comps.rent_comps
        row["sale_comps"] = comps.sale_comps

    return row
