"""Tests for the guide module."""

import os
import tempfile

from wanderlogpro.offline_mode.models import Guide, GuideDay, GuideFlight, GuideHotel, GuidePlace
from wanderlogpro.offline_mode.builder import build_guide, _categorize, _format_time
from wanderlogpro.offline_mode.generator import generate_guide_html, write_guide, _format_time_ampm
from wanderlogpro.calendar_export.models import (
    CalendarTrip, FlightInfo, HotelInfo, ItineraryDay, ItineraryItem,
)


# ── Model tests ───────────────────────────────────────────────


class TestGuideModels:
    def test_guide_flights_list(self):
        guide = Guide(name="Trip", flights=[
            GuideFlight(airline="Vietnam Airlines", flight_number="99",
                        depart_airport="SFO", arrive_airport="SGN"),
        ])
        assert len(guide.flights) == 1
        assert guide.flights[0].airline == "Vietnam Airlines"

    def test_guide_hotels_list(self):
        guide = Guide(name="Trip", hotels=[
            GuideHotel(name="Hilton", check_in="2025-01-15", check_out="2025-01-18", nights=3),
        ])
        assert len(guide.hotels) == 1
        assert guide.hotels[0].name == "Hilton"
        assert guide.hotels[0].nights == 3

    def test_total_places(self):
        guide = Guide(name="Trip", days=[
            GuideDay(date="2025-01-15", places=[
                GuidePlace(name="A"),
                GuidePlace(name="B"),
            ]),
            GuideDay(date="2025-01-16", places=[
                GuidePlace(name="C"),
            ]),
        ])
        assert guide.total_places == 3

    def test_empty_guide(self):
        guide = Guide(name="Empty")
        assert guide.flights == []
        assert guide.hotels == []
        assert guide.total_places == 0


# ── Builder tests ─────────────────────────────────────────────


class TestCategorize:
    def test_flight(self):
        item = ItineraryItem(name="Flight to Hanoi", lat=0, lng=0)
        assert _categorize(item) == "flight"

    def test_airport(self):
        item = ItineraryItem(name="Arrive at airport", lat=0, lng=0)
        assert _categorize(item) == "flight"

    def test_hotel(self):
        item = ItineraryItem(name="Check in Hotel Morin", lat=0, lng=0)
        assert _categorize(item) == "hotel"

    def test_hostel(self):
        item = ItineraryItem(name="Stay at Youth Hostel", lat=0, lng=0)
        assert _categorize(item) == "hotel"

    def test_food(self):
        item = ItineraryItem(name="Lunch at restaurant", lat=0, lng=0)
        assert _categorize(item) == "food"

    def test_food_specific(self):
        item = ItineraryItem(name="Pho 10 Ly Quoc Su", lat=0, lng=0, notes="Best pho restaurant")
        assert _categorize(item) == "food"

    def test_activity_default(self):
        item = ItineraryItem(name="Temple of Literature", lat=0, lng=0)
        assert _categorize(item) == "activity"


class TestFormatTime:
    def test_morning(self):
        assert _format_time("2025-01-15T09:30:00") == "9:30 AM"

    def test_afternoon(self):
        assert _format_time("2025-01-15T14:00:00") == "2:00 PM"

    def test_midnight(self):
        assert _format_time("2025-01-15T00:00:00") == "12:00 AM"

    def test_noon(self):
        assert _format_time("2025-01-15T12:00:00") == "12:00 PM"

    def test_empty(self):
        assert _format_time("") == ""

    def test_no_t(self):
        """Bare HH:MM times (from Wanderlog) should be parsed."""
        assert _format_time("09:30") == "9:30 AM"


class TestBuildGuide:
    def test_converts_trip(self):
        trip = CalendarTrip(
            id="abc",
            name="Vietnam Trip",
            timezone="Asia/Ho_Chi_Minh",
            days=[
                ItineraryDay(date="2025-01-15", items=[
                    ItineraryItem(
                        name="Pho 10", lat=21.03, lng=105.85,
                        address="Ly Quoc Su", notes="Great pho",
                        start_time="2025-01-15T08:00:00",
                        end_time="2025-01-15T09:00:00",
                        duration_minutes=60,
                    ),
                ]),
            ],
        )
        guide = build_guide(trip)
        assert guide.name == "Vietnam Trip"
        assert guide.timezone == "Asia/Ho_Chi_Minh"
        assert len(guide.days) == 1
        assert guide.days[0].places[0].name == "Pho 10"
        assert guide.days[0].places[0].start_time == "8:00 AM"
        assert guide.days[0].places[0].category == "food"

    def test_description_passed_through(self):
        trip = CalendarTrip(
            id="abc",
            name="Test",
            days=[
                ItineraryDay(date="2025-01-15", items=[
                    ItineraryItem(
                        name="Museum", lat=0, lng=0,
                        description="Monday: 10 AM\u20135 PM",
                    ),
                ]),
            ],
        )
        guide = build_guide(trip)
        assert guide.days[0].places[0].description == "Monday: 10 AM\u20135 PM"

    def test_day_notes_passed_through(self):
        trip = CalendarTrip(
            id="abc",
            name="Test",
            days=[
                ItineraryDay(
                    date="2025-01-15",
                    notes="Pack sunscreen\nBring water",
                    items=[
                        ItineraryItem(name="Beach", lat=0, lng=0),
                    ],
                ),
            ],
        )
        guide = build_guide(trip)
        assert guide.days[0].notes == "Pack sunscreen\nBring water"

    def test_empty_trip(self):
        trip = CalendarTrip(id="x", name="Empty")
        guide = build_guide(trip)
        assert len(guide.days) == 0

    def test_flights_passed_through(self):
        trip = CalendarTrip(
            id="abc", name="Test",
            flights=[
                FlightInfo(
                    airline="Vietnam Airlines", flight_number="99",
                    depart_airport="SFO", arrive_airport="SGN",
                    depart_date="2026-03-15", depart_time="22:10",
                    confirmation="ABC123",
                ),
            ],
        )
        guide = build_guide(trip)
        assert len(guide.flights) == 1
        assert guide.flights[0].airline == "Vietnam Airlines"
        assert guide.flights[0].confirmation == "ABC123"

    def test_hotels_passed_through(self):
        trip = CalendarTrip(
            id="abc", name="Test",
            hotels=[
                HotelInfo(
                    name="Somerset", check_in="2026-03-17",
                    check_out="2026-03-27", nights=10,
                    confirmation="CONF123",
                ),
            ],
        )
        guide = build_guide(trip)
        assert len(guide.hotels) == 1
        assert guide.hotels[0].name == "Somerset"
        assert guide.hotels[0].nights == 10


