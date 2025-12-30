# netatmo-energy

A simple Python SDK for the Netatmo Energy API (thermostats).

## Setup

1. Create an app at [dev.netatmo.com](https://dev.netatmo.com) to get your API credentials
2. Create a `.env` file:
```
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
ACCESS_TOKEN=your_access_token
REFRESH_TOKEN=your_refresh_token
```

## Usage

```python
from netatmo import Thermostat

t = Thermostat()
homes = t.homesdata()
home_id = homes.homes[0].id

# Get current status
t.room_temperatures(home_id)

# Set room to 20°C for 1 hour
t.setroomthermpoint(home_id, room_id, mode='manual', temp=20, endtime=int(time())+3600)

# Get temperature history
t.getroommeasure(home_id, room_id)
```

## Methods

- `homesdata()` — get homes and topology
- `homestatus(home_id)` — current device status
- `room_temperatures(home_id)` — quick view of all room temps
- `getroommeasure(home_id, room_id, ...)` — temperature history
- `setroomthermpoint(home_id, room_id, mode, ...)` — set room temperature
- `setthermmode(home_id, mode)` — set home mode (schedule/away/hg)
- `getmeasure(device_id, ...)` — boiler history
- `createnewhomeschedule(...)` — create weekly schedule
- `synchomeschedule(...)` — modify schedule
- `switchhomeschedule(home_id, schedule_id)` — activate schedule

## Background

Inspired by [Andrej Karpathy's tweet](https://x.com/karpathy) about using Claude Code for home automation. Instead of burning tokens on network scanning, this takes the "boring" approach: read the docs, write a simple SDK.
