"""Tests for the calendar/itinerary scraper."""

import pytest

from wanderlogpro.calendar_export.scraper import (
    _build_distance_map,
    _build_place_metadata,
    _detect_timezone,
    _extract_description,
    _extract_notes,
    _get_duration,
    _lookup_travel_time,
    _parse_itinerary_response,
)


SAMPLE_TRIP_STORE = {
    "tripPlan": {
        "title": "Paris 2026",
        "itinerary": {
            "sections": [
                {
                    "heading": "Restaurants",
                    "mode": "placeList",
                    "date": "",
                    "blocks": [
                        {
                            "id": 1,
                            "type": "place",
                            "place": {
                                "name": "List-Only Cafe",
                                "place_id": "list_cafe",
                                "geometry": {"location": {"lat": 48.85, "lng": 2.35}},
                                "formatted_address": "Paris, France",
                            },
                        }
                    ],
                },
                {
                    "heading": "Day 1",
                    "mode": "dayPlan",
                    "date": "2026-04-20",
                    "blocks": [
                        {
                            "id": 100,
                            "type": "place",
                            "place": {
                                "name": "Eiffel Tower",
                                "place_id": "eiffel_id",
                                "geometry": {"location": {"lat": 48.8584, "lng": 2.2945}},
                                "formatted_address": "Champ de Mars, Paris",
                            },
                            "startTime": "14:00",
                            "endTime": None,
                            "text": {"ops": [{"insert": "Book evening slot\n"}]},
                        },
                        {
                            "id": 101,
                            "type": "place",
                            "place": {
                                "name": "Le Comptoir",
                                "place_id": "comptoir_id",
                                "geometry": {"location": {"lat": 48.8534, "lng": 2.3488}},
                                "formatted_address": "Paris, France",
                            },
                            "startTime": "",
                            "endTime": "",
                            "text": {"ops": [{"insert": "\n"}]},
                        },
                    ],
                },
                {
                    "heading": "Day 2",
                    "mode": "dayPlan",
                    "date": "2026-04-21",
                    "blocks": [
                        {
                            "id": 200,
                            "type": "place",
                            "place": {
                                "name": "Louvre Museum",
                                "place_id": "louvre_id",
                                "geometry": {"location": {"lat": 48.8606, "lng": 2.3376}},
                                "formatted_address": "Rue de Rivoli, Paris",
                            },
                            "startTime": "10:00",
                            "endTime": "13:00",
                            "text": {},
                        },
                    ],
                },
            ],
        },
    },
    "resources": {
        "placeMetadata": [
            {
                "placeId": "eiffel_id",
                "name": "Eiffel Tower",
                "minMinutesSpent": 60,
                "maxMinutesSpent": 120,
            },
            {
                "placeId": "comptoir_id",
                "name": "Le Comptoir",
                "minMinutesSpent": 45,
                "maxMinutesSpent": 75,
            },
            {
                "placeId": "louvre_id",
                "name": "Louvre Museum",
                "minMinutesSpent": 120,
                "maxMinutesSpent": 240,
            },
        ],
        "distancesBetweenPlaces": {
            '["eiffel_id","comptoir_id","driving"]': {
                "fromPlaceId": "eiffel_id",
                "toPlaceId": "comptoir_id",
                "travelMode": "driving",
                "route": {
                    "distance": {"value": 5000, "text": "3.1 mi"},
                    "duration": {"value": 900, "text": "15 mins"},
                },
            },
        },
    },
}


