"""Convert scraped itinerary data into Guide models."""

import re

from wanderlogpro.calendar_export.models import CalendarTrip, ItineraryItem
from wanderlogpro.offline_mode.models import Guide, GuideDay, GuideFlight, GuideHotel, GuidePlace

# Heuristics for categorizing places (fallback when no Google types)
_FLIGHT_PATTERNS = re.compile(
    r"\b(flight|fly|airport|airline|depart|arrive|boarding|terminal|"
    r"check.?in.*flight|layover|seatac|lax|jfk|heathrow|changi|"
    r"narita|haneda|incheon|schiphol)\b",
    re.IGNORECASE,
)
_HOTEL_PATTERNS = re.compile(
    r"\b(hotel|hostel|airbnb|check.?in|check.?out|resort|motel|"
    r"guesthouse|lodge|inn|accommodation|stay|villa|bnb)\b",
    re.IGNORECASE,
)
_FOOD_PATTERNS = re.compile(
    r"\b(restaurant|cafe|coffee|breakfast|lunch|dinner|brunch|"
    r"eat|food|bar|pub|bistro|bakery|pho|bun cha|banh mi)\b",
    re.IGNORECASE,
)

# Google Place types → (category, emoji), checked in priority order.
# Uses regex patterns to catch subtypes (e.g. "japanese_restaurant" → food)
# instead of hardcoding every variant. Patterns match on word boundaries
# within snake_case type strings.
#
# Priority order: snack > food > hotel > sightseeing > shopping > nature > worship > transport
# The outermost loop is category (not type), so priority is preserved
# regardless of input order: ["restaurant", "bakery"] → snack wins.

def _token(pat: str) -> str:
    """Wrap pattern with snake_case token boundaries."""
    return rf"(?:^|_){pat}(?:$|_)"

_SNACK_RE = re.compile(
    r"|".join([
        _token("bakery"),
        _token("dessert"),
        _token("ice_cream"),
        _token("candy"),
        _token("chocolate"),
        _token("donut"),
        r"confection",          # confectionery, japanese_confectionery_shop
        r"bubble_tea",          # bubble_tea_store
        r"tea_house",           # exact
        r"tea_market",          # tea_market_place
    ]),
    re.IGNORECASE,
)
_FOOD_RE = re.compile(
    r"|".join([
        r"restaurant",          # any *_restaurant
        _token("cafe"),         # cafe, not cafeteria separately but cafeteria is food too
        r"cafeteria",
        r"coffee",              # coffee_shop, coffee_roasters
        r"gastropub",
        _token("pub"),          # pub, not republic
        r"wine_bar",
        r"sandwich",
        r"meal_",               # meal_delivery, meal_takeaway
        _token("food"),         # food, food_court
        r"night_club",
        _token("bistro"),
        _token("bar(?!b)"),     # bar, wine_bar, but not barber
    ]),
    re.IGNORECASE,
)
_HOTEL_RE = re.compile(
    r"|".join([
        _token("hotel"),        # hotel, resort_hotel, extended_stay_hotel
        _token("lodging"),
        _token("motel"),
        _token("hostel"),
        r"bed_and_breakfast",
        r"guest_house",
        _token("resort"),
        r"serviced_a",          # serviced_apartment, serviced_accommodation
    ]),
    re.IGNORECASE,
)
_SIGHTSEEING_RE = re.compile(
    r"|".join([
        _token("museum"),
        r"scenic",
        r"tourist_attraction",
        _token("monument"),
        r"art_gallery",
        r"historical",
        r"heritage",
    ]),
    re.IGNORECASE,
)
_SHOPPING_RE = re.compile(
    r"|".join([
        r"shopping",            # shopping_center, shopping_mall
        r"department_store",
        r"grocery",             # grocery_or_supermarket, asian_grocery_store
        _token("supermarket"),
        _token(r"store$"),      # catches *_store suffix (clothing_store, etc.)
        _token("market"),       # market, seafood_market (but tea_market caught by snack first)
        r"book_store",
        r"gift_shop",
    ]),
    re.IGNORECASE,
)
_NATURE_RE = re.compile(
    r"|".join([
        _token(r"park(?!ing)"), # park, national_park, amusement_park — not parking
        _token("garden"),
        _token("zoo"),
        _token("aquarium"),
        r"amusement_park",
        r"national_park",
        r"natural_feature",
        r"botanical",
        _token("beach"),
    ]),
    re.IGNORECASE,
)
_WORSHIP_RE = re.compile(
    r"|".join([
        _token("temple"),
        _token("church"),
        _token("mosque"),
        _token("synagogue"),
        r"place_of_worship",
        r"buddhist",
        r"hindu_temple",
    ]),
    re.IGNORECASE,
)
_TRANSPORT_RE = re.compile(
    r"|".join([
        _token("airport"),
        r"train_station",
        r"bus_station",
        r"subway",
        r"transit_station",
        r"light_rail",
        r"ferry_terminal",
    ]),
    re.IGNORECASE,
)

_TYPE_REGEX_PRIORITY = [
    (_SNACK_RE, "snack", "\U0001f366"),            # 🍦
    (_FOOD_RE, "food", "\U0001f37d\uFE0F"),         # 🍽️
    (_HOTEL_RE, "hotel", "\U0001f3e8"),              # 🏨
    (_SIGHTSEEING_RE, "activity", "\U0001f3db\uFE0F"),  # 🏛️
    (_SHOPPING_RE, "activity", "\U0001f6cd\uFE0F"),     # 🛍️
    (_NATURE_RE, "activity", "\U0001f33f"),           # 🌿
    (_WORSHIP_RE, "activity", "\u26E9\uFE0F"),        # ⛩️
    (_TRANSPORT_RE, "activity", "\U0001f6eb"),         # 🛫
]

