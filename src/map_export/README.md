# Map Export

Export your [Wanderlog](https://wanderlog.com) trips to **Google My Maps** as styled KML files. Each Wanderlog list becomes a separate layer with matching pin icons and colors.

---

## Quick Start

```bash
# Export a public trip — outputs <trip-name>.kml in the current directory
wanderlogpro export-map https://wanderlog.com/view/abcd1234/my-trip
```

Open the `.kml` file in Google My Maps.
---

## CLI Reference

### `wanderlogpro export-map`

Export a Wanderlog trip to a styled KML file.

```
wanderlogpro export-map <TRIP_URL> [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `TRIP_URL` | **(Required)** Your Wanderlog trip URL, e.g. `https://wanderlog.com/view/abcd1234/my-trip` |
| `--output`, `-o` | Output file path. Defaults to `<trip-name>.kml` in the current directory |
| `--cookie`, `-c` | Session cookie for private trips (see [Private Trips](#exporting-private-trips) below) |

### Examples

```bash
# Export a public trip (auto-named output file)
wanderlogpro export-map https://wanderlog.com/view/abcd1234/my-trip

# Specify output file name
wanderlogpro export-map https://wanderlog.com/view/abcd1234/my-trip -o paris-2026.kml

# Export a private trip with session cookie
wanderlogpro export-map https://wanderlog.com/view/abcd1234/my-trip -c "session=eyJhbGci..."
```

### Sample Output

```
🗺️  Fetching trip from Wanderlog...
✅ Found trip: Paris 2026
   4 lists, 23 places
📝 Generating KML with styled layers...
🎉 Exported to paris-2026.kml

Import into Google My Maps at https://mymaps.google.com
   📂 Restaurants [restaurant] — 8 places
   📂 Sightseeing [camera] — 7 places
   📂 Hotels [hotel] — 3 places
   📂 Coffee Shops [cafe] — 5 places
```

> **Hotels layer:** Every hotel reservation in your trip (blocks with check-in/check-out dates) is automatically collected into a dedicated **Hotels** layer with a hotel-bed icon — regardless of which section you put them in. If you already have a list literally named "Hotels", the synthesized layer is renamed "Hotels (reservations)" to avoid confusion.

---

## Importing into Google My Maps

### Step-by-step

1. Go to [mymaps.google.com](https://mymaps.google.com)
2. Click **+ Create a new map**
3. In the left panel, click **Import**
4. Upload your `.kml` file
5. Each Wanderlog list appears as a separate **layer** with pins

### What to expect

| Feature | Supported |
|---|---|
| Layers (one per list) | ✅ Yes |
| Pin colors | ✅ Yes |
| Custom icons | ✅ Yes (mapspro format) |
| Place names | ✅ Yes |
| Descriptions (address + notes) | ✅ Yes |

> **Note:** WanderlogPro uses Google My Maps' internal "mapspro" icon system so that icons and colors are preserved on import. Each KML style uses the `#icon-{ID}-{COLOR}` format that My Maps recognizes natively.

---

## Exporting Private Trips

Private trips require your Wanderlog session cookie for authentication:

1. Open your trip in a browser and log in to Wanderlog
2. Open **Developer Tools** (`F12` or `Ctrl+Shift+I`)
3. Go to the **Network** tab
4. Reload the page
5. Click on any request to `wanderlog.com`
6. In the **Headers** tab, find the `Cookie` header
7. Copy the full cookie value

Then pass it to the CLI:

```bash
wanderlogpro export-map https://wanderlog.com/view/abcd1234/my-trip \
  --cookie "session=eyJhbGci...; other_cookie=value"
```

> **Tip:** Your session cookie is sensitive — don't commit it to version control or share it.

---

## Icon & Color Mapping

WanderlogPro maps Wanderlog list icons to Google My Maps' internal "mapspro" icon IDs. This ensures icons display correctly when importing KML into My Maps.

### Supported Icon Mappings

| Wanderlog Icon | Mapspro ID | My Maps Icon | Aliases |
|---|---|---|---|
| 🍽️ utensils | 1577 | food-fork-knife | `restaurant`, `food`, `dining` |
| 🍕 pizza-slice | 1651 | pizza-slice | `pizza` |
| 🍔 hamburger | 1530 | burger | `burger` |
| 🍦 ice-cream | 1607 | ice-cream | — |
| ☕ coffee | 1534 | cafe-cup | `cafe`, `mug-hot` |
| 🍸 wine-glass | 1517 | bar-cocktail | `cocktail`, `glass-martini` |
| 🍺 beer | 1879 | stein-beer | — |
| 🍻 bar | 1518 | bar-pub | `nightlife` |
| 🏨 hotel | 1602 | hotel-bed | `bed`, `lodging` |
| 🛍️ shopping-bag | 1684 | shopping-bag | `shopping` |
| 🏪 shop | 1686 | shop | `store` |
| 🎁 gift | 1584 | gift | — |
| ⛰️ mountain | 1634 | mountain | — |
| 🌳 tree | 1720 | tree | `nature`, `park` |
| 🥾 hiking | 1596 | hiking-solo | — |
| 🏖️ beach | 1521 | beach | `umbrella-beach` |
| 🏊 swimming | 1701 | swimming | `swimmer` |
| 📷 camera | 1535 | camera-photo | `photo` |
| 🏛️ museum | 1636 | museum | — |
| 🗿 monument | 1599 | historic-monument | `landmark` |
| ⭐ star | 1713 | ticket-star | `attraction` |
| ❤️ heart | 1592 | heart | — |
| 🚢 ship | 1569 | ferry | `ferry` |
| ⚓ anchor | 1623 | marine-anchor | — |
| 🚌 bus | 1532 | bus | `transport` |
| 🚇 subway | 1626 | metro | `metro` |
| 🚂 train | 1716 | train | — |
| ✈️ plane | 1504 | airport-plane | `airport`, `flight` |
| 🚗 car | 1538 | car | — |
| 🚕 taxi | 1704 | taxi | — |
| 📍 map-marker | 1899 | default pin | `map-pin` |
| ⛽ gas | 1581 | fuel-gasoline | `gas-pump` |
| 🅿️ parking | 1644 | parking | — |
| ℹ️ info | 1608 | info | `info-circle` |
| 🎵 music | 1637 | music-note | — |
| 🎭 theater | 1709 | theater | `theater-masks` |

Unrecognized icons fall back to a default red pin marker.

### Color Conversion

Wanderlog uses standard hex colors (e.g. `#FF5733`). KML requires ABGR format:

```
#FF5733 (hex RGB) → ff3357ff (KML ABGR)
 ↑                   ↑↑↑↑↑↑↑↑
 R=FF G=57 B=33       A=ff B=33 G=57 R=ff
```

This conversion is handled automatically — you don't need to do anything.

---

## How It Works

1. **URL Parsing** — Extracts the trip ID from a Wanderlog URL
2. **Page Scraping** — Fetches the Wanderlog trip page and extracts the embedded `tripPlan` JSON
3. **Model Parsing** — Converts the JSON into `Trip` → `PlaceList` → `Place` dataclasses, preserving icon and color metadata per list
4. **Style Mapping** — Each list's icon name is mapped to a Google My Maps mapspro icon ID; hex colors are converted to KML ABGR format
5. **KML Generation** — Creates a KML document where each `PlaceList` is a `<Folder>` (layer) with a shared `<Style>` block, and each `Place` is a `<Placemark>` with coordinates and description

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Could not parse trip ID from URL` | Make sure the URL is a Wanderlog trip URL like `https://wanderlog.com/view/<id>/...` |
| `Trip not found` | Double-check the trip ID. The trip may have been deleted or the URL may be wrong. |
| `Authentication required` | The trip is private. Use `--cookie` with your session cookie. |
| Icons don't show in Google My Maps | Make sure you're importing the KML into Google My Maps. WanderlogPro uses the mapspro `#icon-{ID}-{COLOR}` format that My Maps recognizes natively. |
| `No places found in this trip` | The trip may be empty, or the page structure may have changed. |