class TestParseItineraryResponse:
    def test_basic_parsing(self):
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        assert trip.id == "trip123"
        assert trip.name == "Paris 2026"
        assert len(trip.days) == 2

    def test_skips_place_list_sections(self):
        """Sections with mode=placeList should be excluded (not itinerary)."""
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        all_names = [
            item.name for day in trip.days for item in day.items
        ]
        assert "List-Only Cafe" not in all_names

    def test_day_dates(self):
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        dates = [d.date for d in trip.days]
        assert "2026-04-20" in dates
        assert "2026-04-21" in dates

    def test_items_per_day(self):
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        day1 = next(d for d in trip.days if d.date == "2026-04-20")
        day2 = next(d for d in trip.days if d.date == "2026-04-21")
        assert len(day1.items) == 2
        assert len(day2.items) == 1

    def test_item_names(self):
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        day1 = next(d for d in trip.days if d.date == "2026-04-20")
        assert day1.items[0].name == "Eiffel Tower"
        assert day1.items[1].name == "Le Comptoir"

    def test_item_coordinates(self):
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        day1 = next(d for d in trip.days if d.date == "2026-04-20")
        assert day1.items[0].lat == 48.8584
        assert day1.items[0].lng == 2.2945

    def test_item_address(self):
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        day1 = next(d for d in trip.days if d.date == "2026-04-20")
        assert day1.items[0].address == "Champ de Mars, Paris"

    def test_item_times(self):
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        day1 = next(d for d in trip.days if d.date == "2026-04-20")
        assert day1.items[0].start_time == "14:00"
        assert day1.items[0].end_time == ""
        assert day1.items[1].start_time == ""

    def test_item_duration_from_metadata(self):
        """Duration comes from placeMetadata avg(min, max)MinutesSpent."""
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        day1 = next(d for d in trip.days if d.date == "2026-04-20")
        # Eiffel: avg(60, 120) = 90
        assert day1.items[0].duration_minutes == 90
        # Comptoir: avg(45, 75) = 60
        assert day1.items[1].duration_minutes == 60

    def test_item_travel_time_from_distances(self):
        """Travel time comes from distancesBetweenPlaces."""
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        day1 = next(d for d in trip.days if d.date == "2026-04-20")
        # eiffel → comptoir = 900 seconds = 15 min
        assert day1.items[0].travel_minutes_to_next == 15
        # comptoir is last, no travel
        assert day1.items[1].travel_minutes_to_next == 0

    def test_item_notes(self):
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        day1 = next(d for d in trip.days if d.date == "2026-04-20")
        assert "Book evening slot" in day1.items[0].notes

    def test_explicit_end_time(self):
        trip = _parse_itinerary_response("trip123", SAMPLE_TRIP_STORE)
        day2 = next(d for d in trip.days if d.date == "2026-04-21")
        assert day2.items[0].start_time == "10:00"
        assert day2.items[0].end_time == "13:00"

    def test_empty_itinerary(self):
        data = {
            "tripPlan": {"title": "Empty", "itinerary": {"sections": []}},
            "resources": {},
        }
        trip = _parse_itinerary_response("t1", data)
        assert trip.days == []

    def test_day_without_blocks_included(self):
        """Empty dayPlan sections should still create a day entry."""
        data = {
            "tripPlan": {
                "title": "Test",
                "itinerary": {
                    "sections": [
                        {"mode": "dayPlan", "date": "2026-04-20", "blocks": []},
                    ]
                },
            },
            "resources": {},
        }
        trip = _parse_itinerary_response("t1", data)
        assert len(trip.days) == 1
        assert trip.days[0].date == "2026-04-20"
        assert trip.days[0].items == []

    def test_day_without_date_skipped(self):
        data = {
            "tripPlan": {
                "title": "Test",
                "itinerary": {
                    "sections": [
                        {
                            "mode": "dayPlan",
                            "blocks": [
                                {
                                    "type": "place",
                                    "place": {
                                        "name": "X",
                                        "geometry": {"location": {"lat": 1, "lng": 2}},
                                    },
                                }
                            ],
                        },
                    ],
                },
            },
            "resources": {},
        }
        trip = _parse_itinerary_response("t1", data)
        assert trip.days == []


class TestGetDuration:
    def test_avg_min_max(self):
        metadata = {"p1": {"minMinutesSpent": 20, "maxMinutesSpent": 30}}
        assert _get_duration(metadata, "p1") == 25

    def test_min_only(self):
        metadata = {"p1": {"minMinutesSpent": 20, "maxMinutesSpent": None}}
        assert _get_duration(metadata, "p1") == 20

    def test_max_only(self):
        metadata = {"p1": {"minMinutesSpent": None, "maxMinutesSpent": 30}}
        assert _get_duration(metadata, "p1") == 30

    def test_no_data(self):
        metadata = {"p1": {"minMinutesSpent": None, "maxMinutesSpent": None}}
        assert _get_duration(metadata, "p1") == 0

    def test_missing_place(self):
        assert _get_duration({}, "unknown") == 0

    def test_empty_place_id(self):
        assert _get_duration({"": {}}, "") == 0