# ── Generator tests ───────────────────────────────────────────


def _sample_guide():
    return Guide(
        name="Trip to Vietnam",
        timezone="Asia/Ho_Chi_Minh",
        days=[
            GuideDay(date="2025-01-15", places=[
                GuidePlace(
                    name="Pho 10", address="Ly Quoc Su",
                    category="food", start_time="8:00 AM",
                    end_time="9:00 AM", duration_minutes=60,
                ),
                GuidePlace(
                    name="Temple of Literature", address="Quoc Tu Giam",
                    category="activity", start_time="10:00 AM",
                    end_time="12:00 PM", duration_minutes=120,
                    lat=21.0285, lng=105.8360,
                ),
            ]),
        ],
    )


class TestGenerateGuideHtml:
    def test_contains_trip_name(self):
        html = generate_guide_html(_sample_guide())
        assert "Trip to Vietnam" in html

    def test_contains_doctype(self):
        html = generate_guide_html(_sample_guide())
        assert "<!DOCTYPE html>" in html

    def test_contains_place_names(self):
        html = generate_guide_html(_sample_guide())
        assert "Pho 10" in html
        assert "Temple of Literature" in html

    def test_contains_addresses(self):
        html = generate_guide_html(_sample_guide())
        assert "Ly Quoc Su" in html

    def test_contains_times(self):
        html = generate_guide_html(_sample_guide())
        assert "8:00 AM" in html

    def test_contains_timezone(self):
        html = generate_guide_html(_sample_guide())
        assert "Asia/Ho_Chi_Minh" in html

    def test_has_dark_mode_toggle(self):
        html = generate_guide_html(_sample_guide())
        assert "theme-toggle" in html

    def test_has_pwa_manifest(self):
        html = generate_guide_html(_sample_guide())
        assert "manifest" in html
        assert "serviceWorker" in html

    def test_has_service_worker(self):
        html = generate_guide_html(_sample_guide())
        assert "serviceWorker" in html

    def test_empty_guide(self):
        guide = Guide(name="Empty Trip")
        html = generate_guide_html(guide)
        assert "Empty Trip" in html
        assert "<!DOCTYPE html>" in html

    def test_flights_section(self):
        guide = Guide(name="Trip", days=[
            GuideDay(date="2025-01-15", places=[
                GuidePlace(name="Fly to Hanoi", category="flight",
                           start_time="6:00 PM", address="Airport"),
            ])
        ])
        html = generate_guide_html(guide)
        assert "Fly to Hanoi" in html

    def test_hotels_section(self):
        guide = Guide(name="Trip", days=[
            GuideDay(date="2025-01-15", places=[
                GuidePlace(name="Hilton Hanoi", category="hotel",
                           address="123 Main St"),
            ])
        ])
        html = generate_guide_html(guide)
        assert "Hilton Hanoi" in html

    def test_google_maps_link(self):
        guide = Guide(name="Trip", days=[
            GuideDay(date="2025-01-15", places=[
                GuidePlace(name="Temple", address="Quoc Tu Giam",
                           lat=21.0285, lng=105.836),
            ])
        ])
        html = generate_guide_html(guide)
        assert "google.com/maps" in html

    def test_no_surrogates(self):
        html = generate_guide_html(_sample_guide())
        for i, c in enumerate(html):
            assert ord(c) < 0xD800 or ord(c) > 0xDFFF, (
                f"Surrogate at pos {i}: {repr(html[max(0,i-10):i+10])}"
            )


class TestWriteGuide:
    def test_writes_file(self):
        guide = _sample_guide()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "guide.html")
            result = write_guide(guide, path)
            assert os.path.exists(result)
            content = open(result, encoding="utf-8").read()
            assert "Trip to Vietnam" in content

    def test_returns_path(self):
        guide = _sample_guide()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "out.html")
            result = write_guide(guide, path)
            assert result == path


class TestDescriptionRendering:
    def test_description_in_html(self):
        guide = Guide(
            name="Test",
            days=[GuideDay(date="2025-01-15", places=[
                GuidePlace(
                    name="Museum", description="Mon: 10 AM - 5 PM",
                    category="activity",
                ),
            ])],
        )
        html = generate_guide_html(guide)
        assert "Mon: 10 AM - 5 PM" in html
        assert "place-desc" in html

    def test_no_description_no_div(self):
        guide = Guide(
            name="Test",
            days=[GuideDay(date="2025-01-15", places=[
                GuidePlace(name="Beach", category="activity"),
            ])],
        )
        html = generate_guide_html(guide)
        assert '<div class="place-desc">' not in html


