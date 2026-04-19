"""Data models for WanderlogPro calendar/itinerary export."""

from dataclasses import dataclass, field


@dataclass
class ItineraryItem:
    """A single item on the trip itinerary with scheduling info."""

    name: str
    lat: float
    lng: float
    address: str = ""
    notes: str = ""
    icon: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_minutes: int = 0
    travel_minutes_to_next: int = 0
    travel_mode: str = ""  # "driving", "walking", etc.


@dataclass
class ItineraryDay:
    """A single day in the itinerary with an ordered list of items."""

    date: str  # ISO date like "2026-04-20"
    items: list[ItineraryItem] = field(default_factory=list)


@dataclass
class CalendarTrip:
    """A Wanderlog trip's itinerary for calendar export."""

    id: str
    name: str
    days: list[ItineraryDay] = field(default_factory=list)
    timezone: str = ""  # IANA timezone (e.g. "Asia/Ho_Chi_Minh"), auto-detected from coordinates
