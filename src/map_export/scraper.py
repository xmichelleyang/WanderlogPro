"""Fetch trip data from Wanderlog by scraping embedded JSON from the trip page."""

import json
import re

import requests

from wanderlogpro.map_export.models import Place, PlaceList, Trip
from wanderlogpro.utils import normalize_wanderlog_url, parse_trip_id


def _normalize_wanderlog_url(url: str) -> str:
    """Ensure the URL has a scheme and points to the public /view/ page."""
    return normalize_wanderlog_url(url)


def _extract_trip_json(html: str) -> dict:
    """Extract the tripPlan JSON object embedded in the Wanderlog page HTML."""
    idx = html.find('"tripPlan":{')
    if idx < 0:
        raise ValueError(
            "Could not find trip data in page. "
            "The page structure may have changed, or the trip may not exist."
        )

    json_start = idx + len('"tripPlan":')

    # Walk forward matching braces to extract the full JSON object
    depth = 0
    i = json_start
    while i < len(html):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1

    try:
        return json.loads(html[json_start : i + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse trip JSON: {e}")


def fetch_trip(url: str, cookie: str | None = None) -> Trip:
    """Fetch a trip from Wanderlog and return a Trip model.

    Scrapes the trip page HTML and extracts the embedded tripPlan JSON.

    Args:
        url: A Wanderlog trip URL.
        cookie: Optional session cookie for private trips.
    """
    trip_id = parse_trip_id(url)
    page_url = _normalize_wanderlog_url(url)

    headers = {"User-Agent": "Mozilla/5.0 (WanderlogPro/0.1)"}
    if cookie:
        headers["Cookie"] = cookie

    resp = requests.get(page_url, headers=headers, timeout=30)

    if resp.status_code == 404:
        raise ValueError(f"Trip not found: {trip_id}. Is the URL correct?")
    if resp.status_code == 401 or resp.status_code == 403:
        raise PermissionError(
            f"Authentication required for trip {trip_id}. "
            "Use --cookie to provide your session cookie."
        )
    resp.raise_for_status()

    trip_data = _extract_trip_json(resp.text)
    return _parse_trip_response(trip_id, trip_data)


def _parse_trip_response(trip_id: str, data: dict) -> Trip:
    """Parse the embedded tripPlan JSON into a Trip model.

    Wanderlog structure:
      tripPlan.title — trip name
      tripPlan.itinerary.sections[] — each section is a "list"
        section.heading — list name
        section.placeMarkerColor — hex color like #3f52e3
        section.placeMarkerIcon — icon name like "utensils", "mountain"
        section.blocks[] — items in the list
          block.type == "place" → block.place has the place data
            place.name, place.geometry.location.{lat, lng}
    """
    trip_name = data.get("title", data.get("name", "Untitled Trip"))

    sections = data.get("itinerary", {}).get("sections", [])
    place_lists: list[PlaceList] = []

    for section in sections:
        heading = section.get("heading", "").strip()
        if not heading:
            heading = "Other Places"

        color = section.get("placeMarkerColor", "")
        icon = section.get("placeMarkerIcon", "")
        blocks = section.get("blocks", [])

        places: list[Place] = []
        for block in blocks:
            if block.get("type") != "place":
                continue

            place_data = block.get("place", {})
            location = place_data.get("geometry", {}).get("location", {})
            lat = location.get("lat", 0.0)
            lng = location.get("lng", 0.0)

            if lat == 0.0 and lng == 0.0:
                continue

            # Build address from address_components
            address_parts = place_data.get("address_components", [])
            address = ", ".join(
                c.get("long_name", "") for c in address_parts
            ) if address_parts else ""

            # Notes from block text
            text_data = block.get("text", {})
            notes = ""
            if isinstance(text_data, dict):
                ops = text_data.get("ops", [])
                notes = "".join(
                    op.get("insert", "") for op in ops if isinstance(op, dict)
                ).strip()

            places.append(Place(
                name=place_data.get("name", "Unnamed Place"),
                lat=lat,
                lng=lng,
                address=address,
                notes=notes,
                list_name=heading,
                icon=icon,
                color=color,
            ))

        if places:
            place_lists.append(PlaceList(
                name=heading,
                icon=icon,
                color=color,
                places=places,
            ))

    return Trip(id=trip_id, name=trip_name, place_lists=place_lists)
