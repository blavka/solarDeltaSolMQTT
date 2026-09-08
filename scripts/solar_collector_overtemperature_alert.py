#!/usr/bin/env python3
"""Send one e-mail per Home Assistant solar collector overtemperature event.

Configuration is read from the environment, optionally supplemented by a dotenv
file.  Secrets are never logged.  The script is suitable for a systemd timer
or any cron runner.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENTITY_ID = os.environ.get("SOLAR_ALERT_ENTITY", "sensor.deltasol_collector_temperature")
TRIGGER_C = float(os.environ.get("SOLAR_ALERT_TRIGGER_C", "90"))
REARM_C = float(os.environ.get("SOLAR_ALERT_REARM_C", "89"))
RECIPIENT = os.environ.get("SOLAR_ALERT_RECIPIENT", "")
ACCOUNT = os.environ.get("SOLAR_ALERT_HIMALAYA_ACCOUNT", "hermes_gmail")
STATE_FILE = Path(os.environ.get("SOLAR_ALERT_STATE_FILE", Path.home() / ".local/state/solar-collector-alert.json"))
ENV_FILE = Path(os.environ.get("SOLAR_ALERT_ENV_FILE", Path.home() / ".hermes/.env"))


def load_dotenv(path: Path) -> None:
    """Load only missing KEY=VALUE entries; do not print their values."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("'\"")


def read_state(path: Path) -> str:
    try:
        value = json.loads(path.read_text()).get("state")
        return value if value in {"active", "clear"} else "clear"
    except (OSError, ValueError, json.JSONDecodeError):
        return "clear"


def write_state(path: Path, state: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as tmp:
        json.dump({"state": state}, tmp)
        tmp.write("\n")
        tmp.flush()
        os.fchmod(tmp.fileno(), 0o600)
        temporary = Path(tmp.name)
    temporary.replace(path)


def get_temperature(url: str, token: str, entity_id: str) -> float:
    request = Request(
        f"{url.rstrip('/')}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Home Assistant state request failed: {type(exc).__name__}") from exc
    try:
        return float(payload["state"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Home Assistant temperature state is not numeric") from exc


def send_email(temperature: float) -> None:
    now = datetime.now(ZoneInfo("Europe/Prague")).isoformat(timespec="seconds")
    message = (
        f"From: Hermes Alert <{os.environ.get('EMAIL_ADDRESS', 'hermes.blavka@gmail.com')}>\n"
        f"To: {RECIPIENT}\n"
        "Subject: VAROVÁNÍ: solární kolektor nad 90 °C\n\n"
        f"Automatické upozornění Home Assistantu: teplota solárního kolektoru je {temperature:.1f} °C.\n"
        f"Čas kontroly: {now}\n"
    )
    subprocess.run(
        ["himalaya", "--account", ACCOUNT, "template", "send"],
        input=message,
        text=True,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )


def decide(previous: str, temperature: float) -> tuple[str, bool]:
    if temperature > TRIGGER_C:
        return "active", previous != "active"
    if temperature <= REARM_C:
        return "clear", False
    return previous, False


def main() -> int:
    global ENTITY_ID, TRIGGER_C, REARM_C, RECIPIENT, ACCOUNT, STATE_FILE
    load_dotenv(ENV_FILE)
    ENTITY_ID = os.environ.get("SOLAR_ALERT_ENTITY", "sensor.deltasol_collector_temperature")
    TRIGGER_C = float(os.environ.get("SOLAR_ALERT_TRIGGER_C", "90"))
    REARM_C = float(os.environ.get("SOLAR_ALERT_REARM_C", "89"))
    RECIPIENT = os.environ.get("SOLAR_ALERT_RECIPIENT", "")
    ACCOUNT = os.environ.get("SOLAR_ALERT_HIMALAYA_ACCOUNT", "hermes_gmail")
    STATE_FILE = Path(os.environ.get("SOLAR_ALERT_STATE_FILE", Path.home() / ".local/state/solar-collector-alert.json"))
    url = os.environ.get("HOMEASSISTANT_URL")
    token = os.environ.get("HOMEASSISTANT_TOKEN")
    if not url or not token or not RECIPIENT:
        print("solar_alert=configuration_error", file=sys.stderr)
        return 2
    try:
        temperature = get_temperature(url, token, ENTITY_ID)
        previous = read_state(STATE_FILE)
        state, should_send = decide(previous, temperature)
        if should_send:
            send_email(temperature)
        write_state(STATE_FILE, state)
        print(f"solar_alert={state} temperature={temperature:.1f}")
        return 0
    except (RuntimeError, subprocess.SubprocessError, OSError) as exc:
        print(f"solar_alert=error reason={type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