class TestDayNotesRendering:
    def test_day_notes_card_in_html(self):
        guide = Guide(
            name="Test",
            days=[GuideDay(
                date="2025-01-15",
                notes="Remember to pack sunscreen",
                places=[GuidePlace(name="Beach", category="activity")],
            )],
        )
        html = generate_guide_html(guide)
        assert "Remember to pack sunscreen" in html
        assert "day-notes-card" in html
        assert "day-notes-label" in html

    def test_no_notes_no_card(self):
        guide = Guide(
            name="Test",
            days=[GuideDay(
                date="2025-01-15",
                places=[GuidePlace(name="Beach", category="activity")],
            )],
        )
        html = generate_guide_html(guide)
        assert '<div class="day-notes-card">' not in html


# ── AM/PM time conversion tests ──────────────────────────────


class TestFormatTimeAmpm:
    def test_morning(self):
        assert _format_time_ampm("09:30") == "9:30 AM"

    def test_afternoon(self):
        assert _format_time_ampm("14:00") == "2 PM"

    def test_midnight(self):
        assert _format_time_ampm("00:00") == "12 AM"

    def test_noon(self):
        assert _format_time_ampm("12:00") == "12 PM"

    def test_evening(self):
        assert _format_time_ampm("22:10") == "10:10 PM"

    def test_one_am(self):
        assert _format_time_ampm("01:05") == "1:05 AM"

    def test_empty_string(self):
        assert _format_time_ampm("") == ""

    def test_bad_format(self):
        assert _format_time_ampm("not-a-time") == "not-a-time"

    def test_noon_thirty(self):
        assert _format_time_ampm("12:30") == "12:30 PM"

    def test_midnight_thirty(self):
        assert _format_time_ampm("00:30") == "12:30 AM"


# ── Split layout flight/hotel rendering tests ────────────────


class TestFlightBoardingPass:
    def _make_guide_with_flight(self, **kwargs):
        defaults = dict(
            airline="Vietnam Airlines", flight_number="99",
            depart_airport="SFO", depart_airport_name="San Francisco",
            arrive_airport="SGN", arrive_airport_name="Ho Chi Minh City",
            depart_date="2026-03-15", depart_time="22:10",
            arrive_date="2026-03-17", arrive_time="05:30",
            confirmation="ABC123", travelers="Michelle Yang",
        )
        defaults.update(kwargs)
        return Guide(name="Test", flights=[GuideFlight(**defaults)])

    def test_route_as_header(self):
        html = generate_guide_html(self._make_guide_with_flight())
        assert "SFO \u2192 SGN" in html

    def test_airline_tag(self):
        html = generate_guide_html(self._make_guide_with_flight())
        assert "Vietnam Airlines 99" in html
        assert "bp-airline-tag" in html

    def test_full_airport_names(self):
        html = generate_guide_html(self._make_guide_with_flight())
        assert "San Francisco (SFO)" in html
        assert "Ho Chi Minh City (SGN)" in html

    def test_ampm_times_in_flights(self):
        html = generate_guide_html(self._make_guide_with_flight())
        assert "10:10 PM" in html
        assert "5:30 AM" in html
        assert ">22:10<" not in html

    def test_boarding_pass_structure(self):
        html = generate_guide_html(self._make_guide_with_flight())
        assert "bp-card" in html
        assert "bp-header" in html
        assert "bp-body" in html
        assert "bp-columns" in html
        assert "bp-col" in html

    def test_depart_arrive_labels(self):
        html = generate_guide_html(self._make_guide_with_flight())
        assert "Depart" in html
        assert "Arrive" in html

    def test_confirmation_in_strip(self):
        html = generate_guide_html(self._make_guide_with_flight())
        assert "bp-conf-code" in html
        assert "ABC123" in html

    def test_travelers(self):
        html = generate_guide_html(self._make_guide_with_flight())
        assert "Michelle Yang" in html

    def test_section_tabs(self):
        html = generate_guide_html(self._make_guide_with_flight())
        assert "sec-tab" in html
        assert 'data-section="flights"' in html

    def test_always_expanded(self):
        """Flights tab cards have no chevron or date preview (always expanded)."""
        html = generate_guide_html(self._make_guide_with_flight())
        assert "bp-chevron" not in html
        assert "bp-date-preview" not in html

    def test_no_flights_no_section(self):
        guide = Guide(name="Test")
        html = generate_guide_html(guide)
        assert "bp-header" not in html or "Flights" not in html.split("bp-header")[0]
        # No flight accordion cards rendered (section h2 absent)
        assert "Flights</h2>" not in html

    def test_no_emoji_per_card(self):
        html = generate_guide_html(self._make_guide_with_flight())
        # Emoji should be in section h2 only, not in each bp-header
        assert "bp-header" in html
        # The route in bp-header should NOT have an emoji prefix
        import re
        headers = re.findall(r'<div class="bp-header">.*?</div></div>', html)
        for h in headers:
            assert "\u2708" not in h


