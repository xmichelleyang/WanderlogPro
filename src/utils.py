"""Shared utilities for WanderlogPro."""

import re


def parse_trip_id(url: str) -> str:
    """Extract the trip ID from a Wanderlog URL.

    Supports formats like:
      https://wanderlog.com/view/abcd1234/my-trip-name
      https://wanderlog.com/view/abcd1234/my-trip-name/shared
      https://wanderlog.com/view/abcd1234
      https://wanderlog.com/plan/abcd1234/my-trip-name/shared
      wanderlog.com/view/abcd1234/...
      wanderlog.com/plan/abcd1234/...
    """
    match = re.search(r"wanderlog\.com/(?:view|plan)/([^/\s?#]+)", url)
    if not match:
        raise ValueError(
            f"Could not parse trip ID from URL: {url}\n"
            "Expected format: https://wanderlog.com/view/<trip-id>/... "
            "or https://wanderlog.com/plan/<trip-id>/..."
        )
    return match.group(1)


def normalize_wanderlog_url(url: str) -> str:
    """Normalize a Wanderlog URL for fetching.

    Ensures an ``https://`` scheme. Does **not** rewrite between
    ``/view/`` and ``/plan/`` — the caller's path choice is preserved so
    scripts can target whichever page (public share vs. editor) the user
    actually wants to fetch.
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url
