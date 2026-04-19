"""Shared utilities for WanderlogPro."""

import re


def parse_trip_id(url: str) -> str:
    """Extract the trip ID from a Wanderlog URL.

    Supports formats like:
      https://wanderlog.com/view/abcd1234/my-trip-name
      https://wanderlog.com/view/abcd1234/my-trip-name/shared
      https://wanderlog.com/view/abcd1234
      wanderlog.com/view/abcd1234/...
    """
    match = re.search(r"wanderlog\.com/view/([^/\s?#]+)", url)
    if not match:
        raise ValueError(
            f"Could not parse trip ID from URL: {url}\n"
            "Expected format: https://wanderlog.com/view/<trip-id>/..."
        )
    return match.group(1)