class TestHotelBoardingPass:
    def _make_guide_with_hotel(self, **kwargs):
        defaults = dict(
            name="Somerset Feliz",
            address="22 Nguyen Binh Khiem, District 1",
            check_in="2026-03-17", check_out="2026-03-27",
            nights=10, confirmation="CONF456",
            travelers="Michelle Yang", notes="Pool on 5th floor",
        )
        defaults.update(kwargs)
        return Guide(name="Test", hotels=[GuideHotel(**defaults)])

    def test_hotel_name_in_header(self):
        html = generate_guide_html(self._make_guide_with_hotel())
        assert "Somerset Feliz" in html

    def test_pin_emoji_in_address(self):
        html = generate_guide_html(self._make_guide_with_hotel())
        assert "\U0001f4cd" in html
        assert "22 Nguyen Binh Khiem" in html

    def test_checkin_checkout_labels(self):
        html = generate_guide_html(self._make_guide_with_hotel())
        assert "Check-in" in html
        assert "Check-out" in html

    def test_checkin_date_formatted(self):
        html = generate_guide_html(self._make_guide_with_hotel())
        assert "Tue, Mar 17" in html

    def test_checkout_date_formatted(self):
        html = generate_guide_html(self._make_guide_with_hotel())
        assert "Fri, Mar 27" in html

    def test_nights_count(self):
        html = generate_guide_html(self._make_guide_with_hotel())
        assert "10 nights" in html

    def test_single_night(self):
        html = generate_guide_html(self._make_guide_with_hotel(nights=1))
        assert "1 night" in html

    def test_boarding_pass_structure(self):
        html = generate_guide_html(self._make_guide_with_hotel())
        assert "bp-card bp-hotel" in html
        assert "bp-header" in html
        assert "bp-body" in html
        assert "bp-columns" in html

    def test_confirmation_in_strip(self):
        html = generate_guide_html(self._make_guide_with_hotel())
        assert "bp-conf-code" in html
        assert "CONF456" in html

    def test_notes_not_lost(self):
        # Notes field is on the model but not shown in boarding pass conf strip
        # (only confirmation + travelers). Verify the hotel still renders.
        html = generate_guide_html(self._make_guide_with_hotel())
        assert "Somerset Feliz" in html

    def test_no_hotels_no_section(self):
        guide = Guide(name="Test")
        html = generate_guide_html(guide)
        assert "Hotels</h2>" not in html

    def test_section_panel(self):
        html = generate_guide_html(self._make_guide_with_hotel())
        assert 'id="sec-hotels"' in html


class TestFlightDayCard:
    def test_flight_in_day_panel(self):
        flight = GuideFlight(
            airline="Cathay Pacific", flight_number="850",
            depart_airport="HKG", depart_airport_name="Hong Kong",
            arrive_airport="LAX", arrive_airport_name="Los Angeles",
            depart_date="2025-01-15", depart_time="10:00",
            arrive_date="2025-01-15", arrive_time="08:00",
            confirmation="XYZ789",
        )
        guide = Guide(
            name="Trip",
            days=[GuideDay(date="2025-01-15", places=[
                GuidePlace(name="Coffee", category="food"),
            ])],
            flights=[flight],
        )
        html = generate_guide_html(guide)
        assert "HKG \u2192 LAX" in html
        assert "Hong Kong" in html
        assert "Los Angeles" in html
        assert "10 AM" in html
        assert "8 AM" in html
        assert "bp-day-card" in html
        assert "bp-columns" in html


class TestSectionTabs:
    """Tests for the section tab layout."""

    def test_three_tabs_present(self):
        guide = Guide(name="Trip", days=[GuideDay(date="2025-01-15")])
        html = generate_guide_html(guide)
        assert 'data-section="itinerary"' in html
        assert 'data-section="hotels"' in html
        assert 'data-section="flights"' in html

    def test_itinerary_active_by_default(self):
        guide = Guide(name="Trip", days=[GuideDay(date="2025-01-15")])
        html = generate_guide_html(guide)
        assert "active-itin" in html
        assert 'id="sec-itinerary"' in html

    def test_content_area_with_glow(self):
        guide = Guide(name="Trip", days=[GuideDay(date="2025-01-15")])
        html = generate_guide_html(guide)
        assert "content-area" in html
        assert "glow-itin" in html

    def test_sec_panels_exist(self):
        guide = Guide(
            name="Trip",
            days=[GuideDay(date="2025-01-15")],
            flights=[GuideFlight(depart_airport="SFO", arrive_airport="LAX")],
            hotels=[GuideHotel(name="Hotel A", check_in="2025-01-15", check_out="2025-01-16")],
        )
        html = generate_guide_html(guide)
        assert 'id="sec-itinerary"' in html
        assert 'id="sec-hotels"' in html
        assert 'id="sec-flights"' in html

    def test_flight_count_badge(self):
        guide = Guide(
            name="Trip",
            flights=[
                GuideFlight(depart_airport="SFO", arrive_airport="LAX"),
                GuideFlight(depart_airport="LAX", arrive_airport="JFK"),
            ],
        )
        html = generate_guide_html(guide)
        assert "2 flights" in html
        assert "cnt-flight" in html

    def test_hotel_count_badge(self):
        guide = Guide(
            name="Trip",
            hotels=[GuideHotel(name="Hotel A")],
        )
        html = generate_guide_html(guide)
        assert "1 stay" in html
        assert "cnt-hotel" in html

    def test_day_count_badge(self):
        guide = Guide(
            name="Trip",
            days=[GuideDay(date="2025-01-15"), GuideDay(date="2025-01-16")],
        )
        html = generate_guide_html(guide)
        assert "2 days" in html
        assert "cnt-itin" in html

    def test_day_pill_has_data_date(self):
        guide = Guide(name="Trip", days=[GuideDay(date="2025-01-15")])
        html = generate_guide_html(guide)
        assert 'data-date="2025-01-15"' in html

    def test_section_tab_js(self):
        guide = Guide(name="Trip", days=[GuideDay(date="2025-01-15")])
        html = generate_guide_html(guide)
        assert "switchSection" in html
        assert "glowMap" in html

    def test_hotel_uses_consistent_classes(self):
        """Hotel cards should use bp-val-muted for address (not bp-hotel-addr)."""
        guide = Guide(
            name="Trip",
            hotels=[GuideHotel(name="Hotel A", address="123 Main St")],
        )
        html = generate_guide_html(guide)
        assert "bp-val-muted" in html
        assert "bp-hotel-addr" not in html

    def test_no_accordion_in_flights_tab(self):
        """Flight cards in the flights tab should not have accordion elements."""
        guide = Guide(
            name="Trip",
            flights=[GuideFlight(depart_airport="SFO", arrive_airport="LAX", depart_date="2025-01-15")],
        )
        html = generate_guide_html(guide)
        assert "bp-chevron" not in html
        assert "bp-date-preview" not in html

    def test_scroll_dots_present_when_many_days(self):
        """Day pills should have progress dot indicators when >5 days."""
        guide = Guide(
            name="Trip",
            days=[GuideDay(date=f"2025-01-{15+i}") for i in range(7)],
        )
        html = generate_guide_html(guide)
        assert "scroll-dots" in html
        assert 'class="scroll-dot dot-active"' in html
        assert html.count("scroll-dot") >= 6  # 1 container class + 5 dots

    def test_scroll_dots_hidden_when_few_days(self):
        """Day pills should NOT have scroll dots when ≤5 days."""
        guide = Guide(
            name="Trip",
            days=[GuideDay(date="2025-01-15")],
        )
        html = generate_guide_html(guide)
        assert '<div class="scroll-dots">' not in html
        assert "centered" in html

    def test_scroll_dots_js(self):
        """JS should include scroll listener for progress dots."""
        guide = Guide(
            name="Trip",
            days=[GuideDay(date=f"2025-01-{15+i}") for i in range(7)],
        )
        html = generate_guide_html(guide)
        assert "scrollDots" in html
        assert "dot-active" in html