class TestBuildDistanceMap:
    def test_basic(self):
        distances = {
            '["a","b","driving"]': {
                "fromPlaceId": "a",
                "toPlaceId": "b",
                "travelMode": "driving",
                "route": {"duration": {"value": 600}},
            }
        }
        result = _build_distance_map(distances)
        assert result[("a", "b", "driving")] == 600

    def test_walking_mode(self):
        distances = {
            '["a","b","walking"]': {
                "fromPlaceId": "a",
                "toPlaceId": "b",
                "travelMode": "walking",
                "route": {"duration": {"value": 1200}},
            }
        }
        result = _build_distance_map(distances)
        assert result[("a", "b", "walking")] == 1200

    def test_empty(self):
        assert _build_distance_map({}) == {}


class TestLookupTravelTime:
    def test_exact_mode_match(self):
        dm = {("a", "b", "driving"): 600, ("a", "b", "walking"): 1200}
        assert _lookup_travel_time(dm, "a", "b", "driving") == (600, "driving")
        assert _lookup_travel_time(dm, "a", "b", "walking") == (1200, "walking")

    def test_none_defaults_to_driving(self):
        dm = {("a", "b", "driving"): 600}
        assert _lookup_travel_time(dm, "a", "b", None) == (600, "driving")

    def test_fallback_to_any_mode(self):
        dm = {("a", "b", "walking"): 1200}
        # Requesting driving but only walking exists — falls back
        secs, mode = _lookup_travel_time(dm, "a", "b", "driving")
        assert secs == 1200
        assert mode == "walking"

    def test_no_match(self):
        dm = {("a", "b", "driving"): 600}
        secs, mode = _lookup_travel_time(dm, "x", "y", "driving")
        assert secs == 0


class TestBuildPlaceMetadata:
    def test_basic(self):
        metadata_list = [
            {"placeId": "p1", "minMinutesSpent": 25, "maxMinutesSpent": 25},
            {"placeId": "p2", "minMinutesSpent": 60, "maxMinutesSpent": 90},
        ]
        lookup = _build_place_metadata(metadata_list)
        assert "p1" in lookup
        assert lookup["p1"]["minMinutesSpent"] == 25

    def test_empty(self):
        assert _build_place_metadata([]) == {}


class TestExtractNotes:
    def test_basic(self):
        text = {"ops": [{"insert": "Book ahead\n"}]}
        assert "Book ahead" in _extract_notes(text)

    def test_empty(self):
        assert _extract_notes({}) == ""
        assert _extract_notes({"ops": [{"insert": "\n"}]}) == ""

    def test_none(self):
        assert _extract_notes(None) == ""


class TestRealWorldDuration:
    """Verify that placeMetadata durations like LSOUL (25 min) are picked up."""

    def test_25_min_duration_from_metadata(self):
        """Simulates a place like LSOUL with minMinutesSpent=25, maxMinutesSpent=25."""
        data = {
            "tripPlan": {
                "title": "Vietnam Trip",
                "itinerary": {
                    "sections": [
                        {
                            "mode": "dayPlan",
                            "date": "2026-03-20",
                            "blocks": [
                                {
                                    "type": "place",
                                    "place": {
                                        "name": "LSOUL",
                                        "place_id": "ChIJVb9FTqUvdTERYTbXJObsF-c",
                                        "geometry": {"location": {"lat": 10.76, "lng": 106.69}},
                                        "formatted_address": "257B Nguyễn Trãi, District 1, HCMC",
                                    },
                                },
                            ],
                        },
                    ],
                },
            },
            "resources": {
                "placeMetadata": [
                    {
                        "placeId": "ChIJVb9FTqUvdTERYTbXJObsF-c",
                        "name": "LSOUL",
                        "minMinutesSpent": 25,
                        "maxMinutesSpent": 25,
                    },
                ],
                "distancesBetweenPlaces": {},
            },
        }
        trip = _parse_itinerary_response("test", data)
        assert len(trip.days) == 1
        item = trip.days[0].items[0]
        assert item.name == "LSOUL"
        assert item.duration_minutes == 25
        assert item.address == "257B Nguyễn Trãi, District 1, HCMC"


