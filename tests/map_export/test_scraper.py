"""Tests for the Wanderlog scraper."""

import pytest

from wanderlogpro.map_export.scraper import _parse_trip_response
from wanderlogpro.utils import normalize_wanderlog_url, parse_trip_id


class TestParseTripId:
    def test_standard_url(self):
        assert parse_trip_id("https://wanderlog.com/view/abc123/my-trip") == "abc123"

    def test_url_without_slug(self):
        assert parse_trip_id("https://wanderlog.com/view/abc123") == "abc123"

    def test_url_without_scheme(self):
        assert parse_trip_id("wanderlog.com/view/abc123/trip") == "abc123"

    def test_url_with_query_params(self):
        assert parse_trip_id("https://wanderlog.com/view/abc123?tab=map") == "abc123"

    def test_url_with_shared_suffix(self):
        assert parse_trip_id("https://wanderlog.com/view/abc123/my-trip/shared") == "abc123"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Could not parse trip ID"):
            parse_trip_id("https://google.com/something")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_trip_id("")

    def test_plan_url_standard(self):
        assert parse_trip_id("https://wanderlog.com/plan/abc123/my-trip/shared") == "abc123"

    def test_plan_url_without_suffix(self):
        assert parse_trip_id("https://wanderlog.com/plan/abc123/my-trip") == "abc123"

    def test_plan_url_bare(self):
        assert parse_trip_id("wanderlog.com/plan/abc123") == "abc123"

    def test_plan_url_long_id(self):
        assert parse_trip_id("https://wanderlog.com/plan/gpaxvjfljkfalyeh/trip-to-vietnam/shared") == "gpaxvjfljkfalyeh"


class TestNormalizeWanderlogUrl:
    def test_view_url_unchanged(self):
        url = "https://wanderlog.com/view/abc123/my-trip"
        assert normalize_wanderlog_url(url) == url

    def test_plan_url_unchanged(self):
        url = "https://wanderlog.com/plan/abc123/my-trip"
        assert normalize_wanderlog_url(url) == url

    def test_plan_url_with_shared_suffix_unchanged(self):
        url = "https://wanderlog.com/plan/abc123/my-trip/shared"
        assert normalize_wanderlog_url(url) == url

    def test_missing_scheme_gets_https_plan(self):
        assert (
            normalize_wanderlog_url("wanderlog.com/plan/abc123")
            == "https://wanderlog.com/plan/abc123"
        )

    def test_missing_scheme_gets_https_view(self):
        assert (
            normalize_wanderlog_url("wanderlog.com/view/abc123/trip")
            == "https://wanderlog.com/view/abc123/trip"
        )


SAMPLE_TRIP_DATA = {
    "title": "Paris 2026",
    "key": "trip123",
    "itinerary": {
        "sections": [
            {
                "heading": "Restaurants",
                "placeMarkerColor": "#E74C3C",
                "placeMarkerIcon": "utensils",
                "blocks": [
                    {
                        "id": 1,
                        "type": "place",
                        "place": {
                            "name": "Le Comptoir",
                            "geometry": {"location": {"lat": 48.8534, "lng": 2.3488}},
                            "address_components": [
                                {"long_name": "Paris", "short_name": "Paris", "types": ["locality"]},
                                {"long_name": "France", "short_name": "FR", "types": ["country"]},
                            ],
                        },
                        "text": {"ops": [{"insert": "Great bistro\n"}]},
                    },
                    {
                        "id": 2,
                        "type": "place",
                        "place": {
                            "name": "Cafe de Flore",
                            "geometry": {"location": {"lat": 48.8540, "lng": 2.3325}},
                            "address_components": [
                                {"long_name": "172 Bd Saint-Germain", "short_name": "172 Bd Saint-Germain", "types": ["street_address"]},
                            ],
                        },
                    },
                ],
            },
            {
                "heading": "Sightseeing",
                "placeMarkerColor": "#3498DB",
                "placeMarkerIcon": "camera",
                "blocks": [
                    {
                        "id": 3,
                        "type": "place",
                        "place": {
                            "name": "Eiffel Tower",
                            "geometry": {"location": {"lat": 48.8584, "lng": 2.2945}},
                            "address_components": [
                                {"long_name": "Champ de Mars", "short_name": "Champ de Mars", "types": ["premise"]},
                            ],
                        },
                        "text": {"ops": [{"insert": "Book evening slot\n"}]},
                    },
                ],
            },
        ],
    },
}