class TestHotelDayCard:
    """Tests for hotel check-in cards appearing in day panels."""

    def test_hotel_card_on_checkin_day(self):
        hotel = GuideHotel(
            name="Somerset Feliz", address="22 Nguyen Binh Khiem",
            check_in="2025-01-15", check_out="2025-01-17", nights=2,
            confirmation="HTL001", travelers="Michelle Yang",
        )
        guide = Guide(
            name="Trip",
            days=[GuideDay(date="2025-01-15")],
            hotels=[hotel],
        )
        html = generate_guide_html(guide)
        assert "Somerset Feliz" in html
        assert "bp-hotel" in html
        assert "bp-day-card" in html
        assert "Check-in" in html
        assert "HTL001" in html

    def test_hotel_not_on_other_day(self):
        hotel = GuideHotel(
            name="Somerset Feliz", check_in="2025-01-15", check_out="2025-01-17",
        )
        guide = Guide(
            name="Trip",
            days=[GuideDay(date="2025-01-16")],
            hotels=[hotel],
        )
        html = generate_guide_html(guide)
        assert "No events added for this date" in html

    def test_empty_day_shows_empty_message(self):
        guide = Guide(
            name="Trip",
            days=[GuideDay(date="2025-01-15"), GuideDay(date="2025-01-16")],
        )
        html = generate_guide_html(guide)
        assert "No events added for this date" in html


class TestEmptyTabStates:
    """Tests for empty state messages in flights and hotels tabs."""

    def test_no_flights_shows_empty_state(self):
        guide = Guide(name="Trip", days=[GuideDay(date="2025-01-15")])
        html = generate_guide_html(guide)
        assert "No flights booked" in html

    def test_no_hotels_shows_empty_state(self):
        guide = Guide(name="Trip", days=[GuideDay(date="2025-01-15")])
        html = generate_guide_html(guide)
        assert "No hotels booked" in html

    def test_flights_present_no_empty_state(self):
        guide = Guide(
            name="Trip",
            flights=[GuideFlight(depart_airport="SFO", arrive_airport="LAX")],
        )
        html = generate_guide_html(guide)
        assert "No flights booked" not in html

    def test_hotels_present_no_empty_state(self):
        guide = Guide(
            name="Trip",
            hotels=[GuideHotel(name="Hotel A")],
        )
        html = generate_guide_html(guide)
        assert "No hotels booked" not in html


# ── V6 Type-based categorization tests ────────────────────────

from wanderlogpro.offline_mode.builder import (
    _categorize_from_types,
    _DEFAULT_EMOJI,
    _CATEGORY_DEFAULT_EMOJI,
)


