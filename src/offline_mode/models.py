"""Data models for the offline trip guide."""

from dataclasses import dataclass, field


@dataclass
class GuidePlace:
    """A place in the trip guide."""

    name: str
    address: str = ""
    notes: str = ""
    description: str = ""  # Place description/hours (e.g. "Mon: 9 AM–5 PM")
    lat: float = 0.0
    lng: float = 0.0
    start_time: str = ""  # e.g. "09:00"
    end_time: str = ""  # e.g. "11:30"
    duration_minutes: int = 0
    category: str = "activity"  # "flight", "hotel", "food", "snack", "activity"
    icon: str = ""
    color: str = ""
    travel_minutes_to_next: int = 0
    travel_mode_to_next: str = ""  # "driving", "walking", "transit", etc.


@dataclass
class GuideFlight:
    """A flight in the trip guide."""

    airline: str = ""
    flight_number: str = ""
    depart_airport: str = ""
    depart_airport_name: str = ""
    depart_date: str = ""
    depart_time: str = ""
    arrive_airport: str = ""
    arrive_airport_name: str = ""
    arrive_date: str = ""
    arrive_time: str = ""
    travelers: str = ""
    confirmation: str = ""
    notes: str = ""


@dataclass
class GuideHotel:
    """A hotel stay in the trip guide."""

    name: str = ""
    address: str = ""
    check_in: str = ""
    check_out: str = ""
    nights: int = 0
    confirmation: str = ""
    travelers: str = ""
    notes: str = ""


@dataclass
class GuideDay:
    """A single day in the guide."""

    date: str  # ISO date "2025-01-15"
    places: list[GuidePlace] = field(default_factory=list)
    notes: str = ""  # Day-level text notes


@dataclass
class Guide:
    """Complete trip guide data."""

    name: str
    timezone: str = ""
    days: list[GuideDay] = field(default_factory=list)
    flights: list[GuideFlight] = field(default_factory=list)
    hotels: list[GuideHotel] = field(default_factory=list)

    @property
    def total_places(self) -> int:
        return sum(len(d.places) for d in self.days)
