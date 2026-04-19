"""Fetch itinerary data from Wanderlog for calendar export.

Wanderlog embeds trip data in the page HTML as a `window.__MOBX_STATE__` JSON
blob. The itinerary is stored as sections with `mode: "dayPlan"` and a date.
Duration estimates come from `resources.placeMetadata` and travel times from
`resources.distancesBetweenPlaces`.
"""

import json
import re

import requests
from timezonefinder import TimezoneFinder

from wanderlogpro.calendar_export.models import CalendarTrip, ItineraryDay, ItineraryItem
from wanderlogpro.utils import parse_trip_id

_tf = None  # lazy singleton


def _get_timezone_finder() -> TimezoneFinder:
    global _tf
    if _tf is None:
        _tf = TimezoneFinder()
    return _tf


def fetch_itinerary(url: str, cookie: str | None = None) -> CalendarTrip:
    """Fetch a trip's itinerary from Wanderlog and return a CalendarTrip.

    Only retrieves itinerary/schedule data (day-by-day items), not the
    unscheduled list items used by the KML map export.

    Args:
        url: A Wanderlog trip URL.
        cookie: Optional session cookie for private trips.
    """
    trip_id = parse_trip_id(url)

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if cookie:
        headers["Cookie"] = cookie

    resp = requests.get(url, headers=headers, timeout=30)

    if resp.status_code == 404:
        raise ValueError(f"Trip not found: {trip_id}. Is the URL correct?")
    if resp.status_code == 401:
        raise PermissionError(
            f"Authentication required for trip {trip_id}. "
            "Use --cookie to provide your session cookie."
        )
    resp.raise_for_status()

    data = _extract_mobx_state(resp.text)
    if not data:
        raise ValueError(
            "Could not extract trip data from page. "
            "The page structure may have changed."
        )

    trip_store = data.get("tripPlanStore", {}).get("data", {})
    return _parse_itinerary_response(trip_id, trip_store)


def _extract_mobx_state(html: str) -> dict | None:
    """Extract the __MOBX_STATE__ JSON from the page HTML."""
    marker = "window.__MOBX_STATE__ = "
    start_idx = html.find(marker)
    if start_idx < 0:
        return None

    json_start = start_idx + len(marker)
    try:
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(html, json_start)
        return data
    except (json.JSONDecodeError, ValueError):
        return None


def _parse_itinerary_response(trip_id: str, data: dict) -> CalendarTrip:
    """Parse the Wanderlog trip store data into a CalendarTrip.

    The trip data contains:
    - tripPlan.itinerary.sections: list of sections, where mode="dayPlan"
      sections are itinerary days with blocks (places).
    - resources.placeMetadata: list of place metadata with minMinutesSpent/
      maxMinutesSpent for visit duration estimates.
    - resources.distancesBetweenPlaces: travel times between places.
    """
    trip_plan = data.get("tripPlan", {})
    trip_name = trip_plan.get("title", trip_plan.get("name", "Untitled Trip"))
    resources = data.get("resources", {})

    # Build place metadata lookup: placeId → {minMinutesSpent, maxMinutesSpent}
    place_metadata = _build_place_metadata(resources.get("placeMetadata", []))

    # Build distance lookup: (fromPlaceId, toPlaceId) → travel seconds
    distance_map = _build_distance_map(
        resources.get("distancesBetweenPlaces", {})
    )

    # Parse itinerary sections (dayPlan mode only)
    sections = (
        trip_plan.get("itinerary", {}).get("sections", [])
    )

    days: list[ItineraryDay] = []
    for section in sections:
        if section.get("mode") != "dayPlan":
            continue

        date = section.get("date", "")
        if not date:
            continue

        blocks = section.get("blocks", [])
        items: list[ItineraryItem] = []

        for i, block in enumerate(blocks):
            if block.get("type") != "place":
                continue

            place = block.get("place", {})
            if not place:
                continue

            name = place.get("name", "Unnamed Item")
            location = place.get("geometry", {}).get("location", {})
            lat = location.get("lat", 0.0)
            lng = location.get("lng", 0.0)
            address = place.get("formatted_address", place.get("vicinity", ""))
            notes = _extract_notes(block.get("text", {}))
            icon = ""
            place_id = place.get("place_id", "")

            # Time fields from block
            start_time = block.get("startTime") or ""
            end_time = block.get("endTime") or ""

            # Duration from placeMetadata
            duration_minutes = _get_duration(place_metadata, place_id)

            # Travel time to next block (respects per-block travel mode)
            travel_minutes = 0
            block_travel_mode = block.get("travelMode")
            actual_travel_mode = str(block_travel_mode or "driving")
            if i + 1 < len(blocks):
                next_block = blocks[i + 1]
                next_place = next_block.get("place", {})
                next_place_id = next_place.get("place_id", "")
                if place_id and next_place_id:
                    travel_seconds, actual_travel_mode = _lookup_travel_time(
                        distance_map, place_id, next_place_id,
                        block_travel_mode,
                    )
                    travel_minutes = max(0, round(travel_seconds / 60))

            items.append(ItineraryItem(
                name=name,
                lat=lat,
                lng=lng,
                address=address,
                notes=notes,
                icon=icon,
                start_time=str(start_time) if start_time else "",
                end_time=str(end_time) if end_time else "",
                duration_minutes=duration_minutes,
                travel_minutes_to_next=travel_minutes,
                travel_mode=actual_travel_mode,
            ))

        if items:
            days.append(ItineraryDay(date=date, items=items))

    # Auto-detect timezone from first place's coordinates
    timezone = _detect_timezone(days)

    return CalendarTrip(id=trip_id, name=trip_name, days=days, timezone=timezone)