# Noise types to ignore entirely
_NOISE_TYPES = {"point_of_interest", "establishment", "premise", "political",
                "locality", "sublocality", "route", "street_address"}

_DEFAULT_EMOJI = "\U0001f3f7\uFE0F"  # 🏷️


def _categorize_from_types(google_types: list[str]) -> tuple[str, str]:
    """Map Google Place types to (category, emoji) using regex priority.

    Category priority is the outer loop, so e.g. ["restaurant", "bakery"]
    always returns snack regardless of input order.
    """
    types = [t for t in google_types if t not in _NOISE_TYPES]
    if not types:
        return "", ""
    for pattern, category, emoji in _TYPE_REGEX_PRIORITY:
        for t in types:
            if pattern.search(t):
                return category, emoji
    return "", ""


def _categorize(item: ItineraryItem) -> str:
    """Guess a category from the item name, address, and notes."""
    text = f"{item.name} {item.address} {item.notes}"
    if _FLIGHT_PATTERNS.search(text):
        return "flight"
    if _HOTEL_PATTERNS.search(text):
        return "hotel"
    if _FOOD_PATTERNS.search(text):
        return "food"
    return "activity"


_CATEGORY_DEFAULT_EMOJI = {
    "food": "\U0001f37d\uFE0F",   # 🍽️
    "hotel": "\U0001f3e8",         # 🏨
    "flight": "\u2708\uFE0F",     # ✈️
    "activity": _DEFAULT_EMOJI,    # 🏷️
    "snack": "\U0001f366",         # 🍦
}


def _format_time(iso_time: str) -> str:
    """Convert ISO time '2025-01-15T09:00:00' or bare 'HH:MM' to '9:00 AM'."""
    if not iso_time:
        return ""
    # Handle both ISO datetime and bare HH:MM
    if "T" in iso_time:
        time_part = iso_time.split("T")[1][:5]  # "09:00"
    elif len(iso_time) >= 5 and iso_time[2] == ":":
        time_part = iso_time[:5]  # bare "08:00"
    else:
        return ""
    h, m = int(time_part[:2]), time_part[3:5]
    ampm = "AM" if h < 12 else "PM"
    display_h = h % 12 or 12
    return f"{display_h}:{m} {ampm}"


def _parse_minutes(raw: str) -> int:
    """Extract total minutes from midnight for a raw time string.

    Accepts ISO ``2025-01-15T09:00:00`` or bare ``HH:MM``.
    Returns -1 when the string cannot be parsed.
    """
    if not raw:
        return -1
    if "T" in raw:
        part = raw.split("T")[1][:5]
    elif len(raw) >= 5 and raw[2] == ":":
        part = raw[:5]
    else:
        return -1
    try:
        h, m = int(part[:2]), int(part[3:5])
    except (ValueError, IndexError):
        return -1
    return h * 60 + m


def _duration_from_times(start_raw: str, end_raw: str) -> int:
    """Compute duration in minutes from raw start/end time strings.

    Returns 0 when either value is missing or end <= start.
    """
    s = _parse_minutes(start_raw)
    e = _parse_minutes(end_raw)
    if s < 0 or e < 0 or e <= s:
        return 0
    return e - s


def build_guide(trip: CalendarTrip) -> Guide:
    """Convert a CalendarTrip into a Guide."""
    days: list[GuideDay] = []

    for itin_day in trip.days:
        places: list[GuidePlace] = []
        for item in itin_day.items:
            # Try type-based categorization first, fall back to regex
            cat_from_types, emoji_from_types = _categorize_from_types(
                item.google_types
            )
            if cat_from_types:
                category = cat_from_types
                emoji = emoji_from_types
            else:
                category = _categorize(item)
                emoji = _CATEGORY_DEFAULT_EMOJI.get(category, _DEFAULT_EMOJI)

            # Duration: prefer placeMetadata, then compute from start/end
            dur = item.duration_minutes
            if dur <= 0:
                dur = _duration_from_times(item.start_time, item.end_time)

            places.append(
                GuidePlace(
                    name=item.name,
                    address=item.address,
                    notes=item.notes,
                    description=item.description,
                    lat=item.lat,
                    lng=item.lng,
                    start_time=_format_time(item.start_time),
                    end_time=_format_time(item.end_time),
                    duration_minutes=dur,
                    category=category,
                    icon=emoji,
                    travel_minutes_to_next=item.travel_minutes_to_next,
                    travel_mode_to_next=item.travel_mode,
                )
            )
        days.append(GuideDay(date=itin_day.date, places=places, notes=itin_day.notes))

    # Convert flights
    flights = [
        GuideFlight(
            airline=f.airline,
            flight_number=f.flight_number,
            depart_airport=f.depart_airport,
            depart_airport_name=f.depart_airport_name,
            depart_date=f.depart_date,
            depart_time=f.depart_time,
            arrive_airport=f.arrive_airport,
            arrive_airport_name=f.arrive_airport_name,
            arrive_date=f.arrive_date,
            arrive_time=f.arrive_time,
            travelers=f.travelers,
            confirmation=f.confirmation,
            notes=f.notes,
        )
        for f in trip.flights
    ]

    # Convert hotels
    hotels = [
        GuideHotel(
            name=h.name,
            address=h.address,
            check_in=h.check_in,
            check_out=h.check_out,
            nights=h.nights,
            confirmation=h.confirmation,
            travelers=h.travelers,
            notes=h.notes,
        )
        for h in trip.hotels
    ]

    return Guide(
        name=trip.name, timezone=trip.timezone, days=days,
        flights=flights, hotels=hotels,
    )
