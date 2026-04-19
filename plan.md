# Plan: Timezone Note in Dry-Run Preview

## What to do
When the dry-run preview is generated, compare the trip's destination timezone against the local system timezone. If they differ, show a note like:
> ⚠️ Times shown in Asia/Ho_Chi_Minh (destination) — 14 hours ahead of your timezone (America/Los_Angeles)

Calculate the hour offset between the two timezones for the trip dates. No times are shifted in the preview.

## Changes
1. `preview.py` — `generate_preview_html()` and `open_preview()` accept destination `timezone` str; uses `zoneinfo.ZoneInfo` to compute hour difference vs local tz; renders a styled note banner if they differ
2. `cli.py` — Pass `trip.timezone` to `open_preview()` in both `calendar` and `all` commands
3. Tests — Verify banner text includes destination tz, hour difference, and is absent when same/empty
