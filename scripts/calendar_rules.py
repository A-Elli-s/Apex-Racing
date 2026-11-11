"""Season-aware selection of championship rounds for coverage audits.

The public calendar can include exhibitions, qualifying events, and another
season's opening round. Those entries must not count toward the completed
championship rounds needed for full race-classification verification.
"""
import datetime as dt

# Non-points events in the 2026 NASCAR Cup public schedule. The two Daytona
# Duels are separate qualifying races, not championship points rounds.
NASCAR_CUP_NON_POINTS_2026 = (
    "cook out clash at bowman gray",
    "america 250 florida duel at daytona",
    "nascar all-star race",
)


def championship_round(series, event, year):
    """Whether an event belongs to the requested points championship season.

    This is a conservative structural filter, not independent confirmation of
    the organizer's complete schedule or any particular event's result.
    """
    if not isinstance(event, dict):
        return False
    try:
        date = dt.date.fromisoformat(str(event.get("date", "")))
    except (TypeError, ValueError):
        return False

    label = str(event.get("season", "")).strip()
    if series == "Formula E":
        # FIA Formula E 2025/26 spans two calendar years. In particular, the
        # December 2026 opener of 2026/27 must not be counted as a 2025/26 race.
        if label and label not in ("2025/26", "2025-26", "2025-2026", str(year)):
            return False
        if not (dt.date(year - 1, 12, 1) <= date < dt.date(year, 12, 1)):
            return False
    elif date.year != year or (label and label not in (str(year),)):
        return False

    if series == "NASCAR Cup" and year == 2026:
        name = str(event.get("name", "")).lower().removeprefix("cup —").strip()
        if any(term in name for term in NASCAR_CUP_NON_POINTS_2026):
            return False
    return True


def championship_events(series, events, year):
    """Return only championship-round events, retaining source ordering."""
    return [e for e in events if championship_round(series, e, year)]
