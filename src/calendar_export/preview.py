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
        f'<div class="tz-note">'
        f'🌍 Times shown in <strong>{html.escape(dest_tz)}</strong> (destination) '
        f'&mdash; {hours_str} {direction} '
        f'<strong>{html.escape(local_name)}</strong> (your timezone)'
        f'</div>'
    )


def _group_days_into_weeks(
    day_events: list[tuple[str, list[dict]]],
) -> list[list[tuple[str, list[dict]]]]:
    """Group (date, events) pairs into Mon–Sun weeks."""
    if not day_events:
        return []

    all_dates = [datetime.fromisoformat(d).date() for d, _ in day_events]
    min_date = min(all_dates)
    max_date = max(all_dates)

    # Align to Monday
    week_start = min_date - timedelta(days=min_date.weekday())
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
    """Deterministic pastel color from event name."""
    h = hash(summary) % 360
    return f"hsl({h}, 65%, 78%)"


def _event_border_color(summary: str) -> str:
    h = hash(summary) % 360
    return f"hsl({h}, 55%, 55%)"


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

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(trip_name)} — WanderlogPro Preview</title>
<style>
{_css(total_hours)}
</style>
</head>
<body>
<div class="header">
  <h1>📅 {html.escape(trip_name)}</h1>
  <p class="subtitle">{total_events} events across {total_days} days &middot; Dry-run preview</p>
  <p class="hint">Run without <code>--dry-run</code> to create these events in Google Calendar.</p>
</div>
{tz_html}
{nav_html}
{weeks_html}
<div class="legend">
  <span class="legend-item"><span class="legend-dot explicit"></span> <code>[!]</code> Explicit time</span>
  <span class="legend-item"><span class="legend-dot scheduled"></span> Auto-scheduled</span>
  <span class="legend-item"><span class="legend-dot travel"></span> Travel gap</span>