def _detect_timezone(days: list[ItineraryDay]) -> str:
    """Detect IANA timezone from the first place with valid coordinates."""
    for day in days:
        for item in day.items:
            if item.lat != 0.0 and item.lng != 0.0:
                try:
                    tz = _get_timezone_finder().timezone_at(lat=item.lat, lng=item.lng)
                    if tz:
                        return tz
                except Exception:
                    pass
    return "UTC"


def _build_place_metadata(
    metadata_list: list[dict],
) -> dict[str, dict]:
    """Build a placeId → metadata lookup from resources.placeMetadata."""
    lookup: dict[str, dict] = {}
    for entry in metadata_list:
        place_id = entry.get("placeId", "")
        if place_id:
            lookup[place_id] = entry
    return lookup


def _build_distance_map(
    distances: dict[str, dict],
) -> dict[tuple[str, str, str], float]:
    """Build a (fromPlaceId, toPlaceId, travelMode) → seconds lookup."""
    result: dict[tuple[str, str, str], float] = {}
    for _key, entry in distances.items():
        from_id = entry.get("fromPlaceId", "")
        to_id = entry.get("toPlaceId", "")
        mode = entry.get("travelMode", "driving")
        route = entry.get("route", {})
        duration = route.get("duration", {}).get("value", 0)
        if from_id and to_id and duration:
            result[(from_id, to_id, mode)] = duration
    return result


def _lookup_travel_time(
    distance_map: dict[tuple[str, str, str], float],
    from_id: str,
    to_id: str,
    travel_mode: str | None,
) -> tuple[float, str]:
    """Look up travel time in seconds for a place pair and travel mode.

    Uses the block's travelMode to pick the correct entry. Falls back to
    any available mode if the requested mode isn't found.

    Returns:
        Tuple of (travel_seconds, actual_mode_used).
    """
    mode = (travel_mode or "driving").lower()

    # Try exact mode match first
    result = distance_map.get((from_id, to_id, mode), 0)
    if result:
        return result, mode

    # Fallback: try any mode for this pair
    for key, val in distance_map.items():
        if key[0] == from_id and key[1] == to_id:
            return val, key[2]

    return 0, mode


def _get_duration(
    metadata: dict[str, dict], place_id: str
) -> int:
    """Get visit duration in minutes from place metadata.

    Uses the average of minMinutesSpent and maxMinutesSpent if available.
    Returns 0 if no data (caller should use the default fallback).
    """
    if not place_id or place_id not in metadata:
        return 0

    entry = metadata[place_id]
    min_min = entry.get("minMinutesSpent")
    max_min = entry.get("maxMinutesSpent")

    if min_min is not None and max_min is not None:
        return round((min_min + max_min) / 2)
    if min_min is not None:
        return min_min
    if max_min is not None:
        return max_min
    return 0


def _extract_notes(text_obj: dict) -> str:
    """Extract plain text notes from Wanderlog's Quill delta format."""
    if not text_obj:
        return ""
    ops = text_obj.get("ops", [])
    parts = []
    for op in ops:
        insert = op.get("insert", "")
        if isinstance(insert, str) and insert.strip():
            parts.append(insert.strip())
    return " ".join(parts)
