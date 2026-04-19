"""Wanderlog icon/color → Google My Maps style mapping.

Google My Maps uses an internal "mapspro" icon system with numeric IDs.
The styleUrl format is: #icon-{MAPSPRO_ID}-{HEX_COLOR}
Reverse-engineered from: https://github.com/TheStalwart/google-mymaps-icons
"""

# Default My Maps icon (red pin)
DEFAULT_MAPSPRO_ID = 1899

# Default white pin href used in <Style> blocks for Google Earth fallback
DEFAULT_ICON_HREF = "https://www.gstatic.com/mapspro/images/stock/503-wht-blank_maps.png"

# Default color when none specified
DEFAULT_HEX_COLOR = "DB4436"

# Map Wanderlog Font Awesome icon names → Google My Maps mapspro icon IDs
# Full list extracted from Google CDN JS: see mapspro_icons.json
MAPSPRO_ICON_MAP: dict[str, int] = {
    # Food & Drink
    "utensils": 1577,       # food-fork-knife
    "restaurant": 1577,
    "food": 1577,
    "dining": 1577,
    "pizza-slice": 1651,    # pizza-slice
    "pizza": 1651,
    "hamburger": 1530,      # burger
    "burger": 1530,
    "ice-cream": 1607,      # ice-cream
    "ice-cream-cone": 1607,
    "coffee": 1534,         # cafe-cup
    "cafe": 1534,
    "mug-hot": 1534,
    "wine-glass": 1517,     # bar-cocktail
    "wine-glass-alt": 1517,
    "cocktail": 1517,
    "beer": 1879,           # stein-beer
    "glass-martini": 1517,
    "glass-martini-alt": 1517,
    "bar": 1518,            # bar-pub
    "nightlife": 1518,
    "noodles": 1640,        # noodles
    "chicken": 1545,        # chicken
    "fish": 1573,           # fish
    "sushi": 1835,          # musubi-sushi
    "cake": 1762,           # cake-birthday
    "hotdog": 1810,         # hotdog
    "fast-food": 1567,      # fast-food
    "groceries": 1578,      # food-groceries
    "tea": 1705,            # teapot
    # Lodging
    "hotel": 1602,          # hotel-bed
    "bed": 1602,
    "lodging": 1602,
    "accommodation": 1602,
    "concierge-bell": 1602,
    # Shopping
    "shopping-bag": 1684,   # shopping-bag
    "shopping-cart": 1685,  # shopping-cart
    "shopping": 1684,
    "shop": 1686,           # shop
    "store": 1686,
    "gift": 1584,           # gift
    # Nature & Outdoors
    "mountain": 1634,       # mountain
    "tree": 1720,           # tree
    "nature": 1720,
    "park": 1720,
    "leaf": 1720,
    "hiking": 1596,         # hiking-solo
    "walking": 1731,        # walking-pedestrian
    "water": 1892,          # waterfall
    "swimmer": 1701,        # swimming
    "swimming": 1701,
    "umbrella-beach": 1521, # beach
    "beach": 1521,
    "waterfall": 1892,
    "camping": 1765,        # camping-tent
    "campfire": 1764,       # campfire
    "garden": 1582,         # garden-flower
    "flower": 1582,
    # Sightseeing & Culture
    "camera": 1535,         # camera-photo
    "camera-retro": 1535,
    "photo": 1535,
    "museum": 1636,         # museum
    "landmark": 1599,       # historic-monument
    "monument": 1599,
    "university": 1726,     # university
    "star": 1713,           # ticket-star
    "attraction": 1713,
    "sightseeing": 1523,    # binoculars
    "heart": 1592,          # heart
    "theater": 1709,        # theater
    "temple": 1706,         # temple
    "church": 1670,         # religious-christian
    "mosque": 1673,         # religious-islamic
    "castle": 1598,         # historic-building
    "fountain": 1580,       # fountain
    "library": 1664,        # reading-library
    "art": 1509,            # art-palette
    "zoo": 1743,            # zoo-elephant
    "amusement": 1568,      # ferris-wheel
    "ferris-wheel": 1568,
    # Transport
    "ship": 1569,           # ferry
    "ferry": 1569,
    "anchor": 1623,         # marine-anchor
    "bus": 1532,            # bus
    "bus-alt": 1532,
    "transport": 1532,
    "car": 1538,            # car
    "taxi": 1704,           # taxi
    "subway": 1626,         # metro
    "metro": 1626,
    "train": 1716,          # train
    "plane": 1504,          # airport-plane
    "plane-departure": 1504,
    "plane-arrival": 1504,
    "airport": 1504,
    "flight": 1504,
    "bicycle": 1522,        # bicycle
    "motorcycle": 1633,     # motorcycle
    # Misc
    "map-marker": 1899,     # blank-shape_pin (default)
    "map-marker-alt": 1899,
    "map-pin": 1899,
    "gas": 1581,            # fuel-gasoline
    "gas-pump": 1581,
    "info": 1608,           # info
    "info-circle": 1608,
    "parking": 1644,        # parking
    "music": 1637,          # music-note
    "theater-masks": 1709,  # theater
    "guitar": 1801,         # guitar
    "flag": 1574,           # flag
    "rocket": 1856,         # rocket
    "hospital": 1807,       # hospital-h
    "medical": 1624,        # medical
    "gym": 1589,            # gym
    "spa": 1697,            # spa
    "school": 1682,         # school-crossing
}


def hex_to_kml_color(hex_color: str, alpha: str = "ff") -> str:
    """Convert a hex color string (#RRGGBB or RRGGBB) to KML ABGR format.

    KML uses ABGR (alpha-blue-green-red), so #FF5733 → ff3357ff.
    """
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"{alpha}0000ff"  # fallback to red

    r = hex_color[0:2]
    g = hex_color[2:4]
    b = hex_color[4:6]
    return f"{alpha}{b}{g}{r}".lower()


def normalize_hex_color(hex_color: str) -> str:
    """Normalize a hex color to 6 uppercase hex digits (no #)."""
    hex_color = hex_color.lstrip("#").upper()
    if len(hex_color) != 6:
        return DEFAULT_HEX_COLOR
    return hex_color


def get_mapspro_id(icon_name: str) -> int:
    """Map a Wanderlog icon name to a Google My Maps mapspro icon ID."""
    if not icon_name:
        return DEFAULT_MAPSPRO_ID
    return MAPSPRO_ICON_MAP.get(icon_name.lower().strip(), DEFAULT_MAPSPRO_ID)


def get_mymaps_style_id(icon: str = "", color: str = "") -> str:
    """Generate the Google My Maps styleUrl ID for a Wanderlog icon/color.

    Returns a string like 'icon-1577-E74C3C' (without the # prefix).
    """
    mapspro_id = get_mapspro_id(icon)
    hex_color = normalize_hex_color(color)
    return f"icon-{mapspro_id}-{hex_color}"


def get_kml_style(icon: str = "", color: str = "") -> dict[str, str]:
    """Get full KML style properties for a Wanderlog icon/color combo.

    Returns dict with:
      - 'style_id': My Maps style ID (e.g. 'icon-1577-E74C3C')
      - 'icon_href': Default white pin URL (My Maps ignores this, but Earth uses it)
      - 'color': KML ABGR color for Google Earth compatibility
    """
    return {
        "style_id": get_mymaps_style_id(icon, color),
        "icon_href": DEFAULT_ICON_HREF,
        "color": hex_to_kml_color(color) if color else "ff0000ff",
    }