class TestTravelModeSelection:
    """Verify that travel mode per block is respected for distance lookups."""

    def test_walking_mode_used_when_set(self):
        data = {
            "tripPlan": {
                "title": "Walk Trip",
                "itinerary": {
                    "sections": [
                        {
                            "mode": "dayPlan",
                            "date": "2026-04-20",
                            "blocks": [
                                {
                                    "type": "place",
                                    "travelMode": "walking",
                                    "place": {
                                        "name": "A",
                                        "place_id": "place_a",
                                        "geometry": {"location": {"lat": 1, "lng": 2}},
                                    },
                                },
                                {
                                    "type": "place",
                                    "place": {
                                        "name": "B",
                                        "place_id": "place_b",
                                        "geometry": {"location": {"lat": 3, "lng": 4}},
                                    },
                                },
                            ],
                        }
                    ],
                },
            },
            "resources": {
                "placeMetadata": [],
                "distancesBetweenPlaces": {
                    '["place_a","place_b","walking"]': {
                        "fromPlaceId": "place_a",
                        "toPlaceId": "place_b",
                        "travelMode": "walking",
                        "route": {"duration": {"value": 1200}},
                    },
                    '["place_a","place_b","driving"]': {
                        "fromPlaceId": "place_a",
                        "toPlaceId": "place_b",
                        "travelMode": "driving",
                        "route": {"duration": {"value": 300}},
                    },
                },
            },
        }
        trip = _parse_itinerary_response("test", data)
        # Block A has travelMode="walking", so should use 1200s = 20 min
        assert trip.days[0].items[0].travel_minutes_to_next == 20
        assert trip.days[0].items[0].travel_mode == "walking"

    def test_driving_mode_default_when_none(self):
        data = {
            "tripPlan": {
                "title": "Drive Trip",
                "itinerary": {
                    "sections": [
                        {
                            "mode": "dayPlan",
                            "date": "2026-04-20",
                            "blocks": [
                                {
                                    "type": "place",
                                    "travelMode": None,
                                    "place": {
                                        "name": "A",
                                        "place_id": "place_a",
                                        "geometry": {"location": {"lat": 1, "lng": 2}},
                                    },
                                },
                                {
                                    "type": "place",
                                    "place": {
                                        "name": "B",
                                        "place_id": "place_b",
                                        "geometry": {"location": {"lat": 3, "lng": 4}},
                                    },
                                },
                            ],
                        }
                    ],
                },
            },
            "resources": {
                "placeMetadata": [],
                "distancesBetweenPlaces": {
                    '["place_a","place_b","walking"]': {
                        "fromPlaceId": "place_a",
                        "toPlaceId": "place_b",
                        "travelMode": "walking",
                        "route": {"duration": {"value": 1200}},
                    },
                    '["place_a","place_b","driving"]': {
                        "fromPlaceId": "place_a",
                        "toPlaceId": "place_b",
                        "travelMode": "driving",
                        "route": {"duration": {"value": 300}},
                    },
                },
            },
        }
        trip = _parse_itinerary_response("test", data)
        # Block A has travelMode=None, defaults to driving = 300s = 5 min
        assert trip.days[0].items[0].travel_minutes_to_next == 5
        assert trip.days[0].items[0].travel_mode == "driving"

    def test_fallback_when_mode_not_available(self):
        data = {
            "tripPlan": {
                "title": "Fallback Trip",
                "itinerary": {
                    "sections": [
                        {
                            "mode": "dayPlan",
                            "date": "2026-04-20",
                            "blocks": [
                                {
                                    "type": "place",
                                    "travelMode": "driving",
                                    "place": {
                                        "name": "A",
                                        "place_id": "place_a",
                                        "geometry": {"location": {"lat": 1, "lng": 2}},
                                    },
                                },
                                {
                                    "type": "place",
                                    "place": {
                                        "name": "B",
                                        "place_id": "place_b",
                                        "geometry": {"location": {"lat": 3, "lng": 4}},
                                    },
                                },
                            ],
                        }
                    ],
                },
            },
            "resources": {
                "placeMetadata": [],
                "distancesBetweenPlaces": {
                    '["place_a","place_b","walking"]': {
                        "fromPlaceId": "place_a",
                        "toPlaceId": "place_b",
                        "travelMode": "walking",
                        "route": {"duration": {"value": 1200}},
                    },
                },
            },
        }
        trip = _parse_itinerary_response("test", data)
        # Block A requests driving but only walking exists — falls back to walking = 20 min
        assert trip.days[0].items[0].travel_minutes_to_next == 20
        assert trip.days[0].items[0].travel_mode == "walking"


