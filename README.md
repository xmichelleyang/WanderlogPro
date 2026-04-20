# WanderlogPro

Export your [Wanderlog](https://wanderlog.com) trips to **Google My Maps**, **Google Calendar**, and an **offline trip guide** from the command line.

| Module | What it does |
|---|---|
| **Map Export** | Wanderlog lists → styled KML layers for Google My Maps |
| **Calendar Export** | Wanderlog itinerary → Google Calendar events with smart scheduling |
| **Offline Mode** | Wanderlog itinerary → beautiful mobile PWA you can use on a trip without internet |

---

## Prerequisites

- **Python 3.10+**
- A Wanderlog trip URL (public or private)
- **(Calendar export only)** Google OAuth2 credentials — see [Google Calendar Setup](#google-calendar-setup) below

## Installation

```bash
git clone <repo-url>
cd WanderlogPro
pip install -e ".[dev]"
```

---

## Google Calendar Setup

> **Only needed for the `calendar` and `all` commands.** Map export (`export`) works without any Google setup.

To export itinerary events to Google Calendar, you need OAuth2 credentials from your own Google Cloud project. This is a one-time setup.

### Step 1 — Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
3. Name it anything (e.g., "WanderlogPro") → click **Create**

### Step 2 — Enable the Google Calendar API

1. Go to [**APIs & Services → Library**](https://console.cloud.google.com/apis/library)
2. Search for **Google Calendar API**
3. Click **Enable**

### Step 3 — Configure OAuth Consent Screen

1. Go to [**APIs & Services → OAuth consent screen**](https://console.cloud.google.com/apis/credentials/consent)
2. Choose **External** → click **Create**
3. Fill in the required fields:
   - **App name**: anything (e.g., "WanderlogPro")
   - **User support email**: your email
   - **Developer contact email**: your email
4. Click **Save and Continue** through the Scopes and Test Users pages
5. On the **Test Users** page, click **Add Users** and enter your Google email
6. Click **Save and Continue** → **Back to Dashboard**

### Step 4 — Create OAuth2 Credentials

1. Go to [**APIs & Services → Credentials**](https://console.cloud.google.com/apis/credentials)
2. Click **+ Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: anything (e.g., "WanderlogPro CLI")
5. Click **Create**
6. Click **Download JSON** — this is your `credentials.json`

### Step 5 — Install the Credentials

Place the downloaded `credentials.json` in **one** of these locations:

```bash
# Recommended — keeps credentials out of your project directory
# Windows
%USERPROFILE%\.wanderlogpro\credentials.json

# macOS / Linux
~/.wanderlogpro/credentials.json
```

Or in your current working directory:
```bash
./credentials.json
```

**Alternative** — use environment variables instead of a file:
```bash
# Find these values in the downloaded credentials.json
export WANDERLOGPRO_CLIENT_ID='your-id.apps.googleusercontent.com'
export WANDERLOGPRO_CLIENT_SECRET='GOCSPX-your-secret'
```

### Step 6 — First Run

```bash
python -m wanderlogpro.cli calendar https://wanderlog.com/view/abcd1234/my-trip
```

A browser window opens for Google sign-in. After approval, a token is cached at `~/.wanderlogpro/token.json` — subsequent runs won't need browser auth.

> **⚠️ Never commit `credentials.json` or `token.json` to git.** Both are included in `.gitignore`.

---

## Usage

> **Note:** If `wanderlogpro` is not on your PATH, use `python -m wanderlogpro.cli` instead.

### Map export — KML for Google My Maps

```bash
python -m wanderlogpro.cli export https://wanderlog.com/view/abcd1234/my-trip
```

### Calendar export — Google Calendar events

```bash
python -m wanderlogpro.cli calendar https://wanderlog.com/view/abcd1234/my-trip

# Preview without creating events
python -m wanderlogpro.cli calendar https://wanderlog.com/view/abcd1234/my-trip --dry-run
```

### Offline mode — mobile PWA

```bash
python -m wanderlogpro.cli offline-mode https://wanderlog.com/view/abcd1234/my-trip
```

Generates a single self-contained HTML file with:
- ✈️ **Flights** and 🏨 **Hotels** sections (auto-detected)
- 📅 **Day-by-day itinerary** with swipeable tabs
- Tap any address → opens Google Maps for navigation
- **Add to Home Screen** on Android for a fullscreen app experience
- **Works offline** after first open (service worker caches everything)
- Beautiful mesh gradient UI with dark mode

**How to get it on your phone:**
- Email it to yourself → open in Chrome → Add to Home Screen
- Upload to Google Drive / OneDrive → open on phone
- Nearby Share (Android)

### Both map + calendar at once

```bash
python -m wanderlogpro.cli all https://wanderlog.com/view/abcd1234/my-trip
```

---

## CLI Reference

### `export`

Export a Wanderlog trip to a styled KML file for Google My Maps.

```
python -m wanderlogpro.cli export <TRIP_URL> [--output/-o FILE] [--cookie/-c COOKIE]
```

### `calendar`

Export a Wanderlog trip's day-by-day itinerary to Google Calendar.

```
python -m wanderlogpro.cli calendar <TRIP_URL> [--cookie/-c COOKIE] [--dry-run] [--start-hour/-s HOUR]
```

### `offline-mode`

Generate an offline trip viewer as a self-contained HTML/PWA file.

```
python -m wanderlogpro.cli offline-mode <TRIP_URL> [--output/-o FILE] [--cookie/-c COOKIE]
```

### `all`

Run both map export and calendar export in one shot.

```
python -m wanderlogpro.cli all <TRIP_URL> [--output/-o FILE] [--cookie/-c COOKIE] [--dry-run] [--start-hour/-s HOUR]
```

---

## Common Options

| Option | Applies to | Description |
|---|---|---|
| `--cookie`, `-c` | all commands | Session cookie for private trips |
| `--output`, `-o` | `export`, `all`, `offline-mode` | Output file path (KML or HTML) |
| `--dry-run` | `calendar`, `all` | Preview calendar events in a week-view HTML page without creating them |
| `--start-hour`, `-s` | `calendar`, `all` | Hour (0–23) at which auto-scheduled events start each day (default: 10) |

---

## Project Structure

```
WanderlogPro/
├── pyproject.toml
├── README.md
├── src/
│   ├── cli.py                         # CLI entrypoint (export, calendar, all, offline-mode)
│   ├── utils.py                       # Shared utilities (parse_trip_id)
│   ├── map_export/                    # Wanderlog → KML for Google My Maps
│   │   ├── models.py, scraper.py
│   │   ├── kml_export.py, icon_map.py
│   │   └── README.md
│   ├── calendar_export/               # Wanderlog → Google Calendar events
│   │   ├── models.py, scraper.py
│   │   ├── gcal_export.py, preview.py
│   │   └── README.md
│   └── offline_mode/                   # Offline trip viewer (PWA)
│       ├── models.py, builder.py
│       └── generator.py
└── tests/
    ├── map_export/
    ├── calendar_export/
    └── offline_mode/
```

---

## Development

```bash
# Run all tests
pytest tests/ -v

# Run only map export tests
pytest tests/map_export/ -v

# Run only calendar export tests
pytest tests/calendar_export/ -v
```

---

## Limitations

- **No official Wanderlog API** — Uses Wanderlog's internal page data. May break if Wanderlog changes their page structure.
- **Session cookies expire** — Get a fresh cookie from your browser if auth fails.
- **Calendar timezone** — Timezone is auto-detected from the trip's destination coordinates (e.g., `Asia/Ho_Chi_Minh` for Vietnam). Dry-run previews show raw local times without timezone conversion.
- **Itinerary only for calendar** — Only items on the day-by-day itinerary become events, not items saved to lists.
