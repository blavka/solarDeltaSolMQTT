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

## Docker deployment

Docker Compose is the supported deployment method. It uses host networking solely to reach the local Mosquitto listener on `127.0.0.1:1883`; it does not expose a service port. The controller is mapped by stable USB identifier rather than a volatile `/dev/ttyUSB<n>` name.

```sh
cp config/config.example.yaml config/local.yaml
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
