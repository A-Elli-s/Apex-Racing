"""Conservative currency checks for standings snapshots against calendar dates.

A scheduled date is not proof a race ran; this audit only flags snapshots that
might predate a championship round. Passing it does not verify any points.
"""
import datetime as dt


def snapshot_freshness(snapshot, events, as_of=None):
    as_of = as_of or dt.datetime.now(dt.timezone.utc).date()
    if not isinstance(snapshot, dict):
        return {"status": "missing_snapshot"}
    timestamp = snapshot.get("retrieved_at")
    if not isinstance(timestamp, str) or not timestamp.strip():
        return {"status": "retrieval_timestamp_missing"}
    try:
        retrieved = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if retrieved.tzinfo is None or retrieved.utcoffset() is None:
            raise ValueError("Timestamp must contain a timezone")
        retrieved_day = retrieved.astimezone(dt.timezone.utc).date()
    except (ValueError, TypeError, OverflowError):
        return {"status": "invalid_retrieval_timestamp"}

    dates = []
    for event in events:
        if not isinstance(event, dict):
            continue
        try:
            day = dt.date.fromisoformat(str(event.get("date", "")))
        except (TypeError, ValueError):
            continue
        if day <= as_of:
            dates.append(day)
    if not dates:
        return {"status": "no_elapsed_calendar_round_to_compare",
                "retrieved_utc_date": retrieved_day.isoformat()}
    latest = max(dates)
    if latest > retrieved_day:
        status = "potentially_stale_after_scheduled_round"
    elif latest == retrieved_day:
        status = "same_day_timing_requires_review"
    else:
        status = "no_later_scheduled_round"
    return {"status": status, "retrieved_utc_date": retrieved_day.isoformat(),
            "latest_scheduled_round_date": latest.isoformat(),
            "note": "Calendar dates do not confirm an event ran or results were published."}
