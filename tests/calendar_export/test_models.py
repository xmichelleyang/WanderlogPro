"""Tests for calendar data models."""

from wanderlogpro.calendar_export.models import CalendarTrip, ItineraryDay, ItineraryItem


def test_itinerary_item_defaults():
    item = ItineraryItem(name="Museum", lat=48.86, lng=2.34)
    assert item.name == "Museum"
    assert item.address == ""
    assert item.notes == ""
    assert item.icon == ""
    assert item.start_time == ""
    assert item.end_time == ""
    assert item.duration_minutes == 0
    assert item.travel_minutes_to_next == 0


def test_itinerary_item_with_all_fields():
    item = ItineraryItem(
        name="Eiffel Tower",
        lat=48.8584,
        lng=2.2945,
        address="Champ de Mars, Paris",
        notes="Book evening slot",
        icon="attraction",
        start_time="14:00",
        end_time="16:00",
        duration_minutes=120,
        travel_minutes_to_next=25,
    )
    assert item.lat == 48.8584
    assert item.duration_minutes == 120
    assert item.travel_minutes_to_next == 25
    assert item.start_time == "14:00"


def test_itinerary_day_defaults():
    day = ItineraryDay(date="2026-04-20")
    assert day.date == "2026-04-20"
    assert day.items == []


def test_itinerary_day_with_items():
    items = [
        ItineraryItem(name="A", lat=1.0, lng=2.0),
        ItineraryItem(name="B", lat=3.0, lng=4.0),
    ]
    day = ItineraryDay(date="2026-04-20", items=items)
    assert len(day.items) == 2


def test_calendar_trip():
    day = ItineraryDay(
        date="2026-04-20",
        items=[ItineraryItem(name="X", lat=0, lng=0)],
    )
    trip = CalendarTrip(id="abc123", name="Paris Trip", days=[day])
    assert trip.id == "abc123"
    assert trip.name == "Paris Trip"
    assert len(trip.days) == 1
    assert trip.days[0].date == "2026-04-20"


def test_calendar_trip_empty():
    trip = CalendarTrip(id="t1", name="Empty Trip")
    assert trip.days == []
    assert trip.timezone == ""


def test_calendar_trip_with_timezone():
    trip = CalendarTrip(id="t1", name="Vietnam Trip", timezone="Asia/Ho_Chi_Minh")
    assert trip.timezone == "Asia/Ho_Chi_Minh"