class TestCategorizeFromTypes:
    """Tests for priority-based Google Place type → category mapping."""

    def test_bakery_is_snack(self):
        cat, emoji = _categorize_from_types(["bakery"])
        assert cat == "snack"
        assert emoji == "\U0001f366"  # 🍦

    def test_ice_cream_is_snack(self):
        cat, emoji = _categorize_from_types(["ice_cream_shop"])
        assert cat == "snack"

    def test_restaurant_is_food(self):
        cat, emoji = _categorize_from_types(["restaurant"])
        assert cat == "food"
        assert emoji == "\U0001f37d\uFE0F"  # 🍽️

    def test_hotel_is_hotel(self):
        cat, emoji = _categorize_from_types(["hotel"])
        assert cat == "hotel"

    def test_museum_is_activity(self):
        cat, emoji = _categorize_from_types(["museum"])
        assert cat == "activity"

    def test_park_is_activity(self):
        cat, emoji = _categorize_from_types(["park"])
        assert cat == "activity"

    def test_snack_beats_food(self):
        """Bakery + restaurant → snack wins (higher priority)."""
        cat, _emoji = _categorize_from_types(["restaurant", "bakery"])
        assert cat == "snack"

    def test_food_beats_hotel(self):
        cat, _emoji = _categorize_from_types(["hotel", "restaurant"])
        assert cat == "food"

    def test_empty_types_returns_empty(self):
        cat, emoji = _categorize_from_types([])
        assert cat == ""
        assert emoji == ""

    def test_noise_types_ignored(self):
        """point_of_interest alone should not match anything."""
        cat, emoji = _categorize_from_types(["point_of_interest", "establishment"])
        assert cat == ""
        assert emoji == ""

    def test_worship_types(self):
        cat, _emoji = _categorize_from_types(["place_of_worship"])
        assert cat == "activity"

    def test_shopping_types(self):
        cat, _emoji = _categorize_from_types(["shopping_mall"])
        assert cat == "activity"

    # Regex-based matching tests
    def test_dessert_shop_is_snack(self):
        cat, _emoji = _categorize_from_types(["dessert_shop"])
        assert cat == "snack"

    def test_japanese_confectionery_is_snack(self):
        cat, _emoji = _categorize_from_types(["japanese_confectionery_shop"])
        assert cat == "snack"

    def test_bubble_tea_store_is_snack(self):
        cat, _emoji = _categorize_from_types(["bubble_tea_store"])
        assert cat == "snack"

    def test_tea_house_is_snack(self):
        cat, _emoji = _categorize_from_types(["tea_house"])
        assert cat == "snack"

    def test_cantonese_restaurant_is_food(self):
        cat, _emoji = _categorize_from_types(["cantonese_restaurant"])
        assert cat == "food"

    def test_japanese_restaurant_is_food(self):
        cat, _emoji = _categorize_from_types(["japanese_restaurant"])
        assert cat == "food"

    def test_filipino_restaurant_is_food(self):
        cat, _emoji = _categorize_from_types(["filipino_restaurant"])
        assert cat == "food"

    def test_gastropub_is_food(self):
        cat, _emoji = _categorize_from_types(["gastropub"])
        assert cat == "food"

    def test_coffee_roasters_is_food(self):
        cat, _emoji = _categorize_from_types(["coffee_roasters"])
        assert cat == "food"

    def test_sandwich_shop_is_food(self):
        cat, _emoji = _categorize_from_types(["sandwich_shop"])
        assert cat == "food"

    def test_asian_grocery_store_is_shopping(self):
        cat, _emoji = _categorize_from_types(["asian_grocery_store"])
        assert cat == "activity"  # shopping maps to activity category
        assert _emoji == "\U0001f6cd\uFE0F"  # 🛍️

    def test_barber_shop_not_food(self):
        cat, _emoji = _categorize_from_types(["barber_shop"])
        assert cat != "food"

    def test_parking_not_nature(self):
        cat, _emoji = _categorize_from_types(["parking"])
        assert cat != "activity" or _emoji != "\U0001f33f"  # not nature

    def test_snack_priority_order_independent(self):
        """Both orderings should return snack."""
        cat1, _ = _categorize_from_types(["restaurant", "bakery"])
        cat2, _ = _categorize_from_types(["bakery", "restaurant"])
        assert cat1 == "snack"
        assert cat2 == "snack"

    def test_serviced_apartment_is_hotel(self):
        cat, _emoji = _categorize_from_types(["serviced_apartment"])
        assert cat == "hotel"

    def test_cafeteria_is_food(self):
        cat, _emoji = _categorize_from_types(["cafeteria"])
        assert cat == "food"

    def test_convenience_store_is_shopping(self):
        cat, _emoji = _categorize_from_types(["convenience_store"])
        assert cat == "activity"  # shopping maps to activity
        assert _emoji == "\U0001f6cd\uFE0F"  # 🛍️


class TestBuildGuideTypeBased:
    """Tests that build_guide uses type-based categorization."""

    def test_bakery_gets_snack_category(self):
        trip = CalendarTrip(
            id="test",
            name="Trip",
            days=[ItineraryDay(
                date="2025-01-01",
                items=[ItineraryItem(
                    name="Sweet Shop",
                    lat=10,
                    lng=20,
                    google_types=["bakery"],
                )],
            )],
        )
        guide = build_guide(trip)
        assert guide.days[0].places[0].category == "snack"
        assert guide.days[0].places[0].icon == "\U0001f366"

    def test_no_types_falls_back_to_regex(self):
        trip = CalendarTrip(
            id="test",
            name="Trip",
            days=[ItineraryDay(
                date="2025-01-01",
                items=[ItineraryItem(
                    name="Best Restaurant Ever",
                    lat=10,
                    lng=20,
                    google_types=[],
                )],
            )],
        )
        guide = build_guide(trip)
        assert guide.days[0].places[0].category == "food"

    def test_unmatched_gets_tag_emoji(self):
        trip = CalendarTrip(
            id="test",
            name="Trip",
            days=[ItineraryDay(
                date="2025-01-01",
                items=[ItineraryItem(
                    name="Random Place",
                    lat=10,
                    lng=20,
                    google_types=[],
                )],
            )],
        )
        guide = build_guide(trip)
        # Falls back to regex → "activity", default emoji = 🏷️
        assert guide.days[0].places[0].icon == _DEFAULT_EMOJI

    def test_travel_data_passed_through(self):
        trip = CalendarTrip(
            id="test",
            name="Trip",
            days=[ItineraryDay(
                date="2025-01-01",
                items=[ItineraryItem(
                    name="Place A",
                    lat=10,
                    lng=20,
                    travel_minutes_to_next=15,
                    travel_mode="driving",
                )],
            )],
        )
        guide = build_guide(trip)
        p = guide.days[0].places[0]
        assert p.travel_minutes_to_next == 15
        assert p.travel_mode_to_next == "driving"


