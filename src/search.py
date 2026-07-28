"""
OpenDealCheck — Listing Search
Layer 1: HomeHarvest wrapper for Realtor.com listing scraping.
"""
import logging
from typing import Optional

import pandas as pd

from src.config import SEARCH

logger = logging.getLogger(__name__)


def search_listings(
    location: Optional[str] = None,
    listing_type: Optional[str] = None,
    beds_min: Optional[int] = None,
    beds_max: Optional[int] = None,
    baths_min: Optional[int] = None,
    baths_max: Optional[int] = None,
    sqft_min: Optional[int] = None,
    sqft_max: Optional[int] = None,
    lot_sqft_min: Optional[int] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
) -> pd.DataFrame:
    """
    Search Realtor.com for matching listings via HomeHarvest.
    
    Any parameter not provided falls back to SEARCH config defaults.
    Returns a DataFrame with listing data (may be empty).
    """
    from homeharvest import scrape_property

    params = {
        "location": location or SEARCH["location"],
        "listing_type": listing_type or SEARCH["listing_type"],
        "beds_min": beds_min if beds_min is not None else SEARCH.get("beds_min"),
        "beds_max": beds_max if beds_max is not None else SEARCH.get("beds_max"),
        "baths_min": baths_min if baths_min is not None else SEARCH.get("baths_min"),
        "baths_max": baths_max if baths_max is not None else SEARCH.get("baths_max"),
        "sqft_min": sqft_min if sqft_min is not None else SEARCH.get("sqft_min"),
        "sqft_max": sqft_max if sqft_max is not None else SEARCH.get("sqft_max"),
        # NOTE: lot_sqft_min is NOT passed to HomeHarvest — Realtor.com
        # often returns NaN for lot_sqft, and HomeHarvest filters out NaN
        # entries, killing all results. Filter is done post-hoc below.
        "price_min": price_min if price_min is not None else SEARCH.get("price_min"),
        "price_max": price_max if price_max is not None else SEARCH.get("price_max"),
    }

    # Filter out None values so HomeHarvest uses its own defaults
    params = {k: v for k, v in params.items() if v is not None}

    logger.info(f"Searching: {params}")
    results = scrape_property(**params)

    if results is None or results.empty:
        logger.info("No listings found matching criteria.")
        return pd.DataFrame()

    logger.info(f"Found {len(results)} listings.")
    return results


def normalize_listing(row: pd.Series) -> dict:
    """
    Normalize a HomeHarvest DataFrame row into our standard format.
    Handles column name variations between HomeHarvest versions.
    """
    def _get(row, *keys, default=None):
        """Try multiple possible column names."""
        for key in keys:
            if key in row.index:
                val = row[key]
                if pd.notna(val):
                    return val
        return default

    normalized = {
        "listing_id": str(_get(row, "listing_id", "id", default="")),
        "property_url": _get(row, "property_url", "url", "link", default=""),
        "formatted_address": _get(row, "formatted_address", "address", "street_address", default=""),
        "city": _get(row, "city", default=""),
        "state": _get(row, "state", default=""),
        "zip_code": str(_get(row, "zip_code", "zip", "zipcode", default="")),
        "beds": int(_get(row, "beds", "bedrooms", default=0)),
        "full_baths": int(_get(row, "full_baths", "bathrooms", "baths", default=0)),
        "half_baths": int(_get(row, "half_baths", default=0)),
        "sqft": float(_get(row, "sqft", "square_footage", "living_area", default=0)),
        "lot_sqft": float(_get(row, "lot_sqft", "lot_size", "lot_area", default=0)),
        "list_price": float(_get(row, "list_price", "price", "listing_price", default=0)),
        "year_built": int(_get(row, "year_built", "year", default=0)),
        "days_on_mls": int(_get(row, "days_on_mls", "days_on_market", default=0)),
        "estimated_value": _get(row, "estimated_value", "avm", "zestimate", default=0),
        "assessed_value": _get(row, "assessed_value", default=0),
        "tax": _get(row, "tax", "annual_tax", "property_tax", default=0),
        "latitude": _get(row, "latitude", "lat", default=0),
        "longitude": _get(row, "longitude", "lon", "lng", default=0),
    }

    # Post-hoc lot size filter (HomeHarvest can't filter NaN lot_sqft)
    lot_min = SEARCH.get("lot_sqft_min")
    if lot_min and normalized["lot_sqft"] > 0 and normalized["lot_sqft"] < lot_min:
        return None  # Caller should skip this listing
    if lot_min and normalized["lot_sqft"] == 0:
        logger.debug(f"Listing {normalized['formatted_address']}: lot_sqft unknown, including anyway")

    return normalized
