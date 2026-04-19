"""CLI entrypoint for WanderlogPro."""

import re
from pathlib import Path

import click

from wanderlogpro.map_export.kml_export import export_trip_to_kml
from wanderlogpro.map_export.scraper import fetch_trip


@click.group()
def main() -> None:
    """WanderlogPro — Export Wanderlog trips to Google My Maps & Google Calendar."""


@main.command()
@click.argument("trip_url")
@click.option(
    "--output", "-o",
    default=None,
    help="Output KML file path. Defaults to <trip-id>.kml",
)
@click.option(
    "--cookie", "-c",
    default=None,
    help="Session cookie for private trips (from browser DevTools).",
)
def export(trip_url: str, output: str | None, cookie: str | None) -> None:
    """Export a Wanderlog trip to a KML file."""
    click.echo("🗺️  Fetching trip from Wanderlog...")

    try:
        trip = fetch_trip(trip_url, cookie=cookie)
    except ValueError as e:
        raise click.ClickException(str(e))
    except PermissionError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to fetch trip: {e}")

    total_places = sum(len(pl.places) for pl in trip.place_lists)
    click.echo(f"✅ Found trip: {trip.name}")
    click.echo(f"   {len(trip.place_lists)} lists, {total_places} places")

    if not total_places:
        raise click.ClickException("No places found in this trip.")

    # Determine output path
    if output is None:
        safe_name = re.sub(r'[^\w\s-]', '', trip.name).strip().replace(' ', '-').lower()
        output = f"{safe_name or trip.id}.kml"
    output_path = Path(output)

    click.echo("📝 Generating KML with styled layers...")
    export_trip_to_kml(trip, output_path)

    click.echo(f"🎉 Exported to {output_path}")
    click.echo("\nImport into Google My Maps at https://mymaps.google.com")
    for pl in trip.place_lists:
        if pl.places:
            icon_label = f" [{pl.icon}]" if pl.icon else ""
            click.echo(f"   📂 {pl.name}{icon_label} — {len(pl.places)} places")


@main.command()
@click.argument("trip_url")
@click.option(
    "--cookie", "-c",
    default=None,
    help="Session cookie for private trips (from browser DevTools).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview events in a week-view HTML page without creating them.",
)
def calendar(trip_url: str, cookie: str | None, dry_run: bool) -> None:
    """Export a Wanderlog trip itinerary to Google Calendar.

    Creates a dedicated sub-calendar with each itinerary item as an event.
    Timed events (with specific entry times) are prefixed with [!] in the title.
    """
    from wanderlogpro.calendar_export.scraper import fetch_itinerary
    from wanderlogpro.calendar_export.gcal_export import export_trip_to_gcal, preview_trip_events

    click.echo("🗺️  Fetching itinerary from Wanderlog...")

    try:
        trip = fetch_itinerary(trip_url, cookie=cookie)
    except ValueError as e:
        raise click.ClickException(str(e))
    except PermissionError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to fetch itinerary: {e}")

    total_items = sum(len(day.items) for day in trip.days)
    click.echo(f"✅ Found trip: {trip.name}")
    click.echo(f"   {len(trip.days)} days, {total_items} itinerary items")
    if trip.timezone:
        click.echo(f"   🌍 Detected timezone: {trip.timezone}")

    if not total_items:
        raise click.ClickException(
            "No itinerary items found. Make sure your trip has items "
            "added to the day-by-day itinerary (not just lists)."
        )

    if dry_run:
        from wanderlogpro.calendar_export.preview import open_preview

        click.echo("🔍 Generating dry-run preview...")
        day_events = preview_trip_events(trip)
        path = open_preview(trip.name, day_events, trip.timezone)
        total_events = sum(len(evts) for _, evts in day_events)
        click.echo(f"📄 Preview opened in browser ({total_events} events)")
        click.echo(f"   File: {path}")
        return

    click.echo("📅 Signing in to Google Calendar...")

    try:
        calendar_id, event_count = export_trip_to_gcal(trip)
    except Exception as e:
        raise click.ClickException(f"Failed to export to Google Calendar: {e}")

    click.echo(f"🎉 Exported {event_count} events to Google Calendar!")
    click.echo(f"\n   📅 Calendar: {trip.name} — WanderlogPro")
    click.echo("   🔗 View at https://calendar.google.com")

    for day in trip.days:
        timed = sum(1 for item in day.items if item.start_time)
        click.echo(
            f"   📆 {day.date} — {len(day.items)} items "
            f"({timed} with specific times)"
        )


@main.command(name="all")
@click.argument("trip_url")
@click.option(
    "--output", "-o",
    default=None,
    help="Output KML file path. Defaults to <trip-name>.kml",
)
@click.option(
    "--cookie", "-c",
    default=None,
    help="Session cookie for private trips (from browser DevTools).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview calendar events in a week-view HTML page without creating them.",
)
def export_all(
    trip_url: str,
    output: str | None,
    cookie: str | None,
    dry_run: bool,
) -> None:
    """Export a Wanderlog trip to both KML and Google Calendar."""
    from wanderlogpro.calendar_export.scraper import fetch_itinerary
    from wanderlogpro.calendar_export.gcal_export import export_trip_to_gcal, preview_trip_events

    # --- Map export ---
    click.echo("🗺️  Fetching trip from Wanderlog...")
    try:
        map_trip = fetch_trip(trip_url, cookie=cookie)
    except (ValueError, PermissionError) as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to fetch trip: {e}")

    total_places = sum(len(pl.places) for pl in map_trip.place_lists)
    click.echo(f"✅ Found trip: {map_trip.name}")
    click.echo(f"   {len(map_trip.place_lists)} lists, {total_places} places")

    if total_places:
        if output is None:
            safe_name = re.sub(r'[^\w\s-]', '', map_trip.name).strip().replace(' ', '-').lower()
            output = f"{safe_name or map_trip.id}.kml"
        output_path = Path(output)
        click.echo("📝 Generating KML with styled layers...")
        export_trip_to_kml(map_trip, output_path)
        click.echo(f"🎉 KML exported to {output_path}")
    else:
        click.echo("⚠️  No places found — skipping KML export.")

    # --- Calendar export ---
    click.echo("\n🗺️  Fetching itinerary from Wanderlog...")
    try:
        cal_trip = fetch_itinerary(trip_url, cookie=cookie)
    except (ValueError, PermissionError) as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Failed to fetch itinerary: {e}")

    total_items = sum(len(day.items) for day in cal_trip.days)
    if not total_items:
        click.echo("⚠️  No itinerary items found — skipping calendar export.")
        return

    click.echo(f"   {len(cal_trip.days)} days, {total_items} itinerary items")

    if dry_run:
        from wanderlogpro.calendar_export.preview import open_preview

        click.echo("🔍 Generating dry-run preview...")
        day_events = preview_trip_events(cal_trip)
        path = open_preview(cal_trip.name, day_events, cal_trip.timezone)
        total_events = sum(len(evts) for _, evts in day_events)
        click.echo(f"📄 Preview opened in browser ({total_events} events)")
        click.echo(f"   File: {path}")
        return

    click.echo("📅 Signing in to Google Calendar...")

    try:
        calendar_id, event_count = export_trip_to_gcal(cal_trip)
    except Exception as e:
        raise click.ClickException(f"Failed to export to Google Calendar: {e}")

    click.echo(f"🎉 Exported {event_count} events to Google Calendar!")
    click.echo(f"\n   📅 Calendar: {cal_trip.name} — WanderlogPro")
    click.echo("   🔗 View at https://calendar.google.com")


if __name__ == "__main__":
    main()