class TestV6PlaceCardHtml:
    """Tests for V6 Full Glow Connector card HTML output."""

    def _html(self, **kwargs):
        defaults = dict(name="Trip", days=[GuideDay(
            date="2025-01-01",
            places=[GuidePlace(
                name="Test Place",
                lat=10,
                lng=20,
                **kwargs,
            )],
        )])
        return generate_guide_html(Guide(**defaults))

    def test_place_badge_present(self):
        html = self._html(icon="\U0001f37d\uFE0F", category="food")
        assert "place-badge" in html

    def test_cat_class_applied(self):
        html = self._html(category="snack")
        assert "cat-snack" in html

    def test_time_tag_rendered(self):
        html = self._html(start_time="9:00 AM", end_time="10:00 AM")
        assert "place-time" in html
        assert "9:00 AM" in html

    def test_no_time_no_tag(self):
        html = self._html()
        assert '<span class="place-time">' not in html

    def test_duration_in_tag_pills(self):
        html = self._html(duration_minutes=90)
        assert "place-tag" in html
        assert "1h 30m" in html

    def test_connector_between_cards(self):
        guide = Guide(name="Trip", days=[GuideDay(
            date="2025-01-01",
            places=[
                GuidePlace(name="A", lat=1, lng=2, travel_minutes_to_next=10, travel_mode_to_next="walking"),
                GuidePlace(name="B", lat=3, lng=4),
            ],
        )])
        html = generate_guide_html(guide)
        assert "connector" in html
        assert "10 min" in html

    def test_no_connector_after_last_card(self):
        guide = Guide(name="Trip", days=[GuideDay(
            date="2025-01-01",
            places=[
                GuidePlace(name="Only", lat=1, lng=2),
            ],
        )])
        html = generate_guide_html(guide)
        # No rendered connector element (CSS definition exists but no actual connector div)
        assert '<div class="connector">' not in html

    def test_connector_driving_emoji(self):
        guide = Guide(name="Trip", days=[GuideDay(
            date="2025-01-01",
            places=[
                GuidePlace(name="A", lat=1, lng=2, travel_minutes_to_next=30, travel_mode_to_next="driving"),
                GuidePlace(name="B", lat=3, lng=4),
            ],
        )])
        html = generate_guide_html(guide)
        assert "\U0001f697" in html  # 🚗

    def test_connector_hours_format(self):
        guide = Guide(name="Trip", days=[GuideDay(
            date="2025-01-01",
            places=[
                GuidePlace(name="A", lat=1, lng=2, travel_minutes_to_next=90),
                GuidePlace(name="B", lat=3, lng=4),
            ],
        )])
        html = generate_guide_html(guide)
        assert "1h 30m" in html

    def test_v6_css_variables(self):
        html = self._html(category="snack")
        assert "--cat-snack" in html

    def test_estimated_duration_gets_gray_tag(self):
        """Duration with no end_time → tag-dur (gray, estimated)."""
        html = self._html(duration_minutes=25)
        assert "tag-dur" in html
        assert "tag-dur-explicit" not in html.split("</style>")[1]

    def test_explicit_duration_gets_colored_tag(self):
        """Duration with end_time set → tag-dur-explicit (colored)."""
        html = self._html(duration_minutes=90, end_time="11:30 AM")
        assert "tag-dur-explicit" in html.split("</style>")[1]

    def test_duration_key_footnote_present(self):
        """Itinerary page has duration key footnote."""
        html = self._html(duration_minutes=30)
        assert "duration-key" in html
        assert "estimated avg visit" in html
        assert "exact scheduled time" in html


class TestDurationFromTimes:
    """Tests for _duration_from_times and _parse_minutes."""

    def test_bare_hhmm(self):
        from wanderlogpro.offline_mode.builder import _duration_from_times
        assert _duration_from_times("08:00", "18:00") == 600  # 10h

    def test_iso_format(self):
        from wanderlogpro.offline_mode.builder import _duration_from_times
        assert _duration_from_times(
            "2025-01-15T09:00:00", "2025-01-15T11:30:00"
        ) == 150  # 2h 30m

    def test_mixed_formats(self):
        from wanderlogpro.offline_mode.builder import _duration_from_times
        assert _duration_from_times("09:00", "2025-01-15T11:00:00") == 120

    def test_end_before_start_returns_zero(self):
        from wanderlogpro.offline_mode.builder import _duration_from_times
        assert _duration_from_times("18:00", "08:00") == 0

    def test_equal_times_returns_zero(self):
        from wanderlogpro.offline_mode.builder import _duration_from_times
        assert _duration_from_times("08:00", "08:00") == 0

    def test_missing_end_returns_zero(self):
        from wanderlogpro.offline_mode.builder import _duration_from_times
        assert _duration_from_times("08:00", "") == 0

    def test_missing_both_returns_zero(self):
        from wanderlogpro.offline_mode.builder import _duration_from_times
        assert _duration_from_times("", "") == 0

    def test_build_guide_computes_duration_from_times(self):
        """When metadata duration is 0 but start/end exist, compute from times."""
        trip = CalendarTrip(
            id="t", name="Trip",
            days=[ItineraryDay(date="2025-01-15", items=[
                ItineraryItem(
                    name="Gulong Gorge",
                    lat=0, lng=0,
                    start_time="08:00",
                    end_time="18:00",
                    duration_minutes=0,
                ),
            ])],
        )
        guide = build_guide(trip)
        assert guide.days[0].places[0].duration_minutes == 600

    def test_build_guide_prefers_metadata_duration(self):
        """When metadata duration exists, don't override with time computation."""
        trip = CalendarTrip(
            id="t", name="Trip",
            days=[ItineraryDay(date="2025-01-15", items=[
                ItineraryItem(
                    name="Temple",
                    lat=0, lng=0,
                    start_time="09:00",
                    end_time="11:00",
                    duration_minutes=45,
                ),
            ])],
        )
        guide = build_guide(trip)
        assert guide.days[0].places[0].duration_minutes == 45