class TestDetectTimezone:
    def test_detects_vietnam_timezone(self):
        from wanderlogpro.calendar_export.models import ItineraryDay, ItineraryItem
        days = [ItineraryDay(
            date="2026-03-20",
            items=[ItineraryItem(name="HCMC", lat=10.76, lng=106.69)],
        )]
        assert _detect_timezone(days) == "Asia/Ho_Chi_Minh"

    def test_detects_paris_timezone(self):
        from wanderlogpro.calendar_export.models import ItineraryDay, ItineraryItem
        days = [ItineraryDay(
            date="2026-04-20",
            items=[ItineraryItem(name="Eiffel", lat=48.8584, lng=2.2945)],
        )]
        assert _detect_timezone(days) == "Europe/Paris"

    def test_fallback_to_utc_on_zero_coords(self):
        from wanderlogpro.calendar_export.models import ItineraryDay, ItineraryItem
        days = [ItineraryDay(
            date="2026-04-20",
            items=[ItineraryItem(name="Unknown", lat=0.0, lng=0.0)],
        )]
        assert _detect_timezone(days) == "UTC"

    def test_fallback_to_utc_on_empty_days(self):
        assert _detect_timezone([]) == "UTC"

    def test_parse_itinerary_sets_timezone(self):
        """Full integration: _parse_itinerary_response should set timezone."""
        trip = _parse_itinerary_response("test", SAMPLE_TRIP_STORE)
        # SAMPLE_TRIP_STORE has Paris coordinates (lat=48.86, lng=2.35)
        assert trip.timezone == "Europe/Paris"


class TestExtractDescription:
    def test_opening_hours(self):
        place = {
            "opening_hours": {
                "weekday_text": [
                    "Monday: 9 AM\u20135 PM",
                    "Tuesday: 9 AM\u20135 PM",
                ]
            }
        }
        desc = _extract_description(place)
        assert "Monday: 9 AM" in desc
        assert "Tuesday: 9 AM" in desc

    def test_rating_only_ignored(self):
        """Rating-only places return empty description."""
        place = {"rating": 4.5, "user_ratings_total": 1200}
        desc = _extract_description(place)
        assert desc == ""

    def test_rating_not_in_description(self):
        """Rating is no longer included in description."""
        place = {"rating": 3.8}
        desc = _extract_description(place)
        assert desc == ""

    def test_opening_hours_without_rating(self):
        place = {
            "opening_hours": {"weekday_text": ["Monday: 10 AM\u20136 PM"]},
            "rating": 4.2,
            "user_ratings_total": 500,
        }
        desc = _extract_description(place)
        assert "Monday: 10 AM" in desc
        assert "4.2" not in desc

    def test_date_filters_to_weekday(self):
        """Passing a Monday date returns only Monday's hours."""
        place = {
            "opening_hours": {
                "weekday_text": [
                    "Monday: 9 AM\u20135 PM",
                    "Tuesday: 10 AM\u20134 PM",
                    "Wednesday: 9 AM\u20135 PM",
                    "Thursday: 9 AM\u20135 PM",
                    "Friday: 9 AM\u20138 PM",
                    "Saturday: 10 AM\u20136 PM",
                    "Sunday: Closed",
                ]
            }
        }
        # 2026-03-16 is a Monday
        desc = _extract_description(place, "2026-03-16")
        assert desc == "Monday: 9 AM\u20135 PM"

    def test_date_filters_saturday(self):
        place = {
            "opening_hours": {
                "weekday_text": [
                    "Monday: 9 AM\u20135 PM",
                    "Tuesday: 10 AM\u20134 PM",
                    "Wednesday: 9 AM\u20135 PM",
                    "Thursday: 9 AM\u20135 PM",
                    "Friday: 9 AM\u20138 PM",
                    "Saturday: 10 AM\u20136 PM",
                    "Sunday: Closed",
                ]
            }
        }
        # 2026-03-21 is a Saturday
        desc = _extract_description(place, "2026-03-21")
        assert desc == "Saturday: 10 AM\u20136 PM"

    def test_no_date_shows_all(self):
        """Without date, all 7 days are shown."""
        place = {
            "opening_hours": {
                "weekday_text": ["Mon: 9-5", "Tue: 9-5", "Wed: 9-5", "Thu: 9-5", "Fri: 9-5", "Sat: 10-4", "Sun: Closed"]
            }
        }
        desc = _extract_description(place)
        assert "Mon:" in desc and "Sun:" in desc

    def test_empty_place(self):
        assert _extract_description({}) == ""

    def test_no_weekday_text(self):
        place = {"opening_hours": {}}
        assert _extract_description(place) == ""

    def test_invalid_opening_hours_type(self):
        place = {"opening_hours": "not a dict"}
        assert _extract_description(place) == ""


