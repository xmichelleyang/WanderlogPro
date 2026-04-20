"""Generate a self-contained HTML week-view calendar preview."""

from __future__ import annotations

import html
import json
import tempfile
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def _parse_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def _timezone_note(dest_tz: str, reference_date: str) -> str:
    """Build an HTML timezone note if destination tz differs from local.

    Args:
        dest_tz: IANA destination timezone (e.g. "Asia/Ho_Chi_Minh").
        reference_date: An ISO date from the trip to compute offset at.

    Returns:
        HTML string for the banner, or empty string if no difference.
    """
    if not dest_tz:
        return ""

    try:
        dest_zone = ZoneInfo(dest_tz)
    except (KeyError, Exception):
        return ""

    local_zone = datetime.now().astimezone().tzinfo
    local_name = str(local_zone)
    # Try to get a clean IANA name via tzname or key
    try:
        local_name = datetime.now().astimezone().tzinfo.key  # type: ignore[attr-defined]
    except AttributeError:
        local_name = str(datetime.now().astimezone().tzname())

    ref_dt = datetime.fromisoformat(reference_date).replace(hour=12)
    dest_offset = ref_dt.replace(tzinfo=dest_zone).utcoffset()
    local_offset = ref_dt.replace(tzinfo=ZoneInfo(local_name) if "/" in local_name else local_zone).astimezone().utcoffset()

    if dest_offset is None or local_offset is None:
        return ""

    # Handle case where local_name isn't an IANA key — recompute properly
    local_dt = datetime.now().astimezone()
    local_offset = local_dt.utcoffset()
    if local_offset is None:
        return ""

    diff_hours = (dest_offset.total_seconds() - local_offset.total_seconds()) / 3600

    if abs(diff_hours) < 0.01:
        return ""

    if diff_hours > 0:
        direction = "ahead of"
    else:
        direction = "behind"
        diff_hours = abs(diff_hours)

    # Format nicely: "14 hours" or "5.5 hours"
    if diff_hours == int(diff_hours):
        hours_str = f"{int(diff_hours)} hour{'s' if int(diff_hours) != 1 else ''}"
    else:
        hours_str = f"{diff_hours:.1f} hours"

    return (
        f'<span class="tz-badge">'
        f'🌍 {html.escape(dest_tz)}'
        f'</span>'
        f'<span class="tz-offset">'
        f'{hours_str} {direction} {html.escape(local_name)}'
        f'</span>'
    )


def _group_days_into_weeks(
    day_events: list[tuple[str, list[dict]]],
) -> list[list[tuple[str, list[dict]]]]:
    """Group (date, events) pairs into Sun–Sat weeks."""
    if not day_events:
        return []

    all_dates = [datetime.fromisoformat(d).date() for d, _ in day_events]
    min_date = min(all_dates)
    max_date = max(all_dates)

    # Align to Sunday (weekday 6). Sun=0 offset, Mon=1, ... Sat=6
    days_since_sun = (min_date.weekday() + 1) % 7
    week_start = min_date - timedelta(days=days_since_sun)
    weeks: list[list[tuple[str, list[dict]]]] = []
    lookup = {d: evts for d, evts in day_events}

    while week_start <= max_date:
        week: list[tuple[str, list[dict]]] = []
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_str = day.isoformat()
            week.append((day_str, lookup.get(day_str, [])))
        weeks.append(week)
        week_start += timedelta(days=7)

    return weeks


def _time_range(day_events: list[tuple[str, list[dict]]]) -> tuple[int, int]:
    """Find the earliest and latest hours across all events (with padding)."""
    earliest = 23
    latest = 0
    for _, events in day_events:
        for evt in events:
            start_h = _parse_dt(evt["start"]["dateTime"]).hour
            end_dt = _parse_dt(evt["end"]["dateTime"])
            end_h = end_dt.hour + (1 if end_dt.minute > 0 else 0)
            earliest = min(earliest, start_h)
            latest = max(latest, end_h)
    return max(0, earliest - 1), min(24, latest + 1)


def _travel_emoji(mode: str) -> str:
    """Return an appropriate emoji for the travel mode."""
    mode = (mode or "driving").lower()
    if mode == "walking":
        return "🚶"
    if mode in ("bicycling", "cycling"):
        return "🚲"
    if mode == "transit":
        return "🚌"
    return "🚗"


def _event_color(summary: str) -> str:
    """Shared warm peach/amber pastel for all dry-run events."""
    return "hsl(30, 55%, 82%)"


def _event_border_color(summary: str) -> str:
    """Shared darker companion to `_event_color` for all dry-run events."""
    return "hsl(30, 50%, 50%)"


