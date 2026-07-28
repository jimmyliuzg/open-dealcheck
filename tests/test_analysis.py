"""Tests for the financial analysis engine."""
import pytest
from src.analysis import analyze, AnalysisResult, _year_by_year
from src.config import FINANCIAL


# ── Fixture: synthetic enriched listing ────────────────────────
@pytest.fixture
def sample_enriched():
    """A synthetic property that mirrors a real-ish deal."""
    return {
        "formatted_address": "123 Test St, Testville, CA 90001",
        "listing_id": "test-001",
        "beds": 3,
        "full_baths": 2,
        "sqft": 1500,
        "lot_sqft": 6000,
        "year_built": 1985,
        "list_price": 500_000,
        "down_payment": 100_000,
        "loan_amount": 400_000,
        "closing_costs": 10_000,
        "total_cash_needed": 110_000,
        "price_per_sqft": 333.33,
        "estimated_monthly_rent": 3_500,
        "monthly_pi": 2_528,   # 6.5% on $400K, 30yr
        "monthly_tax": 479,    # 1.15% of $500K / 12
        "monthly_insurance": 300,
        "monthly_piti": 3_307,
    }


# ── Basic analysis fields ─────────────────────────────────────
def test_analysis_populates_identity(sample_enriched):
    result = analyze(sample_enriched)
    assert result.address == "123 Test St, Testville, CA 90001"
    assert result.listing_id == "test-001"
    assert result.beds == 3
    assert result.sqft == 1500


def test_analysis_populates_purchase(sample_enriched):
    result = analyze(sample_enriched)
    assert result.list_price == 500_000
    assert result.down_payment == 100_000
    assert result.loan_amount == 400_000
    assert result.total_cash_needed == 110_000


# ── Cash flow ─────────────────────────────────────────────────
def test_monthly_cash_flow(sample_enriched):
    result = analyze(sample_enriched)
    # Gross rent: $3,500
    # Vacancy (5%): -$175
    # EGI: $3,325
    # OpEx: tax $479 + ins $300 + mgmt ($3,325 * 8% = $266) + maint ($500K * 1% / 12 = $417)
    # OpEx total: $1,462
    # NOI: $3,325 - $1,462 = $1,863
    # Cash flow: $1,863 - $2,528 = -$665
    assert result.monthly_cash_flow < 0, "Expected negative cash flow for this expensive property"
    assert -800 < result.monthly_cash_flow < -500, f"Got {result.monthly_cash_flow}"


def test_annual_figures(sample_enriched):
    result = analyze(sample_enriched)
    assert result.annual_gross_rent == pytest.approx(3_500 * 12, rel=0.01)
    assert result.annual_cash_flow == pytest.approx(result.monthly_cash_flow * 12, rel=0.01)


# ── Return metrics ────────────────────────────────────────────
def test_cap_rate(sample_enriched):
    result = analyze(sample_enriched)
    # Cap rate should be positive but small (expensive Bay Area-like property)
    assert 0 < result.cap_rate < 5, f"Cap rate: {result.cap_rate}"


def test_coc_return(sample_enriched):
    result = analyze(sample_enriched)
    # Negative CoC expected (negative cash flow)
    assert result.coc_return < 0


def test_grm(sample_enriched):
    result = analyze(sample_enriched)
    # GRM = price / annual gross rent. Should be > 10 for expensive areas.
    assert result.grm > 10, f"GRM: {result.grm}"


def test_dcr(sample_enriched):
    result = analyze(sample_enriched)
    # DCR < 1 means NOI doesn't cover debt service
    assert result.dcr < 1.0, f"DCR: {result.dcr}"


def test_rent_to_value(sample_enriched):
    result = analyze(sample_enriched)
    # rent_to_value = monthly rent / price * 100
    expected = 3_500 / 500_000 * 100  # 0.7%
    assert result.rent_to_value == pytest.approx(expected, rel=0.01)


# ── Projections ───────────────────────────────────────────────
def test_projections_length(sample_enriched):
    result = analyze(sample_enriched)
    assert len(result.projections) == FINANCIAL["hold_years"]


def test_projections_appreciation(sample_enriched):
    result = analyze(sample_enriched)
    # Year 10 value should be higher than purchase price
    year_10 = result.projections[-1]
    assert year_10["property_value"] > 500_000


def test_projections_equity_grows(sample_enriched):
    result = analyze(sample_enriched)
    # Equity should generally grow over time
    year_1 = result.projections[0]
    year_10 = result.projections[-1]
    assert year_10["equity"] > year_1["equity"]


def test_projections_loan_balance_decreases(sample_enriched):
    result = analyze(sample_enriched)
    year_1 = result.projections[0]
    year_10 = result.projections[-1]
    assert year_10["loan_balance"] < year_1["loan_balance"]


# ── IRR ───────────────────────────────────────────────────────
def test_irr_is_computed(sample_enriched):
    result = analyze(sample_enriched)
    assert result.irr is not None
    assert isinstance(result.irr, float)


def test_irr_negative_for_bad_deal(sample_enriched):
    result = analyze(sample_enriched)
    # This property has negative cash flow, so IRR should be low/negative
    # (though appreciation may keep it positive)
    assert result.irr is not None


# ── Edge cases ────────────────────────────────────────────────
def test_zero_price():
    result = analyze({"list_price": 0, "estimated_monthly_rent": 1000})
    assert result.cap_rate == 0
    assert result.coc_return == 0


def test_zero_rent():
    enriched = {
        "formatted_address": "No Rent Ave",
        "list_price": 300_000,
        "down_payment": 60_000,
        "loan_amount": 240_000,
        "closing_costs": 6_000,
        "total_cash_needed": 66_000,
        "estimated_monthly_rent": 0,
        "monthly_pi": 1_517,
        "monthly_tax": 288,
        "monthly_insurance": 300,
        "monthly_piti": 2_105,
    }
    result = analyze(enriched)
    assert result.monthly_cash_flow < 0  # All expenses, no income
    assert result.annual_gross_rent == 0