</div>
<div id="tooltip" class="tooltip"></div>
<script>
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
    display = "grid" if week_idx == 0 else "none"

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
        time_labels.append(
            f'<div class="time-label" style="top:{top_pct}%">{_fmt_hour(h)}</div>'
        )
    time_labels.append("</div>")
    time_gutter = "\n".join(time_labels)

    # Day columns with events
    day_columns = []
    for date_str, events in week:
        col_parts = [f'<div class="day-column">']
        # Hour grid lines
        for h in range(hour_start, hour_end):
            top_pct = ((h - hour_start) / total_hours) * 100
            col_parts.append(f'<div class="hour-line" style="top:{top_pct}%"></div>')

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

            # Tooltip data
            tooltip_data = {
                "name": display_name,
                "time": time_str,
                "duration": f"{duration_min} min",
                "location": location,
                "explicit": is_explicit,
                "description": description,
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
                        f'<span class="travel-label">{emoji} {gap_minutes} min</span>'
                        f"</div>"
                    )

            badge = '<span class="explicit-badge">[!]</span>' if is_explicit else ""
            compact = duration_min < 40
            name_class = "event-name compact" if compact else "event-name"

            col_parts.append(
                f'<div class="event {explicit_class}" '
                f'style="top:{top_pct}%;height:{height_pct}%;'
                f"background:{color};border-color:{border_color}\" "
                f'data-tooltip="{data_attr}" '
                f"onmouseenter=\"showTooltip(event, this)\" "
                f"onmouseleave=\"hideTooltip()\">"
                f"{badge}"
                f'<div class="{name_class}">{html.escape(display_name)}</div>'
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
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f5f6f8;
  color: #1a1a1a;
  padding: 20px;
}}
.header {{
  text-align: center;
  margin-bottom: 16px;
}}
.header h1 {{
  font-size: 1.6rem;
  font-weight: 600;
  color: #1a73e8;
}}
.tz-note {{
  text-align: center;
  background: #fef7e0;
  border: 1px solid #f9d67a;
  border-radius: 8px;
  padding: 10px 16px;
  margin: 0 auto 14px auto;
  max-width: 700px;
  font-size: 0.9rem;
  color: #5d4d1a;
}}
.subtitle {{
  color: #5f6368;
  font-size: 0.95rem;
  margin-top: 4px;
}}
.hint {{
  color: #80868b;
  font-size: 0.82rem;
  margin-top: 4px;
}}
.hint code {{
  background: #e8eaed;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.82rem;
}}
.week-nav {{
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}}
.week-tab {{
  padding: 6px 14px;
  border: 1px solid #dadce0;
  border-radius: 18px;
  background: white;
  cursor: pointer;
  font-size: 0.85rem;
  color: #5f6368;
  transition: all 0.15s;
}}
.week-tab:hover {{ background: #e8f0fe; color: #1a73e8; border-color: #1a73e8; }}
.week-tab.active {{
  background: #1a73e8;
  color: white;
  border-color: #1a73e8;
}}
.week-container {{
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
  overflow: hidden;
}}
.week-grid {{ display: flex; flex-direction: column; }}
.header-row {{
  display: grid;
  grid-template-columns: 56px repeat(7, 1fr);
  border-bottom: 1px solid #e0e0e0;
  position: sticky;
  top: 0;
  background: white;
  z-index: 10;
}}
.time-gutter-header {{ padding: 10px 4px; }}
.day-header {{
  text-align: center;
  padding: 8px 4px;
  border-left: 1px solid #f0f0f0;
}}
.day-header.has-events {{ background: #e8f0fe; }}
.day-name {{ display: block; font-size: 0.75rem; color: #80868b; text-transform: uppercase; }}
.day-date {{ display: block; font-size: 0.9rem; font-weight: 500; color: #1a1a1a; }}
.body-row {{
  display: grid;
  grid-template-columns: 56px repeat(7, 1fr);
  height: {grid_height}px;
  position: relative;
}}
.time-gutter {{
  position: relative;
  border-right: 1px solid #e0e0e0;
}}
.time-label {{
  position: absolute;
  right: 6px;
  font-size: 0.7rem;
  color: #80868b;
  transform: translateY(-50%);
  white-space: nowrap;
}}
.day-column {{
  position: relative;
  border-left: 1px solid #f0f0f0;
}}
.hour-line {{
  position: absolute;
  left: 0; right: 0;
  border-top: 1px solid #f0f0f0;
}}
.event {{
  position: absolute;
  left: 2px; right: 2px;
  border-radius: 4px;
  border-left: 3px solid;
  padding: 3px 5px;
  overflow: hidden;
  cursor: pointer;
  font-size: 0.78rem;
  line-height: 1.25;
  transition: box-shadow 0.15s, transform 0.1s;
  z-index: 2;
}}
.event:hover {{
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  transform: scale(1.02);
  z-index: 5;
}}
.explicit-event {{
  border-left-width: 4px;
  border-left-color: #d93025 !important;
}}
.explicit-badge {{
  background: #d93025;
  color: white;
  font-size: 0.65rem;
  padding: 0 3px;
  border-radius: 2px;
  font-weight: 700;
  margin-right: 3px;
  vertical-align: middle;
}}
.event-name {{
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.event-name.compact {{ font-size: 0.72rem; }}
.event-time {{
  font-size: 0.68rem;
  color: #555;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
.travel-gap {{
  position: absolute;
  left: 8px; right: 8px;
  border-left: 2px dashed #bbb;
  margin-left: 12px;
  display: flex;
  align-items: center;
  z-index: 1;
}}
.travel-label {{
  font-size: 0.65rem;
  color: #888;
  margin-left: 8px;
  white-space: nowrap;
}}
.legend {{
  display: flex;
  gap: 20px;
  justify-content: center;
  margin-top: 14px;
  font-size: 0.82rem;
  color: #5f6368;
  flex-wrap: wrap;
}}
.legend-item {{ display: flex; align-items: center; gap: 5px; }}
.legend-dot {{
  width: 12px; height: 12px;
  border-radius: 3px;
  display: inline-block;
}}
.legend-dot.explicit {{
  background: #fce8e6;
  border-left: 3px solid #d93025;
}}
.legend-dot.scheduled {{
  background: hsl(210, 65%, 78%);
  border-left: 3px solid hsl(210, 55%, 55%);
}}
.legend-dot.travel {{
  background: transparent;
  border-left: 2px dashed #bbb;
  width: 8px;
}}
.tooltip {{
  display: none;
  position: fixed;
  background: white;
  border: 1px solid #dadce0;
  border-radius: 8px;
  padding: 12px 14px;
  box-shadow: 0 4px 14px rgba(0,0,0,0.15);
  z-index: 100;
  max-width: 300px;
  font-size: 0.85rem;
  line-height: 1.4;
  pointer-events: none;
}}
.tooltip .tt-name {{
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 4px;
}}
.tooltip .tt-time {{
  color: #5f6368;
}}
.tooltip .tt-location {{
  color: #1a73e8;
  margin-top: 4px;
}}
.tooltip .tt-explicit {{
  color: #d93025;
  font-weight: 500;
  font-size: 0.78rem;
  margin-top: 4px;
}}
"""


def _js() -> str:
    return """
function showWeek(idx) {
  document.querySelectorAll('.week-container').forEach(function(el, i) {
    el.style.display = i === idx ? 'block' : 'none';
  });
  document.querySelectorAll('.week-tab').forEach(function(el, i) {
    el.classList.toggle('active', i === idx);
  });
}

function showTooltip(e, el) {
  var data = JSON.parse(el.getAttribute('data-tooltip'));
  var tt = document.getElementById('tooltip');
  var parts = ['<div class="tt-name">' + escHtml(data.name) + '</div>'];
  parts.push('<div class="tt-time">⏰ ' + escHtml(data.time) + ' (' + escHtml(data.duration) + ')</div>');
  if (data.location) {
    parts.push('<div class="tt-location">📍 ' + escHtml(data.location) + '</div>');
  }
  if (data.explicit) {
    parts.push('<div class="tt-explicit">⚡ Explicit time from Wanderlog</div>');
  }
  tt.innerHTML = parts.join('');
  tt.style.display = 'block';

  var rect = el.getBoundingClientRect();
  var tx = rect.right + 8;
  var ty = rect.top;
  if (tx + 300 > window.innerWidth) tx = rect.left - 308;
  if (ty + 150 > window.innerHeight) ty = window.innerHeight - 160;
  tt.style.left = tx + 'px';
  tt.style.top = ty + 'px';
}

function hideTooltip() {
  document.getElementById('tooltip').style.display = 'none';
}

function escHtml(s) {
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
"""


def _empty_html(trip_name: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{html.escape(trip_name)} — Preview</title>
<style>body{{font-family:sans-serif;text-align:center;padding:60px;color:#5f6368;}}
h1{{color:#1a73e8;}}</style></head>
<body><h1>📅 {html.escape(trip_name)}</h1>
<p>No events to preview. Make sure the trip has itinerary items.</p></body></html>"""


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