def _fmt_hour(h: int) -> str:
    """Format an hour (0-23) as 12-hour AM/PM string."""
    if h == 0:
        return "12 AM"
    elif h < 12:
        return f"{h} AM"
    elif h == 12:
        return "12 PM"
    else:
        return f"{h - 12} PM"


def _fmt_time(dt: datetime) -> str:
    """Format a datetime as '1:30 PM' style."""
    return dt.strftime("%I:%M %p").lstrip("0")


def generate_preview_html(
    trip_name: str,
    day_events: list[tuple[str, list[dict]]],
    timezone: str = "",
) -> str:
    """Generate a self-contained HTML string with a week-view calendar.

    Args:
        trip_name: Name of the trip.
        day_events: List of (date_string, events) from preview_trip_events().
        timezone: IANA destination timezone for the info banner.

    Returns:
        Complete HTML document as a string.
    """
    weeks = _group_days_into_weeks(day_events)
    if not weeks:
        return _empty_html(trip_name)

    hour_start, hour_end = _time_range(day_events)
    total_hours = hour_end - hour_start
    if total_hours <= 0:
        hour_start, hour_end, total_hours = 8, 22, 14

    total_events = sum(len(evts) for _, evts in day_events)
    total_days = sum(1 for _, evts in day_events if evts)

    # Compute average duration for stats bar
    all_durations = []
    for _, evts in day_events:
        for evt in evts:
            s = _parse_dt(evt["start"]["dateTime"])
            e = _parse_dt(evt["end"]["dateTime"])
            all_durations.append(int((e - s).total_seconds() / 60))
    avg_duration = int(sum(all_durations) / len(all_durations)) if all_durations else 0

    day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    # Build week sections
    week_sections = []
    for week_idx, week in enumerate(weeks):
        week_sections.append(
            _render_week(week, week_idx, hour_start, hour_end, total_hours, day_names)
        )

    weeks_html = "\n".join(week_sections)

    # Navigation tabs (only if multiple weeks)
    nav_html = ""
    if len(weeks) > 1:
        tabs = []
        for i, week in enumerate(weeks):
            start = week[0][0]
            end = week[6][0]
            start_fmt = datetime.fromisoformat(start).strftime("%b %d")
            end_fmt = datetime.fromisoformat(end).strftime("%b %d")
            active = "active" if i == 0 else ""
            tabs.append(
                f'<button class="week-tab {active}" onclick="showWeek({i})">'
                f"{start_fmt} – {end_fmt}</button>"
            )
        nav_html = f'<div class="week-nav">{"".join(tabs)}</div>'

    # Timezone difference note
    tz_html = ""
    if timezone and day_events:
        ref_date = day_events[0][0]  # first trip date
        tz_html = _timezone_note(timezone, ref_date)

    # First and last trip dates for current-time indicator
    first_date = day_events[0][0]
    last_date = day_events[-1][0]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(trip_name)} — WanderlogPro Preview</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;0,9..144,700;1,9..144,400&family=Geist:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
{_css(total_hours)}
</style>
</head>
<body>
<div class="sticky-header" id="stickyHeader">
  <span class="sticky-title">{html.escape(trip_name)}</span>
</div>
<button class="dark-toggle" onclick="toggleDark()" title="Toggle dark mode" aria-label="Toggle dark mode">🌙</button>
<div class="hero-spacer"></div>
<div class="container">
  <div class="hero-card">
    <div class="hero-icon">✈️</div>
    <div class="hero-text">
      <h1>{html.escape(trip_name)}</h1>
      <p class="subtitle">Dry-run preview &middot; {total_events} events across {total_days} days</p>
      {f'<p class="tz-line">{tz_html}</p>' if tz_html else ''}
      <p class="hint">Run without <code>--dry-run</code> to create these events in Google Calendar.</p>
    </div>
  </div>
  {nav_html}
  {weeks_html}
  <div class="legend">
    <span class="legend-item"><span class="legend-dot explicit"></span> Explicit time</span>
    <span class="legend-item"><span class="legend-dot scheduled"></span> Auto-scheduled</span>
    <span class="legend-item"><span class="legend-dot travel"></span> Travel gap</span>
  </div>