class TestDayNotes:
    def test_text_blocks_collected_as_day_notes(self):
        """Text blocks in a dayPlan section become ItineraryDay.notes."""
        store = {
            "tripPlan": {
                "title": "Test Trip",
                "itinerary": {
                    "sections": [
                        {
                            "mode": "dayPlan",
                            "date": "2026-01-01",
                            "blocks": [
                                {
                                    "type": "text",
                                    "text": {"ops": [{"insert": "Remember to pack sunscreen\n"}]},
                                },
                                {
                                    "type": "place",
                                    "place": {
                                        "name": "Beach",
                                        "place_id": "beach_id",
                                        "geometry": {"location": {"lat": 10.0, "lng": 20.0}},
                                    },
                                    "startTime": "09:00",
                                    "text": {},
                                },
                                {
                                    "type": "text",
                                    "text": {"ops": [{"insert": "Bring extra water\n"}]},
                                },
                            ],
                        }
                    ],
                },
            },
            "resources": {"placeMetadata": [], "distancesBetweenPlaces": {}},
        }
        trip = _parse_itinerary_response("test", store)
        assert len(trip.days) == 1
        assert trip.days[0].notes == "Remember to pack sunscreen\nBring extra water"
        assert len(trip.days[0].items) == 1

    def test_no_text_blocks_empty_notes(self):
        """Day with only place blocks has empty notes."""
        trip = _parse_itinerary_response("test", SAMPLE_TRIP_STORE)
        for day in trip.days:
            assert day.notes == ""

    def test_place_description_extracted(self):
        """Place with opening_hours gets a description filtered to that day."""
        store = {
            "tripPlan": {
                "title": "Test Trip",
                "itinerary": {
                    "sections": [
                        {
                            "mode": "dayPlan",
                            "date": "2026-01-05",
                            "blocks": [
                                {
                                    "type": "place",
                                    "place": {
                                        "name": "Museum",
                                        "place_id": "museum_id",
                                        "geometry": {"location": {"lat": 10.0, "lng": 20.0}},
                                        "opening_hours": {
                                            "weekday_text": [
                                                "Monday: 10 AM\u20135 PM",
                                                "Tuesday: 10 AM\u20135 PM",
                                                "Wednesday: 10 AM\u20135 PM",
                                                "Thursday: 10 AM\u20135 PM",
                                                "Friday: 10 AM\u20138 PM",
                                                "Saturday: 11 AM\u20136 PM",
                                                "Sunday: Closed",
                                            ]
                                        },
                                        "rating": 4.6,
                                        "user_ratings_total": 3000,
                                    },
                                    "startTime": "10:00",
                                    "text": {},
                                },
                            ],
                        }
                    ],
                },
            },
            "resources": {"placeMetadata": [], "distancesBetweenPlaces": {}},
        }
        trip = _parse_itinerary_response("test", store)
        item = trip.days[0].items[0]
        # 2026-01-05 is a Monday
        assert item.description == "Monday: 10 AM\u20135 PM"
        assert "4.6" not in item.description
