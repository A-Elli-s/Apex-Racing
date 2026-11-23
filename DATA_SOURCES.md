# Racing data: sources, automation and licensing

Every series below is refreshed by `.github/workflows/schedule-dev-racing-bots.yml`
(daily gate; runs on Mondays, within two days after any listed race, and whenever an
automatically refreshable series is behind the calendar). Bots write to `dev`;
promotion to `main` stays a manual pull request.

`python scripts/check_freshness.py` reports which snapshots predate a completed round.
The workflow opens a `racing-data` issue listing anything the bots could not refresh.

## Refresh path per series

| Series | Standings source | Refresh |
|---|---|---|
| F1 | Jolpica API (CC BY-NC-SA, see licensing) | automatic |
| F2, F3 | Wikipedia (CC BY-SA 4.0) | automatic |
| MotoGP, Moto2, Moto3 | Wikipedia (CC BY-SA 4.0) | automatic |
| WEC, WRC | FIA standings pages | automatic |
| Formula E | FIA standings pages | automatic |
| IndyCar, IMSA, Supercross, Pro Motocross, MXGP | official standings pages (HTML) | automatic |
| NASCAR Cup, O’Reilly, Trucks | nascar.com blocks automated access | manual after each round |
| Monster Jam | official page blocks automated access | manual after each round |
| NHRA, Supercars, WorldSBK | rights pending | link only, no bot |

Calendars: `scripts/update_schedules.py` (twice daily) from Jolpica for F1, the community
`moto-db` dataset for most others, plus `data/sources.json`.

## Free APIs evaluated (2026-11-15)

| API | Covers | Verdict |
|---|---|---|
| OpenF1 | F1 only; free historical data from 2023, real-time is paid; terms not stated | possible F1 cross-check, not a multi-series source |
| API-Sports | 100 requests/day on the free plan; free-plan coverage unclear | not enough for 20+ series |
| TheSportsDB | free key; league tables limited to soccer | not usable for standings |
| Sportmonks | F1 only, paid | no |
| `motorsport-calendar` (MIT) | calendars for 16 series via public sources | calendar reference only |

No single free source covers all series with standings, so each series uses its best
available source above.

## Licensing (decide before relying on this commercially)

The site carries an Amazon Associates tag. `data/quality/source-permissions-2026.json`
records that Jolpica data is CC BY-NC-SA (commercial use needs permission), NHRA forbids
automated collection, and Supercars/organizer terms reserve content. These are not
cleared; `commercial_reuse_cleared` stays false until they are.