</div>
<footer class="footer">✨ Generated by <span class="footer-brand">WanderlogPro</span></footer>
<div id="tooltip" class="tooltip"></div>
<script>
var TRIP_START="{first_date}",TRIP_END="{last_date}",HOUR_START={hour_start},HOUR_END={hour_end};
{_js()}
</script>
</body>
</html>"""


def _render_week(
    week: list[tuple[str, list[dict]]],
    week_idx: int,
    hour_start: int,
    hour_end: int,
    total_hours: int,
    day_names: list[str],
) -> str:
    display = "block" if week_idx == 0 else "none"

    # Header row
    headers = ['<div class="time-gutter-header"></div>']
    for i, (date_str, _) in enumerate(week):
        dt = datetime.fromisoformat(date_str)
        day_label = day_names[i]
        date_label = dt.strftime("%b %d")
        has_events = "has-events" if week[i][1] else ""
        headers.append(
            f'<div class="day-header {has_events}">'
            f'<span class="day-name">{day_label}</span>'
            f'<span class="day-date">{date_label}</span></div>'
        )
    header_html = "\n".join(headers)

    # Time grid rows
    time_labels = ['<div class="time-gutter">']
    for h in range(hour_start, hour_end):
        top_pct = ((h - hour_start) / total_hours) * 100
        alt_class = " alt" if h % 2 == 0 else ""
        time_labels.append(
            f'<div class="time-label{alt_class}" style="top:{top_pct}%">{_fmt_hour(h)}</div>'
        )
    time_labels.append("</div>")
    time_gutter = "\n".join(time_labels)

    # Global event counter for staggered animations
    global_evt_idx = 0

    # Day columns with events
    day_columns = []
    for col_idx, (date_str, events) in enumerate(week):
        col_parts = [f'<div class="day-column" data-date="{date_str}">']
        # Hour grid lines (alternating shading)
        for h in range(hour_start, hour_end):
            top_pct = ((h - hour_start) / total_hours) * 100
            row_h_pct = (1 / total_hours) * 100
            alt = " hour-alt" if h % 2 == 0 else ""
            col_parts.append(
                f'<div class="hour-line{alt}" '
                f'style="top:{top_pct}%;height:{row_h_pct}%"></div>'
            )

        # Render events
        for evt_idx, evt in enumerate(events):
            start_dt = _parse_dt(evt["start"]["dateTime"])
            end_dt = _parse_dt(evt["end"]["dateTime"])
            summary = evt.get("summary", "")
            location = evt.get("location", "")
            description = evt.get("description", "")

            start_minutes = start_dt.hour * 60 + start_dt.minute
            end_minutes = end_dt.hour * 60 + end_dt.minute
            duration_min = end_minutes - start_minutes
            if duration_min <= 0:
                duration_min = 60

            top_pct = ((start_minutes / 60 - hour_start) / total_hours) * 100
            height_pct = (duration_min / 60 / total_hours) * 100
            height_pct = max(height_pct, 1.5)  # min visible height

            is_explicit = summary.startswith("[!]")
            display_name = summary[3:] if is_explicit else summary
            explicit_class = "explicit-event" if is_explicit else ""
            color = _event_color(display_name)
            border_color = _event_border_color(display_name)

            time_str = f"{_fmt_time(start_dt)}–{_fmt_time(end_dt)}"

            # Tooltip data — strip the address line from description
            # since it's already shown via the location field.
            tooltip_desc = description
            if location and tooltip_desc:
                # description often starts with "📍 <address>\n..."
                lines = tooltip_desc.split("\n")
                filtered = [l for l in lines if location not in l]
                tooltip_desc = "\n".join(filtered).strip()

            tooltip_data = {
                "name": display_name,
                "time": time_str,
                "duration": f"{duration_min} min",
                "location": location,
                "explicit": is_explicit,
                "description": tooltip_desc,
            }
            data_attr = html.escape(json.dumps(tooltip_data), quote=True)

            # Render travel connector to next event
            travel_html = ""
            if evt_idx < len(events) - 1:
                next_evt = events[evt_idx + 1]
                next_start = _parse_dt(next_evt["start"]["dateTime"])
                gap_minutes = (
                    next_start.hour * 60 + next_start.minute
                ) - end_minutes
                if gap_minutes > 0:
                    travel_top = top_pct + height_pct
                    travel_height = (gap_minutes / 60 / total_hours) * 100
                    emoji = _travel_emoji(evt.get("_travel_mode", ""))
                    travel_html = (
                        f'<div class="travel-gap" '
                        f'style="top:{travel_top}%;height:{travel_height}%">'
                        f'<span class="travel-dots"></span>'
                        f'<span class="travel-label">{emoji} {gap_minutes} min</span>'
                        f"</div>"
                    )

            badge = '<span class="explicit-badge"><span class="pulse-dot"></span></span>' if is_explicit else ""
            compact = duration_min < 40
            name_class = "event-name compact" if compact else "event-name"
            anim_delay = f"animation-delay:{global_evt_idx * 0.04}s;"
            global_evt_idx += 1

            col_parts.append(
                f'<div class="event {explicit_class}" '
                f'style="top:{top_pct}%;height:{height_pct}%;'
                f"background:{color};border-color:{border_color};{anim_delay}\" "
                f'data-tooltip="{data_attr}" '
                f"onmouseenter=\"showTooltip(event, this)\" "
                f"onmouseleave=\"hideTooltip()\">"
                f"{badge}"
                f'<div class="{name_class}">'
                f"{html.escape(display_name)}</div>"
                f'<div class="event-time">{time_str}</div>'
                f"</div>"
                f"{travel_html}"
            )

        col_parts.append("</div>")
        day_columns.append("\n".join(col_parts))

    columns_html = "\n".join(day_columns)

    return f"""<div class="week-container" id="week-{week_idx}" style="display:{display}">
  <div class="week-grid">
    <div class="header-row">{header_html}</div>
    <div class="body-row">
      {time_gutter}
      {columns_html}
    </div>
  </div>
