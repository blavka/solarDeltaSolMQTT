# Solar controller DeltaSol® BS series MQTT

[![Tests](https://github.com/blavka/solarDeltaSolMQTT/actions/workflows/test.yml/badge.svg?branch=master)](https://github.com/blavka/solarDeltaSolMQTT/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/release/blavka/solarDeltaSolMQTT.svg)](https://github.com/blavka/solarDeltaSolMQTT/releases)
[![License](https://img.shields.io/github/license/blavka/solarDeltaSolMQTT.svg)](https://github.com/blavka/solarDeltaSolMQTT/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/solarDeltaSolMQTT.svg)](https://pypi.org/project/solarDeltaSolMQTT)

## Installing

Requires Python 3.10 or newer. Until the next PyPI release, install from a checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
```

## Config

Insert this snippet to the file /etc/solarDeltaSolMQTT.yml:

```yml
---
solar:
  device: /dev/ttyUSB1
mqtt:
  host: 127.0.0.1
  port: 1883
  prefix: solar
publish:
  S1: collector/temperature
  S2: boiler-bottom/temperature
  S3: boiler-top/temperature
  S4: return/temperature
  SpeedRelay1: pump/speed
  Errormask: true
```

## Usage

Update /etc/solarDeltaSolMQTT.yml and run

```sh
solarDeltaSolMQTT -c /etc/solarDeltaSolMQTT.yml
```

## Home Assistant MQTT Discovery

Set `home_assistant.enabled: true` in the local configuration. The service retains discovery configuration under `homeassistant/.../config` and retains its state messages. Home Assistant consumes the existing `solar/...` telemetry state topics; no parallel Home Assistant-only temperature topics are created.

Published entities are four temperature sensors, two relay-speed sensors, and two read-only relay-state binary sensors. The latter are derived from bits 0 and 1 of the controller `Relaymask`; the raw mask is not exposed as an HA entity. Availability is published to `solar/availability` and has an MQTT last-will of `offline`.


## Overtemperature e-mail alert

`scripts/solar_collector_overtemperature_alert.py` is an optional, dependency-free watchdog for a Home Assistant installation. It reads a Home Assistant entity through the REST API and sends one e-mail per temperature excursion with the locally configured Himalaya account. It is intentionally separate from the telemetry container, so DeltaSol collection remains read-only and continues if e-mail delivery fails.

Required environment variables:

```sh
HOMEASSISTANT_URL=http://homeassistant.local:8123
HOMEASSISTANT_TOKEN=<long-lived-access-token>
SOLAR_ALERT_RECIPIENT=operator@example.invalid
```

Optional variables: `SOLAR_ALERT_ENTITY` (default `sensor.deltasol_collector_temperature`), `SOLAR_ALERT_TRIGGER_C` (default `90`), `SOLAR_ALERT_REARM_C` (default `89`), `SOLAR_ALERT_HIMALAYA_ACCOUNT` (default `hermes_gmail`), and `SOLAR_ALERT_STATE_FILE`. The state file suppresses duplicate e-mails while the temperature remains over the threshold; the alert is rearmed at or below the rearm temperature. Run it once per minute from a systemd timer or cron.


For a supervisor that should invoke an external agent only on meaningful changes, use `scripts/solar_collector_alarm_monitor.py` instead. It emits a stable `solar=<clear|active|unavailable> matter=<ok|unavailable|unknown>` line and deliberately does not send e-mail itself. A hash-based scheduler can use that output to launch an agent only when a high-temperature condition, Home Assistant telemetry failure, or configured Matter-outlet availability changes. Set `SOLAR_ALERT_MATTER_ENTITIES` to a comma-separated list of critical HA switches; it defaults to `switch.zasuvka_01,switch.zasuvka_02`.

## Docker deployment

Docker Compose is the supported deployment method. It uses host networking solely to reach the local Mosquitto listener on `127.0.0.1:1883`; it does not expose a service port. The controller is mapped by stable USB identifier rather than a volatile `/dev/ttyUSB<n>` name.

```sh
cp config/config.example.yaml config/local.yaml
sudo chown root:10002 config/local.yaml
sudo chmod 640 config/local.yaml
DIALOUT_GID=$(getent group dialout | cut -d: -f3)
printf 'DIALOUT_GID=%s\n' "$DIALOUT_GID" > .env
docker compose up -d --build
```

The container is deliberately restricted: it runs as an unprivileged user, has no Linux capabilities, uses a read-only filesystem, and receives only the DeltaSol USB serial device. It reads VBus traffic; it does not send controller commands.

Check the running service with:

```sh
docker compose ps
docker compose logs -f solar-deltasol-mqtt
```

## Development

```sh
git clone git@github.com:blavka/solarDeltaSolMQTT.git
cd solarDeltaSolMQTT
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```
