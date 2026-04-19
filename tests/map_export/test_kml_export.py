"""Tests for KML export."""

import xml.etree.ElementTree as ET
from pathlib import Path

from wanderlogpro.map_export.kml_export import export_trip_to_kml
from wanderlogpro.map_export.models import Place, PlaceList, Trip

KML_NS = "{http://www.opengis.net/kml/2.2}"


def _make_test_trip() -> Trip:
    return Trip(
        id="test123",
        name="Test Trip",
        place_lists=[
            PlaceList(
                name="Restaurants",
                icon="utensils",
                color="#E74C3C",
                places=[
                    Place(name="Place A", lat=48.85, lng=2.35, address="Paris"),
                    Place(name="Place B", lat=48.86, lng=2.34, notes="Great food"),
                ],
            ),
            PlaceList(
                name="Hotels",
                icon="bed",
                color="#3498DB",
                places=[
                    Place(name="Hotel X", lat=48.87, lng=2.33, address="1 Rue X"),
                ],
            ),
            PlaceList(name="Empty List", places=[]),
        ],
    )


def _parse_kml(path: Path) -> ET.Element:
    tree = ET.parse(path)
    return tree.getroot()


def test_export_creates_file(tmp_path: Path):
    trip = _make_test_trip()
    output = tmp_path / "test.kml"
    result = export_trip_to_kml(trip, output)
    assert result.exists()
    assert result.suffix == ".kml"


def test_kml_has_correct_folders(tmp_path: Path):
    trip = _make_test_trip()
    output = tmp_path / "test.kml"
    export_trip_to_kml(trip, output)

    root = _parse_kml(output)
    folders = root.findall(f".//{KML_NS}Folder")

    # Empty list should be skipped
    assert len(folders) == 2
    folder_names = [f.find(f"{KML_NS}name").text for f in folders]
    assert "Restaurants" in folder_names
    assert "Hotels" in folder_names


def test_kml_placemarks_have_coordinates(tmp_path: Path):
    trip = _make_test_trip()
    output = tmp_path / "test.kml"
    export_trip_to_kml(trip, output)

    root = _parse_kml(output)
    placemarks = root.findall(f".//{KML_NS}Placemark")
    assert len(placemarks) == 3

    for pm in placemarks:
        coords = pm.find(f".//{KML_NS}coordinates")
        assert coords is not None
        assert coords.text.strip() != ""


def test_kml_style_ids_use_mymaps_format(tmp_path: Path):
    """Style IDs must be in icon-{MAPSPRO_ID}-{HEX_COLOR} format."""
    trip = _make_test_trip()
    output = tmp_path / "test.kml"
    export_trip_to_kml(trip, output)

    root = _parse_kml(output)
    styles = root.findall(f".//{KML_NS}Style")

    assert len(styles) >= 2
    style_ids = [s.get("id") for s in styles]
    # utensils=1577 with color E74C3C, bed=1602 with color 3498DB
    assert "icon-1577-E74C3C" in style_ids
    assert "icon-1602-3498DB" in style_ids


def test_kml_styleurl_references_mymaps_format(tmp_path: Path):
    """Each placemark's styleUrl must reference #icon-{ID}-{COLOR}."""
    trip = _make_test_trip()
    output = tmp_path / "test.kml"
    export_trip_to_kml(trip, output)

    root = _parse_kml(output)
    placemarks = root.findall(f".//{KML_NS}Placemark")

    for pm in placemarks:
        style_url = pm.find(f"{KML_NS}styleUrl")
        assert style_url is not None
        assert style_url.text.startswith("#icon-")

    # Check specific style URLs
    restaurant_folder = None
    for folder in root.findall(f".//{KML_NS}Folder"):
        if folder.find(f"{KML_NS}name").text == "Restaurants":
            restaurant_folder = folder
            break
    assert restaurant_folder is not None
    for pm in restaurant_folder.findall(f"{KML_NS}Placemark"):
        assert pm.find(f"{KML_NS}styleUrl").text == "#icon-1577-E74C3C"


def test_kml_styles_have_icon_href(tmp_path: Path):
    trip = _make_test_trip()
    output = tmp_path / "test.kml"
    export_trip_to_kml(trip, output)

    root = _parse_kml(output)
    icon_hrefs = root.findall(f".//{KML_NS}IconStyle/{KML_NS}Icon/{KML_NS}href")
    assert len(icon_hrefs) > 0
    for href in icon_hrefs:
        assert "gstatic.com" in href.text


def test_kml_styles_have_abgr_colors(tmp_path: Path):
    trip = _make_test_trip()
    output = tmp_path / "test.kml"
    export_trip_to_kml(trip, output)

    root = _parse_kml(output)
    colors = root.findall(f".//{KML_NS}IconStyle/{KML_NS}color")
    assert len(colors) > 0
    color_values = [c.text for c in colors]
    # #E74C3C → ABGR = ff3c4ce7
    assert any("ff3c4ce7" in c for c in color_values)
    # #3498DB → ABGR = ffdb9834
    assert any("ffdb9834" in c for c in color_values)


def test_kml_description_includes_address(tmp_path: Path):
    trip = _make_test_trip()
    output = tmp_path / "test.kml"
    export_trip_to_kml(trip, output)

    content = output.read_text(encoding="utf-8")
    assert "Paris" in content


def test_kml_description_includes_notes(tmp_path: Path):
    trip = _make_test_trip()
    output = tmp_path / "test.kml"
    export_trip_to_kml(trip, output)

    content = output.read_text(encoding="utf-8")
    assert "Great food" in content