</div>"""


def _css(total_hours: int) -> str:
    row_height = max(50, 720 // total_hours) if total_hours > 0 else 50
    grid_height = row_height * total_hours

    return f"""
/* ── Reset & Custom Properties ─────────────────────────────── */
*, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
:root {{
  --primary: #4338CA;
  --primary-light: #6366F1;
  --accent-warm: #F59E0B;
  --accent-hot: #F97316;
  --surface: #FFFBF5;
  --surface-card: #FFFFFF;
  --surface-card-glass: rgba(255,251,245,0.72);
  --text: #1C1917;
  --text-muted: #78716C;
  --border: rgba(120,113,108,0.18);
  --shadow-sm: 0 1px 3px rgba(28,25,23,0.06);
  --shadow-md: 0 4px 16px rgba(28,25,23,0.08);
  --shadow-lg: 0 12px 40px rgba(28,25,23,0.12);
  --radius: 0.75rem;
  --radius-lg: 1.25rem;
  --spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease: cubic-bezier(0.4, 0, 0.2, 1);
  --transition: 0.3s var(--ease);
  --font-display: 'Fraunces', Georgia, serif;
  --font-body: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color-scheme: light;
}}

/* ── Dark Mode ─────────────────────────────────────────────── */
body.dark {{
  --surface: #0F172A;
  --surface-card: #1E293B;
  --surface-card-glass: rgba(15,23,42,0.78);
  --text: #FEF3C7;
  --text-muted: #A8A29E;
  --border: rgba(254,243,199,0.1);
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.35);
  --shadow-lg: 0 12px 40px rgba(0,0,0,0.45);
  color-scheme: dark;
}}

body {{
  font-family: var(--font-body);
  background: var(--surface);
  color: var(--text);
  transition: background var(--transition), color var(--transition);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}}

/* ── Micro-label style ─────────────────────────────────────── */
.micro-label {{
  text-transform: uppercase;
  letter-spacing: 0.22em;
  font-size: 0.7rem;
  color: var(--text-muted);
  font-weight: 500;
}}

/* ── Sticky Glass Header ───────────────────────────────────── */
.sticky-header {{
  position: fixed;
  top: 0; left: 0; right: 0;
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 24px;
  background: rgba(255,251,245,0.7);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid transparent;
  transition: border-color 0.3s var(--ease), box-shadow 0.3s var(--ease);
  opacity: 0;
  transform: translateY(-100%);
  transition: opacity 0.3s var(--ease), transform 0.3s var(--ease), border-color 0.3s var(--ease);
}}
body.dark .sticky-header {{
  background: rgba(15,23,42,0.7);
}}
.sticky-header.visible {{
  opacity: 1;
  transform: translateY(0);
}}
.sticky-header.scrolled {{
  border-bottom-color: var(--border);
  box-shadow: var(--shadow-sm);
}}
.sticky-title {{
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 1rem;
  color: var(--text);
}}

/* ── Dark Toggle ───────────────────────────────────────────── */
.dark-toggle {{
  position: fixed;
  top: 16px;
  right: 20px;
  z-index: 300;
  width: 40px; height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--surface-card);
  cursor: pointer;
  font-size: 1.1rem;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.3s var(--spring), box-shadow var(--transition);
  box-shadow: var(--shadow-sm);
}}
.dark-toggle:hover {{ transform: scale(1.1); box-shadow: var(--shadow-md); }}

/* ── Hero Header — Cinematic ───────────────────────────────── */
/* ── Hero Spacer ───────────────────────────────────────────── */
.hero-spacer {{ height: 32px; }}

