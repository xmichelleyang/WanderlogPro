"""Data models for WanderlogPro."""

from dataclasses import dataclass, field


@dataclass
class Place:
    """A single place/point of interest."""

    name: str
    lat: float
    lng: float
    address: str = ""
    notes: str = ""
    list_name: str = ""
    icon: str = ""
    color: str = ""


@dataclass
class PlaceList:
    """A named list of places with an icon and color."""

    name: str
    icon: str = ""
    color: str = ""
    places: list[Place] = field(default_factory=list)


@dataclass
class Trip:
    """A Wanderlog trip containing multiple place lists."""

    id: str
    name: str
    place_lists: list[PlaceList] = field(default_factory=list)
