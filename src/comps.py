"""
OpenDealCheck — Comparable Properties
Phase 3: Fetch rent comps and sale comps via HomeHarvest.

Uses Realtor.com data through HomeHarvest to find:
- Rental comps (active for_rent listings near the property)
- Sale comps (recently sold properties near the property)
- Market statistics (median rent, median sale price, $/sqft trends)
"""
import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class RentComp:
    """A single rental comparable."""
    address: str
    price: float  # monthly rent
    beds: int
    baths: float
    sqft: float
    price_per_sqft: float = 0
    property_url: str = ""

    def __post_init__(self):
        if self.sqft > 0 and self.price > 0:
            self.price_per_sqft = round(self.price / self.sqft, 2)


@dataclass
class SaleComp:
    """A single sale comparable."""
    address: str
    price: float  # sold price
    beds: int
    baths: float
    sqft: float
    price_per_sqft: float = 0
    sold_date: str = ""
    property_url: str = ""

    def __post_init__(self):
        if self.sqft > 0 and self.price > 0:
            self.price_per_sqft = round(self.price / self.sqft, 2)


@dataclass
class CompsResult:
    """Aggregated comparable properties data."""
    # Rent comps
    rent_comps: list[RentComp] = field(default_factory=list)
    median_rent: float = 0
    median_rent_per_sqft: float = 0
    avg_rent: float = 0
    rent_comp_count: int = 0

    # Sale comps
    sale_comps: list[SaleComp] = field(default_factory=list)
    median_sale_price: float = 0
    median_sale_price_per_sqft: float = 0
    avg_sale_price: float = 0
    sale_comp_count: int = 0

    # Market context
    estimated_rent: float = 0  # Best rent estimate (comps or $/sqft fallback)
    rent_source: str = ""      # "comps" or "estimate"
    arv: float = 0             # After Repair Value (median of sale comps)
    arv_source: str = ""       # "comps" or "listing_price"


def fetch_rent_comps(
    address: str,
    beds: int = 0,
    baths: float = 0,
    sqft: float = 0,
    radius: float = 2.0,
    limit: int = 20,
) -> list[RentComp]:
    """
    Fetch active rental listings near a property for rent comp analysis.
    
    Uses HomeHarvest to search for_rent listings with similar characteristics
    within a radius of the subject property.
    """
    from homeharvest import scrape_property

    # Build search parameters
    params = {
        "location": address,
        "listing_type": "for_rent",
        "radius": radius,
        "limit": limit,
    }

    # Add filters similar to subject property
    if beds > 0:
        params["beds_min"] = max(1, beds - 1)
        params["beds_max"] = beds + 1
    if sqft > 0:
        params["sqft_min"] = max(500, int(sqft * 0.7))
        params["sqft_max"] = int(sqft * 1.3)

    logger.info(f"Fetching rent comps near: {address} (radius={radius}mi)")
    try:
        df = scrape_property(**params)
    except Exception as e:
        logger.warning(f"Failed to fetch rent comps: {e}")
        return []

    if df is None or df.empty:
        logger.info("No rent comps found.")
        return []

    comps = []
    for _, row in df.iterrows():
        try:
            price = float(row.get("list_price", 0) or 0)
            if price <= 0:
                continue

            comp = RentComp(
                address=str(row.get("formatted_address", row.get("street", ""))),
                price=price,
                beds=int(row.get("beds", 0) or 0),
                baths=float(row.get("full_baths", row.get("baths", 0)) or 0),
                sqft=float(row.get("sqft", 0) or 0),
                property_url=str(row.get("property_url", "")),
            )
            comps.append(comp)
        except (ValueError, TypeError) as e:
            logger.debug(f"Skipping rent comp row: {e}")
            continue

    logger.info(f"Found {len(comps)} rent comps.")
    return comps


