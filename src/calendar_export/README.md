# Calendar Export

Export your [Wanderlog](https://wanderlog.com) trip itinerary to **Google Calendar** as individual events via the Calendar API. Each itinerary item becomes a Google Calendar event with smart scheduling, travel time gaps, and `[!]` markers for timed entries.

---

## Quick Start

```bash
python -m wanderlogpro.cli export-calendar https://wanderlog.com/view/abcd1234/my-trip
# → Browser opens for Google sign-in (first time only)
# → Events are created in a new sub-calendar
```

This creates a new sub-calendar (e.g., "Paris 2026 — WanderlogPro") with each itinerary item as an event.

---

## CLI Reference

### `export-calendar`

Export a Wanderlog trip's day-by-day itinerary to Google Calendar.

```
python -m wanderlogpro.cli export-calendar <TRIP_URL> [OPTIONS]
```

| Argument / Option | Description |
|---|---|
| `TRIP_URL` | **(Required)** Your Wanderlog trip URL |
| `--cookie`, `-c` | Session cookie for private trips |
| `--dry-run` | Preview events in a week-view HTML page in your browser — no Google sign-in needed |
| `--start-hour`, `-s` | Hour (0–23) at which auto-scheduled events start each day (default: 10) |
| `--invite`, `-i` | Comma-separated emails to share the trip calendar with (writer access) |
| `--invite-file`, `-f` | Path to a `.txt` file with one email per line (`#` comments and blank lines ignored) |

### Examples

```bash
# Export itinerary to Google Calendar
python -m wanderlogpro.cli export-calendar https://wanderlog.com/view/abcd1234/my-trip

# Preview what events would be created (opens an HTML week-view in your browser)
python -m wanderlogpro.cli export-calendar https://wanderlog.com/view/abcd1234/my-trip --dry-run

# Start each day at 9 AM instead of the default 10 AM
python -m wanderlogpro.cli export-calendar https://wanderlog.com/view/abcd1234/my-trip --start-hour 9

# Private trip with session cookie
python -m wanderlogpro.cli export-calendar https://wanderlog.com/view/abcd1234/my-trip -c "session=eyJhbGci..."

# Invite travel companions — they get an email from Google to add the calendar
python -m wanderlogpro.cli export-calendar <TRIP_URL> --invite "alice@example.com,bob@example.com"

# Invitees from a file (one email per line, # for comments)
python -m wanderlogpro.cli export-calendar <TRIP_URL> --invite-file invitees.txt
```

Invitees receive a standard Google Calendar sharing email and gain **writer** access
(they can see and edit events). `--invite` and `--invite-file` can be combined; emails
are deduplicated automatically.

### Sample Output

```
🗺️  Fetching itinerary from Wanderlog...
✅ Found trip: Paris 2026
   3 days, 12 itinerary items
📅 Signing in to Google Calendar...
🎉 Exported 12 events to Google Calendar!

   📅 Calendar: Paris 2026 — WanderlogPro
   🔗 View at https://calendar.google.com
   📆 2026-04-20 — 5 items (2 with specific times)
   📆 2026-04-21 — 4 items (1 with specific times)
   📆 2026-04-22 — 3 items (0 with specific times)
```

---

## Dry-Run Preview

Use `--dry-run` to preview your itinerary as an interactive HTML week-view calendar **without signing in to Google**:

```bash
python -m wanderlogpro.cli export-calendar https://wanderlog.com/view/abcd1234/my-trip --dry-run
```

This opens a browser tab with a Google Calendar-style week view showing:

- **Event blocks** positioned on a time grid — sized by duration
- **`[!]` badge** (red accent) on events with explicit times from Wanderlog
- **Travel gaps** as dashed connectors between events with the travel time
- **Hover tooltips** with full details: name, time, duration, location
- **Week navigation tabs** if the trip spans multiple weeks
- **Legend** distinguishing explicit-time events, auto-scheduled events, and travel gaps

No events are created — once you're happy with the preview, run again without `--dry-run` to export to Google Calendar.

---

## How Scheduling Works

| Rule | Details |
|---|---|
| **Day start** | `--start-hour` value (default 10:00 AM) if the first item has no specific time |
| **Event duration** | Uses Wanderlog's "average time spent" per item; falls back to 1 hour |
| **Travel gaps** | Travel time between items (from Wanderlog) is inserted as a gap between events |
| **Explicit times** | If an item has a specific start time (e.g., a ticket entry time), that time is used and the event title is prefixed with `[!]` |
| **Location** | Each event's location is set to the Wanderlog address for Google Maps integration |

### The `[!]` Prefix

Events with a specific entry time are titled `[!]Event Name` so you can quickly spot time-sensitive items on your calendar. For example:
- `[!]Eiffel Tower` — you have a 2:00 PM ticket
- `Café de Flore` — no fixed time, scheduled sequentially

---

## Google Calendar Setup

To export to Google Calendar, you need OAuth2 credentials from a Google Cloud project.

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **Select a project** → **New Project**
3. Name it something like "WanderlogPro" and click **Create**

### 2. Enable the Google Calendar API

1. In the Cloud Console, go to **APIs & Services** → **Library**
2. Search for **Google Calendar API**
3. Click **Enable**

### 3. Create OAuth2 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **OAuth client ID**
3. If prompted, configure the **OAuth consent screen** first:
   - Choose **External** user type
   - Fill in the app name (e.g., "WanderlogPro")
   - Add your email as a test user
4. Back in Credentials, select **Desktop app** as the application type
5. Click **Create** and **Download JSON**
6. Save the file as `credentials.json`

### 4. Install Credentials

Place `credentials.json` in one of these locations:

```bash
# Recommended — keeps it out of your project directory
~/.wanderlogpro/credentials.json

# Or in the current working directory
./credentials.json
```

**Alternative:** Set environment variables instead of using a file:

```bash
export WANDERLOGPRO_CLIENT_ID='your-client-id.apps.googleusercontent.com'
export WANDERLOGPRO_CLIENT_SECRET='GOCSPX-your-secret'
```

### 5. First Run

On first run, a browser window opens for Google sign-in:

```bash
python -m wanderlogpro.cli export-calendar https://wanderlog.com/view/abcd1234/my-trip
# → Browser opens for Google OAuth consent
# → After approval, a token is cached at ~/.wanderlogpro/token.json
```

> **Note:** Subsequent runs won't require browser auth unless the token expires.

### Re-authentication

To re-authenticate (e.g., if the token expires or you switch accounts), delete the cached token:

```bash
# Windows
del %USERPROFILE%\.wanderlogpro\token.json

# macOS / Linux
rm ~/.wanderlogpro/token.json
```

> **Security:** Never commit `credentials.json` or `token.json` to git. Both are included in `.gitignore`.

---

## How It Works

1. **URL Parsing** — Extracts the trip ID from a Wanderlog URL
2. **Page Scraping** — Fetches the Wanderlog trip page and extracts the embedded JSON blob
3. **Itinerary Parsing** — Filters `dayPlan` sections (not `placeList` sections), extracts place metadata for durations and travel times between places
4. **Smart Scheduling** — For each day: starts at `--start-hour` (default 10 AM, unless explicit time), applies Wanderlog durations, inserts travel time gaps between events
5. **Google Calendar API** — Creates a sub-calendar for the trip and inserts each item as an event with title, location, description, and proper start/end times

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `No Google OAuth2 credentials found` | Place `credentials.json` in `~/.wanderlogpro/` or set `WANDERLOGPRO_CLIENT_ID` + `WANDERLOGPRO_CLIENT_SECRET` env vars. See [Google Calendar Setup](#google-calendar-setup). |
| `No itinerary items found` | Items must be added to the day-by-day itinerary in Wanderlog, not just saved to lists. |
| `access_denied` / app not verified | Add your Google account as a test user in [Cloud Console → OAuth consent screen → Test users](https://console.cloud.google.com/apis/credentials/consent). |
| OAuth browser window doesn't open | Make sure you're running the CLI on a machine with a browser. If running headless, set up OAuth on a machine with a browser first and copy `~/.wanderlogpro/token.json`. |
| `Token has been expired or revoked` | Delete `~/.wanderlogpro/token.json` and run again to re-authenticate. |
| Calendar events appear at wrong times | Timezone is auto-detected from destination coordinates. Check the CLI output for the detected timezone (e.g., `🌍 Detected timezone: Asia/Ho_Chi_Minh`). |
| `Authentication required` | The trip is private. Use `--cookie` with your session cookie. |