class TestParseTripResponse:
    def test_basic_parsing(self):
        trip = _parse_trip_response("trip123", SAMPLE_TRIP_DATA)
        assert trip.id == "trip123"
        assert trip.name == "Paris 2026"
        assert len(trip.place_lists) == 2

    def test_list_names(self):
        trip = _parse_trip_response("trip123", SAMPLE_TRIP_DATA)
        names = {pl.name for pl in trip.place_lists}
        assert "Restaurants" in names
        assert "Sightseeing" in names

    def test_list_icons_and_colors(self):
        trip = _parse_trip_response("trip123", SAMPLE_TRIP_DATA)
        restaurants = next(pl for pl in trip.place_lists if pl.name == "Restaurants")
        assert restaurants.icon == "utensils"
        assert restaurants.color == "#E74C3C"

    def test_places_assigned_to_lists(self):
        trip = _parse_trip_response("trip123", SAMPLE_TRIP_DATA)
        restaurants = next(pl for pl in trip.place_lists if pl.name == "Restaurants")
        sightseeing = next(pl for pl in trip.place_lists if pl.name == "Sightseeing")
        assert len(restaurants.places) == 2
        assert len(sightseeing.places) == 1

    def test_place_coordinates(self):
        trip = _parse_trip_response("trip123", SAMPLE_TRIP_DATA)
        restaurants = next(pl for pl in trip.place_lists if pl.name == "Restaurants")
        le_comptoir = restaurants.places[0]
        assert le_comptoir.lat == 48.8534
        assert le_comptoir.lng == 2.3488

    def test_place_notes_from_text_ops(self):
        trip = _parse_trip_response("trip123", SAMPLE_TRIP_DATA)
        restaurants = next(pl for pl in trip.place_lists if pl.name == "Restaurants")
        le_comptoir = restaurants.places[0]
        assert "Great bistro" in le_comptoir.notes

    def test_section_with_no_heading_uses_default(self):
        data = {
            "title": "Test",
            "itinerary": {
                "sections": [
                    {
                        "heading": "",
                        "blocks": [
                            {
                                "type": "place",
                                "place": {
                                    "name": "Orphan",
                                    "geometry": {"location": {"lat": 1.0, "lng": 2.0}},
                                },
                            },
                        ],
                    },
                ],
            },
        }
        trip = _parse_trip_response("t1", data)
        assert len(trip.place_lists) == 1
        assert trip.place_lists[0].name == "Other Places"

    def test_skips_places_without_coordinates(self):
        data = {
            "title": "Test",
            "itinerary": {
                "sections": [
                    {
                        "heading": "Places",
                        "blocks": [
                            {
                                "type": "place",
                                "place": {
                                    "name": "No coords",
                                    "geometry": {"location": {"lat": 0.0, "lng": 0.0}},
                                },
                            },
                            {
                                "type": "place",
                                "place": {
                                    "name": "Has coords",
                                    "geometry": {"location": {"lat": 1.0, "lng": 2.0}},
                                },
                            },
                        ],
                    },
                ],
            },
        }
        trip = _parse_trip_response("t1", data)
        total = sum(len(pl.places) for pl in trip.place_lists)
        assert total == 1

    def test_skips_non_place_blocks(self):
        data = {
            "title": "Test",
            "itinerary": {
                "sections": [
                    {
                        "heading": "Mix",
                        "blocks": [
                            {"type": "text", "text": "some note"},
                            {
                                "type": "place",
                                "place": {
                                    "name": "Real Place",
                                    "geometry": {"location": {"lat": 1.0, "lng": 2.0}},
                                },
                            },
                        ],
                    },
                ],
            },
        }
        trip = _parse_trip_response("t1", data)
        assert sum(len(pl.places) for pl in trip.place_lists) == 1

    def test_empty_trip(self):
        data = {"title": "Empty", "itinerary": {"sections": []}}
        trip = _parse_trip_response("t1", data)
        assert trip.place_lists == []
