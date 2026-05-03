# VBB Routes for Home Assistant

Custom Home Assistant integration for VBB/BVG route planning via `v6.vbb.transport.rest`.

## Features

- Shows the next VBB/BVG routes as Home Assistant sensor entities
- Supports origin by address and coordinates
- Supports destination by VBB stop ID
- Filters by minimum departure offset
- Filters by maximum transfers
- Creates one sensor per route
- Exposes legs, line colours, delay, transfer station and duration as attributes
- Keeps the last successful result as fallback if the VBB API is temporarily unavailable

## Installation via HACS

1. Open HACS.
2. Open the three-dot menu.
3. Select **Custom repositories**.
4. Add this repository URL:

   ```text
   https://github.com/nashsmartdom/ha-vbb-routes
   ```

5. Select category **Integration**.
6. Install **VBB Routes**.
7. Restart Home Assistant.
8. Go to **Settings → Devices & services → Add integration**.
9. Search for **VBB Routes**.

## Example configuration

For Karl-Marx-Allee 72 → S+U Pankow:

- Origin name: `Karl-Marx-Allee 72`
- Origin address: `Karl-Marx-Allee 72, 10243 Berlin`
- Origin latitude: `52.517481`
- Origin longitude: `13.436806`
- Destination stop ID: `900130002`
- Destination name: `S+U Pankow`
- Minimum departure offset: `7`
- Maximum transfers: `1`
- Raw results: `8`
- Number of route sensors: `3`
- Update interval: `60`

## Entities

The integration creates sensors like:

```text
sensor.vbb_pankow_route_1
sensor.vbb_pankow_route_2
sensor.vbb_pankow_route_3
```

The sensor state is the recommended leave-home time.

Attributes include:

- `arrival`
- `duration_min`
- `minutes_until_leave`
- `transfers`
- `change_at`
- `max_delay_min`
- `legs`
- `api_ok`
- `served_from_cache`

## Notes

The integration runs locally inside Home Assistant, but it still needs internet access to query VBB route data.

Data source: <https://v6.vbb.transport.rest>
