"""Tests for Google Calendar export logic."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from wanderlogpro.calendar_export.models import CalendarTrip, ItineraryDay, ItineraryItem
from wanderlogpro.calendar_export.gcal_export import (
    build_event,
    create_trip_calendar,
    schedule_day,
    _parse_item_time,
    parse_invitees,
    share_calendar,
)


class TestBuildEvent:
    def test_timed_event_has_exclamation_prefix(self):
        item = ItineraryItem(name="Eiffel Tower", lat=48.85, lng=2.29)
        start = datetime(2026, 4, 20, 14, 0)
        end = datetime(2026, 4, 20, 15, 0)
        event = build_event(item, start, end, has_explicit_time=True)
        assert event["summary"] == "[!]Eiffel Tower"

    def test_untimed_event_no_prefix(self):
        item = ItineraryItem(name="Le Comptoir", lat=48.85, lng=2.35)
        start = datetime(2026, 4, 20, 10, 0)
        end = datetime(2026, 4, 20, 11, 0)
        event = build_event(item, start, end, has_explicit_time=False)
        assert event["summary"] == "Le Comptoir"

    def test_event_has_start_and_end(self):
        item = ItineraryItem(name="Test", lat=0, lng=0)
        start = datetime(2026, 4, 20, 14, 0)
        end = datetime(2026, 4, 20, 15, 30)
        event = build_event(item, start, end, has_explicit_time=True)
        assert event["start"]["dateTime"] == start.isoformat()
        assert event["end"]["dateTime"] == end.isoformat()

    def test_event_no_timezone_when_empty(self):
        item = ItineraryItem(name="Test", lat=0, lng=0)
        event = build_event(item, datetime(2026, 4, 20, 10, 0), datetime(2026, 4, 20, 11, 0), False)
        assert "timeZone" not in event["start"]
        assert "timeZone" not in event["end"]

    def test_event_has_timezone_when_provided(self):
        item = ItineraryItem(name="Test", lat=0, lng=0)
        event = build_event(
            item, datetime(2026, 4, 20, 10, 0), datetime(2026, 4, 20, 11, 0),
            False, timezone="Asia/Ho_Chi_Minh",
        )
        assert event["start"]["timeZone"] == "Asia/Ho_Chi_Minh"
        assert event["end"]["timeZone"] == "Asia/Ho_Chi_Minh"

    def test_event_includes_address_and_notes(self):
        item = ItineraryItem(
            name="Museum", lat=0, lng=0,
            address="123 Art St", notes="Free on Sundays",
        )
        event = build_event(item, datetime(2026, 4, 20, 10, 0), datetime(2026, 4, 20, 12, 0), False)
        assert "123 Art St" in event["description"]
        assert "Free on Sundays" in event["description"]
        assert event["location"] == "123 Art St"

    def test_event_no_description_when_empty(self):
        item = ItineraryItem(name="Test", lat=0, lng=0)
        event = build_event(item, datetime(2026, 4, 20, 10, 0), datetime(2026, 4, 20, 11, 0), False)
        assert "description" not in event
        assert "location" not in event


class TestScheduleDay:
    def test_default_start_at_10am(self):
        day = ItineraryDay(
            date="2026-04-20",
            items=[ItineraryItem(name="A", lat=0, lng=0, duration_minutes=60)],
        )
        events = schedule_day(day)
        assert len(events) == 1
        assert events[0]["start"]["dateTime"] == "2026-04-20T10:00:00"
        assert events[0]["end"]["dateTime"] == "2026-04-20T11:00:00"

    def test_explicit_time_overrides_default(self):
        day = ItineraryDay(
            date="2026-04-20",
            items=[
                ItineraryItem(name="A", lat=0, lng=0, start_time="14:00", duration_minutes=90),
            ],
        )
        events = schedule_day(day)
        assert events[0]["start"]["dateTime"] == "2026-04-20T14:00:00"
        assert events[0]["summary"] == "[!]A"

    def test_explicit_end_time(self):
        day = ItineraryDay(
            date="2026-04-20",
            items=[
                ItineraryItem(
                    name="A", lat=0, lng=0,
                    start_time="10:00", end_time="13:00",
                    duration_minutes=180,
                ),
            ],
        )
        events = schedule_day(day)
        assert events[0]["end"]["dateTime"] == "2026-04-20T13:00:00"

    def test_duration_fallback_to_60_minutes(self):
        day = ItineraryDay(
            date="2026-04-20",
            items=[ItineraryItem(name="A", lat=0, lng=0, duration_minutes=0)],
        )
        events = schedule_day(day)
        assert events[0]["end"]["dateTime"] == "2026-04-20T11:00:00"

    def test_sequential_scheduling_with_travel_gap(self):
        day = ItineraryDay(
            date="2026-04-20",
            items=[
                ItineraryItem(name="A", lat=0, lng=0, duration_minutes=60, travel_minutes_to_next=20),
                ItineraryItem(name="B", lat=0, lng=0, duration_minutes=90),
            ],
        )
        events = schedule_day(day)
        assert len(events) == 2
        # A: 10:00 - 11:00, travel 20min, B: 11:20 - 12:50
        assert events[0]["start"]["dateTime"] == "2026-04-20T10:00:00"
        assert events[0]["end"]["dateTime"] == "2026-04-20T11:00:00"
        assert events[1]["start"]["dateTime"] == "2026-04-20T11:20:00"
        assert events[1]["end"]["dateTime"] == "2026-04-20T12:50:00"

    def test_explicit_time_mid_sequence(self):
        """An explicit time in the middle of the day overrides sequential flow."""
        day = ItineraryDay(
            date="2026-04-20",
            items=[
                ItineraryItem(name="A", lat=0, lng=0, duration_minutes=60, travel_minutes_to_next=15),
                ItineraryItem(name="B", lat=0, lng=0, start_time="15:00", duration_minutes=120),
            ],
        )
        events = schedule_day(day)
        # A: 10:00-11:00, B explicitly at 15:00-17:00
        assert events[1]["start"]["dateTime"] == "2026-04-20T15:00:00"
        assert events[1]["end"]["dateTime"] == "2026-04-20T17:00:00"
        assert events[1]["summary"] == "[!]B"

    def test_empty_day(self):
        day = ItineraryDay(date="2026-04-20", items=[])
        events = schedule_day(day)
        assert events == []

    def test_multiple_items_no_travel(self):
        day = ItineraryDay(
            date="2026-04-20",
            items=[
                ItineraryItem(name="A", lat=0, lng=0, duration_minutes=30),
                ItineraryItem(name="B", lat=0, lng=0, duration_minutes=45),
            ],
        )
        events = schedule_day(day)
        # A: 10:00-10:30, B: 10:30-11:15
        assert events[1]["start"]["dateTime"] == "2026-04-20T10:30:00"
        assert events[1]["end"]["dateTime"] == "2026-04-20T11:15:00"

    def test_25_min_duration_event(self):
        """Verify a 25-minute visit (like LSOUL) produces correct event times."""
        day = ItineraryDay(
            date="2026-03-20",
            items=[
                ItineraryItem(
                    name="LSOUL", lat=10.76, lng=106.69,
                    address="257B Nguyễn Trãi, District 1, HCMC",
                    duration_minutes=25,
                ),
            ],
        )
        events = schedule_day(day)
        assert len(events) == 1
        assert events[0]["summary"] == "LSOUL"
        assert events[0]["start"]["dateTime"] == "2026-03-20T10:00:00"
        assert events[0]["end"]["dateTime"] == "2026-03-20T10:25:00"
        assert events[0]["location"] == "257B Nguyễn Trãi, District 1, HCMC"

    def test_schedule_day_no_timezone_by_default(self):
        """Dry-run: no timezone field when timezone is empty."""
        day = ItineraryDay(
            date="2026-04-20",
            items=[ItineraryItem(name="A", lat=0, lng=0, duration_minutes=60)],
        )
        events = schedule_day(day)
        assert "timeZone" not in events[0]["start"]
        assert "timeZone" not in events[0]["end"]

    def test_schedule_day_with_timezone(self):
        """Real export: timezone field present when provided."""
        day = ItineraryDay(
            date="2026-04-20",
            items=[ItineraryItem(name="A", lat=0, lng=0, duration_minutes=60)],
        )
        events = schedule_day(day, timezone="Asia/Ho_Chi_Minh")
        assert events[0]["start"]["timeZone"] == "Asia/Ho_Chi_Minh"
        assert events[0]["end"]["timeZone"] == "Asia/Ho_Chi_Minh"

    def test_custom_start_hour(self):
        day = ItineraryDay(
            date="2026-04-20",
            items=[ItineraryItem(name="A", lat=0, lng=0, duration_minutes=60)],
        )
        events = schedule_day(day, start_hour=9)
        assert events[0]["start"]["dateTime"] == "2026-04-20T09:00:00"
        assert events[0]["end"]["dateTime"] == "2026-04-20T10:00:00"

    def test_start_hour_early_morning(self):
        day = ItineraryDay(
            date="2026-04-20",
            items=[ItineraryItem(name="A", lat=0, lng=0, duration_minutes=30)],
        )
        events = schedule_day(day, start_hour=6)
        assert events[0]["start"]["dateTime"] == "2026-04-20T06:00:00"

    def test_start_hour_does_not_override_explicit_time(self):
        day = ItineraryDay(
            date="2026-04-20",
            items=[
                ItineraryItem(name="A", lat=0, lng=0, start_time="14:00", duration_minutes=60),
            ],
        )
        events = schedule_day(day, start_hour=8)
        # Explicit time wins over start_hour
        assert events[0]["start"]["dateTime"] == "2026-04-20T14:00:00"

    def test_hh_mm_format(self):
        result = _parse_item_time("2026-04-20", "14:00")
        assert result == datetime(2026, 4, 20, 14, 0)

    def test_hh_mm_ss_format(self):
        result = _parse_item_time("2026-04-20", "14:30:00")
        assert result == datetime(2026, 4, 20, 14, 30, 0)

    def test_iso_datetime(self):
        result = _parse_item_time("2026-04-20", "2026-04-20T14:00:00")
        assert result == datetime(2026, 4, 20, 14, 0)

    def test_fallback_on_invalid(self):
        result = _parse_item_time("2026-04-20", "not-a-time")
        assert result.hour == 10
        assert result.minute == 0


class TestCreateTripCalendar:
    def test_creates_calendar_with_trip_name(self):
        mock_service = MagicMock()
        mock_service.calendars().insert().execute.return_value = {"id": "cal_123"}

        calendar_id = create_trip_calendar(mock_service, "Paris 2026")
        assert calendar_id == "cal_123"

        call_args = mock_service.calendars().insert.call_args
        body = call_args[1]["body"] if "body" in call_args[1] else call_args[0][0]
        assert "Paris 2026" in body["summary"]
        assert "WanderlogPro" in body["summary"]




class TestParseInvitees:
    def test_empty_returns_empty_list(self):
        assert parse_invitees(None, None) == []
        assert parse_invitees("", None) == []

    def test_single_email_string(self):
        assert parse_invitees("foo@example.com", None) == ["foo@example.com"]

    def test_comma_separated_string(self):
        assert parse_invitees("a@x.com, b@y.com ,c@z.com", None) == [
            "a@x.com", "b@y.com", "c@z.com"
        ]

    def test_file_one_per_line(self, tmp_path):
        f = tmp_path / "invites.txt"
        f.write_text("foo@x.com\nbar@y.com\n")
        assert parse_invitees(None, f) == ["foo@x.com", "bar@y.com"]

    def test_file_skips_blanks_and_comments(self, tmp_path):
        f = tmp_path / "invites.txt"
        f.write_text("# team trip\nfoo@x.com\n\n# another\nbar@y.com\n")
        assert parse_invitees(None, f) == ["foo@x.com", "bar@y.com"]

    def test_merges_string_and_file_with_dedup(self, tmp_path):
        f = tmp_path / "invites.txt"
        f.write_text("bar@y.com\nFOO@x.com\n")
        result = parse_invitees("foo@x.com, baz@z.com", f)
        assert result == ["foo@x.com", "baz@z.com", "bar@y.com"]

    def test_invalid_email_raises(self):
        with pytest.raises(ValueError, match="Invalid email"):
            parse_invitees("notanemail", None)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            parse_invitees(None, tmp_path / "nope.txt")


class TestShareCalendar:
    def test_inserts_acl_rule_per_email(self):
        service = MagicMock()
        service.acl().insert().execute.return_value = {}
        service.acl.reset_mock()

        succeeded, failures = share_calendar(
            service, "cal_abc", ["a@x.com", "b@y.com"], role="writer"
        )

        assert succeeded == ["a@x.com", "b@y.com"]
        assert failures == []
        assert service.acl().insert.call_count == 2
        call = service.acl().insert.call_args_list[0]
        assert call.kwargs["calendarId"] == "cal_abc"
        body = call.kwargs["body"]
        assert body == {
            "scope": {"type": "user", "value": "a@x.com"},
            "role": "writer",
        }

    def test_continues_on_per_email_failure(self):
        service = MagicMock()

        def insert_side_effect(**kwargs):
            mock_req = MagicMock()
            if kwargs["body"]["scope"]["value"] == "bad@x.com":
                mock_req.execute.side_effect = Exception("403 forbidden")
            else:
                mock_req.execute.return_value = {}
            return mock_req

        service.acl().insert.side_effect = insert_side_effect

        succeeded, failures = share_calendar(
            service, "cal_abc", ["ok@x.com", "bad@x.com", "also@x.com"]
        )

        assert succeeded == ["ok@x.com", "also@x.com"]
        assert len(failures) == 1
        assert failures[0][0] == "bad@x.com"
        assert "403" in failures[0][1]

    def test_empty_emails_noop(self):
        service = MagicMock()
        succeeded, failures = share_calendar(service, "cal_abc", [])
        assert succeeded == []
        assert failures == []
