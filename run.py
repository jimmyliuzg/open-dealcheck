#!/usr/bin/env python3
"""
OpenDealCheck — Main Entry Point
Orchestrates: search → dedup → enrich → analyze → report → notify

Usage:
  python run.py                  # Normal run (new listings only)
  python run.py --dry-run        # Search + analyze, don't save to DB
  python run.py --force          # Re-analyze all listings (ignore dedup)
  python run.py --zip 94087      # Override zip code
  python run.py --address "123 Main St, Sunnyvale, CA 94087" --price 1700000  # Single address
  python run.py --with-comps          # Fetch rent/sale comps (slower)
"""
import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import SEARCH, DB_PATH
from src.db import init_db, is_new_listing, save_listing, mark_analyzed, get_stats
from src.search import search_listings, normalize_listing
from src.comps import compute_comps
from src.enrich import enrich_listing
from src.analysis import analyze
from src.report import generate_report
from src.notify import notify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="OpenDealCheck listing pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Search and analyze without saving to DB")
    parser.add_argument("--force", action="store_true", help="Re-analyze all listings (skip dedup)")
    parser.add_argument("--zip", type=str, help="Override search zip code")
    parser.add_argument("--address", type=str, help="Analyze a single address (skip search)")
    parser.add_argument("--price", type=float, help="List price for --address mode (required with --address)")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--no-comps", action="store_true", help="(deprecated, comps are now opt-in)")
    parser.add_argument("--with-comps", action="store_true", help="Fetch rent/sale comps (slower, 2 extra API calls per listing)")
    args = parser.parse_args()

    if not args.quiet:
        logger.info("OpenDealCheck — starting pipeline")
        logger.info(f"Search: zip={args.zip or SEARCH['location']}, "
                     f"price=${SEARCH['price_min']:,}-${SEARCH['price_max']:,}, "
                     f"{SEARCH['beds_min']}-{SEARCH['beds_max']}bed/{SEARCH['baths_min']}-{SEARCH['baths_max']}bath")

    # ── Step 1: Initialize DB ────────────────────────────────
    if not args.dry_run:
        init_db()
        stats = get_stats()
        logger.info(f"DB: {stats['total']} tracked, {stats['analyzed']} analyzed, {stats['pending']} pending")

    # ── Step 2: Search listings ──────────────────────────────
    if args.address:
        # Single address mode — require --price
        if not args.price:
            parser.error("--price is required when using --address")
        logger.info(f"Analyzing single address: {args.address} (${args.price:,.0f})")
        raw_listing = {
            "listing_id": args.address.replace(" ", "_").lower(),
            "formatted_address": args.address,
            "list_price": args.price,
            "beds": SEARCH["beds_min"],
            "full_baths": SEARCH["baths_min"],
            "sqft": (SEARCH["sqft_min"] + SEARCH["sqft_max"]) // 2,
        }
        df = None  # No DataFrame in single-address mode
        listings = [raw_listing]
    else:
        search_kwargs = {}
        if args.zip:
            search_kwargs["location"] = args.zip

        logger.info("Searching for listings...")
        df = search_listings(**search_kwargs)

        if df is None or df.empty:
            logger.info("No listings found matching criteria.")
            return

        listings = [n for n in (normalize_listing(row) for _, row in df.iterrows()) if n is not None]
        logger.info(f"Found {len(listings)} listing(s)")

    # ── Step 3: Dedup (unless --force or --dry-run) ──────────
    new_listings = []
    for listing in listings:
        lid = listing.get("listing_id", "")
        if not lid:
            # Generate ID from address
            lid = listing.get("formatted_address", "").replace(" ", "_").lower()
            listing["listing_id"] = lid

        if args.dry_run or args.force or is_new_listing(lid):
            new_listings.append(listing)

    if not new_listings:
        logger.info("No new listings to process.")
        if not args.quiet:
            stats = get_stats()
            logger.info(f"DB: {stats['total']} total, {stats['analyzed']} analyzed")
        return

    logger.info(f"Processing {len(new_listings)} new listing(s)...")

    # ── Step 4: Enrich → Analyze → Report ────────────────────
    reports = []
    for listing in new_listings:
        address = listing.get("formatted_address", "Unknown")
        logger.info(f"  → {address}")

        # Fetch comps (--with-comps flag, opt-in)
        comps = None
        if args.with_comps:
            logger.info(f"    Fetching market comps...")
            comps = compute_comps(
                address=address,
                beds=listing.get("beds", 0),
                baths=listing.get("full_baths", 0),
                sqft=listing.get("sqft", 0),
                list_price=listing.get("list_price", 0),
            )
            logger.info(f"    Rent comps: {comps.rent_comp_count}, Sale comps: {comps.sale_comp_count}")

        # Enrich (with comps data)
        enriched = enrich_listing(listing, comps=comps)

        # Analyze
        result = analyze(enriched)

        # Sync metrics back to listing dict for DB/notification
        listing["monthly_cash_flow"] = result.monthly_cash_flow
        listing["cap_rate"] = result.cap_rate
        listing["coc_return"] = result.coc_return

        # Generate PDF
        report_path = generate_report(result, enriched=enriched)
        logger.info(f"    Report: {report_path}")

        # Save to DB
        if not args.dry_run:
            save_listing(listing)
            mark_analyzed(listing["listing_id"], report_path)

        reports.append((listing, report_path))

    # ── Step 5: Notify ───────────────────────────────────────
    notify(reports)

    if not args.quiet:
        stats = get_stats() if not args.dry_run else {"total": len(reports), "analyzed": len(reports), "pending": 0}
        logger.info(f"Done. {len(reports)} report(s) generated. DB: {stats['total']} total")


if __name__ == "__main__":
    main()