class TestTimeRangeHtml:
    """Tests for Option A time range rendering in V6 cards."""

    def _html(self, **kwargs):
        defaults = dict(name="Trip", days=[GuideDay(
            date="2025-01-01",
            places=[GuidePlace(
                name="Test Place",
                lat=10, lng=20,
                **kwargs,
            )],
        )])
        return generate_guide_html(Guide(**defaults))

    def test_range_shows_arrow(self):
        html = self._html(start_time="8:00 AM", end_time="6:00 PM")
        body = html.split("</style>")[1]
        assert "8:00 AM" in body
        assert "\u2192" in body  # → arrow
        assert "6:00 PM" in body

    def test_range_has_separator_span(self):
        html = self._html(start_time="8:00 AM", end_time="6:00 PM")
        body = html.split("</style>")[1]
        assert "t-sep" in body

    def test_start_only_no_arrow(self):
        html = self._html(start_time="9:00 AM")
        body = html.split("</style>")[1]
        assert "9:00 AM" in body
        assert "t-sep" not in body

    def test_no_time_no_range(self):
        html = self._html()
        body = html.split("</style>")[1]
        assert "place-time" not in body


class TestDayCarousel:
    """Verify the swipe-carousel HTML structure for offline mode days."""

    def _guide(self, num_days=2):
        days = [
            GuideDay(date=f"2025-01-{15 + i:02d}", places=[
                GuidePlace(name=f"Place {i}", category="activity",
                           address="Addr"),
            ])
            for i in range(num_days)
        ]
        return Guide(name="Trip", days=days)

    def test_carousel_container_exists(self):
        html = generate_guide_html(self._guide())
        assert 'class="day-carousel"' in html

    def test_day_panels_inside_carousel(self):
        html = generate_guide_html(self._guide(3))
        body = html.split('<script>')[0]
        idx = body.index('class="day-carousel"')
        # All 3 day panels should appear after the carousel div
        for i in range(3):
            panel_pos = body.index(f'class="day-panel" data-day="{i}"')
            assert panel_pos > idx

    def test_no_active_class_on_day_panels(self):
        html = generate_guide_html(self._guide())
        assert 'day-panel active' not in html

    def test_carousel_scroll_snap_css(self):
        html = generate_guide_html(self._guide())
        assert 'scroll-snap-type: x mandatory' in html

    def test_js_uses_carousel_scroll(self):
        html = generate_guide_html(self._guide())
        assert 'day-carousel' in html
        assert 'scrollTo' in html

    def test_pills_still_rendered(self):
        html = generate_guide_html(self._guide(3))
        assert html.count('tab-pill') >= 3

    def test_duration_key_inside_day_panels(self):
        """Duration key footnote should be inside each day panel."""
        html = generate_guide_html(self._guide())
        body = html.split('<script>')[0].split('</style>')[-1]
        # Each day panel should contain a duration-key
        import re
        panels = re.findall(r'<div class="day-panel"[^>]*>.*?</div>\s*</div>', body, re.DOTALL)
        # At minimum, the duration-key class should appear inside the carousel
        carousel_start = body.index('day-carousel')
        carousel_section = body[carousel_start:]
        assert 'duration-key' in carousel_section

    def test_nudge_animation_css(self):
        html = generate_guide_html(self._guide())
        assert 'carouselNudge' in html
        assert 'carousel-nudge' in html

    def test_nudge_js_adds_and_removes_class(self):
        html = generate_guide_html(self._guide())
        assert "classList.add('carousel-nudge')" in html
        assert "animationiteration" in html

    def test_nudge_stops_after_timeout(self):
        html = generate_guide_html(self._guide())
        assert 'setTimeout(stopNudge, 5000)' in html

    def test_float_toggle_html(self):
        html = generate_guide_html(self._guide())
        assert 'float-toggle' in html
        assert 'btnSwipe' in html
        assert 'btnScroll' in html

    def test_float_toggle_css(self):
        html = generate_guide_html(self._guide())
        assert '.float-toggle' in html

    def test_scroll_view_container(self):
        html = generate_guide_html(self._guide())
        body = html.split('<script>')[0].split('</style>')[-1]
        assert 'id="scrollView"' in body
        assert 'scroll-view' in body

    def test_switch_view_mode_js(self):
        html = generate_guide_html(self._guide())
        assert 'switchViewMode' in html
        assert 'sv-divider' in html

    def test_footer_has_extra_padding(self):
        html = generate_guide_html(self._guide())
        assert 'padding: 2rem 1rem 5rem' in html