def fetch_sale_comps(
    address: str,
    beds: int = 0,
    baths: float = 0,
    sqft: float = 0,
    radius: float = 2.0,
    past_days: int = 180,
    limit: int = 20,
) -> list[SaleComp]:
    """
    Fetch recently sold properties near a property for sale comp analysis.
    
    Uses HomeHarvest to search sold listings within a radius.
    Default window: 6 months of sales history.
    """
    from homeharvest import scrape_property

    params = {
        "location": address,
        "listing_type": "sold",
        "radius": radius,
        "past_days": past_days,
        "limit": limit,
    }

    if beds > 0:
        params["beds_min"] = max(1, beds - 1)
        params["beds_max"] = beds + 1
    if sqft > 0:
        params["sqft_min"] = max(500, int(sqft * 0.7))
        params["sqft_max"] = int(sqft * 1.3)

    logger.info(f"Fetching sale comps near: {address} (radius={radius}mi, {past_days}d)")
    try:
        df = scrape_property(**params)
    except Exception as e:
        logger.warning(f"Failed to fetch sale comps: {e}")
        return []

    if df is None or df.empty:
        logger.info("No sale comps found.")
        return []

    comps = []
    for _, row in df.iterrows():
        try:
            # For sold properties, use sold_price if available, else list_price
            price = float(row.get("sold_price", 0) or row.get("list_price", 0) or 0)
            if price <= 0:
                continue

            sold_date = ""
            if "last_sold_date" in row.index and pd.notna(row["last_sold_date"]):
                sold_date = str(row["last_sold_date"])[:10]
            elif "list_date" in row.index and pd.notna(row["list_date"]):
                sold_date = str(row["list_date"])[:10]

            comp = SaleComp(
                address=str(row.get("formatted_address", row.get("street", ""))),
                price=price,
                beds=int(row.get("beds", 0) or 0),
                baths=float(row.get("full_baths", row.get("baths", 0)) or 0),
                sqft=float(row.get("sqft", 0) or 0),
                sold_date=sold_date,
                property_url=str(row.get("property_url", "")),
            )
            comps.append(comp)
        except (ValueError, TypeError) as e:
            logger.debug(f"Skipping sale comp row: {e}")
            continue

    logger.info(f"Found {len(comps)} sale comps.")
    return comps


def compute_comps(
    address: str,
    beds: int = 0,
    baths: float = 0,
    sqft: float = 0,
    list_price: float = 0,
    rent_estimate_sqft: float = 3.50,
    radius: float = 2.0,
) -> CompsResult:
    """
    Fetch and compute all comparable data for a property.
    
    Returns a CompsResult with rent comps, sale comps, and market statistics.
    Falls back to $/sqft estimate if no rent comps are available.
    """
    result = CompsResult()

    # ── Rent comps ────────────────────────────────────────────
    result.rent_comps = fetch_rent_comps(address, beds, baths, sqft, radius)
    result.rent_comp_count = len(result.rent_comps)

    if result.rent_comps:
        rents = [c.price for c in result.rent_comps]
        rents_psf = [c.price_per_sqft for c in result.rent_comps if c.price_per_sqft > 0]

        result.median_rent = float(np.median(rents))
        result.avg_rent = float(np.mean(rents))
        result.median_rent_per_sqft = float(np.median(rents_psf)) if rents_psf else 0

        # Best rent estimate: median of comps
        result.estimated_rent = result.median_rent
        result.rent_source = "comps"
    else:
        # Fallback to $/sqft estimate
        result.estimated_rent = sqft * rent_estimate_sqft if sqft > 0 else 0
        result.rent_source = "estimate"

    # ── Sale comps ────────────────────────────────────────────
    result.sale_comps = fetch_sale_comps(address, beds, baths, sqft, radius)
    result.sale_comp_count = len(result.sale_comps)

    if result.sale_comps:
        prices = [c.price for c in result.sale_comps]
        prices_psf = [c.price_per_sqft for c in result.sale_comps if c.price_per_sqft > 0]

        result.median_sale_price = float(np.median(prices))
        result.avg_sale_price = float(np.mean(prices))
        result.median_sale_price_per_sqft = float(np.median(prices_psf)) if prices_psf else 0

        # ARV based on median sale comp price
        result.arv = result.median_sale_price
        result.arv_source = "comps"
    else:
        result.arv = list_price
        result.arv_source = "listing_price"

    return result
