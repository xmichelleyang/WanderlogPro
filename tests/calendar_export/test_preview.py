"""Tests for the dry-run preview functionality."""

from datetime import datetime

import pytest

from wanderlogpro.calendar_export.models import CalendarTrip, ItineraryDay, ItineraryItem
from wanderlogpro.calendar_export.gcal_export import preview_trip_events
from wanderlogpro.calendar_export.preview import (
    generate_preview_html,
    _group_days_into_weeks,
    _time_range,
    _timezone_note,
)


class TestPreviewTripEvents:
    def test_returns_day_event_pairs(self):
        trip = CalendarTrip(
            id="test",
            name="Test Trip",
            days=[
                ItineraryDay(
                    date="2026-04-20",
                    items=[ItineraryItem(name="A", lat=0, lng=0, duration_minutes=60)],
                ),
                ItineraryDay(
                    date="2026-04-21",
                    items=[ItineraryItem(name="B", lat=0, lng=0, duration_minutes=30)],
                ),
            ],
        )
        result = preview_trip_events(trip)
        assert len(result) == 2
        assert result[0][0] == "2026-04-20"
        assert result[1][0] == "2026-04-21"

    def test_events_have_correct_structure(self):
        trip = CalendarTrip(
            id="test",
            name="Test Trip",
            days=[
                ItineraryDay(
                    date="2026-04-20",
                    items=[
                        ItineraryItem(
                            name="Museum", lat=48.86, lng=2.33,
                            address="1 Rue du Louvre", duration_minutes=120,
                        ),
                    ],
                ),
            ],
        )
        result = preview_trip_events(trip)
        events = result[0][1]
        assert len(events) == 1
        assert events[0]["summary"] == "Museum"
        assert events[0]["location"] == "1 Rue du Louvre"
        assert "dateTime" in events[0]["start"]
        assert "dateTime" in events[0]["end"]

    def test_explicit_time_gets_prefix(self):
        trip = CalendarTrip(
            id="test",
            name="Test Trip",
            days=[
                ItineraryDay(
                    date="2026-04-20",
                    items=[
                        ItineraryItem(
                            name="Tower", lat=0, lng=0,
                            start_time="14:00", duration_minutes=60,
                        ),
                    ],
                ),
            ],
        )
        result = preview_trip_events(trip)
        assert result[0][1][0]["summary"] == "[!]Tower"

    def test_skips_empty_days(self):
        trip = CalendarTrip(
            id="test",
            name="Test Trip",
            days=[
                ItineraryDay(date="2026-04-20", items=[]),
                ItineraryDay(
                    date="2026-04-21",
                    items=[ItineraryItem(name="A", lat=0, lng=0, duration_minutes=30)],
                ),
            ],
        )
        result = preview_trip_events(trip)
        assert len(result) == 1
        assert result[0][0] == "2026-04-21"

    def test_empty_trip(self):
        trip = CalendarTrip(id="test", name="Empty", days=[])
        result = preview_trip_events(trip)
        assert result == []

    def test_scheduling_preserved(self):
        """Verify sequential scheduling + travel gaps work in preview."""
        trip = CalendarTrip(
            id="test",
            name="Test Trip",
            days=[
                ItineraryDay(
                    date="2026-04-20",
                    items=[
                        ItineraryItem(
                            name="A", lat=0, lng=0,
                            duration_minutes=60, travel_minutes_to_next=15,
                        ),
                        ItineraryItem(name="B", lat=0, lng=0, duration_minutes=30),
                    ],
                ),
            ],
        )
        result = preview_trip_events(trip)
        events = result[0][1]
        assert events[0]["start"]["dateTime"] == "2026-04-20T10:00:00"
        assert events[0]["end"]["dateTime"] == "2026-04-20T11:00:00"
        # 11:00 + 15 min travel = 11:15
        assert events[1]["start"]["dateTime"] == "2026-04-20T11:15:00"
        assert events[1]["end"]["dateTime"] == "2026-04-20T11:45:00"


class TestGroupDaysIntoWeeks:
    def test_single_day(self):
        day_events = [("2026-04-20", [{"summary": "A"}])]  # Monday
        weeks = _group_days_into_weeks(day_events)
        assert len(weeks) == 1
        assert len(weeks[0]) == 7  # always full week

    def test_multi_week_trip(self):
        day_events = [
            ("2026-04-20", [{"summary": "A"}]),  # Monday week 1
            ("2026-04-28", [{"summary": "B"}]),  # Tuesday week 2
        ]
        weeks = _group_days_into_weeks(day_events)
        assert len(weeks) == 2

    def test_empty_input(self):
        assert _group_days_into_weeks([]) == []

    def test_week_aligned_to_sunday(self):
        # Wednesday 2026-04-22
        day_events = [("2026-04-22", [{"summary": "A"}])]
        weeks = _group_days_into_weeks(day_events)
        # Week should start on Sunday 2026-04-19
        assert weeks[0][0][0] == "2026-04-19"
        assert weeks[0][6][0] == "2026-04-25"  # Saturday


class TestTimeRange:
    def test_finds_min_max_hours(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "start": {"dateTime": "2026-04-20T09:00:00"},
                        "end": {"dateTime": "2026-04-20T11:30:00"},
                    },
                    {
                        "start": {"dateTime": "2026-04-20T15:00:00"},
                        "end": {"dateTime": "2026-04-20T17:00:00"},
                    },
                ],
            )
        ]
        start, end = _time_range(day_events)
        assert start == 8   # 9 - 1 padding
        assert end == 18     # 17 + 1 padding


