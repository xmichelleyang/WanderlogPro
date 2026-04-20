"""Tests for the CLI's /view → /plan URL resolution helper."""

from unittest.mock import patch

import pytest

from wanderlogpro.cli import _resolve_trip_url


@pytest.fixture
def tty_stdin():
    """Pretend stdin is a TTY so the prompt path is exercised."""
    with patch("wanderlogpro.cli.sys.stdin.isatty", return_value=True):
        yield


@pytest.fixture
def non_tty_stdin():
    with patch("wanderlogpro.cli.sys.stdin.isatty", return_value=False):
        yield


class TestResolveTripUrl:
    def test_plan_url_passthrough_no_prompt(self, tty_stdin):
        url = "https://wanderlog.com/plan/abc123/my-trip/shared"
        # If a prompt were issued we'd hang; patch to fail loudly if called.
        with patch("wanderlogpro.cli.click.prompt", side_effect=AssertionError("should not prompt")):
            assert _resolve_trip_url(url) == url

    def test_non_wanderlog_url_passthrough(self, tty_stdin):
        url = "https://example.com/something"
        with patch("wanderlogpro.cli.click.prompt", side_effect=AssertionError("should not prompt")):
            assert _resolve_trip_url(url) == url

    def test_view_url_blank_input_keeps_view(self, tty_stdin):
        url = "https://wanderlog.com/view/abc123/my-trip"
        with patch("wanderlogpro.cli.click.prompt", return_value=""):
            assert _resolve_trip_url(url) == url

    def test_view_url_pasted_plan_replaces(self, tty_stdin):
        view = "https://wanderlog.com/view/abc123/my-trip"
        plan = "https://wanderlog.com/plan/abc123/my-trip/shared"
        with patch("wanderlogpro.cli.click.prompt", return_value=plan):
            assert _resolve_trip_url(view) == plan

    def test_view_url_pasted_whitespace_kept_as_view(self, tty_stdin):
        url = "https://wanderlog.com/view/abc123/my-trip"
        with patch("wanderlogpro.cli.click.prompt", return_value="   "):
            assert _resolve_trip_url(url) == url

    def test_view_url_invalid_paste_falls_back(self, tty_stdin):
        url = "https://wanderlog.com/view/abc123/my-trip"
        with patch("wanderlogpro.cli.click.prompt", return_value="https://example.com/not-wanderlog"):
            assert _resolve_trip_url(url) == url

    def test_non_tty_stdin_skips_prompt(self, non_tty_stdin):
        url = "https://wanderlog.com/view/abc123/my-trip"
        with patch("wanderlogpro.cli.click.prompt", side_effect=AssertionError("should not prompt")):
            assert _resolve_trip_url(url) == url