/* ── Hero Card ─────────────────────────────────────────────── */
.hero-card {{
  display: flex;
  align-items: center;
  gap: 24px;
  background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 25%, #FBBF24 50%, #F59E0B 75%, #F97316 100%);
  border-radius: var(--radius-lg);
  padding: 36px 40px;
  margin-bottom: 24px;
  box-shadow: 0 8px 32px rgba(245,158,11,0.2), 0 2px 8px rgba(249,115,22,0.1);
  animation: heroSlideDown 0.8s var(--ease) both;
  overflow: hidden;
  position: relative;
}}
body.dark .hero-card {{
  background: linear-gradient(135deg, #78350F 0%, #92400E 30%, #B45309 60%, #D97706 100%);
  box-shadow: 0 8px 32px rgba(217,119,6,0.25), 0 2px 8px rgba(0,0,0,0.3);
}}
@keyframes heroSlideDown {{
  from {{ opacity: 0; transform: translateY(-20px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
.hero-icon {{
  font-size: 3rem;
  flex-shrink: 0;
  filter: drop-shadow(0 2px 8px rgba(0,0,0,0.15));
  animation: planeBob 3s ease-in-out infinite;
}}
@keyframes planeBob {{
  0%, 100% {{ transform: translateY(0) rotate(-2deg); }}
  50% {{ transform: translateY(-6px) rotate(2deg); }}
}}
@media (prefers-reduced-motion: reduce) {{
  .hero-icon {{ animation: none; }}
}}
.hero-text {{ flex: 1; min-width: 0; }}
.hero-card h1 {{
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 700;
  color: #1C1917;
  letter-spacing: -0.02em;
  margin-bottom: 6px;
  line-height: 1.2;
}}
body.dark .hero-card h1 {{ color: #FEF3C7; }}
.hero-card .subtitle {{
  color: #44403C;
  font-size: 0.95rem;
  font-weight: 400;
  margin-bottom: 8px;
}}
body.dark .hero-card .subtitle {{ color: #D6D3D1; }}
.hero-card .hint {{
  color: #57534E;
  font-size: 0.82rem;
  opacity: 0.8;
  margin-top: 8px;
}}
body.dark .hero-card .hint {{ color: #A8A29E; }}
.hero-card .hint code {{
  background: rgba(28,25,23,0.12);
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 0.82rem;
  color: #1C1917;
}}
body.dark .hero-card .hint code {{
  background: rgba(254,243,199,0.15);
  color: #FDE68A;
}}

/* ── Container ─────────────────────────────────────────────── */
.container {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px 40px;
  animation: slideUp 0.7s 0.2s var(--ease) both;
}}
@keyframes slideUp {{
  from {{ opacity: 0; transform: translateY(40px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

/* ── Stats Bar — Solid warm cards ──────────────────────────── */
.stats-bar {{
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
  margin: -24px auto 24px;
  position: relative;
  z-index: 10;
  animation: fadeIn 0.6s 0.5s both;
}}
@keyframes fadeIn {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}
.stat-card {{
  background: #FEF3C7;
  border: 1px solid rgba(245,158,11,0.25);
  border-radius: var(--radius);
  padding: 12px 20px;
  display: flex; align-items: center; gap: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  box-shadow: var(--shadow-md);
  transition: transform var(--transition), box-shadow var(--transition);
}}
body.dark .stat-card {{
  background: #292524;
  border-color: rgba(245,158,11,0.15);
}}
.stat-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-lg); }}
.stat-value {{ font-weight: 700; color: var(--primary); font-family: var(--font-display); }}
body.dark .stat-value {{ color: var(--primary-light); }}
.stat-label {{ color: var(--text-muted); font-weight: 400; }}

/* ── Timezone Note (inline in hero) ────────────────────────── */
.tz-line {{
  font-size: 0.82rem;
  color: var(--text-muted);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  flex-wrap: wrap;
}}
.tz-badge {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 4px 14px;
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--text);
  letter-spacing: 0.01em;
}}
.tz-offset {{
  font-size: 0.8rem;
  color: var(--text-muted);
  font-weight: 400;
  opacity: 0.85;
}}

/* ── Week Navigation — Pill ────────────────────────────────── */
.week-nav {{
  display: flex;
  gap: 4px;
  justify-content: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  background: var(--surface-card);
  border: 1px solid var(--border);
  border-radius: 28px;
  padding: 4px;
  display: inline-flex;
  margin-left: auto; margin-right: auto;
  display: flex;
}}
.week-tab {{
  padding: 8px 18px;
  border: none;
  border-radius: 24px;
  background: transparent;
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-muted);
  transition: all 0.35s var(--spring);
}}
.week-tab:hover {{
  color: var(--primary);
  background: rgba(67,56,202,0.06);
}}
.week-tab.active {{
  background: linear-gradient(135deg, #4338CA, #6366F1, #F97316);
  color: #fff;
  box-shadow: 0 4px 16px rgba(67,56,202,0.3);
}}

/* ── Week Container ────────────────────────────────────────── */
.week-container {{
  background: var(--surface-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  animation: weekFade 0.45s var(--ease) both;
}}
@keyframes weekFade {{
  from {{ opacity: 0; transform: scale(0.98); }}
  to {{ opacity: 1; transform: scale(1); }}
}}
.week-grid {{ display: flex; flex-direction: column; }}

/* ── Header Row ────────────────────────────────────────────── */
.header-row {{
  display: grid;
  grid-template-columns: 60px repeat(7, 1fr);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--surface-card);
  z-index: 10;
}}
.time-gutter-header {{ padding: 12px 4px; }}
.day-header {{
  text-align: center;
  padding: 10px 4px;
  border-left: 1px solid var(--border);
  transition: background var(--transition);
}}
.day-header.has-events {{
  background: rgba(67,56,202,0.05);
}}
body.dark .day-header.has-events {{
  background: rgba(99,102,241,0.1);
}}
.day-name {{
  display: block;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.22em;
}}
.day-date {{
  display: block;
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text);
  margin-top: 2px;
}}

/* ── Body Row / Grid ───────────────────────────────────────── */
.body-row {{
  display: grid;
  grid-template-columns: 60px repeat(7, 1fr);
  height: {grid_height}px;
  position: relative;
}}
.time-gutter {{
  position: relative;
  border-right: 1px solid var(--border);
}}
.time-label {{
  position: absolute;
  right: 8px;
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--text-muted);
  transform: translateY(-50%);
  white-space: nowrap;
  padding-left: 4px;
  border-left: 2px solid transparent;
}}
.time-label.alt {{ border-left-color: var(--accent-warm); opacity: 0.7; }}

.day-column {{
  position: relative;
  border-left: 1px solid var(--border);
}}
.hour-line {{
  position: absolute;
  left: 0; right: 0;
  border-top: 1px solid var(--border);
}}
.hour-line.hour-alt {{
  background: rgba(245,158,11,0.03);
}}
body.dark .hour-line.hour-alt {{
  background: rgba(245,158,11,0.02);
}}

/* ── Current Time Indicator ────────────────────────────────── */
.now-line {{
  position: absolute;
  left: 0; right: 0;
  height: 2px;
  background: var(--accent-hot);
  z-index: 8;
  pointer-events: none;
}}
.now-line::before {{
  content: '';
  position: absolute;
  left: -4px;
  top: -3px;
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent-hot);
}}

/* ── Events ────────────────────────────────────────────────── */
.event {{
  position: absolute;
  left: 3px; right: 3px;
  border-radius: 6px;
  border-left: 4px solid;
  padding: 4px 8px;
  overflow: hidden;
  cursor: pointer;
  font-size: 0.78rem;
  line-height: 1.3;
  z-index: 2;
  background: var(--surface-card);
  transition: box-shadow 0.3s var(--ease), transform 0.3s var(--spring);
  animation: fadeSlideIn 0.5s var(--spring) both;
}}
@keyframes fadeSlideIn {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
.event:hover {{
  transform: translateY(-6px);
  box-shadow: 0 8px 24px rgba(245,158,11,0.2);
  z-index: 5;
}}
body.dark .event {{
  box-shadow: inset 0 0 0 1px rgba(254,243,199,0.08);
}}
body.dark .event:hover {{
  box-shadow: 0 0 20px rgba(99,102,241,0.25), inset 0 0 0 1px rgba(254,243,199,0.15);
}}

.explicit-event {{
  border-left-width: 4px;
  border-left-color: var(--accent-hot) !important;
}}

.explicit-badge {{
  display: inline-flex;
  align-items: center;
  margin-right: 4px;
  vertical-align: middle;
}}
.pulse-dot {{
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--accent-hot);
  animation: pulseDot 1.5s ease-in-out infinite;
}}
@keyframes pulseDot {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50% {{ opacity: 0.5; transform: scale(1.4); }}
}}

.event-name {{
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text);
  font-family: var(--font-body);
}}
.event-name.compact {{ font-size: 0.72rem; }}
.event-time {{
  font-size: 0.66rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 1px;
}}

/* ── Travel Gaps — Animated Polyline ───────────────────────── */
.travel-gap {{
  position: absolute;
  left: 10px; right: 10px;
  margin-left: 12px;
  display: flex;
  align-items: center;
  z-index: 1;
  overflow: hidden;
}}
.travel-dots {{
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 2px;
  background: repeating-linear-gradient(
    to bottom,
    var(--text-muted) 0px,
    var(--text-muted) 3px,
    transparent 3px,
    transparent 7px
  );
  animation: dotsFlow 1.5s linear infinite;
}}
@keyframes dotsFlow {{
  from {{ background-position: 0 0; }}
  to {{ background-position: 0 14px; }}
}}
.travel-label {{
  font-size: 0.64rem;
  color: var(--text-muted);
  margin-left: 10px;
  white-space: nowrap;
  font-weight: 500;
}}

/* ── Legend ─────────────────────────────────────────────────── */
.legend {{
  display: flex;
  gap: 20px;
  justify-content: center;
  margin-top: 18px;
  font-size: 0.82rem;
  color: var(--text-muted);
  flex-wrap: wrap;
}}
.legend-item {{ display: flex; align-items: center; gap: 6px; }}
.legend-dot {{
  width: 12px; height: 12px;
  border-radius: 4px;
  display: inline-block;
}}
.legend-dot.explicit {{
  background: #FED7AA;
  border-left: 3px solid var(--accent-hot);
}}
body.dark .legend-dot.explicit {{ background: rgba(249,115,22,0.2); }}
.legend-dot.scheduled {{
  background: hsl(35, 55%, 82%);
  border-left: 3px solid hsl(35, 50%, 50%);
}}
.legend-dot.travel {{
  background: transparent;
  border-left: 2px dashed var(--text-muted);
  width: 8px;
}}

/* ── Tooltip — Warm glass ──────────────────────────────────── */
.tooltip {{
  display: none;
  position: fixed;
  background: var(--surface-card-glass);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  box-shadow: var(--shadow-lg);
  z-index: 100;
  max-width: 320px;
  font-size: 0.85rem;
  line-height: 1.5;
  pointer-events: none;
  opacity: 0;
  transform: scale(0.92);
  transition: opacity 0.2s, transform 0.2s var(--spring);
}}
.tooltip.visible {{
  opacity: 1;
  transform: scale(1);
}}
.tooltip .tt-name {{
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1rem;
  margin-bottom: 6px;
  color: var(--text);
}}
.tooltip .tt-time {{
  color: var(--text-muted);
  font-size: 0.82rem;
}}
.tooltip .tt-location {{
  color: var(--primary);
  margin-top: 5px;
  font-size: 0.82rem;
}}
body.dark .tooltip .tt-location {{ color: var(--primary-light); }}
.tooltip .tt-desc {{
  color: var(--text-muted);
  margin-top: 4px;
  font-size: 0.8rem;
  font-style: italic;
}}
.tooltip .tt-explicit {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: rgba(249,115,22,0.1);
  color: var(--accent-hot);
  font-weight: 600;
  font-size: 0.75rem;
  margin-top: 6px;
  padding: 3px 8px;
  border-radius: 4px;
}}

/* ── Footer ────────────────────────────────────────────────── */
.footer {{
  text-align: center;
  padding: 28px 16px 20px;
  font-size: 0.78rem;
  color: var(--text-muted);
}}
.footer-brand {{
  font-weight: 700;
  background: linear-gradient(135deg, #4338CA, #6366F1, #F97316);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}}

/* ── Empty State ───────────────────────────────────────────── */
.empty-wrap {{
  text-align: center;
  padding: 80px 24px;
  animation: fadeIn 0.8s both;
}}
.empty-emoji {{
  font-size: 4.5rem;
  display: block;
  margin-bottom: 20px;
  animation: emFloat 3s ease-in-out infinite;
}}
@keyframes emFloat {{
  0%, 100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-12px); }}
}}
.empty-title {{
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}}
.empty-sub {{
  color: var(--text-muted);
  font-size: 0.95rem;
  max-width: 400px;
  margin: 0 auto;
}}

/* ── Reduced Motion ────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }}
}}
"""


def _js() -> str:
    return """
/* ── Dark Mode Toggle ──────────────────────────────────────── */
function toggleDark() {
  document.body.classList.toggle('dark');
  var btn = document.querySelector('.dark-toggle');
  btn.textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
}

/* ── Sticky Header on scroll ───────────────────────────────── */
(function() {
  var header = document.getElementById('stickyHeader');
  if (!header) return;
  var hero = document.querySelector('.hero-card');
  window.addEventListener('scroll', function() {
    var threshold = hero ? hero.offsetHeight - 60 : 100;
    if (window.scrollY > threshold) {
      header.classList.add('visible', 'scrolled');
    } else {
      header.classList.remove('visible', 'scrolled');
    }
  });
})();

/* ── Week Navigation with crossfade ────────────────────────── */
function showWeek(idx) {
  document.querySelectorAll('.week-container').forEach(function(el, i) {
    if (i === idx) {
      el.style.display = 'block';
      el.style.animation = 'weekFade 0.4s cubic-bezier(0.22,1,0.36,1) both';
    } else {
      el.style.display = 'none';
    }
  });
  document.querySelectorAll('.week-tab').forEach(function(el, i) {
    el.classList.toggle('active', i === idx);
  });
}

/* ── Tooltip ───────────────────────────────────────────────── */
function showTooltip(e, el) {
  var data = JSON.parse(el.getAttribute('data-tooltip'));
  var tt = document.getElementById('tooltip');
  var parts = ['<div class="tt-name">' + escHtml(data.name) + '</div>'];
  parts.push('<div class="tt-time">' + escHtml(data.time) + ' (' + escHtml(data.duration) + ')</div>');
  if (data.location) {
    parts.push('<div class="tt-location">📍 ' + escHtml(data.location) + '</div>');
  }
  if (data.description && data.description !== data.location) {
    parts.push('<div class="tt-desc">' + escHtml(data.description) + '</div>');
  }
  if (data.explicit) {
    parts.push('<div class="tt-explicit">\u26A1 Pinned</div>');
  }
  tt.innerHTML = parts.join('');
  tt.style.display = 'block';
  requestAnimationFrame(function() { tt.classList.add('visible'); });

  var rect = el.getBoundingClientRect();
  var tx = rect.right + 10;
  var ty = rect.top;
  if (tx + 320 > window.innerWidth) tx = rect.left - 330;
  if (ty + 180 > window.innerHeight) ty = window.innerHeight - 190;
  if (ty < 8) ty = 8;
  tt.style.left = tx + 'px';
  tt.style.top = ty + 'px';
}

function hideTooltip() {
  var tt = document.getElementById('tooltip');
  tt.classList.remove('visible');
  setTimeout(function() { tt.style.display = 'none'; }, 200);
}

function escHtml(s) {
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

/* ── Init: current-time line ────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function() {
  var now = new Date();
  var todayStr = now.getFullYear() + '-' +
    String(now.getMonth()+1).padStart(2,'0') + '-' +
    String(now.getDate()).padStart(2,'0');
  if (todayStr >= TRIP_START && todayStr <= TRIP_END) {
    document.querySelectorAll('.day-column').forEach(function(col) {
      if (col.getAttribute('data-date') === todayStr) {
        var mins = now.getHours() * 60 + now.getMinutes();
        var totalMins = (HOUR_END - HOUR_START) * 60;
        var pct = ((mins - HOUR_START * 60) / totalMins) * 100;
        if (pct >= 0 && pct <= 100) {
          var line = document.createElement('div');
          line.className = 'now-line';
          line.style.top = pct + '%';
          col.appendChild(line);
        }
      }
    });
  }
});
"""


def _empty_html(trip_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(trip_name)} — Preview</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;0,9..144,700;1,9..144,400&family=Geist:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Geist',-apple-system,sans-serif;min-height:100vh;display:flex;flex-direction:column;
align-items:center;justify-content:center;
background:#FFFBF5;color:#1C1917;padding:40px 24px;position:relative;overflow:hidden;}}
body::before{{content:'';position:absolute;inset:0;
background:radial-gradient(ellipse at 20% 50%,rgba(67,56,202,0.2) 0%,transparent 60%),
radial-gradient(ellipse at 80% 30%,rgba(245,158,11,0.15) 0%,transparent 55%),
radial-gradient(ellipse at 50% 80%,rgba(249,115,22,0.1) 0%,transparent 50%);
pointer-events:none;}}
.empty-wrap{{text-align:center;animation:fadeIn 0.8s both;position:relative;z-index:1;}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(20px);}}to{{opacity:1;transform:translateY(0);}}}}
.empty-emoji{{font-size:5rem;display:block;margin-bottom:24px;animation:emFloat 3s ease-in-out infinite;}}
@keyframes emFloat{{0%,100%{{transform:translateY(0);}}50%{{transform:translateY(-14px);}}}}
h1{{font-family:'Fraunces',Georgia,serif;font-size:1.8rem;font-weight:700;margin-bottom:10px;}}
.sub{{color:#78716C;font-size:1rem;max-width:360px;margin:0 auto;}}
@media (prefers-reduced-motion: reduce){{*,*::before,*::after{{animation-duration:0.01ms !important;animation-iteration-count:1 !important;transition-duration:0.01ms !important;}}}}
</style></head>
<body><div class="empty-wrap">
<span class="empty-emoji">🗺️</span>
<h1>{html.escape(trip_name)}</h1>
<p class="sub">No events to preview. Make sure the trip has itinerary items.</p>
</div></body></html>"""


def open_preview(
    trip_name: str,
    day_events: list[tuple[str, list[dict]]],
    timezone: str = "",
) -> Path:
    """Generate HTML preview and open it in the default browser.

    Args:
        trip_name: Name of the trip.
        day_events: List of (date_string, events) from preview_trip_events().
        timezone: IANA destination timezone for the info banner.

    Returns:
        Path to the generated HTML file.
    """
    html_content = generate_preview_html(trip_name, day_events, timezone)
    tmp = tempfile.NamedTemporaryFile(
        suffix=".html", prefix="wanderlogpro-preview-", delete=False, mode="w",
        encoding="utf-8",
    )
    tmp.write(html_content)
    tmp.close()
    path = Path(tmp.name)
    webbrowser.open(path.as_uri())
    return path