class TestGeneratePreviewHtml:
    def test_contains_trip_name(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "Museum",
                        "start": {"dateTime": "2026-04-20T10:00:00"},
                        "end": {"dateTime": "2026-04-20T12:00:00"},
                    }
                ],
            )
        ]
        html = generate_preview_html("Paris 2026", day_events)
        assert "Paris 2026" in html
        assert "<!DOCTYPE html>" in html

    def test_contains_event_name(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "Eiffel Tower",
                        "start": {"dateTime": "2026-04-20T14:00:00"},
                        "end": {"dateTime": "2026-04-20T15:00:00"},
                    }
                ],
            )
        ]
        html = generate_preview_html("Trip", day_events)
        assert "Eiffel Tower" in html

    def test_explicit_event_has_badge(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "[!]Ticket Event",
                        "start": {"dateTime": "2026-04-20T14:00:00"},
                        "end": {"dateTime": "2026-04-20T15:00:00"},
                    }
                ],
            )
        ]
        html = generate_preview_html("Trip", day_events)
        assert "explicit-badge" in html
        assert "Ticket Event" in html

    def test_location_in_tooltip(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "Place",
                        "location": "123 Main St",
                        "start": {"dateTime": "2026-04-20T10:00:00"},
                        "end": {"dateTime": "2026-04-20T11:00:00"},
                    }
                ],
            )
        ]
        html = generate_preview_html("Trip", day_events)
        assert "123 Main St" in html

    def test_empty_trip_fallback(self):
        html = generate_preview_html("Empty Trip", [])
        assert "Empty Trip" in html
        assert "No events to preview" in html

    def test_dry_run_hint(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "A",
                        "start": {"dateTime": "2026-04-20T10:00:00"},
                        "end": {"dateTime": "2026-04-20T11:00:00"},
                    }
                ],
            )
        ]
        html = generate_preview_html("Trip", day_events)
        assert "--dry-run" in html
        assert "Dry-run preview" in html

    def test_multi_week_has_navigation(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "A",
                        "start": {"dateTime": "2026-04-20T10:00:00"},
                        "end": {"dateTime": "2026-04-20T11:00:00"},
                    }
                ],
            ),
            (
                "2026-04-28",
                [
                    {
                        "summary": "B",
                        "start": {"dateTime": "2026-04-28T10:00:00"},
                        "end": {"dateTime": "2026-04-28T11:00:00"},
                    }
                ],
            ),
        ]
        html = generate_preview_html("Long Trip", day_events)
        assert "week-tab" in html
        assert "showWeek" in html

    def test_travel_gap_shown(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "A",
                        "start": {"dateTime": "2026-04-20T10:00:00"},
                        "end": {"dateTime": "2026-04-20T11:00:00"},
                    },
                    {
                        "summary": "B",
                        "start": {"dateTime": "2026-04-20T11:20:00"},
                        "end": {"dateTime": "2026-04-20T12:00:00"},
                    },
                ],
            )
        ]
        html = generate_preview_html("Trip", day_events)
        assert "travel-gap" in html
        assert "20 min" in html

    def test_event_count_summary(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "A",
                        "start": {"dateTime": "2026-04-20T10:00:00"},
                        "end": {"dateTime": "2026-04-20T11:00:00"},
                    },
                    {
                        "summary": "B",
                        "start": {"dateTime": "2026-04-20T11:00:00"},
                        "end": {"dateTime": "2026-04-20T12:00:00"},
                    },
                ],
            )
        ]
        html = generate_preview_html("Trip", day_events)
        assert "2 events" in html


class TestTimezoneNote:
    def test_empty_timezone_no_note(self):
        assert _timezone_note("", "2026-04-20") == ""

    def test_invalid_timezone_no_note(self):
        assert _timezone_note("Not/A/Timezone", "2026-04-20") == ""

    def test_different_timezone_shows_note(self):
        note = _timezone_note("Asia/Ho_Chi_Minh", "2026-04-20")
        assert "Asia/Ho_Chi_Minh" in note
        assert "hour" in note

    def test_note_contains_hour_difference(self):
        note = _timezone_note("Asia/Ho_Chi_Minh", "2026-04-20")
        # Should contain some number of hours
        assert "hour" in note
        assert "ahead" in note or "behind" in note

    def test_generate_preview_includes_tz_banner(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "A",
                        "start": {"dateTime": "2026-04-20T10:00:00"},
                        "end": {"dateTime": "2026-04-20T11:00:00"},
                    },
                ],
            )
        ]
        result = generate_preview_html("Trip", day_events, timezone="Asia/Ho_Chi_Minh")
        assert "tz-badge" in result
        assert "Asia/Ho_Chi_Minh" in result

    def test_generate_preview_no_banner_without_timezone(self):
        day_events = [
            (
                "2026-04-20",
                [
                    {
                        "summary": "A",
                        "start": {"dateTime": "2026-04-20T10:00:00"},
                        "end": {"dateTime": "2026-04-20T11:00:00"},
                    },
                ],
            )
        ]
        result = generate_preview_html("Trip", day_events)
        # CSS class will exist in stylesheet but no actual banner div
        assert '<div class="tz-note">' not in result
