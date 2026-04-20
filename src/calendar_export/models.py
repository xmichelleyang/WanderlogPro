"""Data models for WanderlogPro calendar/itinerary export."""

from dataclasses import dataclass, field


@dataclass
class FlightInfo:
    """A flight extracted from Wanderlog."""

    airline: str = ""
    flight_number: str = ""
    depart_airport: str = ""  # IATA code like "SFO"
    depart_airport_name: str = ""
    depart_date: str = ""  # ISO date "2026-03-15"
    depart_time: str = ""  # "22:10"
    arrive_airport: str = ""
    arrive_airport_name: str = ""
    arrive_date: str = ""
    arrive_time: str = ""
    travelers: str = ""
    confirmation: str = ""
    notes: str = ""


@dataclass
class HotelInfo:
    """A hotel stay extracted from Wanderlog."""

    name: str = ""
    address: str = ""
    check_in: str = ""  # ISO date "2026-03-17"
    check_out: str = ""  # ISO date "2026-03-27"
    nights: int = 0
    confirmation: str = ""
    travelers: str = ""
    notes: str = ""


@dataclass
class ItineraryItem:
    """A single item on the trip itinerary with scheduling info."""

    name: str
    lat: float
    lng: float
    address: str = ""
    notes: str = ""
    description: str = ""  # Place description/hours from Wanderlog (e.g. opening hours)
    icon: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_minutes: int = 0
    travel_minutes_to_next: int = 0
    travel_mode: str = ""  # "driving", "walking", etc.
    google_types: list[str] = field(default_factory=list)


@dataclass
class ItineraryDay:
    """A single day in the itinerary with an ordered list of items."""

    date: str  # ISO date like "2026-04-20"
    items: list[ItineraryItem] = field(default_factory=list)
    notes: str = ""  # Day-level text notes (not attached to a place)


@dataclass
class CalendarTrip:
    """A Wanderlog trip's itinerary for calendar export."""

    id: str
    name: str
    days: list[ItineraryDay] = field(default_factory=list)
    timezone: str = ""  # IANA timezone (e.g. "Asia/Ho_Chi_Minh"), auto-detected from coordinates
    flights: list[FlightInfo] = field(default_factory=list)
    hotels: list[HotelInfo] = field(default_factory=list)
