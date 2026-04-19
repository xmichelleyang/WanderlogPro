"""KML export with Google My Maps-compatible styled layers.

Uses raw XML generation instead of simplekml to control Style IDs.
Google My Maps requires styleUrl format: #icon-{MAPSPRO_ID}-{HEX_COLOR}
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from wanderlogpro.map_export.icon_map import get_kml_style
from wanderlogpro.map_export.models import PlaceList, Trip

KML_NS = "http://www.opengis.net/kml/2.2"


def export_trip_to_kml(trip: Trip, output_path: str | Path) -> Path:
    """Export a Trip to a KML file with Google My Maps-compatible styles.

    Each PlaceList becomes a KML Folder (layer in Google My Maps) with
    matching icon and color via the mapspro styleUrl format.
    """
    output_path = Path(output_path)

    kml = ET.Element("kml", xmlns=KML_NS)
    document = ET.SubElement(kml, "Document")
    ET.SubElement(document, "name").text = trip.name

    # Collect all unique styles needed, then add folders
    styles_added: set[str] = set()

    for place_list in trip.place_lists:
        if not place_list.places:
            continue

        style_props = get_kml_style(icon=place_list.icon, color=place_list.color)
        style_id = style_props["style_id"]

        # Add <Style> at Document level if not already added
        if style_id not in styles_added:
            _add_style(document, style_props)
            styles_added.add(style_id)

        # Add the folder with placemarks
        _add_place_list_folder(document, place_list, style_id)

    # Write pretty-printed XML
    xml_str = ET.tostring(kml, encoding="unicode", xml_declaration=False)
    pretty = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="UTF-8")

    output_path.write_bytes(pretty)
    return output_path


def _add_style(document: ET.Element, style_props: dict[str, str]) -> None:
    """Add a <Style> element with Google My Maps-compatible ID."""
    style = ET.SubElement(document, "Style", id=style_props["style_id"])
    icon_style = ET.SubElement(style, "IconStyle")
    ET.SubElement(icon_style, "color").text = style_props["color"]
    ET.SubElement(icon_style, "scale").text = "1.1"
    icon = ET.SubElement(icon_style, "Icon")
    ET.SubElement(icon, "href").text = style_props["icon_href"]
    # Hotspot for pin alignment
    ET.SubElement(icon_style, "hotSpot", x="32", xunits="pixels", y="64", yunits="insetPixels")


def _add_place_list_folder(
    document: ET.Element, place_list: PlaceList, style_id: str
) -> None:
    """Add a PlaceList as a KML Folder with styled placemarks."""
    folder = ET.SubElement(document, "Folder")
    ET.SubElement(folder, "name").text = place_list.name

    for place in place_list.places:
        placemark = ET.SubElement(folder, "Placemark")
        ET.SubElement(placemark, "name").text = place.name

        # Build description from notes and address
        description_parts = []
        if place.address:
            description_parts.append(f"📍 {place.address}")
        if place.notes:
            description_parts.append(place.notes)
        if description_parts:
            ET.SubElement(placemark, "description").text = "\n".join(description_parts)

        # Reference the My Maps style
        ET.SubElement(placemark, "styleUrl").text = f"#{style_id}"

        point = ET.SubElement(placemark, "Point")
        ET.SubElement(point, "coordinates").text = f"{place.lng},{place.lat},0"
