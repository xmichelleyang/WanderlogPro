"""Tests for icon/color mapping."""

from wanderlogpro.map_export.icon_map import (
    DEFAULT_MAPSPRO_ID,
    get_kml_style,
    get_mapspro_id,
    get_mymaps_style_id,
    hex_to_kml_color,
    normalize_hex_color,
)


class TestHexToKmlColor:
    def test_standard_red(self):
        assert hex_to_kml_color("#FF0000") == "ff0000ff"

    def test_standard_green(self):
        assert hex_to_kml_color("#00FF00") == "ff00ff00"

    def test_standard_blue(self):
        assert hex_to_kml_color("#0000FF") == "ffff0000"

    def test_mixed_color(self):
        assert hex_to_kml_color("#FF5733") == "ff3357ff"

    def test_without_hash(self):
        assert hex_to_kml_color("FF5733") == "ff3357ff"

    def test_custom_alpha(self):
        assert hex_to_kml_color("#FF0000", alpha="80") == "800000ff"

    def test_invalid_color_returns_fallback(self):
        assert hex_to_kml_color("bad") == "ff0000ff"

    def test_empty_string_returns_fallback(self):
        assert hex_to_kml_color("") == "ff0000ff"

    def test_lowercase_input(self):
        assert hex_to_kml_color("#ff5733") == "ff3357ff"


class TestNormalizeHexColor:
    def test_strips_hash(self):
        assert normalize_hex_color("#3F52E3") == "3F52E3"

    def test_uppercases(self):
        assert normalize_hex_color("#3f52e3") == "3F52E3"

    def test_no_hash(self):
        assert normalize_hex_color("E74C3C") == "E74C3C"

    def test_invalid_returns_default(self):
        assert normalize_hex_color("bad") == "DB4436"

    def test_empty_returns_default(self):
        assert normalize_hex_color("") == "DB4436"


class TestGetMapsproId:
    def test_utensils(self):
        assert get_mapspro_id("utensils") == 1577

    def test_mountain(self):
        assert get_mapspro_id("mountain") == 1634

    def test_hotel(self):
        assert get_mapspro_id("hotel") == 1602

    def test_shopping_bag(self):
        assert get_mapspro_id("shopping-bag") == 1684

    def test_camera(self):
        assert get_mapspro_id("camera") == 1535

    def test_case_insensitive(self):
        assert get_mapspro_id("UTENSILS") == get_mapspro_id("utensils")

    def test_with_whitespace(self):
        assert get_mapspro_id("  utensils  ") == get_mapspro_id("utensils")

    def test_unknown_icon_returns_default(self):
        assert get_mapspro_id("unknown_xyz") == DEFAULT_MAPSPRO_ID

    def test_empty_returns_default(self):
        assert get_mapspro_id("") == DEFAULT_MAPSPRO_ID

    def test_coffee_variants(self):
        assert get_mapspro_id("cafe") == get_mapspro_id("coffee")

    def test_nature_variants(self):
        assert get_mapspro_id("park") == get_mapspro_id("tree")

    def test_ship(self):
        assert get_mapspro_id("ship") == 1569

    def test_wine_glass(self):
        assert get_mapspro_id("wine-glass") == 1517

    def test_map_marker(self):
        assert get_mapspro_id("map-marker") == 1899

    def test_ice_cream(self):
        assert get_mapspro_id("ice-cream") == 1607

    def test_pizza(self):
        assert get_mapspro_id("pizza-slice") == 1651

    def test_burger(self):
        assert get_mapspro_id("hamburger") == 1530

    def test_beer(self):
        assert get_mapspro_id("beer") == 1879

    def test_bus(self):
        assert get_mapspro_id("bus") == 1532

    def test_train(self):
        assert get_mapspro_id("train") == 1716

    def test_museum(self):
        assert get_mapspro_id("museum") == 1636


class TestGetMymapsStyleId:
    def test_utensils_red(self):
        assert get_mymaps_style_id("utensils", "#E74C3C") == "icon-1577-E74C3C"

    def test_mountain_blue(self):
        assert get_mymaps_style_id("mountain", "#3F52E3") == "icon-1634-3F52E3"

    def test_defaults(self):
        assert get_mymaps_style_id() == "icon-1899-DB4436"

    def test_lowercase_color_normalized(self):
        assert get_mymaps_style_id("camera", "#3f52e3") == "icon-1535-3F52E3"

    def test_ice_cream(self):
        assert get_mymaps_style_id("ice-cream", "#004A7C") == "icon-1607-004A7C"


class TestGetKmlStyle:
    def test_with_icon_and_color(self):
        style = get_kml_style(icon="utensils", color="#E74C3C")
        assert style["style_id"] == "icon-1577-E74C3C"
        assert "gstatic.com" in style["icon_href"]
        assert style["color"] == "ff3c4ce7"

    def test_empty_icon_and_color(self):
        style = get_kml_style()
        assert style["style_id"] == "icon-1899-DB4436"
        assert style["color"] == "ff0000ff"

    def test_only_color(self):
        style = get_kml_style(color="#00FF00")
        assert style["style_id"] == "icon-1899-00FF00"
        assert style["color"] == "ff00ff00"

    def test_only_icon(self):
        style = get_kml_style(icon="hotel")
        assert style["style_id"] == "icon-1602-DB4436"
