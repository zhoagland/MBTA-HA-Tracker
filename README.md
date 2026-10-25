# MBTA Next Train (Home Assistant)

Shows the next MBTA train leaving a stop. Defaults to the **Orange Line, Malden Center → Forest Hills**.

## Install
1. Copy `custom_components/mbta_next_train` into your Home Assistant `config/custom_components/` folder.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **MBTA Next Train**. Accept the defaults.

Optional: get a free API key at https://api-v3.mbta.com to raise the rate limit (not needed for one stop polled every 30s).

## Sensors
- `sensor.malden_center_to_forest_hills_next_departure` — departure time (shows "in 4 minutes"). Attributes: `headsign`, `status`, `source` (`prediction` or `schedule`), `upcoming` (next 5).
- `sensor.malden_center_to_forest_hills_minutes_away` — minutes until departure.

## Dashboard card
```yaml
type: entities
title: Orange Line → Forest Hills
entities:
  - entity: sensor.malden_center_to_forest_hills_next_departure
    name: Next train
  - entity: sensor.malden_center_to_forest_hills_minutes_away
    name: Minutes
```

Other stops: use any stop ID from `https://api-v3.mbta.com/stops?filter[route]=Orange`.
