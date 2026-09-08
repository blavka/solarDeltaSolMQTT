#!/usr/bin/env python3
"""Stable Home Assistant alarm state for Hermes monitor-mode cron jobs.

This script emits only semantic state changes, so scheduler hashing starts an
agent on an overtemperature event, recovery, Matter-outlet outage, or recovery
rather than every time a temperature sample changes.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENV_FILE = Path(os.environ.get("SOLAR_ALERT_ENV_FILE", Path.home() / ".hermes/.env"))
STATE_FILE = Path(os.environ.get("SOLAR_ALERT_MONITOR_STATE_FILE", Path.home() / ".local/state/solar-collector-monitor.json"))


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value.strip().strip("'\""))


def get_state(url: str, token: str, entity_id: str) -> str:
    request = Request(
        f"{url.rstrip('/')}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return str(json.loads(response.read())["state"])
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        raise RuntimeError(type(exc).__name__) from exc


def read_solar_state() -> str:
    try:
        value = json.loads(STATE_FILE.read_text()).get("solar")
        return value if value in {"active", "clear"} else "clear"
    except (OSError, ValueError, json.JSONDecodeError):
        return "clear"


def write_solar_state(value: str) -> None:
    STATE_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=STATE_FILE.parent, delete=False) as tmp:
        json.dump({"solar": value}, tmp)
        tmp.write("\n")
        tmp.flush()
        os.fchmod(tmp.fileno(), 0o600)
        temporary = Path(tmp.name)
    temporary.replace(STATE_FILE)


def main() -> int:
    load_dotenv(ENV_FILE)
    url = os.environ.get("HOMEASSISTANT_URL")
    token = os.environ.get("HOMEASSISTANT_TOKEN")
    if not url or not token:
        print("solar=invalid matter=unknown")
        return 0

    collector = os.environ.get("SOLAR_ALERT_ENTITY", "sensor.deltasol_collector_temperature")
    trigger = float(os.environ.get("SOLAR_ALERT_TRIGGER_C", "90"))
    rearm = float(os.environ.get("SOLAR_ALERT_REARM_C", "89"))
    outlets = [x.strip() for x in os.environ.get("SOLAR_ALERT_MATTER_ENTITIES", "switch.zasuvka_01,switch.zasuvka_02").split(",") if x.strip()]
    try:
        temperature = float(get_state(url, token, collector))
        prior = read_solar_state()
        solar = "active" if temperature > trigger else "clear" if temperature <= rearm else prior
        write_solar_state(solar)
        outlet_states = [get_state(url, token, entity) for entity in outlets]
        matter = "unavailable" if any(state in {"unavailable", "unknown"} for state in outlet_states) else "ok"
        print(f"solar={solar} matter={matter}")
    except (RuntimeError, ValueError, OSError):
        print("solar=invalid matter=unknown")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
