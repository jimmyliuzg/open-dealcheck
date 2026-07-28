"""
OpenDealCheck — Notification Delivery
Layer 5: Summary output + optional Telegram delivery.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def notify(reports: list[tuple[dict, str]], summary_path: Optional[str] = None):
    """
    Send notification with new analysis results.
    
    For now: prints summary and optionally writes to a log file.
    Can be extended to Telegram delivery via Hermes cron.
    """
    if not reports:
        logger.info("No new reports to notify about.")
        return

    lines = [
        f"{'='*50}",
        f" OpenDealCheck — {len(reports)} New Listing(s) Analyzed",
        f"{'='*50}",
        "",
    ]

    for listing, report_path in reports:
        address = listing.get("formatted_address", listing.get("address", "Unknown"))
        price = listing.get("list_price", listing.get("price", 0))
        monthly_cf = listing.get("monthly_cash_flow", 0)
        cap_rate = listing.get("cap_rate", 0)
        coc = listing.get("coc_return", 0)

        cf_indicator = "🟢" if monthly_cf >= 0 else "🔴"

        lines.append(f"📍 {address}")
        lines.append(f"   Price: ${price:,.0f}")
        lines.append(f"   {cf_indicator} Cash Flow: ${monthly_cf:,.0f}/mo")
        lines.append(f"   Cap Rate: {cap_rate:.1f}%  |  CoC: {coc:.1f}%")
        lines.append(f"   Report: {report_path}")
        lines.append("")

    lines.append(f"{'='*50}")

    summary = "\n".join(lines)

    # Print to stdout (for cron job capture)
    print(summary)

    # Optionally save to file
    if summary_path:
        from pathlib import Path
        Path(summary_path).write_text(summary)
        logger.info(f"Summary saved to {summary_path}")

    return summary
