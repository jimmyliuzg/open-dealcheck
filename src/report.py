"""
OpenDealCheck — Report Generation
Layer 4: Jinja2 HTML → WeasyPrint PDF.
"""
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from src.analysis import AnalysisResult
from src.config import FINANCIAL, PROJECT_ROOT, REPORTS_DIR

logger = logging.getLogger(__name__)

# Jinja2 environment
_template_env = Environment(
    loader=FileSystemLoader(str(PROJECT_ROOT / "templates")),
    autoescape=True,
)


def generate_report(analysis: AnalysisResult) -> str:
    """
    Generate a PDF report from an AnalysisResult.
    
    Returns the path to the generated PDF.
    """
    template = _template_env.get_template("report.html")

    # Build template context
    f = FINANCIAL
    context = {
        # Identity
        "address": analysis.address,
        "generated_date": datetime.now().strftime("%B %d, %Y"),

        # Property
        "beds": analysis.beds,
        "baths": analysis.baths,
        "sqft": analysis.sqft,
        "lot_sqft": analysis.lot_sqft,
        "year_built": analysis.year_built,

        # Purchase
        "list_price": analysis.list_price,
        "down_payment": analysis.down_payment,
        "down_payment_pct": f["down_payment_pct"] * 100,
        "loan_amount": analysis.loan_amount,
        "interest_rate_pct": f["interest_rate"] * 100,
        "loan_term_years": f["loan_term_years"],
        "closing_costs": analysis.closing_costs,
        "rehab_budget": analysis.rehab_budget,
        "total_cash_needed": analysis.total_cash_needed,
        "price_per_sqft": analysis.price_per_sqft,

        # Monthly cash flow
        "estimated_monthly_rent": analysis.estimated_monthly_rent,
        "vacancy_loss": analysis.vacancy_loss,
        "vacancy_pct": f["vacancy_rate"] * 100,
        "effective_gross_income": analysis.estimated_monthly_rent - analysis.vacancy_loss,
        "monthly_pi": analysis.monthly_pi,
        "monthly_tax": analysis.monthly_tax,
        "monthly_insurance": analysis.monthly_insurance,
        "mgmt_fee": analysis.mgmt_fee,
        "mgmt_pct": f["property_mgmt_pct"] * 100,
        "maintenance": analysis.maintenance,
        "monthly_cash_flow": analysis.monthly_cash_flow,

        # Returns
        "cap_rate": analysis.cap_rate,
        "coc_return": analysis.coc_return,
        "irr": analysis.irr,
        "grm": analysis.grm,
        "dcr": analysis.dcr,
        "rent_to_value": analysis.rent_to_value,
        "break_even_ratio": analysis.break_even_ratio,
        "annual_noi": analysis.annual_noi,
        "annual_cash_flow": analysis.annual_cash_flow,
        "hold_years": f["hold_years"],

        # Projections
        "projections": analysis.projections,

        # Assumptions footer
        "assumptions": {
            "Down Payment": f"{f['down_payment_pct']*100:.0f}%",
            "Interest Rate": f"{f['interest_rate']*100:.1f}%",
            "Loan Term": f"{f['loan_term_years']} years",
            "Property Tax Rate": f"{f['property_tax_rate']*100:.2f}%",
            "Insurance": f"${f['insurance_annual']:,}/yr",
            "Vacancy": f"{f['vacancy_rate']*100:.0f}%",
            "Property Mgmt": f"{f['property_mgmt_pct']*100:.0f}% of gross rent",
            "Maintenance": f"{f['maintenance_pct']*100:.0f}% of value/yr",
            "Closing Costs": f"{f['closing_cost_pct']*100:.0f}% of price",
            "Appreciation": f"{f['appreciation_rate']*100:.0f}%/yr",
            "Rent Growth": f"{f['rent_growth_rate']*100:.0f}%/yr",
            "Rent Estimate": f"${f['rent_estimate_sqft']:.2f}/sqft/mo",
        },
    }

    # Render HTML
    html_content = template.render(**context)

    # Generate PDF filename
    safe_address = analysis.address.replace(" ", "_").replace(",", "").replace("/", "-")[:60]
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{safe_address}_{date_str}.pdf"
    output_path = REPORTS_DIR / filename

    # Write PDF
    HTML(string=html_content).write_pdf(str(output_path))

    logger.info(f"Report generated: {output_path}")
    return str(output_path)
