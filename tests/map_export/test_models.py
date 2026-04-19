"""Tests for data models."""

from wanderlogpro.map_export.models import Place, PlaceList, Trip


def test_place_defaults():
    p = Place(name="Cafe", lat=40.0, lng=-74.0)
    assert p.name == "Cafe"
    assert p.address == ""
    assert p.notes == ""
    assert p.icon == ""
    assert p.color == ""


def test_place_with_all_fields():
    p = Place(
        name="Tower of London",
        lat=51.5081,
        lng=-0.0759,
        address="London, UK",
        notes="Buy tickets online",
        list_name="attractions",
        icon="star",
        color="#FF0000",
    )
    assert p.lat == 51.5081
    assert p.icon == "star"
    assert p.color == "#FF0000"


def test_place_list_defaults():
    pl = PlaceList(name="Restaurants")
    assert pl.name == "Restaurants"
    assert pl.places == []
    assert pl.icon == ""
    assert pl.color == ""


def test_place_list_with_places():
    places = [
        Place(name="A", lat=1.0, lng=2.0),
        Place(name="B", lat=3.0, lng=4.0),
    ]
    pl = PlaceList(name="Food", icon="restaurant", color="#FF5733", places=places)
    assert len(pl.places) == 2
    assert pl.icon == "restaurant"


def test_trip():
    pl = PlaceList(name="Sights", places=[Place(name="X", lat=0, lng=0)])
    trip = Trip(id="abc123", name="Paris Trip", place_lists=[pl])
    assert trip.id == "abc123"
    assert len(trip.place_lists) == 1
    assert trip.place_lists[0].name == "Sights"
